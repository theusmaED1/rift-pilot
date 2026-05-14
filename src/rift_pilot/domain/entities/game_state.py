"""Snapshot completo do estado da partida em um tick."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rift_pilot.domain.entities.abilities import Abilities
from rift_pilot.domain.entities.game_event import GameEvent
from rift_pilot.domain.ports.game_data_source import GameLoading


_TRINKET_SLOT = 6


@dataclass(frozen=True)
class GameState:
    """Foto imutável do estado do jogo num instante."""

    game_time_seconds: float
    player_level: int
    abilities: Abilities
    current_gold: float
    events: list[GameEvent]
    champion_name: str = ""
    position: str = ""
    owned_item_ids: frozenset[int] = field(default_factory=frozenset)
    has_smite: bool = False
    trinket_available: bool = False
    trinket_charges: int = 0

    @classmethod
    def from_live_api(cls, payload: dict[str, Any]) -> GameState:
        active = payload.get("activePlayer", {}) or {}
        if not {"level", "abilities", "currentGold"}.issubset(active):
            raise GameLoading("Payload do activePlayer incompleto (modo espectador ou transição).")
        all_players = payload.get("allPlayers", [])

        champion_name = ""
        position = ""
        owned_item_ids: frozenset[int] = frozenset()
        has_smite = False
        trinket_available = False
        active_riot_id = active.get("riotId") or active.get("summonerName", "")
        for player in all_players:
            player_riot_id = player.get("riotId") or player.get("summonerName", "")
            if player_riot_id == active_riot_id:
                champion_name = player.get("championName", "")
                position = player.get("position", "")
                items = player.get("items", [])
                owned_item_ids = frozenset(item["itemID"] for item in items)
                has_smite = _player_has_smite(player.get("summonerSpells", {}))
                trinket_available, trinket_charges = _trinket_state(items)
                break

        return cls(
            game_time_seconds=payload["gameData"]["gameTime"],
            player_level=active["level"],
            abilities=Abilities.from_live_api(active["abilities"]),
            current_gold=active["currentGold"],
            events=[GameEvent.from_live_api(ev) for ev in payload["events"]["Events"]],
            champion_name=champion_name,
            position=position,
            owned_item_ids=owned_item_ids,
            has_smite=has_smite,
            trinket_available=trinket_available,
            trinket_charges=trinket_charges,
        )


def _trinket_state(items: list[dict[str, Any]]) -> tuple[bool, int]:
    """Retorna (canUse, charges) da trinket. `count` da API = número de cargas."""
    for item in items:
        if item.get("slot") == _TRINKET_SLOT:
            return bool(item.get("canUse", False)), int(item.get("count", 1))
    return False, 0


def _player_has_smite(summoner_spells: dict[str, Any]) -> bool:
    """Identifica Golpear/Smite em qualquer um dos dois slots de feitiço."""
    for slot in ("summonerSpellOne", "summonerSpellTwo"):
        spell = summoner_spells.get(slot, {}) or {}
        if "Smite" in spell.get("rawDisplayName", ""):
            return True
        if spell.get("displayName", "").lower() in {"smite", "golpear"}:
            return True
    return False
