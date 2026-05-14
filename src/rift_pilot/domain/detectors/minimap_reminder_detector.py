"""Lembra o jogador periodicamente de checar o minimapa."""
from __future__ import annotations

import random

from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.entities.state_diff import StateDiff
from rift_pilot.settings.constants import EventPriority, Timing
from rift_pilot.settings.messages import TTSMessages


class MinimapReminderDetector:
    """Emite um aviso aleatório sobre o minimapa em intervalos variáveis."""

    def __init__(self) -> None:
        self._next_reminder_at: float = self._draw_next_interval()

    def detect(self, diff: StateDiff) -> list[CoachEvent]:
        now = diff.current.game_time_seconds
        if now < self._next_reminder_at:
            return []
        self._next_reminder_at = now + self._draw_next_interval()
        message = random.choice(TTSMessages.MINIMAP_REMINDERS)
        return [CoachEvent(message=message, priority=EventPriority.MINIMAP_REMINDER)]

    @staticmethod
    def _draw_next_interval() -> float:
        return random.uniform(
            Timing.MINIMAP_REMINDER_MIN_INTERVAL_SECONDS,
            Timing.MINIMAP_REMINDER_MAX_INTERVAL_SECONDS,
        )
