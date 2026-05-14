"""Detecta o próximo item da build e alerta quando há ouro para comprá-lo."""
from __future__ import annotations

from lol_coach.domain.entities.coach_event import CoachEvent
from lol_coach.domain.entities.recommended_build import RecommendedBuild
from lol_coach.domain.entities.state_diff import StateDiff
from lol_coach.settings.constants import EventPriority, EventTags, Timing
from lol_coach.settings.messages import TTSMessages


class NextItemDetector:
    """Acompanha o próximo item da build e fala em dois momentos.

    1. **Alerta imediato** (prioridade alta) quando o ouro cruza o preço do item.
    2. **Lembrete periódico** (prioridade baixa) repetindo o próximo item.
    """

    def __init__(
        self,
        build: RecommendedBuild,
        item_prices: dict[int, int],
    ) -> None:
        self._build = build
        self._item_prices = item_prices
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
        price = self._item_prices.get(item_id, 0)
        now = diff.current.game_time_seconds

        affordable_event = self._affordable_alert(diff, item_id, item_name, price)
        if affordable_event:
            self._last_periodic_reminder_at = now
            return [affordable_event]

        if (
            now - self._last_periodic_reminder_at
            >= Timing.NEXT_ITEM_PERIODIC_INTERVAL_SECONDS
        ):
            self._last_periodic_reminder_at = now
            can_afford = price > 0 and diff.current.current_gold >= price
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
        price: int,
    ) -> CoachEvent | None:
        if price <= 0 or self._last_affordable_item_id == item_id:
            return None
        if diff.current.current_gold >= price > diff.previous.current_gold:
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
