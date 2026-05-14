"""Diferença entre dois snapshots consecutivos da partida."""
from __future__ import annotations

from dataclasses import dataclass

from rift_pilot.domain.entities.game_event import GameEvent
from rift_pilot.domain.entities.game_state import GameState


@dataclass(frozen=True)
class StateDiff:
    """Compara dois `GameState` consecutivos e expõe mudanças relevantes."""

    previous: GameState
    current: GameState

    @property
    def player_leveled_up(self) -> bool:
        return self.current.player_level != self.previous.player_level

    @property
    def abilities_changed(self) -> bool:
        return self.current.abilities != self.previous.abilities

    @property
    def items_changed(self) -> bool:
        return self.current.owned_item_ids != self.previous.owned_item_ids

    @property
    def new_events(self) -> list[GameEvent]:
        seen_ids = {ev.event_id for ev in self.previous.events}
        return [ev for ev in self.current.events if ev.event_id not in seen_ids]

    @property
    def available_skill_points(self) -> int:
        """Pontos de skill ganhos por level up que ainda não foram gastos."""
        return max(
            0,
            self.current.player_level - self.current.abilities.total_points_spent,
        )

    @property
    def previous_available_skill_points(self) -> int:
        return max(
            0,
            self.previous.player_level - self.previous.abilities.total_points_spent,
        )

    @property
    def trinket_became_available(self) -> bool:
        return self.current.trinket_available and not self.previous.trinket_available

    @property
    def trinket_charge_consumed(self) -> bool:
        """True quando uma carga da trinket foi usada (count diminuiu)."""
        return self.current.trinket_charges < self.previous.trinket_charges

    @property
    def gained_item_ids(self) -> frozenset[int]:
        return self.current.owned_item_ids - self.previous.owned_item_ids
