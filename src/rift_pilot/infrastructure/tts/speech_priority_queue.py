"""Fila de prioridade dedicada para anúncios falados."""
from __future__ import annotations

import heapq
import threading
import time

from rift_pilot.domain.entities.coach_event import CoachEvent
from rift_pilot.domain.ports.speaker import Speaker
from rift_pilot.settings.constants import Timing


class SpeechPriorityQueue:
    """Worker thread que consome eventos em ordem de prioridade.

    - `enqueue()` é não bloqueante e descarta duplicatas por `message`.
    - `cancel_by_tag()` remove eventos pendentes pelo `tag` (ex.: cancelar
      lembretes de skill quando o jogador acaba de gastar o ponto).
    - Entre falas, espera `min_gap_seconds` para evitar atropelamento.
    """

    def __init__(
        self,
        speaker: Speaker,
        min_gap_seconds: float = Timing.MIN_GAP_BETWEEN_SPEECHES_SECONDS,
    ) -> None:
        self._speaker = speaker
        self._min_gap_seconds = min_gap_seconds
        self._heap: list[tuple[int, int, CoachEvent]] = []
        self._pending_messages: set[str] = set()
        self._sequence_counter = 0
        self._lock = threading.Lock()
        self._has_items_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._worker_thread.start()

    def enqueue(self, events: list[CoachEvent]) -> None:
        if not events:
            return
        with self._lock:
            for event in events:
                if event.message in self._pending_messages:
                    continue
                heapq.heappush(
                    self._heap,
                    (-event.priority, self._sequence_counter, event),
                )
                self._pending_messages.add(event.message)
                self._sequence_counter += 1
        self._has_items_event.set()

    def cancel_by_tag(self, tag: str) -> None:
        if not tag:
            return
        with self._lock:
            survivors = [
                entry for entry in self._heap if entry[2].tag != tag
            ]
            if len(survivors) != len(self._heap):
                removed_messages = {
                    entry[2].message for entry in self._heap if entry[2].tag == tag
                }
                self._pending_messages -= removed_messages
                self._heap = survivors
                heapq.heapify(self._heap)

    def _run_worker(self) -> None:
        while True:
            self._has_items_event.wait()
            self._has_items_event.clear()
            while True:
                with self._lock:
                    if not self._heap:
                        break
                    _, _, event = heapq.heappop(self._heap)
                    self._pending_messages.discard(event.message)
                self._speaker.speak(event.message)
                time.sleep(self._min_gap_seconds)
