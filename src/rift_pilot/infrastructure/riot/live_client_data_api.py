"""Cliente HTTPS da Live Client Data API do League of Legends."""
from __future__ import annotations

from typing import Any

import httpx

from rift_pilot.domain.ports.game_data_source import GameDataSourceUnavailable, GameLoading
from rift_pilot.settings.constants import Network, Timing


class LiveClientDataApi:
    """Lê o snapshot da partida em curso em `127.0.0.1:2999`.

    Implementa o protocolo `GameDataSource`. O certificado do cliente do LoL é
    auto-assinado, daí `verify=False`.
    """

    def __init__(self, timeout_seconds: float = Timing.HTTP_REQUEST_TIMEOUT_SECONDS) -> None:
        self._http = httpx.Client(verify=False, timeout=timeout_seconds)

    def get_all_data(self) -> dict[str, Any]:
        try:
            response = self._http.get(f"{Network.LIVE_CLIENT_BASE_URL}/allgamedata")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise GameLoading("Jogo ainda carregando.") from exc
            raise GameDataSourceUnavailable("Live API do LoL inacessível.") from exc
        except (
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.RemoteProtocolError,
            httpx.ReadError,
        ) as exc:
            raise GameDataSourceUnavailable("Live API do LoL inacessível.") from exc

    def is_game_running(self) -> bool:
        try:
            self.get_all_data()
            return True
        except (GameDataSourceUnavailable, GameLoading):
            # GameLoading = tela de carregamento (404): ainda não está em
            # jogo, então segue esperando em vez de estourar o chamador.
            return False

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> LiveClientDataApi:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
