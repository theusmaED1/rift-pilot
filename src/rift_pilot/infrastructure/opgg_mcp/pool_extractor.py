"""Funções puras de extração de pools do retorno do `lol_get_lane_matchup_guide`.

O MCP retorna múltiplas opções por categoria com `play`, `win` e `pick_rate`.
A IA recebe top-N filtrados para escolher uma alternativa.

Sample-size filtering: opções com `play` < MIN_PLAY são consideradas ruído
estatístico e descartadas. Se nenhuma opção passar do threshold (matchup raro),
o fallback é ordenar por play (mais conservador que winrate).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Thresholds para considerar uma opção como "realista" (não nicho).
# Pick rate baixo (< 5%) significa que pouquíssimos players usam aquilo —
# normalmente são edge cases, builds experimentais ou amostra contaminada
# (ex: dados de outra posição misturados). Mesmo com winrate alto, esses
# casos têm variância estatística enorme.
MIN_PLAY_FOR_WINRATE = 30
MIN_PICK_RATE_FOR_WINRATE = 0.05  # 5%


@dataclass(frozen=True)
class ItemOption:
    """Uma opção individual de item (ou conjunto, no caso de starter/boots)."""

    ids: list[int]
    names: list[str]
    play: int
    win: int
    pick_rate: float

    @property
    def winrate(self) -> float:
        return self.win / self.play if self.play > 0 else 0.0


@dataclass(frozen=True)
class CoreCombo:
    """Combinação completa de itens core (3-4 itens em ordem)."""

    ids: list[int]
    names: list[str]
    play: int
    win: int
    pick_rate: float

    @property
    def winrate(self) -> float:
        return self.win / self.play if self.play > 0 else 0.0


def _to_option(raw: dict[str, Any]) -> ItemOption:
    return ItemOption(
        ids=list(raw.get("ids", []) or []),
        names=list(raw.get("ids_names", []) or []),
        play=int(raw.get("play", 0)),
        win=int(raw.get("win", 0)),
        pick_rate=float(raw.get("pick_rate", 0.0)),
    )


def _to_combo(raw: dict[str, Any]) -> CoreCombo:
    return CoreCombo(
        ids=list(raw.get("ids", []) or []),
        names=list(raw.get("ids_names", []) or []),
        play=int(raw.get("play", 0)),
        win=int(raw.get("win", 0)),
        pick_rate=float(raw.get("pick_rate", 0.0)),
    )


def _top_n_by_winrate_with_min_play(
    options: list[ItemOption], n: int
) -> list[ItemOption]:
    """Top N por winrate filtrando opções nicho.

    Requer AMBOS para ser "confiável":
      - play >= MIN_PLAY_FOR_WINRATE (amostra suficiente)
      - pick_rate >= MIN_PICK_RATE_FOR_WINRATE (não é build esquisita)

    Se nenhuma opção passar, cai para ordenação por play (mais conservador).
    """
    confiantes = [
        o for o in options
        if o.play >= MIN_PLAY_FOR_WINRATE
        and o.pick_rate >= MIN_PICK_RATE_FOR_WINRATE
    ]
    if confiantes:
        confiantes.sort(key=lambda o: (o.winrate, o.play), reverse=True)
        return confiantes[:n]
    # Fallback: matchup raro — usa play como sinal mais robusto
    options.sort(key=lambda o: o.play, reverse=True)
    return options[:n]


def top_starters(data: dict[str, Any], n: int = 2) -> list[ItemOption]:
    """Top N starters por winrate (com filtro de sample mínimo)."""
    raw = data.get("starter_items", []) or []
    options = [_to_option(r) for r in raw if r.get("play", 0) > 0]
    return _top_n_by_winrate_with_min_play(options, n)


def top_boots(data: dict[str, Any], n: int = 2) -> list[ItemOption]:
    """Top N botas por winrate (com filtro de sample mínimo)."""
    raw = data.get("boots", []) or []
    options = [_to_option(r) for r in raw if r.get("play", 0) > 0]
    return _top_n_by_winrate_with_min_play(options, n)


def top_core_combos(data: dict[str, Any], n: int = 2) -> list[CoreCombo]:
    """Top N combos core por play (mais jogados, conforme spec do usuário)."""
    raw = data.get("core_items", []) or []
    combos = [_to_combo(r) for r in raw if r.get("play", 0) > 0]
    combos.sort(key=lambda c: c.play, reverse=True)
    return combos[:n]


def slot_pool(data: dict[str, Any], slot: int) -> list[ItemOption]:
    """Retorna pool de items para o slot (1-6).

    `data.single_items` é uma lista de objetos com `depth` (slot index) e
    `items[]` (opções daquele slot, ordenadas por pick_rate).
    """
    single_items = data.get("single_items", []) or []
    for entry in single_items:
        if int(entry.get("depth", -1)) == slot:
            return [_to_option(r) for r in (entry.get("items", []) or [])]
    return []


def summary_stats(data: dict[str, Any]) -> dict[str, Any]:
    """Retorna stats agregadas do champion na posição (winrate, pickrate, ...)."""
    summary = data.get("summary", {}) or {}
    avg = summary.get("average_stats", {}) or {}
    return {
        "play": int(avg.get("play", 0)),
        "win_rate": float(avg.get("win_rate", 0.0)),
        "pick_rate": float(avg.get("pick_rate", 0.0)),
        "ban_rate": float(avg.get("ban_rate", 0.0)),
        "kda": float(avg.get("kda", 0.0)),
    }


def runes_top(data: dict[str, Any]) -> dict[str, Any] | None:
    """Retorna a página de runas de maior winrate (com tie-break em play)."""
    runes = data.get("runes", []) or []
    if not runes:
        return None
    valid = [r for r in runes if int(r.get("play", 0)) > 0]
    if not valid:
        return None
    valid.sort(
        key=lambda r: (
            int(r.get("win", 0)) / int(r.get("play", 1)),
            int(r.get("play", 0)),
        ),
        reverse=True,
    )
    return valid[0]



@dataclass(frozen=True)
class RunePageIds:
    """IDs completos de uma página de runas (keystone + menores + shards)."""

    keystone_id: int
    primary_rune_ids: tuple[int, ...]
    primary_page_id: int
    secondary_rune_ids: tuple[int, ...]
    secondary_page_id: int
    stat_mod_ids: tuple[int, ...]


def rune_ids(data: dict[str, Any]) -> RunePageIds | None:
    """Extrai os IDs de runa da página MAIS JOGADA (não a de maior winrate).

    Para estimar stats do inimigo queremos a página que ele mais provavelmente
    usa — popularidade (play) é melhor sinal que winrate aqui. Página com
    `play < MIN_PLAY_FOR_WINRATE` é descartada se houver alternativa; se
    nenhuma passar, usa a mais jogada disponível.
    """
    runes = data.get("runes", []) or []
    valid = [r for r in runes if int(r.get("play", 0)) > 0]
    if not valid:
        return None
    confiantes = [r for r in valid if int(r.get("play", 0)) >= MIN_PLAY_FOR_WINRATE]
    pool = confiantes or valid
    pool.sort(key=lambda r: int(r.get("play", 0)), reverse=True)
    top = pool[0]
    primary = [int(x) for x in (top.get("primary_rune_ids") or [])]
    secondary = [int(x) for x in (top.get("secondary_rune_ids") or [])]
    stat_mods = [int(x) for x in (top.get("stat_mod_ids") or [])]
    if not primary:
        return None
    return RunePageIds(
        keystone_id=primary[0],
        primary_rune_ids=tuple(primary),
        primary_page_id=int(top.get("primary_page_id", 0)),
        secondary_rune_ids=tuple(secondary),
        secondary_page_id=int(top.get("secondary_page_id", 0)),
        stat_mod_ids=tuple(stat_mods),
    )


def _page_to_ids(page: dict[str, Any]) -> RunePageIds | None:
    primary = [int(x) for x in (page.get("primary_rune_ids") or [])]
    if not primary:
        return None
    return RunePageIds(
        keystone_id=primary[0],
        primary_rune_ids=tuple(primary),
        primary_page_id=int(page.get("primary_page_id", 0)),
        secondary_rune_ids=tuple(int(x) for x in (page.get("secondary_rune_ids") or [])),
        secondary_page_id=int(page.get("secondary_page_id", 0)),
        stat_mod_ids=tuple(int(x) for x in (page.get("stat_mod_ids") or [])),
    )


def match_rune_page(
    data: dict[str, Any],
    enemy_keystone_id: int,
    enemy_secondary_tree_id: int,
) -> tuple[RunePageIds | None, bool]:
    """Casa as runas observadas do inimigo (Live API só dá keystone + árvores)
    com a página MCP mais jogada que tenha o MESMO keystone e árvore
    secundária. Retorna (página, match_exato).

    - match_exato=True: keystone + árvore secundária batem → shards confiáveis.
    - match_exato=False: nenhuma página bate → cai pra `rune_ids` (mais
      jogada geral) e o chamador marca `confidence="low"`.
    """
    pages = data.get("runes", []) or []
    candidates = []
    for p in pages:
        ids = _page_to_ids(p)
        if ids is None:
            continue
        if (
            ids.keystone_id == enemy_keystone_id
            and ids.secondary_page_id == enemy_secondary_tree_id
        ):
            candidates.append((int(p.get("play", 0)), ids))
    if candidates:
        candidates.sort(key=lambda c: c[0], reverse=True)
        return candidates[0][1], True
    return rune_ids(data), False

def skill_order_top(data: dict[str, Any]) -> list[str]:
    """Retorna a sequência de leveling de skills (Q/W/E/R por nível) mais usada."""
    skills = data.get("skills", []) or []
    if not skills:
        return []
    # Ordenar por play (mais jogado) — usuário escolheu winrate pra outras
    # categorias, mas skills é menos sensível; play é mais estável aqui
    valid = [s for s in skills if int(s.get("play", 0)) > 0]
    if not valid:
        return []
    valid.sort(key=lambda s: int(s.get("play", 0)), reverse=True)
    return list(valid[0].get("order", []) or [])


def skill_priority_top(data: dict[str, Any]) -> list[str]:
    """Retorna a prioridade de max (ex: ['Q', 'W', 'E']) mais usada."""
    masteries = data.get("skill_masteries", []) or []
    if not masteries:
        return []
    valid = [m for m in masteries if int(m.get("play", 0)) > 0]
    if not valid:
        return []
    valid.sort(key=lambda m: int(m.get("play", 0)), reverse=True)
    # `ids` pode vir como ['Q','W','E'] (strings) ou [1,2,3] (ints).
    top = valid[0]
    ids = top.get("ids", []) or []
    name_map = {1: "Q", 2: "W", 3: "E"}
    result: list[str] = []
    for i in ids:
        if isinstance(i, str) and i.upper() in {"Q", "W", "E"}:
            result.append(i.upper())
        else:
            try:
                mapped = name_map.get(int(i))
                if mapped:
                    result.append(mapped)
            except (ValueError, TypeError):
                continue
    return result
