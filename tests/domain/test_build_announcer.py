"""Testes do `build_announcement_event`."""

from rift_pilot.domain.detectors.build_announcer import build_announcement_event
from rift_pilot.domain.entities.recommended_build import RecommendedBuild
from rift_pilot.settings.constants import EventPriority


def test_announcement_includes_all_sections_when_build_is_complete():
    build = RecommendedBuild(
        champion="Ahri",
        position="MIDDLE",
        starter_items=["Cajado Doran"],
        core_items=["Pedra Lunar Despertada"],
        boots="Botas Mágicas",
        skill_priority=["Q", "W", "E"],
    )

    event = build_announcement_event(build)

    assert event.priority == EventPriority.BUILD_ANNOUNCE
    assert "Ahri" in event.message
    assert "mid" in event.message
    assert "Cajado Doran" in event.message
    assert "Pedra Lunar Despertada" in event.message
    assert "Botas Mágicas" in event.message
    assert "Q" in event.message and "W" in event.message and "E" in event.message


def test_announcement_translates_position_to_pt_br():
    build = RecommendedBuild(champion="Lulu", position="UTILITY")

    event = build_announcement_event(build)

    assert "suporte" in event.message
