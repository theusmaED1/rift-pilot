"""Testes do `NextItemDetector`."""

from lol_coach.domain.detectors.next_item_detector import NextItemDetector
from lol_coach.domain.entities.recommended_build import RecommendedBuild
from lol_coach.settings.constants import EventPriority


def _build_with_items() -> RecommendedBuild:
    return RecommendedBuild(
        champion="Ahri",
        position="MIDDLE",
        starter_items=["Cajado Doran"],
        starter_item_ids=[1056],
        core_items=["Pedra Lunar Despertada", "Calice Sombrio"],
        core_item_ids=[3001, 3010],
        boots="Botas Mágicas",
        boots_id=3020,
    )


def test_alerts_immediately_when_gold_crosses_item_price(make_state, make_diff):
    build = _build_with_items()
    detector = NextItemDetector(build=build, item_prices={1056: 450, 3001: 3000, 3010: 2500})
    diff = make_diff(
        previous=make_state(current_gold=400.0),
        current=make_state(current_gold=460.0, game_time_seconds=120.0),
    )

    events = detector.detect(diff)

    assert len(events) == 1
    assert events[0].priority == EventPriority.NEXT_ITEM_AFFORDABLE
    assert "Cajado Doran" in events[0].message


def test_does_not_alert_when_gold_is_still_short(make_state, make_diff):
    build = _build_with_items()
    detector = NextItemDetector(build=build, item_prices={1056: 450})
    diff = make_diff(
        previous=make_state(current_gold=100.0, game_time_seconds=3.0),
        current=make_state(current_gold=200.0, game_time_seconds=4.0),
    )

    events = detector.detect(diff)

    assert events == []


def test_skips_owned_items_and_targets_next_one(make_state, make_diff):
    build = _build_with_items()
    detector = NextItemDetector(build=build, item_prices={1056: 450, 3001: 3000})
    diff = make_diff(
        previous=make_state(current_gold=2800.0, owned_item_ids=(1056,)),
        current=make_state(current_gold=3100.0, owned_item_ids=(1056,), game_time_seconds=600.0),
    )

    events = detector.detect(diff)

    assert events
    assert "Pedra Lunar Despertada" in events[0].message
