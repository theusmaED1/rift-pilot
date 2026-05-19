"""Detecta o próximo item da build e alerta quando há ouro para comprá-lo."""
from __future__ import annotations

from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.entities.recommended_build import RecommendedBuild
from rift_pilot.domain.entities.state_diff import StateDiff
from rift_pilot.settings.constants import EventPriority, EventTags, Timing
from rift_pilot.settings.messages import TTSMessages


class NextItemDetector:
    """Acompanha o próximo item da build e fala em dois momentos.

    1. **Alerta imediato** (prioridade alta) quando o ouro cruza o custo restante.
    2. **Lembrete periódico** (prioridade baixa) repetindo o próximo item.

    Custo restante é consciente de receita: se já tem um componente, só precisa
    do custo faltante até completar o item final.
    """

    def __init__(
        self,
        build: RecommendedBuild,
        item_prices: dict[int, int],
        item_sources: dict[int, list[int]] | None = None,
    ) -> None:
        self._build = build
        self._item_prices = item_prices
        self._item_sources = item_sources or {}
        self._last_periodic_reminder_at: float = (
            Timing.NEXT_ITEM_FIRST_REMINDER_SECONDS
            - Timing.NEXT_ITEM_PERIODIC_INTERVAL_SECONDS
        )
        self._last_affordable_item_id: int | None = None

    def detect(self, diff: StateDiff) -> list[CoachEvent]:
        next_item = self._find_next_unowned_item(diff.current.owned_item_ids)
        if next_item is None:
            return []

        item_id, item_name = next_item
        remaining = self._remaining_cost(item_id, diff.current.owned_item_ids)
        now = diff.current.game_time_seconds

        affordable_event = self._affordable_alert(
            diff, item_id, item_name, remaining
        )
        if affordable_event:
            self._last_periodic_reminder_at = now
            return [affordable_event]

        if (
            now - self._last_periodic_reminder_at
            >= Timing.NEXT_ITEM_PERIODIC_INTERVAL_SECONDS
        ):
            self._last_periodic_reminder_at = now
            can_afford = remaining > 0 and diff.current.current_gold >= remaining
            missing_boots = self._missing_boots_text(diff.current.owned_item_ids)
            message = TTSMessages.next_item_reminder(item_name, can_afford, missing_boots)
            return [
                CoachEvent(
                    message=message,
                    priority=EventPriority.NEXT_ITEM_PERIODIC,
                    tag=EventTags.NEXT_ITEM,
                )
            ]

        return []

    def _affordable_alert(
        self,
        diff: StateDiff,
        item_id: int,
        item_name: str,
        remaining_cost: int,
    ) -> CoachEvent | None:
        if remaining_cost <= 0 or self._last_affordable_item_id == item_id:
            return None
        if diff.current.current_gold >= remaining_cost > diff.previous.current_gold:
            self._last_affordable_item_id = item_id
            return CoachEvent(
                message=TTSMessages.gold_reached_for_item(item_name),
                priority=EventPriority.NEXT_ITEM_AFFORDABLE,
                tag=EventTags.NEXT_ITEM,
            )
        return None

    def _find_next_unowned_item(
        self,
        owned_item_ids: frozenset[int],
    ) -> tuple[int, str] | None:
        for item_id, item_name in self._build.items_in_purchase_order():
            if item_id not in owned_item_ids:
                return item_id, item_name
        return None

    def _missing_boots_text(self, owned_item_ids: frozenset[int]) -> str | None:
        if not self._build.boots:
            return None
        if self._build.boots_id in owned_item_ids:
            return None
        return self._build.boots

    def _invested(
        self,
        target: int,
        owned: frozenset[int],
        memo: dict[int, int] | None = None,
        _guard: int = 0,
    ) -> int:
        """Gold already invested in target item, considering owned recipe components.

        If target is in inventory, returns full price. Otherwise, recursively sums
        investment in components of its recipe. Capped at target's total price
        (combination cost only paid upon completion).
        """
        if memo is None:
            memo = {}
        if target in owned:
            return self._item_prices.get(target, 0)
        if target in memo:
            return memo[target]
        if _guard > 12:  # Recursion guard (LoL recipes are shallow)
            return 0
        invested = 0
        for component in self._item_sources.get(target, []):
            invested += self._invested(component, owned, memo, _guard + 1)
        invested = min(invested, self._item_prices.get(target, 0))
        memo[target] = invested
        return invested

    def _remaining_cost(self, target: int, owned: frozenset[int]) -> int:
        """Remaining gold needed to complete target item."""
        full_price = self._item_prices.get(target, 0)
        invested = self._invested(target, owned)
        return max(0, full_price - invested)
