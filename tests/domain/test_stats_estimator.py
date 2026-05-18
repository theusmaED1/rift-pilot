"""Testes do estimador puro de stats e do matching de runas.

Valores de referência da Akali batem o `championStats` real medido no
replay game_20260515_203142 (validado com 0% de erro).
"""
from __future__ import annotations

import pytest

from rift_pilot.domain.services.stats_estimator import (
    ChampionBase,
    RunePage,
    estimate_stat_block,
    growth,
)
from rift_pilot.infrastructure.opgg_mcp.pool_extractor import (
    match_rune_page,
    rune_ids,
)

# Akali (fonte: champion_bases.json gerado da Wiki).
_AKALI = ChampionBase(
    apiname="Akali", resource="Energy", rangetype="Melee",
    hp_base=600, hp_lvl=119, mp_base=200, mp_lvl=0,
    arm_base=23, arm_lvl=4.7, mr_base=37, mr_lvl=2.05,
    dam_base=62, dam_lvl=3.3, as_base=0.625, as_lvl=3.2,
)
# Itens do replay aos lvl 8: Doran's Shield, Hextech Alternator, Tome, Boots.
_ITEMS_L8 = [
    {"FlatHPPoolMod": 110, "FlatHPRegenMod": 0.8},  # 1054
    {"FlatMagicDamageMod": 45},                      # 3145
    {"FlatMagicDamageMod": 20},                      # 1052
    {"FlatMovementSpeedMod": 25},                    # 1001
]


def test_growth_known_values():
    assert growth(1) == 0.0
    assert growth(2) == pytest.approx(0.72, abs=1e-9)
    assert growth(8) == pytest.approx(5.775, abs=1e-9)
    assert growth(18) == pytest.approx(17.0, abs=1e-9)


def test_akali_lvl8_matches_real_championstats():
    sb = estimate_stat_block(
        summoner_name="me", base=_AKALI, level=8,
        item_stats=_ITEMS_L8,
        rune_page=RunePage(stat_mod_ids=(5008, 5008, 5001)),
    )
    assert sb.max_hp == pytest.approx(1477.2, abs=0.2)
    assert sb.total_ad == pytest.approx(81.06, abs=0.2)
    assert sb.ability_power == pytest.approx(83.0, abs=0.2)
    assert sb.armor == pytest.approx(50.14, abs=0.2)
    assert sb.magic_resist == pytest.approx(48.84, abs=0.2)
    assert sb.attack_speed == pytest.approx(0.7405, abs=0.005)
    assert sb.resource_type == "energy"
    assert sb.confidence == "high"


def test_adaptive_shard_picks_ap_when_ap_bonus_higher():
    # Item só de AP -> adaptive vira AP (2x +9).
    sb = estimate_stat_block(
        summoner_name="x", base=_AKALI, level=1,
        item_stats=[{"FlatMagicDamageMod": 40}],
        rune_page=RunePage(stat_mod_ids=(5008, 5008)),
    )
    assert sb.ability_power == pytest.approx(40 + 18, abs=1e-6)
    assert sb.total_ad == pytest.approx(_AKALI.dam_base, abs=1e-6)  # sem adaptive AD


def test_adaptive_shard_defaults_ad_on_tie():
    # Sem itens (empate 0x0) -> adaptive vira AD (2x +5.4).
    sb = estimate_stat_block(
        summoner_name="x", base=_AKALI, level=1,
        item_stats=[], rune_page=RunePage(stat_mod_ids=(5008, 5008)),
    )
    assert sb.total_ad == pytest.approx(_AKALI.dam_base + 10.8, abs=1e-6)
    assert sb.ability_power == pytest.approx(0.0, abs=1e-6)


def test_confidence_flag_propagates():
    sb = estimate_stat_block(
        summoner_name="x", base=_AKALI, level=3, item_stats=[],
        confidence="low", confidence_reason="stacking",
    )
    assert sb.confidence == "low"
    assert sb.confidence_reason == "stacking"


# ── Runas ────────────────────────────────────────────────────────────────

_MCP_DATA = {
    "runes": [
        {"primary_rune_ids": [8112, 8143, 8140, 8106],
         "primary_page_id": 8100, "secondary_rune_ids": [8444, 8451],
         "secondary_page_id": 8400, "stat_mod_ids": [5008, 5008, 5001],
         "play": 300, "win": 160},
        {"primary_rune_ids": [8128, 8126, 8138, 8106],
         "primary_page_id": 8100, "secondary_rune_ids": [8009, 8014],
         "secondary_page_id": 8000, "stat_mod_ids": [5008, 5008, 5011],
         "play": 80, "win": 40},
    ]
}


def test_rune_ids_picks_most_played():
    r = rune_ids(_MCP_DATA)
    assert r is not None
    assert r.keystone_id == 8112
    assert r.stat_mod_ids == (5008, 5008, 5001)


def test_match_rune_page_exact():
    page, exact = match_rune_page(_MCP_DATA, enemy_keystone_id=8128,
                                  enemy_secondary_tree_id=8000)
    assert exact is True
    assert page.keystone_id == 8128
    assert page.stat_mod_ids == (5008, 5008, 5011)


def test_match_rune_page_fallback_when_no_match():
    page, exact = match_rune_page(_MCP_DATA, enemy_keystone_id=9999,
                                  enemy_secondary_tree_id=9999)
    assert exact is False
    assert page is not None  # cai pra mais jogada
    assert page.keystone_id == 8112
