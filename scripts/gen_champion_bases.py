"""Gera champion_bases.json a partir do Module:ChampionData/data da Wiki.

A Wiki LoL (wiki.leagueoflegends.com) mantém os stats base/per-level
canônicos em um único módulo Lua. O Data Dragon tem bug crônico em
`attackdamageperlevel` (retorna 0; real ~3.0-3.3) — validado empiricamente
em Akali/Ahri/Hwei. A Wiki é a fonte correta.

Uso (rodar 1x por patch):
    python scripts/gen_champion_bases.py

Faz sanity-check contra o Data Dragon nos campos que o DD ACERTA
(hp/arm/mr/as base+lvl). Se divergirem além da tolerância, o parser
quebrou — aborta SEM gravar lixo. `dam_lvl` não é checado (DD bugado).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

WIKI_API = "https://wiki.leagueoflegends.com/en-us/api.php"
DDRAGON_VERSIONS = "https://ddragon.leagueoflegends.com/api/versions.json"
OUT_PATH = (
    Path(__file__).parent.parent
    / "src" / "rift_pilot" / "infrastructure" / "riot" / "data"
    / "champion_bases.json"
)
HEADERS = {"User-Agent": "rift-pilot-dev/0.1 (champion base stats sync)"}

# Campos scalar de `["stats"] = { ... }` que extraímos (todos aparecem ANTES
# das sub-tabelas aninhadas aram/ar/nb/ofa/urf — cortamos o bloco lá).
_STAT_FIELDS = (
    "hp_base", "hp_lvl", "mp_base", "mp_lvl",
    "arm_base", "arm_lvl", "mr_base", "mr_lvl",
    "dam_base", "dam_lvl", "as_base", "as_lvl",
    "range", "ms",
)
_NESTED_KEYS = ("aram", "ar", "nb", "ofa", "urf", "usb")

# Sanity-check: (campo_wiki, stat_dd). dam_lvl FORA — DD bugado de propósito.
_SANITY = {
    "hp_base": "hp", "hp_lvl": "hpperlevel",
    "arm_base": "armor", "arm_lvl": "armorperlevel",
    "mr_base": "spellblock", "mr_lvl": "spellblockperlevel",
    "as_base": "attackspeed",
}
_TOL = 0.02  # 2% relativo


def fetch_wiki_data() -> str:
    r = httpx.get(
        WIKI_API,
        params={
            "action": "parse",
            "page": "Module:ChampionData/data",
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        },
        timeout=60,
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()["parse"]["wikitext"]


def _find_blocks(wt: str) -> dict[str, str]:
    """Isola o texto de cada `["Nome"] = { ... }` de nível superior."""
    blocks: dict[str, str] = {}
    for m in re.finditer(r'\n  \["([^"]+)"\] = \{', wt):
        name = m.group(1)
        start = m.end()
        depth = 1
        i = start
        while i < len(wt) and depth:
            c = wt[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        blocks[name] = wt[start:i]
    return blocks


def _scalar(block: str, key: str) -> str | None:
    m = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*"?([^",\n}]+?)"?\s*,', block)
    return m.group(1).strip() if m else None


def _parse_stats(block: str) -> dict[str, float]:
    m = re.search(r'\["stats"\]\s*=\s*\{', block)
    if not m:
        return {}
    seg = block[m.end():]
    # corta no primeiro aninhamento (sub-tabelas reusam nomes como hp_lvl)
    cut = len(seg)
    for nk in _NESTED_KEYS:
        j = seg.find(f'["{nk}"]')
        if j != -1:
            cut = min(cut, j)
    seg = seg[:cut]
    out: dict[str, float] = {}
    for fld in _STAT_FIELDS:
        mm = re.search(r'\["' + fld + r'"\]\s*=\s*(-?[\d.]+)', seg)
        if mm:
            out[fld] = float(mm.group(1))
    return out


def parse_champions(wt: str) -> dict[str, dict]:
    """Parseia campeões. Alguns têm múltiplas entradas com o mesmo apiname
    (ex: 'Kled' vs 'Kled & Skaarl' — mecânica de montaria). Preferimos a
    entrada canônica (nome do bloco == apiname), que é a que casa com o
    Data Dragon. As variantes de forma são tratadas como `form_unverified`
    na camada do estimador, não aqui.
    """
    champs: dict[str, dict] = {}
    for name, block in _find_blocks(wt).items():
        apiname = _scalar(block, "apiname")
        if not apiname:
            continue
        stats = _parse_stats(block)
        if "hp_base" not in stats or "dam_lvl" not in stats:
            continue  # bloco sem stats reais (entrada não-campeão)
        entry = {
            "apiname": apiname,
            "resource": _scalar(block, "resource") or "None",
            "rangetype": _scalar(block, "rangetype") or "",
            "stats": stats,
        }
        existing = champs.get(apiname)
        if existing is None or name == apiname:
            # primeira vez, OU este bloco é o canônico (nome == apiname):
            # o canônico sempre vence variantes de forma ("X & Y").
            champs[apiname] = entry
    return champs


def sanity_check(champs: dict[str, dict]) -> list[str]:
    """Compara campos sãos contra o Data Dragon. Retorna lista de erros."""
    ver = httpx.get(DDRAGON_VERSIONS, timeout=20).json()[0]
    dd = httpx.get(
        f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/championFull.json",
        timeout=30,
    ).json()["data"]
    by_key = {c["id"]: c for c in dd.values()}  # id == apiname no DD
    errs: list[str] = []
    checked = 0
    for apiname, c in champs.items():
        ddc = by_key.get(apiname)
        if not ddc:
            continue
        dds = ddc["stats"]
        for wk, ddk in _SANITY.items():
            wv = c["stats"].get(wk)
            dv = dds.get(ddk)
            if wv is None or dv is None:
                continue
            denom = abs(dv) if abs(dv) > 1e-6 else 1.0
            if abs(wv - dv) / denom > _TOL:
                errs.append(f"{apiname}.{wk}: wiki={wv} dd={dv}")
        checked += 1
    if checked < 100:
        errs.append(f"sanity cobriu só {checked} campeões (esperado >150)")
    return errs


def main() -> None:
    print("Buscando Module:ChampionData/data da Wiki...")
    wt = fetch_wiki_data()
    print(f"  wikitext: {len(wt)} chars")
    champs = parse_champions(wt)
    print(f"  parseados: {len(champs)} campeões")
    if len(champs) < 150:
        sys.exit(f"ERRO: só {len(champs)} campeões parseados — parser quebrou.")

    print("Sanity-check contra Data Dragon (campos não-bugados)...")
    errs = sanity_check(champs)
    if errs:
        print(f"  {len(errs)} divergências:")
        for e in errs[:20]:
            print("   -", e)
        sys.exit("ERRO: sanity-check falhou — parser provavelmente quebrou. Nada gravado.")
    print("  OK — Wiki bate com DD nos campos sãos.")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {"source": "wiki.leagueoflegends.com Module:ChampionData/data",
             "champions": dict(sorted(champs.items()))},
            f, ensure_ascii=False, indent=2,
        )
    print(f"Gravado: {OUT_PATH} ({len(champs)} campeões)")


if __name__ == "__main__":
    main()
