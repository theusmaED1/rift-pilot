"""Estimador puro de stats de campeão (sem I/O).

`stat = base + per_level·growth(level) + Σ itens + runas`. Validado
empiricamente contra `activePlayer.championStats` (~0% de erro quando os
inputs estão corretos). Os stats base vêm da Wiki (champion_bases.json),
os de item do Data Dragon — esta camada só faz a aritmética.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Crescimento per-level oficial da Riot.
def growth(level: int) -> float:
    n = max(1, level)
    return (n - 1) * (0.7025 + 0.0175 * (n - 1))


# Stat shards (validados empiricamente). Só os que afetam o StatBlock.
_SHARD_ADAPTIVE = 5008   # +5.4 AD OU +9 AP (o tipo de bônus que o champ tem mais)
_SHARD_HP_SCALING = 5001  # +10 HP por level
_SHARD_HP_FLAT = 5011     # +65 HP
_SHARD_ARMOR = 5002       # +6 armor
_SHARD_MR = 5003          # +8 MR
_SHARD_AS = 5005          # +10% attack speed
_ADAPTIVE_AD = 5.4
_ADAPTIVE_AP = 9.0


@dataclass(frozen=True)
class ChampionBase:
    """Stats base + per-level de um campeão (fonte: Wiki)."""

    apiname: str
    resource: str          # "Mana" | "Energy" | "None" | outros
    rangetype: str         # "Melee" | "Ranged"
    hp_base: float
    hp_lvl: float
    mp_base: float
    mp_lvl: float
    arm_base: float
    arm_lvl: float
    mr_base: float
    mr_lvl: float
    dam_base: float
    dam_lvl: float
    as_base: float
    as_lvl: float          # percentual (3.3 = +3.3%/level)

    @classmethod
    def from_json(cls, apiname: str, entry: dict) -> "ChampionBase":
        s = entry["stats"]
        return cls(
            apiname=apiname,
            resource=entry.get("resource", "None"),
            rangetype=entry.get("rangetype", ""),
            hp_base=s["hp_base"], hp_lvl=s["hp_lvl"],
            mp_base=s.get("mp_base", 0.0), mp_lvl=s.get("mp_lvl", 0.0),
            arm_base=s["arm_base"], arm_lvl=s["arm_lvl"],
            mr_base=s["mr_base"], mr_lvl=s["mr_lvl"],
            dam_base=s["dam_base"], dam_lvl=s["dam_lvl"],
            as_base=s["as_base"], as_lvl=s["as_lvl"],
        )


@dataclass(frozen=True)
class RunePage:
    """Apenas o que afeta o StatBlock: os 3 stat shards."""

    stat_mod_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class StatBlock:
    summoner_name: str
    champion: str
    level: int
    max_hp: float
    max_resource: float
    resource_type: str            # "mana" | "energy" | "none"
    total_ad: float
    ability_power: float
    armor: float
    magic_resist: float
    attack_speed: float
    items: tuple[int, ...] = ()
    confidence: str = "high"      # "high" | "low"
    confidence_reason: str | None = None


def _sum_item(item_stats: list[dict], key: str) -> float:
    return sum(float(s.get(key, 0) or 0) for s in item_stats)


def _resource_type(resource: str) -> str:
    r = (resource or "").lower()
    if r == "mana":
        return "mana"
    if r == "energy":
        return "energy"
    return "none"


def estimate_stat_block(
    *,
    summoner_name: str,
    base: ChampionBase,
    level: int,
    item_stats: list[dict],
    item_ids: tuple[int, ...] = (),
    rune_page: RunePage | None = None,
    confidence: str = "high",
    confidence_reason: str | None = None,
) -> StatBlock:
    """Calcula o StatBlock. `item_stats` = lista dos dicts `stats` do DD
    (um por item possuído). `rune_page` opcional (shards)."""
    g = growth(level)
    shard_ids = list(rune_page.stat_mod_ids) if rune_page else []

    # Bônus de item por tipo (necessário pra resolver o shard adaptive).
    item_ad = _sum_item(item_stats, "FlatPhysicalDamageMod")
    item_ap = _sum_item(item_stats, "FlatMagicDamageMod")

    # Shard adaptive: cada 5008 dá AD ou AP conforme o maior bônus atual.
    # Empate / zero → AD (regra da Riot).
    n_adaptive = shard_ids.count(_SHARD_ADAPTIVE)
    adaptive_ad = adaptive_ap = 0.0
    if n_adaptive:
        if item_ap > item_ad:
            adaptive_ap = n_adaptive * _ADAPTIVE_AP
        else:
            adaptive_ad = n_adaptive * _ADAPTIVE_AD

    shard_hp = (
        shard_ids.count(_SHARD_HP_FLAT) * 65.0
        + shard_ids.count(_SHARD_HP_SCALING) * 10.0 * level
    )
    shard_armor = shard_ids.count(_SHARD_ARMOR) * 6.0
    shard_mr = shard_ids.count(_SHARD_MR) * 8.0
    shard_as_pct = shard_ids.count(_SHARD_AS) * 0.10

    max_hp = (
        base.hp_base + base.hp_lvl * g
        + _sum_item(item_stats, "FlatHPPoolMod") + shard_hp
    )
    max_resource = base.mp_base + base.mp_lvl * g + _sum_item(
        item_stats, "FlatMPPoolMod"
    )
    total_ad = base.dam_base + base.dam_lvl * g + item_ad + adaptive_ad
    ability_power = item_ap + adaptive_ap
    armor = base.arm_base + base.arm_lvl * g + _sum_item(
        item_stats, "FlatArmorMod"
    ) + shard_armor
    magic_resist = base.mr_base + base.mr_lvl * g + _sum_item(
        item_stats, "FlatSpellBlockMod"
    ) + shard_mr
    attack_speed = base.as_base * (
        1.0
        + (base.as_lvl / 100.0) * g
        + _sum_item(item_stats, "PercentAttackSpeedMod")
        + shard_as_pct
    )

    return StatBlock(
        summoner_name=summoner_name,
        champion=base.apiname,
        level=level,
        max_hp=max_hp,
        max_resource=max_resource,
        resource_type=_resource_type(base.resource),
        total_ad=total_ad,
        ability_power=ability_power,
        armor=armor,
        magic_resist=magic_resist,
        attack_speed=attack_speed,
        items=item_ids,
        confidence=confidence,
        confidence_reason=confidence_reason,
    )
