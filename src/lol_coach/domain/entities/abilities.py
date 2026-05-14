"""Níveis das habilidades do campeão ativo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Abilities:
    """Snapshot dos níveis de Q, W, E e R do jogador ativo."""

    q: int
    w: int
    e: int
    r: int

    @property
    def total_points_spent(self) -> int:
        return self.q + self.w + self.e + self.r

    @classmethod
    def from_live_api(cls, abilities_payload: dict[str, Any]) -> Abilities:
        return cls(
            q=abilities_payload["Q"].get("abilityLevel", 0),
            w=abilities_payload["W"].get("abilityLevel", 0),
            e=abilities_payload["E"].get("abilityLevel", 0),
            r=abilities_payload["R"].get("abilityLevel", 0),
        )
