"""Contrato para a fila de prioridade de avisos falados."""
from __future__ import annotations

from typing import Protocol

from rift_pilot.domain.entities.coach_event import CoachEvent


class SpeechQueue(Protocol):
    """Enfileira eventos para serem falados em ordem de prioridade."""

    def enqueue(self, events: list[CoachEvent]) -> None: ...
    def cancel_by_tag(self, tag: str) -> None: ...
    def clear(self) -> None: ...
