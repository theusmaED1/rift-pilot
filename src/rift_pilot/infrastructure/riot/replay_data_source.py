"""Reproduz uma partida gravada em arquivo `.jsonl` como se fosse a Live API."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rift_pilot.domain.ports.game_data_source import GameDataSourceUnavailable


class ReplayDataSource:
    """Lê um arquivo `.jsonl` produzido por `scripts/log_game.py`.

    Mesma interface da `LiveClientDataApi`, permitindo testar a stack inteira
    sem precisar de uma partida real.
    """

    def __init__(self, recording_path: Path, realtime: bool = False) -> None:
        self._realtime = realtime
        self._ticks = self._load_ticks(recording_path)
        self._current_index = 0

    @staticmethod
    def _load_ticks(path: Path) -> list[dict[str, Any]]:
        ticks: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    ticks.append(json.loads(line))
        if not ticks:
            raise ValueError(f"Arquivo de replay vazio: {path}")
        return ticks

    def get_all_data(self) -> dict[str, Any]:
        if self._current_index >= len(self._ticks):
            raise GameDataSourceUnavailable("Replay encerrado — sem mais ticks.")

        entry = self._ticks[self._current_index]

        if self._realtime and self._current_index > 0:
            previous_timestamp = self._ticks[self._current_index - 1]["ts"]
            elapsed = entry["ts"] - previous_timestamp
            if elapsed > 0:
                time.sleep(elapsed)

        self._current_index += 1
        return entry["data"]

    def is_game_running(self) -> bool:
        return self._current_index < len(self._ticks)

    def close(self) -> None:
        return None

    def __enter__(self) -> ReplayDataSource:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @property
    def total_ticks(self) -> int:
        return len(self._ticks)

    @property
    def current_tick(self) -> int:
        return self._current_index
