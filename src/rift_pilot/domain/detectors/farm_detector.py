"""Detector de feedback de farm.

Três avaliações (A: CS/min vs ideal, B: vs oponente da rota, C: maior da
partida), unificadas por um cooldown global anti-spam: farm fala no máximo
1x a cada FARM_GLOBAL_COOLDOWN segundos, e só a mensagem de maior prioridade
disponível na janela.
"""
from __future__ import annotations

import collections
import logging
import time

from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.entities.state_diff import StateDiff
from rift_pilot.settings.constants import EventPriority, EventTags
from rift_pilot.settings.messages import TTSMessages

logger = logging.getLogger(__name__)

# Janela anti-repetição: uma frase só reaparece após RECENT_WINDOW outras
# da mesma categoria. Com 8+ variantes por combinação, sempre sobra pool.
RECENT_WINDOW = 4

# TTL do evento de farm. Após esse tempo na fila, a fala é descartada pelo
# worker (já obsoleta dado o ciclo detect->IA-removida->TTS->fila).
FARM_TTL = 8.0

# Chegada de wave / nascimento de camps por posição (segundos)
_WAVE_ARRIVAL = {
    "MIDDLE": 52.0,
    "TOP": 62.0,
    "BOTTOM": 62.0,
    "JUNGLE": 55.0,
}

# Constantes configuráveis (sujeitas a validação em partidas reais)
CS_PER_MIN_IDEAL = 7.0
FARM_GLOBAL_COOLDOWN = 120.0     # único cooldown de emissão de farm (anti-spam)
CS_MIN_GATE_DELAY = 60.0         # A elegível após wave_arrival + isto
VS_OPPONENT_START_GT = 240.0     # B elegível após 4 min
GLOBAL_START_GT = 360.0          # C elegível após 6 min
OPPONENT_CS_THRESHOLD = 10
GLOBAL_LEAD_MARGIN = 20          # C só se liderar o 2º por esta margem

# Prioridade (menor número = mais prioritário). Só 1 é falado por janela.
_PRIO_A_LOW = 1
_PRIO_B_BEHIND = 2
_PRIO_C_HIGHEST = 3
_PRIO_B_AHEAD = 4
_PRIO_A_GOOD = 5


class FarmDetector:
    """Feedback de farm com cooldown global e seleção por prioridade.

    Suporte (UTILITY) não recebe feedback de farm.
    """

    def __init__(
        self,
        tone: str = "neutral",
        mode: str = "simple",
    ):
        self._tone = tone
        self._mode = mode
        self._last_farm_spoken_gt: float = -float("inf")
        self._farm_start_gt: float | None = None
        # Janela deslizante de templates recentes por categoria (anti-repeat).
        self._recent_by_category: dict[str, collections.deque[str]] = {}
        logger.info(
            f"[FarmDetector] Inicializado — tone={tone!r}, mode={mode!r} "
            f"(determinístico, sem IA)"
        )

    def _recent(self, category: str) -> collections.deque[str]:
        return self._recent_by_category.setdefault(
            category, collections.deque(maxlen=RECENT_WINDOW)
        )

    def detect(self, diff: StateDiff) -> list[CoachEvent]:
        gt = diff.current.game_time_seconds
        position = diff.current.position

        # Suporte e posição inválida: sem feedback de farm
        if not position or position == "UTILITY":
            return []

        wave_arrival = _WAVE_ARRIVAL.get(position, 52.0)

        # Marca o início da contagem de farm (chegada da wave/camp)
        if self._farm_start_gt is None and gt >= wave_arrival:
            self._farm_start_gt = wave_arrival
            logger.info(
                f"[FarmDetector] Farm tracking iniciado — wave_arrival={wave_arrival:.0f}s "
                f"para {position} (gt atual={gt:.1f}s)"
            )

        if self._farm_start_gt is None:
            return []

        # Cooldown global anti-spam
        if gt - self._last_farm_spoken_gt < FARM_GLOBAL_COOLDOWN:
            return []

        # Coleta candidatos elegíveis: (prioridade, builder_callable)
        candidates: list[tuple[int, Any]] = []

        # ── FEEDBACK A — farm atual vs farm ideal NO MOMENTO ──
        if gt >= wave_arrival + CS_MIN_GATE_DELAY:
            elapsed_min = (gt - self._farm_start_gt) / 60.0
            if elapsed_min > 0:
                my_farm = diff.current.creep_score
                # Farm que se espera ter AGORA (não média/min): ideal/min * minutos
                ideal_now = round(CS_PER_MIN_IDEAL * elapsed_min)
                if my_farm < ideal_now:
                    candidates.append(
                        (_PRIO_A_LOW, lambda: self._farm_low(my_farm, ideal_now))
                    )
                else:
                    candidates.append(
                        (_PRIO_A_GOOD, lambda: self._farm_good(my_farm, ideal_now))
                    )

        # ── FEEDBACK B — vs oponente da mesma rota ──
        if gt >= VS_OPPONENT_START_GT and diff.current.lane_enemy_cs is not None:
            diff_cs = diff.current.creep_score - diff.current.lane_enemy_cs
            enemy = diff.current.lane_enemy_champion or "inimigo"
            if diff_cs <= -OPPONENT_CS_THRESHOLD:
                behind = abs(diff_cs)
                candidates.append(
                    (_PRIO_B_BEHIND, lambda: self._farm_behind(behind, enemy))
                )
            elif diff_cs >= OPPONENT_CS_THRESHOLD:
                ahead = diff_cs
                candidates.append(
                    (_PRIO_B_AHEAD, lambda: self._farm_ahead(ahead, enemy))
                )
            # faixa neutra (-10, +10): nada

        # ── FEEDBACK C — maior farm da partida POR MARGEM RELEVANTE ──
        # Só parabeniza se for o maior E liderar o 2º colocado por >= 20.
        # Evita "parabéns" quando todos farmam mal e a liderança é técnica.
        if gt >= GLOBAL_START_GT and diff.current.highest_cs_in_game > 0:
            my_cs = diff.current.creep_score
            is_highest = my_cs >= diff.current.highest_cs_in_game
            lead = my_cs - diff.current.second_highest_cs_in_game
            if is_highest and lead >= GLOBAL_LEAD_MARGIN:
                candidates.append(
                    (_PRIO_C_HIGHEST, lambda: self._farm_highest(my_cs))
                )

        if not candidates:
            return []

        # Escolhe o de maior prioridade (menor número)
        candidates.sort(key=lambda c: c[0])
        prio, builder = candidates[0]
        message, event_priority = builder()
        self._last_farm_spoken_gt = gt
        logger.info(
            f"[FarmDetector] gt={gt:.1f}s — emitindo prio={prio}: {message[:70]}"
        )
        return [
            CoachEvent(
                message=message,
                priority=event_priority,
                tag=EventTags.FARM,
                expires_at=time.monotonic() + FARM_TTL,
            )
        ]

    # ── Builders: retornam (mensagem, EventPriority p/ SpeechQueue) ──────────
    # Todos determinísticos: TTSMessages.farm_* retorna (template, frase). O
    # template cru entra na janela anti-repeat; a frase formatada é falada.
    # `my_farm`/`ideal_now`/`my_cs` ficam na assinatura por compat com os
    # call sites em detect(), mas o texto não cita números (decisão de UX:
    # número vira obsoleto na latência detect->fala).

    def _farm_low(self, my_farm: int, ideal_now: int) -> tuple[str, int]:
        recent = self._recent("farm_low")
        template, msg = TTSMessages.farm_low(
            tone=self._tone, mode=self._mode, recent=tuple(recent)
        )
        recent.append(template)
        return msg, EventPriority.FARM_BEHIND

    def _farm_good(self, my_farm: int, ideal_now: int) -> tuple[str, int]:
        recent = self._recent("farm_good")
        template, msg = TTSMessages.farm_good(
            tone=self._tone, mode=self._mode, recent=tuple(recent)
        )
        recent.append(template)
        return msg, EventPriority.FARM_LOW

    def _farm_behind(self, diff_cs: int, enemy_name: str) -> tuple[str, int]:
        recent = self._recent("farm_behind")
        template, msg = TTSMessages.farm_behind(
            diff_cs=diff_cs,
            enemy_name=enemy_name,
            tone=self._tone,
            mode=self._mode,
            recent=tuple(recent),
        )
        recent.append(template)
        return msg, EventPriority.FARM_BEHIND

    def _farm_ahead(self, diff_cs: int, enemy_name: str) -> tuple[str, int]:
        recent = self._recent("farm_ahead")
        template, msg = TTSMessages.farm_ahead(
            diff_cs=diff_cs,
            enemy_name=enemy_name,
            tone=self._tone,
            mode=self._mode,
            recent=tuple(recent),
        )
        recent.append(template)
        return msg, EventPriority.FARM_LOW

    def _farm_highest(self, my_cs: int) -> tuple[str, int]:
        recent = self._recent("farm_highest")
        template, msg = TTSMessages.farm_highest(
            tone=self._tone, mode=self._mode, recent=tuple(recent)
        )
        recent.append(template)
        return msg, EventPriority.FARM_LOW
