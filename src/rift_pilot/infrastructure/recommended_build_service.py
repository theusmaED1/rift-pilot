"""Serviço que combina BuildProvider + fallback estático em uma RecommendedBuild."""
from __future__ import annotations

from rift_pilot.domain.entities.recommended_build import RecommendedBuild
from rift_pilot.domain.ports.build_provider import BuildProvider
from rift_pilot.domain.ports.data_dragon_repository import DataDragonRepository
from rift_pilot.infrastructure.build_providers.fallback_skill_priorities import (
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

        try:
            item_purchasable = self._data_dragon.get_item_purchasable()
            item_sources = self._data_dragon.get_item_sources()
        except Exception:
            item_purchasable = {}
            item_sources = {}

        starter_pairs = list(provider_result.starter_items)
        core_pairs = list(provider_result.core_items)
        quest_item_id, quest_item_name, quest_intermediate_id = _extract_quest_item(
            starter_pairs, core_pairs, item_purchasable, item_sources
        )

        return RecommendedBuild(
            champion=champion_name,
            position=position,
            starter_items=[name for _, name in starter_pairs],
            core_items=[name for _, name in core_pairs],
            boots=provider_result.boots[1] if provider_result.boots else "",
            runes_primary=provider_result.runes_primary,
            runes_secondary=provider_result.runes_secondary,
            skill_priority=skill_priority,
            skill_sequence=provider_result.skill_sequence,
            source=provider_result.source,
            starter_item_ids=[iid for iid, _ in starter_pairs],
            core_item_ids=[iid for iid, _ in core_pairs],
            boots_id=provider_result.boots[0] if provider_result.boots else 0,
            quest_item_id=quest_item_id,
            quest_item_name=quest_item_name,
            quest_intermediate_id=quest_intermediate_id,
        )


def _extract_quest_item(
    starter_pairs: list[tuple[int, str]],
    core_pairs: list[tuple[int, str]],
    item_purchasable: dict[int, bool],
    item_sources: dict[int, list[int]],
) -> tuple[int, str, int]:
    """Encontra e remove o item de quest das listas de itens da build.

    Um item de quest é aquele cujo pai direto (from) tem purchasable=False,
    indicando que é obtido gratuitamente pelo sistema de quest (ex: Dádiva dos Mundos).
    Retorna (quest_item_id, quest_item_name, quest_intermediate_id) ou (0, "", 0).
    """
    for pairs in (starter_pairs, core_pairs):
        for i, (iid, name) in enumerate(pairs):
            for from_id in item_sources.get(iid, []):
                if not item_purchasable.get(from_id, True):
                    pairs.pop(i)
                    return iid, name, from_id
    return 0, "", 0


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
