"""Detector de feedback de farm (CS/min e comparação com inimigo de lane)."""
from __future__ import annotations

import time

from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.entities.state_diff import StateDiff
from rift_pilot.settings.constants import EventPriority, EventTags
from rift_pilot.settings.messages import TTSMessages

# Wave arrival timing por posição (segundos)
_WAVE_ARRIVAL = {
    "MIDDLE": 52.0,
    "TOP": 62.0,
    "BOTTOM": 62.0,
    "JUNGLE": 55.0,
}

# CS/min ideal por posição
_CS_IDEAL_PER_MINUTE = {
    "TOP": 8.0,
    "MIDDLE": 8.0,
    "BOTTOM": 8.0,
    "JUNGLE": 8.0,
}


class FarmDetector:
    """Emite alertas de farm: CS baixo ou atrás do inimigo de lane.

    Dois tipos de feedback:
    1. FARM_BEHIND: Se estiver 10+ CS atrás do inimigo de mesma posição (max 1x/60s)
    2. FARM_LOW: Se CS/min < ideal em épocas de 60s
    """

    def __init__(
        self,
        tone: str = "neutral",
        farm_check_interval: float = 60.0,
        enemy_threshold: int = 10,
    ):
        self._tone = tone
        self._farm_check_interval = farm_check_interval
        self._enemy_threshold = enemy_threshold
        self._last_behind_alert_gt = -float("inf")
        self._farm_epoch_start_gt = -float("inf")
        self._farm_start_gt: float | None = None

    def detect(self, diff: StateDiff) -> list[CoachEvent]:
        """Detecta farm low ou behind vs inimigo de lane."""
        events: list[CoachEvent] = []
        gt = diff.current.game_time_seconds
        position = diff.current.position

        # Ignora UTILITY (support) — não há feedback de farm
        if not position or position == "UTILITY":
            return events

        # Marca o GT de início do farm (após waves chegarem)
        wave_arrival = _WAVE_ARRIVAL.get(position, 52.0)
        if self._farm_start_gt is None and gt >= wave_arrival + 60:
            self._farm_start_gt = gt

        # Antes de farm_start_gt, ignora
        if self._farm_start_gt is None:
            return events

        # FARM_BEHIND: comparação com inimigo de lane (threshold 10 CS)
        if diff.current.lane_enemy_cs is not None:
            cs_diff = diff.current.lane_enemy_cs - diff.current.creep_score
            if cs_diff >= self._enemy_threshold:
                if gt - self._last_behind_alert_gt >= self._farm_check_interval:
                    enemy_name = self._find_enemy_name(diff)
                    message = TTSMessages.farm_behind(
                        diff_cs=cs_diff,
                        enemy_name=enemy_name or "inimigo",
                        tone=self._tone,
                    )
                    events.append(
                        CoachEvent(
                            message=message,
                            priority=EventPriority.FARM_BEHIND,
                            tag=EventTags.FARM,
                        )
                    )
                    self._last_behind_alert_gt = gt

        # FARM_LOW: CS/min em épocas de 60s
        if gt - self._farm_epoch_start_gt >= self._farm_check_interval:
            time_elapsed = gt - self._farm_start_gt
            if time_elapsed > 0:
                cs_per_minute = (diff.current.creep_score / time_elapsed) * 60
                if cs_per_minute < _CS_IDEAL_PER_MINUTE.get(position, 8.0):
                    message = TTSMessages.farm_low(tone=self._tone)
                    events.append(
                        CoachEvent(
                            message=message,
                            priority=EventPriority.FARM_LOW,
                            tag=EventTags.FARM,
                        )
                    )
            self._farm_epoch_start_gt = gt

        return events

    def _find_enemy_name(self, diff: StateDiff) -> str | None:
        """Encontra o nome do inimigo de mesma posição."""
        position = diff.current.position
        # Esta é uma heurística simples; em um sistema real, consultaria
        # a GameState para allPlayers inimigos
        return None
