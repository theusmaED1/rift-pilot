"""Bootstrap do tracking de stats — espelha BuildLoader.fetch_in_background.

Numa daemon thread: carrega champion_bases.json + item stats do DD, busca
as páginas de runa dos inimigos via MCP em paralelo (matchup invertido),
constrói o PlayerStatsTracker e devolve via callback. Não bloqueia o
fluxo da build.
"""
from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import rift_pilot
from rift_pilot.application.player_stats_tracker import PlayerStatsTracker, _apiname
from rift_pilot.domain.services.stats_estimator import RunePage
from rift_pilot.infrastructure.opgg_mcp.pool_extractor import match_rune_page

logger = logging.getLogger(__name__)

_BASES_PATH = (
    Path(rift_pilot.__file__).parent
    / "infrastructure" / "riot" / "data" / "champion_bases.json"
)


class StatsBootstrap:
    def __init__(self, data_dragon: Any, mcp_client: Any) -> None:
        self._dd = data_dragon
        self._mcp = mcp_client
        self._bases_cache: dict[str, dict] | None = None
        self._started = False

    def _load_bases(self) -> dict[str, dict]:
        if self._bases_cache is None:
            with _BASES_PATH.open(encoding="utf-8") as f:
                self._bases_cache = json.load(f)["champions"]
        return self._bases_cache

    def fetch_in_background(
        self,
        payload: dict[str, Any],
        my_champion: str,
        on_ready: Callable[[PlayerStatsTracker], None],
        on_log: Callable[[str], None],
    ) -> None:
        if self._started:
            return
        self._started = True
        threading.Thread(
            target=self._fetch,
            args=(payload, my_champion, on_ready, on_log),
            daemon=True,
        ).start()

    def _fetch(
        self,
        payload: dict[str, Any],
        my_champion: str,
        on_ready: Callable[[PlayerStatsTracker], None],
        on_log: Callable[[str], None],
    ) -> None:
        try:
            bases = self._load_bases()
            item_stats = self._dd.get_item_stats()
            tracker = PlayerStatsTracker(bases, item_stats)

            active = payload.get("activePlayer", {}) or {}
            all_players = payload.get("allPlayers", [])
            my_team = next(
                (p.get("team") for p in all_players
                 if (p.get("riotId") or p.get("summonerName", "")) ==
                    (active.get("riotId") or active.get("summonerName", ""))),
                None,
            )
            enemies = [
                p for p in all_players
                if p.get("team") not in (None, my_team)
            ]

            def fetch_one(p: dict) -> tuple[str, tuple[RunePage, bool]] | None:
                champ = _apiname(p)  # mesma chave que o tracker usa
                pos = p.get("position", "") or ""
                if not champ or not pos or pos == "NONE":
                    return None  # sem matchup possível (ARAM/practice)
                runes = p.get("runes", {}) or {}
                ks = (runes.get("keystone", {}) or {}).get("id", 0)
                sec = (runes.get("secondaryRuneTree", {}) or {}).get("id", 0)
                try:
                    data = self._mcp.matchup_guide(champ, my_champion, pos)
                except Exception as e:
                    logger.warning(f"[StatsBootstrap] MCP falhou p/ {champ}: {e}")
                    return None
                ids, exact = match_rune_page(data, int(ks), int(sec))
                if ids is None:
                    return None
                return champ, (RunePage(stat_mod_ids=ids.stat_mod_ids), exact)

            enemy_runes: dict[str, tuple[RunePage, bool]] = {}
            with ThreadPoolExecutor(max_workers=5) as ex:
                for res in ex.map(fetch_one, enemies):
                    if res is not None:
                        enemy_runes[res[0]] = res[1]

            tracker.set_enemy_runes(enemy_runes)
            logger.info(
                f"[StatsBootstrap] pronto — {len(enemy_runes)}/"
                f"{len(enemies)} inimigos com runa casada"
            )
            on_ready(tracker)
        except Exception as e:
            logger.error(f"[StatsBootstrap] falhou: {e}", exc_info=True)
            on_log(f"Stats tracker indisponível: {e}")
