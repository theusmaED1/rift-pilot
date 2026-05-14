"""Testes do `MinimapReminderDetector`."""

from lol_coach.domain.detectors.minimap_reminder_detector import MinimapReminderDetector
from lol_coach.settings.constants import EventPriority, Timing
from lol_coach.settings.messages import TTSMessages


def test_does_not_fire_before_first_interval(make_state, make_diff):
    detector = MinimapReminderDetector()
    diff = make_diff(
        previous=make_state(game_time_seconds=0.0),
        current=make_state(game_time_seconds=Timing.MINIMAP_REMINDER_MIN_INTERVAL_SECONDS - 1.0),
    )

    events = detector.detect(diff)

    assert events == []


def test_fires_after_min_interval(make_state, make_diff):
    detector = MinimapReminderDetector()
    detector._next_reminder_at = 50.0

    diff = make_diff(
        previous=make_state(game_time_seconds=49.0),
        current=make_state(game_time_seconds=50.0),
    )

    events = detector.detect(diff)

    assert len(events) == 1
    assert events[0].message in TTSMessages.MINIMAP_REMINDERS
    assert events[0].priority == EventPriority.MINIMAP_REMINDER


def test_does_not_repeat_immediately_after_firing(make_state, make_diff):
    detector = MinimapReminderDetector()
    detector._next_reminder_at = 50.0

    diff = make_diff(
        previous=make_state(game_time_seconds=49.0),
        current=make_state(game_time_seconds=50.0),
    )
    detector.detect(diff)

    diff2 = make_diff(
        previous=make_state(game_time_seconds=50.0),
        current=make_state(game_time_seconds=51.0),
    )
    events = detector.detect(diff2)

    assert events == []


def test_next_reminder_time_advances_after_firing(make_state, make_diff):
    detector = MinimapReminderDetector()
    detector._next_reminder_at = 50.0

    diff = make_diff(
        previous=make_state(game_time_seconds=49.0),
        current=make_state(game_time_seconds=50.0),
    )
    detector.detect(diff)

    assert detector._next_reminder_at >= 50.0 + Timing.MINIMAP_REMINDER_MIN_INTERVAL_SECONDS
    assert detector._next_reminder_at <= 50.0 + Timing.MINIMAP_REMINDER_MAX_INTERVAL_SECONDS
