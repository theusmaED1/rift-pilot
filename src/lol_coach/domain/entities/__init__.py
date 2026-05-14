"""Entidades imutáveis que representam o estado do jogo e os eventos do coach."""

from lol_coach.domain.entities.abilities import Abilities
from lol_coach.domain.entities.coach_event import CoachEvent
from lol_coach.domain.entities.game_event import GameEvent
from lol_coach.domain.entities.game_state import GameState
from lol_coach.domain.entities.recommended_build import (
    ProviderResult,
    RecommendedBuild,
)
from lol_coach.domain.entities.state_diff import StateDiff

__all__ = [
    "Abilities",
    "CoachEvent",
    "GameEvent",
    "GameState",
    "ProviderResult",
    "RecommendedBuild",
    "StateDiff",
]
