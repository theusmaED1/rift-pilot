"""Avisa quando a trinket está disponível há mais de 1 minuto sem uso."""
from __future__ import annotations

import random

from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.entities.state_diff import StateDiff
from rift_pilot.settings.constants import EventPriority, EventTags, Timing
from rift_pilot.settings.messages import TTSMessages


class TrinketReminderDetector:
    def __init__(self) -> None:
        self._available_since: float | None = None
        self._last_reminder_at: float | None = None

    def detect(self, diff: StateDiff) -> list[CoachEvent]:
        now = diff.current.game_time_seconds

        if diff.trinket_became_available:
            self._available_since = now

        if not diff.current.trinket_available:
            self._available_since = None
            self._last_reminder_at = None
            return []

        if diff.trinket_charge_consumed:
            self._available_since = now
            self._last_reminder_at = None

        if self._available_since is None:
            return []

        idle_seconds = now - self._available_since
        since_last = (
            now - self._last_reminder_at
            if self._last_reminder_at is not None
            else idle_seconds
        )

        if idle_seconds < Timing.TRINKET_REMINDER_IDLE_SECONDS:
            return []
        if since_last < Timing.TRINKET_REMINDER_IDLE_SECONDS:
            return []

        self._last_reminder_at = now
        message = random.choice(TTSMessages.TRINKET_REMINDERS)
        return [CoachEvent(message=message, priority=EventPriority.TRINKET_REMINDER, tag=EventTags.TRINKET)]
