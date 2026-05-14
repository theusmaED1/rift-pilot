"""Snapshot completo do estado da partida em um tick."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lol_coach.domain.entities.abilities import Abilities
from lol_coach.domain.entities.game_event import GameEvent


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

    @classmethod
    def from_live_api(cls, payload: dict[str, Any]) -> GameState:
        active = payload["activePlayer"]
        all_players = payload.get("allPlayers", [])

        champion_name = ""
        position = ""
        owned_item_ids: frozenset[int] = frozenset()
        has_smite = False
        active_riot_id = active.get("riotId") or active.get("summonerName", "")
        for player in all_players:
            player_riot_id = player.get("riotId") or player.get("summonerName", "")
            if player_riot_id == active_riot_id:
                champion_name = player.get("championName", "")
                position = player.get("position", "")
                owned_item_ids = frozenset(
                    item["itemID"] for item in player.get("items", [])
                )
                has_smite = _player_has_smite(player.get("summonerSpells", {}))
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
        )


def _player_has_smite(summoner_spells: dict[str, Any]) -> bool:
    """Identifica Golpear/Smite em qualquer um dos dois slots de feitiço."""
    for slot in ("summonerSpellOne", "summonerSpellTwo"):
        spell = summoner_spells.get(slot, {}) or {}
        if "Smite" in spell.get("rawDisplayName", ""):
            return True
        if spell.get("displayName", "").lower() in {"smite", "golpear"}:
            return True
    return False
