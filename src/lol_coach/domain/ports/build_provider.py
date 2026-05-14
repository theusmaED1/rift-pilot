"""Contrato para provedores externos de build (deeplol, op.gg, etc.)."""
from __future__ import annotations

from typing import Protocol

from lol_coach.domain.entities.recommended_build import ProviderResult


class BuildProvider(Protocol):
    """Retorna a build recomendada para um campeão+posição."""

    def fetch(self, champion_id: int, position: str) -> ProviderResult | None: ...
