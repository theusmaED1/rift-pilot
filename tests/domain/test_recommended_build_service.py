"""Testes do `_derive_skill_priority_from_sequence` no `RecommendedBuildService`."""

from lol_coach.infrastructure.recommended_build_service import (
    _derive_skill_priority_from_sequence,
)


def test_annie_sequence_maxes_w_before_q():
    annie_sequence = [2, 1, 3, 2, 4, 2, 2, 1, 2, 1, 4, 1, 1, 3, 3, 4, 3, 3]

    priority = _derive_skill_priority_from_sequence(annie_sequence)

    assert priority[0] == "W"
    assert priority[1] == "Q"
    assert priority[2] == "E"


def test_ahri_sequence_maxes_q_first():
    ahri_sequence = [1, 2, 3, 1, 1, 4, 1, 2, 1, 2, 4, 2, 2, 3, 3, 4, 3, 3]

    priority = _derive_skill_priority_from_sequence(ahri_sequence)

    assert priority[0] == "Q"


def test_empty_sequence_returns_qwe_in_count_order():
    priority = _derive_skill_priority_from_sequence([])
    assert sorted(priority) == ["E", "Q", "W"]
