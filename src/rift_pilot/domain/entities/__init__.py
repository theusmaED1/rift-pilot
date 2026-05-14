"""Entidades imutáveis que representam o estado do jogo e os eventos do coach."""

from rift_pilot.domain.entities.abilities import Abilities
from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.entities.game_event import GameEvent
from rift_pilot.domain.entities.game_state import GameState
from rift_pilot.domain.entities.recommended_build import (
    ProviderResult,
    RecommendedBuild,
)
from rift_pilot.domain.entities.state_diff import StateDiff

__all__ = [
    "Abilities",
    "CoachEvent",
    "GameEvent",
    "GameState",
    "ProviderResult",
    "RecommendedBuild",
    "StateDiff",
]
