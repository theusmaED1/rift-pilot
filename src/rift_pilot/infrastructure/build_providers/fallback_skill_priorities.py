"""Tabela estática de prioridade Q/W/E como fallback quando o deeplol falhar.

Cada entrada usa o nome PascalCase do campeão (mesmo formato da Live API).
Atualize manualmente quando o meta mudar.
"""
from __future__ import annotations

_DEFAULT_PRIORITY: list[str] = ["Q", "W", "E"]

_SKILL_PRIORITY_BY_CHAMPION: dict[str, list[str]] = {
    # Mid
    "Akali": ["Q", "E", "W"],
    "Ahri": ["Q", "W", "E"],
    "Yasuo": ["Q", "E", "W"],
    "Yone": ["Q", "E", "W"],
    "Zed": ["Q", "E", "W"],
    "Katarina": ["Q", "E", "W"],
    "Syndra": ["Q", "W", "E"],
    "Orianna": ["Q", "W", "E"],
    "LeBlanc": ["Q", "W", "E"],
    "Vex": ["E", "Q", "W"],
    "Hwei": ["Q", "E", "W"],
    # Top
    "Darius": ["Q", "W", "E"],
    "Garen": ["E", "Q", "W"],
    "Sett": ["Q", "E", "W"],
    "Camille": ["Q", "E", "W"],
    "Fiora": ["Q", "E", "W"],
    "Riven": ["Q", "W", "E"],
    "Aatrox": ["Q", "W", "E"],
    "Mordekaiser": ["Q", "E", "W"],
    "Renekton": ["Q", "W", "E"],
    "KSante": ["Q", "E", "W"],
    # Jungle
    "Graves": ["Q", "E", "W"],
    "LeeSin": ["Q", "E", "W"],
    "Viego": ["Q", "E", "W"],
    "Kayn": ["Q", "W", "E"],
    "Warwick": ["Q", "E", "W"],
    "Hecarim": ["Q", "E", "W"],
    "MasterYi": ["Q", "E", "W"],
    # ADC
    "Jinx": ["Q", "W", "E"],
    "Caitlyn": ["Q", "W", "E"],
    "Jhin": ["Q", "W", "E"],
    "Kaisa": ["Q", "W", "E"],
    "Ezreal": ["Q", "W", "E"],
    "Lucian": ["Q", "W", "E"],
    "MissFortune": ["Q", "E", "W"],
    "Ashe": ["W", "Q", "E"],
    "Vayne": ["Q", "W", "E"],
    # Support
    "Lulu": ["E", "Q", "W"],
    "Thresh": ["Q", "E", "W"],
    "Leona": ["E", "W", "Q"],
    "Nautilus": ["Q", "E", "W"],
    "Pyke": ["Q", "E", "W"],
    "Rakan": ["W", "Q", "E"],
    "Senna": ["Q", "W", "E"],
}


def fallback_skill_priority(champion_name: str) -> list[str]:
    return _SKILL_PRIORITY_BY_CHAMPION.get(champion_name, list(_DEFAULT_PRIORITY))
