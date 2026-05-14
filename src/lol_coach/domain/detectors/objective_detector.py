"""Detecta proximidade de spawn/respawn de dragão, barão e arauto."""
from __future__ import annotations

from dataclasses import dataclass, field

from lol_coach.domain.entities.coach_event import CoachEvent
from lol_coach.domain.entities.state_diff import StateDiff
from lol_coach.settings.constants import EventPriority, GameRules
from lol_coach.settings.messages import TTSMessages

_INITIAL_SPAWN_SECONDS: dict[str, float] = {
    "dragon": GameRules.DRAGON_INITIAL_SPAWN_SECONDS,
    "voidgrubs": GameRules.VOIDGRUBS_INITIAL_SPAWN_SECONDS,
    "herald": GameRules.HERALD_INITIAL_SPAWN_SECONDS,
    "baron": GameRules.BARON_INITIAL_SPAWN_SECONDS,
}

_RESPAWN_SECONDS: dict[str, float] = {
    "dragon": GameRules.DRAGON_RESPAWN_SECONDS,
    "baron": GameRules.BARON_RESPAWN_SECONDS,
    "herald": GameRules.HERALD_RESPAWN_SECONDS,
}

_OBJECTIVE_BY_EVENT_NAME: dict[str, str] = {
    "DragonKill": "dragon",
    "BaronKill": "baron",
    "HeraldKill": "herald",
}

_MESSAGES_BY_OBJECTIVE: dict[str, dict[int, str]] = {
    "dragon": TTSMessages.OBJECTIVE_DRAGON,
    "baron": TTSMessages.OBJECTIVE_BARON,
    "herald": TTSMessages.OBJECTIVE_HERALD,
    "voidgrubs": TTSMessages.OBJECTIVE_VOIDGRUBS,
}


@dataclass
class _ObjectiveTimer:
    name: str
    spawn_at_seconds: float
    warnings_fired: set[int] = field(default_factory=set)


def _priority_for_offset(offset_seconds: int) -> int:
    if offset_seconds <= 10:
        return EventPriority.OBJECTIVE_IMMINENT
    if offset_seconds <= 30:
        return EventPriority.OBJECTIVE_SOON
    return EventPriority.OBJECTIVE_APPROACHING


class ObjectiveDetector:
    """Mantém timers de objetivos neutros e avisa antes do spawn."""

    def __init__(self, warn_offsets_seconds: tuple[int, ...] | None = None) -> None:
        offsets = warn_offsets_seconds or GameRules.OBJECTIVE_DEFAULT_WARN_OFFSETS_SECONDS
        self._warn_offsets = sorted(offsets, reverse=True)
        self._timers: list[_ObjectiveTimer] = [
            _ObjectiveTimer(name=name, spawn_at_seconds=spawn_at)
            for name, spawn_at in _INITIAL_SPAWN_SECONDS.items()
        ]

    def detect(self, diff: StateDiff) -> list[CoachEvent]:
        events: list[CoachEvent] = []
        now = diff.current.game_time_seconds

        self._schedule_respawns_from_kills(diff)

        expired: list[_ObjectiveTimer] = []
        for timer in self._timers:
            time_until_spawn = timer.spawn_at_seconds - now
            if time_until_spawn < -1.0:
                expired.append(timer)
                continue
            for offset in self._warn_offsets:
                already_warned = offset in timer.warnings_fired
                within_warning_window = time_until_spawn <= offset + 0.9
                if already_warned or not within_warning_window:
                    continue
                timer.warnings_fired.add(offset)
                message = _MESSAGES_BY_OBJECTIVE.get(timer.name, {}).get(offset)
                if message:
                    events.append(
                        CoachEvent(message=message, priority=_priority_for_offset(offset))
                    )

        for timer in expired:
            self._timers.remove(timer)

        return events

    def _schedule_respawns_from_kills(self, diff: StateDiff) -> None:
        for event in diff.new_events:
            objective = _OBJECTIVE_BY_EVENT_NAME.get(event.name)
            if objective is None or objective not in _RESPAWN_SECONDS:
                continue
            self._timers = [t for t in self._timers if t.name != objective]
            self._timers.append(
                _ObjectiveTimer(
                    name=objective,
                    spawn_at_seconds=event.time_seconds + _RESPAWN_SECONDS[objective],
                )
            )
