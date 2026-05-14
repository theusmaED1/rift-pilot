"""Evento bruto reportado pela Live Client Data API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GameEvent:
    """Evento da partida (kill de dragão/barão, primeira torre, etc.)."""

    event_id: int
    name: str
    time_seconds: float
    raw_payload: dict[str, Any]

    @classmethod
    def from_live_api(cls, payload: dict[str, Any]) -> GameEvent:
        return cls(
            event_id=payload["EventID"],
            name=payload["EventName"],
            time_seconds=payload["EventTime"],
            raw_payload=payload,
        )
