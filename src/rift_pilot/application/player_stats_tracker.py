"""Rastreia StatBlocks estimados dos 10 campeões, recalculando só quando
level/itens mudam. Auto-valida o próprio campeão contra o `championStats`
real (única ground truth da Live API)."""
from __future__ import annotations

import logging
import threading
from typing import Any

from rift_pilot.domain.services.stats_estimator import (
    ChampionBase,
    RunePage,
    StatBlock,
    estimate_stat_block,
)

logger = logging.getLogger(__name__)

# Forma variável NÃO verificada (a Live API não expõe a forma; podem ter
# delta de stat). Kayn NÃO está aqui — validado empiricamente que a
# transformação não muda stat base.
_FORM_UNVERIFIED = {"Jayce", "Nidalee", "Elise", "Kled"}

# Stack permanente que altera stat e a API não revela o nº de stacks.
_STACKING = {
    "Veigar", "Nasus", "Senna", "Smolder", "Sion",
    "Chogath", "Kindred", "AurelionSol", "Belveth",
}

# Tolerância da auto-validação (erro relativo). Acima disso a fórmula
# divergiu (bug de fonte) → rebaixa confiança do próprio campeão.
_SELF_VALIDATION_TOL = 0.06

_RAW_PREFIX = "game_character_displayname_"


def _apiname(player: dict) -> str:
    """apiname canônico. `championName` é display ('Dr. Mundo'); o apiname
    real ('DrMundo') está embutido em `rawChampionName`."""
    raw = player.get("rawChampionName", "") or ""
    if raw.startswith(_RAW_PREFIX):
        return raw[len(_RAW_PREFIX):]
    return player.get("championName", "")


class PlayerStatsTracker:
    def __init__(
        self,
        champion_bases: dict[str, dict],
        item_stats_map: dict[int, dict[str, float]],
    ) -> None:
        self._bases = champion_bases
        self._item_stats = item_stats_map
        self._enemy_runes: dict[str, tuple[RunePage, bool]] = {}
        self._blocks: dict[str, StatBlock] = {}
        self._sig: dict[str, tuple] = {}
        self._lock = threading.Lock()

    def set_enemy_runes(self, mapping: dict[str, tuple[RunePage, bool]]) -> None:
        """`{championName: (RunePage, match_exato)}` vindo do bootstrap MCP."""
        with self._lock:
            self._enemy_runes = dict(mapping)

    def get(self, summoner_name: str) -> StatBlock | None:
        with self._lock:
            return self._blocks.get(summoner_name)

    def all(self) -> dict[str, StatBlock]:
        with self._lock:
            return dict(self._blocks)

    def update(self, payload: dict[str, Any]) -> None:
        active = payload.get("activePlayer", {}) or {}
        active_id = active.get("riotId") or active.get("summonerName", "")
        for p in payload.get("allPlayers", []):
            name = p.get("riotId") or p.get("summonerName", "")
            champ = _apiname(p)
            level = int(p.get("level", 1))
            item_ids = tuple(i["itemID"] for i in p.get("items", []))
            sig = (champ, level, tuple(sorted(item_ids)))
            if self._sig.get(name) == sig:
                continue  # nada mudou — não recalcula
            base_entry = self._bases.get(champ)
            if base_entry is None:
                logger.warning(f"[StatsTracker] sem base para {champ!r} — pulando")
                continue
            base = ChampionBase.from_json(champ, base_entry)
            item_stats = [self._item_stats.get(i, {}) for i in item_ids]

            confidence, reason = "high", None
            if champ in _STACKING:
                confidence, reason = "low", "stacking"
            elif champ in _FORM_UNVERIFIED:
                confidence, reason = "low", "form_unverified"

            is_active = name == active_id
            if is_active:
                shards = tuple(
                    r["id"]
                    for r in active.get("fullRunes", {}).get("statRunes", [])
                )
                rune_page: RunePage | None = RunePage(stat_mod_ids=shards)
            else:
                pair = self._enemy_runes.get(champ)
                if pair is None:
                    rune_page = None
                    if confidence == "high":
                        confidence, reason = "low", "missing_runes"
                else:
                    rune_page, exact = pair
                    if not exact and confidence == "high":
                        confidence, reason = "low", "missing_runes"

            block = estimate_stat_block(
                summoner_name=name, base=base, level=level,
                item_stats=item_stats, item_ids=item_ids,
                rune_page=rune_page, confidence=confidence,
                confidence_reason=reason,
            )

            if is_active:
                block = self._self_validate(block, active.get("championStats", {}))

            with self._lock:
                self._blocks[name] = block
                self._sig[name] = sig

    def _self_validate(self, block: StatBlock, cs: dict[str, Any]) -> StatBlock:
        """Compara o próprio campeão com o championStats real. Drift => low."""
        if not cs:
            return block
        checks = [
            (block.max_hp, cs.get("maxHealth")),
            (block.total_ad, cs.get("attackDamage")),
            (block.armor, cs.get("armor")),
            (block.magic_resist, cs.get("magicResist")),
            (block.attack_speed, cs.get("attackSpeed")),
        ]
        for est, real in checks:
            if not real:
                continue
            if abs(est - real) / abs(real) > _SELF_VALIDATION_TOL:
                logger.warning(
                    f"[StatsTracker] drift em {block.champion}: "
                    f"est={est:.1f} real={real:.1f}"
                )
                from dataclasses import replace
                return replace(
                    block, confidence="low",
                    confidence_reason="self_validation_drift",
                )
        return block
