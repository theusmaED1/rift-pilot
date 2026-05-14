"""Testes da resolução de posição com base na summoner spell Punir."""

from lol_coach.domain.role_inference import resolve_position_for_build_lookup


def test_player_with_smite_is_treated_as_jungler_even_if_position_says_top():
    assert resolve_position_for_build_lookup("TOP", has_smite=True) == "JUNGLE"


def test_jungle_position_without_smite_is_cleared_for_provider_fallback():
    assert resolve_position_for_build_lookup("JUNGLE", has_smite=False) == ""


def test_lane_position_without_smite_is_kept():
    assert resolve_position_for_build_lookup("MIDDLE", has_smite=False) == "MIDDLE"


def test_empty_position_without_smite_returns_empty():
    assert resolve_position_for_build_lookup("", has_smite=False) == ""


def test_none_position_string_returns_empty():
    assert resolve_position_for_build_lookup("NONE", has_smite=False) == ""


def test_position_is_uppercased():
    assert resolve_position_for_build_lookup("middle", has_smite=False) == "MIDDLE"
