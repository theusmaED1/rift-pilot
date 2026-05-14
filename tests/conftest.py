"""Fixtures compartilhadas pelos testes do domínio."""
from __future__ import annotations

from typing import Callable, Iterable

import pytest

from rift_pilot.domain.entities.abilities import Abilities
from rift_pilot.domain.entities.game_event import GameEvent
from rift_pilot.domain.entities.game_state import GameState
from rift_pilot.domain.entities.state_diff import StateDiff


@pytest.fixture
def make_state() -> Callable[..., GameState]:
    """Factory para `GameState` com defaults razoáveis."""

    def _build(
        *,
        game_time_seconds: float = 60.0,
        player_level: int = 1,
        q: int = 0,
        w: int = 0,
        e: int = 0,
        r: int = 0,
        current_gold: float = 500.0,
        events: Iterable[GameEvent] = (),
        champion_name: str = "Ahri",
        position: str = "MIDDLE",
        owned_item_ids: Iterable[int] = (),
    ) -> GameState:
        return GameState(
            game_time_seconds=game_time_seconds,
            player_level=player_level,
            abilities=Abilities(q=q, w=w, e=e, r=r),
            current_gold=current_gold,
            events=list(events),
            champion_name=champion_name,
            position=position,
            owned_item_ids=frozenset(owned_item_ids),
        )

    return _build


@pytest.fixture
def make_diff(make_state) -> Callable[..., StateDiff]:
    """Factory para `StateDiff` a partir de dois snapshots."""

    def _build(previous: GameState | None = None, current: GameState | None = None) -> StateDiff:
        prev = previous if previous is not None else make_state()
        curr = current if current is not None else make_state()
        return StateDiff(previous=prev, current=curr)

    return _build


@pytest.fixture
def make_game_event() -> Callable[..., GameEvent]:
    def _build(event_id: int, name: str, time_seconds: float = 0.0) -> GameEvent:
        return GameEvent(
            event_id=event_id,
            name=name,
            time_seconds=time_seconds,
            raw_payload={},
        )

    return _build
