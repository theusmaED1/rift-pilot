"""Detectores que transformam StateDiff em eventos a serem anunciados."""

from lol_coach.domain.detectors.build_announcer import build_announcement_event
from lol_coach.domain.detectors.event_detector import EventDetector
from lol_coach.domain.detectors.next_item_detector import NextItemDetector
from lol_coach.domain.detectors.objective_detector import ObjectiveDetector
from lol_coach.domain.detectors.skill_point_detector import SkillPointDetector

__all__ = [
    "EventDetector",
    "NextItemDetector",
    "ObjectiveDetector",
    "SkillPointDetector",
    "build_announcement_event",
]
