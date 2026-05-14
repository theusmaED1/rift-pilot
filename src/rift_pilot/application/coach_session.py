"""Orquestrador do loop principal: lê o estado da partida e dispara avisos."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from rift_pilot.application.build_loader import BuildLoader
from rift_pilot.application.session_options import SessionOptions
from rift_pilot.domain.detectors.build_announcer import build_announcement_event
from rift_pilot.domain.detectors.event_detector import EventDetector
from rift_pilot.domain.detectors.next_item_detector import NextItemDetector
from rift_pilot.domain.detectors.minimap_reminder_detector import MinimapReminderDetector
from rift_pilot.domain.detectors.trinket_reminder_detector import TrinketReminderDetector
from rift_pilot.domain.detectors.objective_detector import ObjectiveDetector
from rift_pilot.domain.detectors.skill_point_detector import SkillPointDetector
from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.entities.game_state import GameState
from rift_pilot.domain.entities.recommended_build import RecommendedBuild
from rift_pilot.domain.entities.state_diff import StateDiff
from rift_pilot.domain.ports.game_data_source import (
    GameDataSource,
    GameDataSourceUnavailable,
    GameLoading,
)
from rift_pilot.domain.ports.speech_queue import SpeechQueue
from rift_pilot.domain.role_inference import resolve_position_for_build_lookup
from rift_pilot.settings.constants import EventTags, Network
from rift_pilot.settings.messages import LogMessages


class SessionStatus(Enum):
    CONNECTING = auto()
    WAITING_FOR_GAME = auto()
    LOADING_SCREEN = auto()
    MONITORING = auto()
    GAME_ENDED = auto()


@dataclass(frozen=True)
class SessionCallbacks:
    """Hooks que a UI/CLI conecta na sessão para receber atualizações."""

    on_status_change: Callable[[SessionStatus], None]
    on_log_message: Callable[[str], None]
    on_build_loaded: Callable[[RecommendedBuild], None]


class CoachSession:
    """Loop principal do coach.

    Polla o `GameDataSource`, monta um `StateDiff`, roda os detectores
    habilitados e enfileira os eventos resultantes na `SpeechQueue`.
    """

    def __init__(
        self,
        data_source: GameDataSource,
        speech_queue: SpeechQueue,
        build_loader: BuildLoader,
        options: SessionOptions,
        callbacks: SessionCallbacks,
        poll_interval_seconds: float,
        warn_offsets_seconds: tuple[int, ...] | None = None,
    ) -> None:
        self._data_source = data_source
        self._speech_queue = speech_queue
        self._build_loader = build_loader
        self._options = options
        self._callbacks = callbacks
        self._poll_interval_seconds = poll_interval_seconds
        self._warn_offsets_seconds = warn_offsets_seconds

        self._skill_detector: SkillPointDetector | None = None
        self._next_item_detector: NextItemDetector | None = None
        self._next_item_lock = threading.Lock()
        self._pending_build: RecommendedBuild | None = None
        self._pending_build_lock = threading.Lock()
        self._game_started = False
        self._detectors_unlocked = False

    def run(self, stop_signal: threading.Event) -> None:
        detectors = self._build_detectors()

        previous_state: GameState | None = None
        consecutive_failures = 0
        is_connected = False
        loading_screen_signaled = False
        build_fetch_requested = False
        unlock_deadline: float | None = None

        while not stop_signal.is_set():
            try:
                payload = self._data_source.get_all_data()
            except GameLoading:
                consecutive_failures = 0
                if not loading_screen_signaled:
                    loading_screen_signaled = True
                    self._callbacks.on_log_message(LogMessages.LOADING_SCREEN_DETECTED)
                    self._callbacks.on_status_change(SessionStatus.LOADING_SCREEN)
                time.sleep(self._poll_interval_seconds)
                continue
            except GameDataSourceUnavailable:
                consecutive_failures += 1
                if (
                    is_connected
                    and consecutive_failures >= Network.MAX_CONSECUTIVE_API_FAILURES
                ):
                    self._callbacks.on_log_message(LogMessages.GAME_ENDED)
                    self._callbacks.on_status_change(SessionStatus.GAME_ENDED)
                    break
                if not is_connected:
                    self._callbacks.on_status_change(SessionStatus.WAITING_FOR_GAME)
                time.sleep(self._poll_interval_seconds)
                continue

            if not is_connected:
                is_connected = True
                consecutive_failures = 0
                self._callbacks.on_log_message(LogMessages.GAME_CONNECTED)

            consecutive_failures = 0
            current_state = GameState.from_live_api(payload)

            if not build_fetch_requested and current_state.champion_name:
                build_fetch_requested = True
                resolved_position = resolve_position_for_build_lookup(
                    current_state.position, current_state.has_smite
                )
                self._build_loader.fetch_in_background(
                    champion_name=current_state.champion_name,
                    position=resolved_position,
                    on_build_loaded=self._handle_build_loaded,
                    on_log=self._callbacks.on_log_message,
                    skill_detector=self._skill_detector,
                    next_item_detector_setter=self._install_next_item_detector
                    if self._options.next_item
                    else None,
                )

            if not self._game_started:
                self._game_started = True
                self._callbacks.on_status_change(SessionStatus.MONITORING)
                unlock_deadline = current_state.game_time_seconds + 10.0
                with self._pending_build_lock:
                    if self._pending_build is not None:
                        if self._options.build_announce and self._pending_build.is_complete:
                            event = build_announcement_event(self._pending_build)
                            self._speech_queue.enqueue([event])
                        self._detectors_unlocked = True

            if not self._detectors_unlocked:
                if unlock_deadline and current_state.game_time_seconds >= unlock_deadline:
                    self._detectors_unlocked = True

            if previous_state is not None and self._detectors_unlocked:
                self._process_tick(previous_state, current_state, detectors)

            previous_state = current_state
            time.sleep(self._poll_interval_seconds)

        self._speech_queue.clear()
        self._data_source.close()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_detectors(self) -> list[EventDetector]:
        detectors: list[EventDetector] = []
        if self._options.skill_points:
            self._skill_detector = SkillPointDetector()
            detectors.append(self._skill_detector)
        if self._options.objectives:
            detectors.append(
                ObjectiveDetector(warn_offsets_seconds=self._warn_offsets_seconds)
            )
        if self._options.minimap:
            detectors.append(MinimapReminderDetector())
        if self._options.trinket:
            detectors.append(TrinketReminderDetector())
        return detectors

    def _process_tick(
        self,
        previous_state: GameState,
        current_state: GameState,
        detectors: list[EventDetector],
    ) -> None:
        diff = StateDiff(previous=previous_state, current=current_state)

        if diff.available_skill_points == 0:
            self._speech_queue.cancel_by_tag(EventTags.SKILL)
        if diff.items_changed:
            self._speech_queue.cancel_by_tag(EventTags.NEXT_ITEM)

        coach_events: list[CoachEvent] = []
        for detector in detectors:
            coach_events.extend(detector.detect(diff))

        with self._next_item_lock:
            if self._next_item_detector is not None:
                coach_events.extend(self._next_item_detector.detect(diff))

        if not coach_events:
            return

        coach_events.sort(key=lambda ev: ev.priority, reverse=True)
        for event in coach_events:
            self._callbacks.on_log_message(
                LogMessages.coach_event(current_state.game_time_seconds, event.message)
            )
        self._speech_queue.enqueue(coach_events)

    def _install_next_item_detector(self, detector: NextItemDetector) -> None:
        with self._next_item_lock:
            self._next_item_detector = detector

    def _handle_build_loaded(self, build: RecommendedBuild) -> None:
        self._callbacks.on_build_loaded(build)
        with self._pending_build_lock:
            if not self._game_started:
                self._pending_build = build
                return
            if self._options.build_announce and build.is_complete:
                event = build_announcement_event(build)
                self._speech_queue.enqueue([event])
            self._detectors_unlocked = True
