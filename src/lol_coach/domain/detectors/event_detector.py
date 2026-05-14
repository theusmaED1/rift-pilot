"""Protocolo comum a todos os detectores de evento."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from lol_coach.domain.entities.coach_event import CoachEvent
from lol_coach.domain.entities.state_diff import StateDiff


@runtime_checkable
class EventDetector(Protocol):
    """Observa um `StateDiff` e emite zero ou mais `CoachEvent`."""

    def detect(self, diff: StateDiff) -> list[CoachEvent]: ...
