"""Testes do `ObjectiveDetector` para dragão/barão/arauto."""

from lol_coach.domain.detectors.objective_detector import ObjectiveDetector
from lol_coach.settings.constants import EventPriority, GameRules


def _advance(detector: ObjectiveDetector, diff_factory, **state_kwargs):
    diff = diff_factory(current=None, previous=None)
    return detector.detect(diff)


def test_warns_about_dragon_60_seconds_before_initial_spawn(make_state, make_diff):
    detector = ObjectiveDetector()
    dragon_spawn = GameRules.DRAGON_INITIAL_SPAWN_SECONDS
    diff = make_diff(
        previous=make_state(game_time_seconds=dragon_spawn - 65.0),
        current=make_state(game_time_seconds=dragon_spawn - 59.0),
    )

    events = detector.detect(diff)

    dragon_events = [event for event in events if "Dragão" in event.message]
    assert dragon_events
    assert dragon_events[0].priority == EventPriority.OBJECTIVE_APPROACHING


def test_does_not_repeat_same_warning_for_same_timer(make_state, make_diff):
    detector = ObjectiveDetector()
    dragon_spawn = GameRules.DRAGON_INITIAL_SPAWN_SECONDS

    detector.detect(make_diff(
        previous=make_state(game_time_seconds=dragon_spawn - 65.0),
        current=make_state(game_time_seconds=dragon_spawn - 59.0),
    ))
    second_diff = make_diff(
        previous=make_state(game_time_seconds=dragon_spawn - 59.0),
        current=make_state(game_time_seconds=dragon_spawn - 58.0),
    )

    events = detector.detect(second_diff)

    assert all("1 minuto" not in event.message for event in events)


def test_imminent_warning_uses_higher_priority(make_state, make_diff):
    detector = ObjectiveDetector()
    dragon_spawn = GameRules.DRAGON_INITIAL_SPAWN_SECONDS
    diff = make_diff(
        previous=make_state(game_time_seconds=dragon_spawn - 11.0),
        current=make_state(game_time_seconds=dragon_spawn - 5.0),
    )

    events = detector.detect(diff)

    imminent = [event for event in events if event.priority == EventPriority.OBJECTIVE_IMMINENT]
    assert imminent
    assert any("10 segundos" in event.message for event in imminent)


def test_warns_about_voidgrubs_at_initial_spawn(make_state, make_diff):
    detector = ObjectiveDetector()
    voidgrubs_spawn = GameRules.VOIDGRUBS_INITIAL_SPAWN_SECONDS
    diff = make_diff(
        previous=make_state(game_time_seconds=voidgrubs_spawn - 65.0),
        current=make_state(game_time_seconds=voidgrubs_spawn - 59.0),
    )

    events = detector.detect(diff)

    larvae_events = [event for event in events if "Larvas" in event.message]
    assert larvae_events


def test_herald_initial_spawn_is_at_ten_minutes():
    assert GameRules.HERALD_INITIAL_SPAWN_SECONDS == 600.0


def test_voidgrubs_initial_spawn_is_at_five_minutes():
    assert GameRules.VOIDGRUBS_INITIAL_SPAWN_SECONDS == 300.0
