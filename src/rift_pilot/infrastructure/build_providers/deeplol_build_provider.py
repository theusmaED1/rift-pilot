"""Provedor de build via API JSON pública do deeplol.gg."""
from __future__ import annotations

import httpx

from rift_pilot.domain.entities.recommended_build import ProviderResult
from rift_pilot.domain.ports.data_dragon_repository import DataDragonRepository
from rift_pilot.settings.constants import Network, Timing

_POSITION_TO_DEEPLOL_LANE: dict[str, str] = {
    "TOP": "Top",
    "JUNGLE": "Jungle",
    "MIDDLE": "Middle",
    "BOTTOM": "Adc",
    "UTILITY": "Support",
}

_LANE_FALLBACK_ORDER: tuple[str, ...] = ("Top", "Middle", "Adc", "Support", "Jungle")


class DeeplolBuildProvider:
    """Busca a build mais popular no tier configurado via deeplol.gg.

    Itera pelas versões mais recentes até encontrar uma que tenha dados.
    Resolve IDs de itens/runas para nomes pt-BR via `DataDragonRepository`.
    """

    def __init__(self, data_dragon: DataDragonRepository) -> None:
        self._data_dragon = data_dragon

    def fetch(self, champion_id: int, position: str) -> ProviderResult | None:
        recent_versions = self._fetch_recent_versions()
        if not recent_versions:
            return None

        build_data = self._fetch_build_data(champion_id, position, recent_versions)
        if build_data is None:
            return None

        return self._parse_build(build_data)

    def _fetch_recent_versions(self) -> list[str]:
        try:
            response = httpx.get(
                Network.DEEPLOL_VERSION_URL,
                timeout=Timing.DEEPLOL_HTTP_TIMEOUT_SECONDS,
            )
            return response.json().get("game_version_list", [])
        except Exception:
            return []

    def _fetch_build_data(
        self,
        champion_id: int,
        position: str,
        versions: list[str],
    ) -> dict | None:
        target_lane = _POSITION_TO_DEEPLOL_LANE.get(position.upper(), "")

        for version in versions:
            try:
                response = httpx.get(
                    Network.DEEPLOL_BUILD_URL,
                    params={
                        "platform_id": Network.DEEPLOL_PLATFORM_ID,
                        "champion_id": champion_id,
                        "game_version": version,
                        "tier": Network.DEEPLOL_TIER,
                    },
                    timeout=Timing.DEEPLOL_HTTP_TIMEOUT_SECONDS,
                )
                if response.status_code != 200:
                    continue
                payload = response.json()
                lanes = payload.get("build_by_lane", {})
                if any(lane.get("build_lst") for lane in lanes.values()):
                    return self._extract_lane(lanes, target_lane)
            except Exception:
                continue

        return None

    @staticmethod
    def _extract_lane(lanes: dict, target_lane: str) -> dict | None:
        candidate = lanes.get(target_lane) if target_lane else None
        if candidate and candidate.get("build_lst"):
            return candidate["build_lst"][0]
        for lane_name in _LANE_FALLBACK_ORDER:
            lane_data = lanes.get(lane_name)
            if lane_data and lane_data.get("build_lst"):
                return lane_data["build_lst"][0]
        return None

    def _parse_build(self, build: dict) -> ProviderResult | None:
        try:
            item_names = self._data_dragon.get_item_names()
            rune_names = self._data_dragon.get_rune_names()
        except Exception:
            item_names = {}
            rune_names = {}

        def resolve_item(item_id: int) -> tuple[int, str]:
            return item_id, item_names.get(item_id, str(item_id))

        starter_ids: list[int] = build.get("start_item", {}).get("build", [])
        starter_items = [resolve_item(iid) for iid in starter_ids]

        boots_id: int = build.get("boots", {}).get("item", 0)
        boots = resolve_item(boots_id) if boots_id else None

        final_item_ids: list[int] = build.get("item", {}).get("build", [])
        starter_id_set = set(starter_ids)
        seen_core: set[int] = set()
        core_items: list[tuple[int, str]] = []
        for item_id in final_item_ids:
            if item_id != boots_id and item_id not in starter_id_set and item_id not in seen_core:
                seen_core.add(item_id)
                core_items.append(resolve_item(item_id))

        rune_data = build.get("rune", {})
        primary_tree_ids: list[int] = rune_data.get("main_build", [])
        secondary_tree_ids: list[int] = rune_data.get("sub_build", [])
        runes_primary = rune_names.get(primary_tree_ids[0], "") if primary_tree_ids else ""
        runes_secondary = (
            rune_names.get(secondary_tree_ids[0], "") if secondary_tree_ids else ""
        )

        skill_sequence: list[int] = build.get("skill", {}).get("detail", [])

        if not starter_items and not core_items and not boots:
            return None

        return ProviderResult(
            starter_items=starter_items,
            core_items=core_items,
            boots=boots,
            runes_primary=runes_primary,
            runes_secondary=runes_secondary,
            skill_sequence=skill_sequence,
            source="deeplol.gg",
        )
