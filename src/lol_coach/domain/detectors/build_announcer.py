"""Constrói o evento de anúncio inicial da build recomendada."""
from __future__ import annotations

from lol_coach.domain.entities.coach_event import CoachEvent
from lol_coach.domain.entities.recommended_build import RecommendedBuild
from lol_coach.settings.constants import EventPriority
from lol_coach.settings.messages import TTSMessages, translate_position


def build_announcement_event(build: RecommendedBuild) -> CoachEvent:
    """Produz um único `CoachEvent` falando a build completa.

    Usado uma vez por partida, logo que a build é carregada.
    """
    parts: list[str] = [
        TTSMessages.build_introduction(build.champion, translate_position(build.position))
    ]

    if build.starter_items:
        parts.append(TTSMessages.build_starters(build.starter_items))

    if build.core_items:
        parts.append(TTSMessages.build_core(build.core_items))

    if build.boots:
        parts.append(TTSMessages.build_boots(build.boots))

    if build.skill_priority:
        parts.append(TTSMessages.build_max_order(build.skill_priority))

    return CoachEvent(message=" ".join(parts), priority=EventPriority.BUILD_ANNOUNCE)
