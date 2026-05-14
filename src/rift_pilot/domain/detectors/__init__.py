"""Detectores que transformam StateDiff em eventos a serem anunciados."""

from rift_pilot.domain.detectors.build_announcer import build_announcement_event
from rift_pilot.domain.detectors.event_detector import EventDetector
from rift_pilot.domain.detectors.next_item_detector import NextItemDetector
from rift_pilot.domain.detectors.objective_detector import ObjectiveDetector
from rift_pilot.domain.detectors.skill_point_detector import SkillPointDetector

__all__ = [
    "EventDetector",
    "NextItemDetector",
    "ObjectiveDetector",
    "SkillPointDetector",
    "build_announcement_event",
]
