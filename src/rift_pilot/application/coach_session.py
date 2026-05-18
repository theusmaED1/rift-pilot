"""Orquestrador do loop principal: lê o estado da partida e dispara avisos."""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

from rift_pilot.application.build_loader import BuildLoader
from rift_pilot.application.session_options import SessionOptions
from rift_pilot.domain.detectors.build_announcer import build_announcement_event
from rift_pilot.domain.detectors.event_detector import EventDetector
from rift_pilot.domain.detectors.farm_detector import FarmDetector
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
from rift_pilot.settings.constants import EventPriority, EventTags, Network
from rift_pilot.settings.messages import LogMessages, TTSMessages


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
        token_logger: Any | None = None,
        message_provider: Any | None = None,
    ) -> None:
        self._data_source = data_source
        self._speech_queue = speech_queue
        self._build_loader = build_loader
        self._options = options
        self._callbacks = callbacks
        self._poll_interval_seconds = poll_interval_seconds
        self._warn_offsets_seconds = warn_offsets_seconds
        self._token_logger = token_logger
        self._message_provider = message_provider

        self._skill_detector: SkillPointDetector | None = None
        self._next_item_detector: NextItemDetector | None = None
        self._next_item_lock = threading.Lock()
        self._pending_build: RecommendedBuild | None = None
        self._pending_build_lock = threading.Lock()
        self._current_build: RecommendedBuild | None = None
        self._quest_announced = False
        self._game_started = False
        self._detectors_unlocked = False

        # Game recording for analysis
        self._recordings_dir = Path("recordings")
        self._recordings_dir.mkdir(exist_ok=True)
        self._log_file: Any = None
        self._log_path: Path | None = None

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
                current_state = GameState.from_live_api(payload)
                self._log_game_tick(payload)
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

            # Sempre resolver a posição (inferindo por exclusão se a Live API
            # retorna NONE para o active player mas preenche aliados).
            resolved_position = resolve_position_for_build_lookup(
                current_state.position,
                current_state.has_smite,
                team_positions=current_state.all_player_positions,
            )

            if not build_fetch_requested and current_state.champion_name:
                build_fetch_requested = True

                # Injetar dados de inimigos para modo IA
                if self._options.use_ai_build:
                    lane_enemy = self._extract_lane_enemy(
                        payload, current_state, resolved_position
                    )
                    full_comp = self._extract_enemy_comp(payload, current_state)
                    self._build_loader.inject_enemies(lane_enemy, full_comp)
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
                logger.info(f"[CoachSession] Game iniciado! champion={current_state.champion_name}, position={current_state.position}")
                self._game_started = True
                self._callbacks.on_status_change(SessionStatus.MONITORING)
                unlock_deadline = current_state.game_time_seconds + 10.0
                self._init_game_recording()

                # Anunciar início do Rift Pilot
                startup_events: list[CoachEvent] = [
                    CoachEvent(
                        message="Rift Pilot pronto!",
                        priority=EventPriority.BUILD_ANNOUNCE,
                    )
                ]

                # Anunciar campeão e lane (usa a posição resolvida).
                champion_name = current_state.champion_name or "Campeão desconhecido"
                champion_msg = f"Jogando de {champion_name}"
                announce_position = resolved_position or current_state.position
                if announce_position and announce_position != "NONE":
                    champion_msg += f" na {self._position_name(announce_position)}"
                startup_events.append(
                    CoachEvent(
                        message=champion_msg,
                        priority=EventPriority.BUILD_ANNOUNCE,
                    )
                )

                with self._pending_build_lock:
                    if self._pending_build is not None:
                        logger.info(f"[CoachSession] Pending build encontrada: {self._pending_build.champion}")
                        if self._pending_build.starter_items:
                            starter_msg = f"Starter: {', '.join(self._pending_build.starter_items)}"
                            logger.info(f"[CoachSession] Adicionando starter announcement: {starter_msg}")
                            startup_events.append(
                                CoachEvent(
                                    message=starter_msg,
                                    priority=EventPriority.BUILD_ANNOUNCE,
                                )
                            )
                        if self._options.build_announce and self._pending_build.is_complete:
                            logger.info(f"[CoachSession] Build complete, anunciando build announcement")
                            event = build_announcement_event(self._pending_build)
                            startup_events.append(event)
                        self._detectors_unlocked = True
                    else:
                        # Build ainda não chegou da IA — anúncio sairá em
                        # _handle_build_loaded quando ela chegar. Não enfileira
                        # mensagem de "carregando" para não ocupar a fila de fala.
                        logger.info(
                            "[CoachSession] Build ainda em andamento — anúncio "
                            "sairá quando _handle_build_loaded for chamado"
                        )

                logger.info(f"[CoachSession] Enfileirando {len(startup_events)} startup events")
                self._speech_queue.enqueue(startup_events)

            if not self._detectors_unlocked:
                if unlock_deadline and current_state.game_time_seconds >= unlock_deadline:
                    self._detectors_unlocked = True

            if previous_state is not None and self._detectors_unlocked:
                self._process_tick(previous_state, current_state, detectors)

            previous_state = current_state
            time.sleep(self._poll_interval_seconds)

        self._speech_queue.clear()
        self._data_source.close()
        self._close_game_recording()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _init_game_recording(self) -> None:
        """Initialize game recording file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = self._recordings_dir / f"game_{timestamp}.jsonl"
        self._log_file = self._log_path.open("w", encoding="utf-8")
        if self._token_logger is not None:
            try:
                self._token_logger.start_game(timestamp)
            except Exception as e:
                logger.warning(f"[CoachSession] Falha ao iniciar TokenLogger: {e}")

    def _log_game_tick(self, payload: dict[str, Any]) -> None:
        """Log a single game tick."""
        if self._log_file is None:
            return
        try:
            self._log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._log_file.flush()
        except Exception:
            pass

    def _close_game_recording(self) -> None:
        """Close the game recording file."""
        if self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass
        if self._token_logger is not None:
            try:
                self._token_logger.end_game()
            except Exception:
                pass

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
        if self._options.farm:
            detectors.append(
                FarmDetector(
                    tone=self._options.tone,
                    mode=self._options.mode,
                )
            )
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
            self._check_quest_completion(diff)
        if (diff.previous.trinket_available and not diff.current.trinket_available) or diff.trinket_charge_consumed:
            self._speech_queue.cancel_by_tag(EventTags.TRINKET)
        # Farm é reavaliado a cada tick. Cancela qualquer farm pendente ainda
        # não falado: se o jogador recuperou o CS, nenhum novo evento de farm
        # é emitido e o antigo (já obsoleto) some. Com o cooldown de 120s há
        # ≤1 farm em voo, então o cancel é barato.
        self._speech_queue.cancel_by_tag(EventTags.FARM)

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
        logger.info(f"[CoachSession] _handle_build_loaded: {build.champion} - is_complete={build.is_complete}, ai_messages={bool(build.ai_messages)}")
        logger.info(f"[CoachSession]   starter_items={build.starter_items}, core_items={build.core_items}, boots={build.boots}")
        self._current_build = build
        self._callbacks.on_build_loaded(build)
        with self._pending_build_lock:
            if not self._game_started:
                logger.info(f"[CoachSession] Game ainda não começou (_game_started={self._game_started}), guardando build como pending")
                self._pending_build = build
                return
            logger.info(f"[CoachSession] Game já começou (_game_started={self._game_started}), verificando se deve anunciar")
            logger.info(f"[CoachSession]   build_announce={self._options.build_announce}, is_complete={build.is_complete}")
            if self._options.build_announce and build.is_complete:
                # Modo IA: usar mensagens geradas pela IA
                if build.ai_messages:
                    logger.info(f"[CoachSession] >>>>>> MODO IA DETECTADO <<<<<<")
                    events: list[CoachEvent] = []
                    if "starter" in build.ai_messages:
                        logger.info(f"[CoachSession] Adicionando starter message")
                        events.append(
                            CoachEvent(
                                message=build.ai_messages["starter"],
                                priority=EventPriority.BUILD_ANNOUNCE,
                            )
                        )
                    if "core" in build.ai_messages:
                        logger.info(f"[CoachSession] Adicionando core message")
                        events.append(
                            CoachEvent(
                                message=build.ai_messages["core"],
                                priority=EventPriority.BUILD_ANNOUNCE,
                            )
                        )
                    if "boots" in build.ai_messages:
                        logger.info(f"[CoachSession] Adicionando boots message")
                        events.append(
                            CoachEvent(
                                message=build.ai_messages["boots"],
                                priority=EventPriority.BUILD_ANNOUNCE,
                            )
                        )
                    if events:
                        logger.info(f"[CoachSession] >>>>>> ENFILEIRANDO {len(events)} EVENTOS DE IA <<<<<<")
                        self._speech_queue.enqueue(events)
                    else:
                        logger.warning(f"[CoachSession] Nenhum evento de IA criado (ai_messages vazio?)")
                else:
                    # Modo determinístico: usar template fixo
                    logger.info(f"[CoachSession] >>>>>> MODO DETERMINÍSTICO - ANUNCIANDO BUILD <<<<<<")
                    event = build_announcement_event(build)
                    logger.info(f"[CoachSession] Evento: {event.message}")
                    self._speech_queue.enqueue([event])
                    logger.info(f"[CoachSession] >>>>>> BUILD ENFILEIRADA <<<<<<<<")
            else:
                if not self._options.build_announce:
                    logger.info(f"[CoachSession] Não anunciando: build_announce=False")
                if not build.is_complete:
                    logger.info(f"[CoachSession] Não anunciando: build não está completa (is_complete={build.is_complete})")
                    logger.info(f"[CoachSession]   Para is_complete ser True precisa: starter_items AND core_items AND boots")
                    logger.info(f"[CoachSession]   Tem starter? {bool(build.starter_items)}, Tem core? {bool(build.core_items)}, Tem boots? {bool(build.boots)}")
            self._detectors_unlocked = True

    def _position_name(self, position: str) -> str:
        """Converte código de posição para nome legível."""
        names = {
            "TOP": "Top lane",
            "JUNGLE": "Jungle",
            "MIDDLE": "Mid lane",
            "BOTTOM": "Bot lane",
            "UTILITY": "Suporte",
        }
        return names.get(position, position)

    def _extract_lane_enemy(
        self,
        payload: dict[str, Any],
        state: GameState,
        resolved_position: str = "",
    ) -> dict[str, Any] | None:
        """Extrai o campeão inimigo de mesma posição do payload da Live API.

        Usa `resolved_position` (vindo de `resolve_position_for_build_lookup`)
        em vez de `state.position` cru — a Live API às vezes deixa a posição
        do active player como NONE, mas preenche dos aliados, permitindo
        inferência por exclusão.
        """
        my_position = resolved_position or state.position
        if not my_position or my_position == "NONE":
            logger.warning(
                f"[CoachSession] extract_lane_enemy: position inválida "
                f"(state={state.position!r}, resolved={resolved_position!r})"
            )
            return None

        all_players = payload.get("allPlayers", [])
        active = payload.get("activePlayer", {}) or {}

        # Encontrar meu time com fallback
        my_identifier = active.get("riotId") or active.get("summonerName")
        if not my_identifier:
            logger.warning(f"[CoachSession] Não conseguiu identificar activePlayer")
            return None

        my_team = None
        for p in all_players:
            player_id = p.get("riotId") or p.get("summonerName")
            if player_id == my_identifier:
                my_team = p.get("team")
                break

        logger.info(f"[CoachSession] extract_lane_enemy: my_team={my_team}, my_position={my_position}")
        if my_team is None:
            logger.warning(f"[CoachSession] Não conseguiu encontrar meu time no allPlayers")
            return None

        # Procurar inimigo na mesma posição
        for player in all_players:
            player_team = player.get("team")
            player_pos = player.get("position")
            logger.debug(f"[CoachSession]   player: team={player_team}, pos={player_pos}, champ={player.get('championName')}")

            if (player_team and player_team != my_team and player_pos == my_position):
                enemy = {
                    "championName": player.get("championName", "?"),
                    "level": player.get("level", 0),
                }
                logger.info(f"[CoachSession] Lane enemy encontrado: {enemy}")
                return enemy

        logger.warning(f"[CoachSession] Nenhum inimigo de lane encontrado para posição {my_position}")
        return None

    def _extract_enemy_comp(self, payload: dict[str, Any], state: GameState) -> list[dict[str, Any]]:
        """Extrai lista de campeões inimigos do payload."""
        all_players = payload.get("allPlayers", [])
        active = payload.get("activePlayer", {}) or {}
        my_team = next(
            (p.get("team") for p in all_players
             if (p.get("riotId") or p.get("summonerName", "")) ==
                 (active.get("riotId") or active.get("summonerName", ""))),
            None,
        )

        enemies = []
        for player in all_players:
            if player.get("team") != my_team and player.get("team") is not None:
                enemies.append({
                    "championName": player.get("championName", "?"),
                    "level": player.get("level", 0),
                })
        return enemies

    def _check_quest_completion(self, diff: StateDiff) -> None:
        build = self._current_build
        if (
            self._quest_announced
            or build is None
            or build.quest_intermediate_id == 0
            or build.quest_item_id == 0
        ):
            return
        if (
            build.quest_intermediate_id in diff.gained_item_ids
            and build.quest_item_id not in diff.current.owned_item_ids
        ):
            self._quest_announced = True
            event = CoachEvent(
                message=TTSMessages.quest_item_available(build.quest_item_name),
                priority=EventPriority.BUILD_ANNOUNCE,
            )
            self._callbacks.on_log_message(
                LogMessages.coach_event(diff.current.game_time_seconds, event.message)
            )
            self._speech_queue.enqueue([event])
