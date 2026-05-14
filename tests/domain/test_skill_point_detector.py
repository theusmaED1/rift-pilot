"""Testes do `SkillPointDetector`."""

from lol_coach.domain.detectors.skill_point_detector import SkillPointDetector
from lol_coach.settings.constants import EventPriority, EventTags


def test_emits_event_when_player_levels_up(make_state, make_diff):
    detector = SkillPointDetector(skill_priority=["Q", "W", "E"])
    diff = make_diff(
        previous=make_state(player_level=1, q=1),
        current=make_state(player_level=2, q=1, game_time_seconds=120.0),
    )

    events = detector.detect(diff)

    assert len(events) == 1
    assert events[0].priority == EventPriority.SKILL_GAINED
    assert events[0].tag == EventTags.SKILL
    assert "W" in events[0].message


def test_does_not_emit_when_no_points_available(make_state, make_diff):
    detector = SkillPointDetector(skill_priority=["Q", "W", "E"])
    diff = make_diff(
        previous=make_state(player_level=3, q=1, w=1, e=1),
        current=make_state(player_level=3, q=1, w=1, e=1),
    )

    assert detector.detect(diff) == []


def test_uses_skill_sequence_when_provided(make_state, make_diff):
    detector = SkillPointDetector(skill_sequence=[1, 2, 3, 1, 1, 4, 1, 2, 1, 2, 4, 2, 2, 3, 3])
    diff = make_diff(
        previous=make_state(player_level=1, q=0),
        current=make_state(player_level=2, q=1, game_time_seconds=120.0),
    )

    events = detector.detect(diff)

    assert events
    assert "W" in events[0].message


def test_fallback_priority_used_when_sequence_missing(make_state, make_diff):
    detector = SkillPointDetector(skill_priority=["W", "Q", "E"])
    diff = make_diff(
        previous=make_state(player_level=1, q=0, w=0),
        current=make_state(player_level=2, q=0, w=0, game_time_seconds=120.0),
    )

    events = detector.detect(diff)

    assert events
    assert "W" in events[0].message


def test_recommends_r_when_unlocked_and_not_maxed(make_state, make_diff):
    detector = SkillPointDetector(skill_priority=["Q", "W", "E"])
    diff = make_diff(
        previous=make_state(player_level=5, q=3, w=1, e=1, r=0),
        current=make_state(player_level=6, q=3, w=1, e=1, r=0, game_time_seconds=400.0),
    )

    events = detector.detect(diff)

    assert events
    assert "R" in events[0].message
