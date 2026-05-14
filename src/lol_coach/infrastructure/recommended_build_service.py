"""Serviço que combina BuildProvider + fallback estático em uma RecommendedBuild."""
from __future__ import annotations

from lol_coach.domain.entities.recommended_build import RecommendedBuild
from lol_coach.domain.ports.build_provider import BuildProvider
from lol_coach.domain.ports.data_dragon_repository import DataDragonRepository
from lol_coach.infrastructure.build_providers.fallback_skill_priorities import (
    fallback_skill_priority,
)

_SKILL_NAME_BY_CODE = {1: "Q", 2: "W", 3: "E"}


class RecommendedBuildService:
    """Busca a build recomendada para um campeão na posição informada.

    Combina o resultado do `BuildProvider` (deeplol) com um fallback estático
    de prioridade de skills quando o provider não retorna `skill_sequence`.
    """

    def __init__(
        self,
        build_provider: BuildProvider,
        data_dragon: DataDragonRepository,
    ) -> None:
        self._build_provider = build_provider
        self._data_dragon = data_dragon

    def fetch_for_champion(
        self,
        champion_name: str,
        position: str,
    ) -> RecommendedBuild | None:
        champion_id = self._data_dragon.get_champion_id(champion_name)
        if not champion_id:
            return None

        provider_result = self._build_provider.fetch(champion_id, position)
        bundled_priority = fallback_skill_priority(champion_name)

        if provider_result is None:
            return RecommendedBuild(
                champion=champion_name,
                position=position,
                skill_priority=bundled_priority,
                source="bundled",
            )

        skill_priority = (
            _derive_skill_priority_from_sequence(provider_result.skill_sequence)
            if provider_result.skill_sequence
            else bundled_priority
        )

        return RecommendedBuild(
            champion=champion_name,
            position=position,
            starter_items=[name for _, name in provider_result.starter_items],
            core_items=[name for _, name in provider_result.core_items],
            boots=provider_result.boots[1] if provider_result.boots else "",
            runes_primary=provider_result.runes_primary,
            runes_secondary=provider_result.runes_secondary,
            skill_priority=skill_priority,
            skill_sequence=provider_result.skill_sequence,
            source=provider_result.source,
            starter_item_ids=[iid for iid, _ in provider_result.starter_items],
            core_item_ids=[iid for iid, _ in provider_result.core_items],
            boots_id=provider_result.boots[0] if provider_result.boots else 0,
        )


def _derive_skill_priority_from_sequence(skill_sequence: list[int]) -> list[str]:
    """Ordena Q/W/E pela ordem em que cada skill atinge 5 pontos no skill_sequence.

    Skills que nunca chegam a 5 pontos vão para o final, ordenadas pelo total
    de pontos investidos (decrescente).
    """
    point_counts: dict[str, int] = {"Q": 0, "W": 0, "E": 0}
    maxed_in_order: list[str] = []
    for code in skill_sequence:
        skill = _SKILL_NAME_BY_CODE.get(code)
        if skill is None:
            continue
        point_counts[skill] += 1
        if point_counts[skill] == 5 and skill not in maxed_in_order:
            maxed_in_order.append(skill)

    remaining = sorted(
        [s for s in ("Q", "W", "E") if s not in maxed_in_order],
        key=lambda s: point_counts[s],
        reverse=True,
    )
    return maxed_in_order + remaining
