"""Contrato para qualquer fonte de snapshots de partida."""
from __future__ import annotations

from typing import Any, Protocol


class GameDataSourceUnavailable(Exception):
    """A fonte de dados não conseguiu produzir um snapshot."""


class GameLoading(Exception):
    """O cliente do LoL está rodando mas o jogo ainda não começou."""


class GameDataSource(Protocol):
    """Implementado pela Live API e pelo player de replay."""

    def get_all_data(self) -> dict[str, Any]: ...
    def close(self) -> None: ...
