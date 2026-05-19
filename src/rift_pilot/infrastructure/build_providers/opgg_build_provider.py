"""OP.GG build provider — DESATIVADO POR ENQUANTO.

Fallback para starter items hardcoded até MCP ser validado.
"""
from __future__ import annotations

import logging
from typing import Any

from rift_pilot.domain.entities.recommended_build import ProviderResult
from rift_pilot.domain.ports.data_dragon_repository import DataDragonRepository

logger = logging.getLogger(__name__)

# Starter items hardcoded para teste (por campeão)
_STARTER_ITEMS = {
    "Akali": ["Anel de Doran", "Poção de Vida"],
    "Diana": ["Anel de Doran", "Poção de Vida"],
    "Ahri": ["Escudo de Doran", "Poção de Vida"],
}

_CORE_ITEMS = {
    "Akali": ["Pistola Laminar Hextec", "Chama Sombria", "Ampulheta de Zhonya"],
    "Diana": ["Pistola Laminar Hextec", "Chama Sombria", "Ampulheta de Zhonya"],
    "Ahri": ["Bastão das Eras", "Chama Sombria", "Ampulheta de Zhonya"],
}

_BOOTS = {
    "Akali": "Sapatos do Feiticeiro",
    "Diana": "Sapatos do Feiticeiro",
    "Ahri": "Sapatos do Feiticeiro",
}


class OpggBuildProvider:
    """OP.GG provider — fallback com dados hardcoded.

    TODO: Implementar MCP call quando estável.
    """

    def __init__(self, data_dragon: DataDragonRepository) -> None:
        """Inicializa o provider (compatível com interface BuildProvider)."""
        self._data_dragon = data_dragon

    def fetch(self, champion_id: int, position: str) -> ProviderResult | None:
        """Retorna build fallback hardcoded para o campeão."""
        logger.info(f"[OpggBuildProvider] Iniciando fetch para champion_id={champion_id}, position={position}")

        champion_name = self._data_dragon.get_champion_name(champion_id)
        logger.info(f"[OpggBuildProvider] get_champion_name({champion_id}) = {champion_name}")
        if not champion_name:
            logger.warning(f"[OpggBuildProvider] Champion name não encontrado para ID {champion_id}")
            return None

        item_names = self._data_dragon.get_item_names()
        logger.info(f"[OpggBuildProvider] Carregou {len(item_names)} nomes de itens do DataDragon")

        # Converter nomes para IDs
        starter_names = _STARTER_ITEMS.get(champion_name, [])
        core_names = _CORE_ITEMS.get(champion_name, [])
        boots_name = _BOOTS.get(champion_name, "")
        logger.info(f"[OpggBuildProvider] starter_names={starter_names}, core_names={core_names}, boots_name={boots_name}")

        starter_items = [
            (iid, name) for name, iid in
            [(n, next((i for i, nm in item_names.items() if nm == n), None))
             for n in starter_names]
            if iid is not None
        ]
        logger.info(f"[OpggBuildProvider] starter_items encontrados: {starter_items} (total={len(starter_items)})")

        core_items = [
            (iid, name) for name, iid in
            [(n, next((i for i, nm in item_names.items() if nm == n), None))
             for n in core_names]
            if iid is not None
        ]
        logger.info(f"[OpggBuildProvider] core_items encontrados: {core_items} (total={len(core_items)})")

        boots_id = next((i for i, nm in item_names.items() if nm == boots_name), None)
        boots = (boots_id, boots_name) if boots_id else None
        logger.info(f"[OpggBuildProvider] boots encontrado: {boots}")

        if not starter_items and not core_items:
            logger.warning(f"[OpggBuildProvider] Nenhum starter ou core item encontrado! Retornando None")
            return None

        result = ProviderResult(
            starter_items=starter_items,
            core_items=core_items,
            boots=boots,
            runes_primary="",
            runes_secondary="",
            skill_sequence=[],
            source="fallback (OP.GG MCP em desenvolvimento)",
        )
        logger.info(f"[OpggBuildProvider] Sucesso! ProviderResult criado")
        return result
