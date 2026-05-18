"""Cliente HTTP do OP.GG MCP Server.

JSON-RPC 2.0 sobre https://mcp-api.op.gg/mcp. Endpoint público hospedado
pela OP.GG, sem necessidade de auth. Resposta vem em formato MCP com
content[0].text contendo JSON serializado.
"""
from __future__ import annotations

import json
import logging
import re
import time
from threading import Lock
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_ENDPOINT = "https://mcp-api.op.gg/mcp"
_TIMEOUT_SECONDS = 15.0
_CACHE_TTL_SECONDS = 3600.0  # 1 hora

# Campos do data.* que pedimos para a IA — closed set do MCP.
# Manter enxuto para reduzir payload de retorno.
_MATCHUP_GUIDE_FIELDS_USED = (
    "data.starter_items",
    "data.core_items",
    "data.boots",
    "data.single_items",
    "data.runes",
    "data.skills",
    "data.skill_masteries",
    "data.damage_type",
    "data.summary",
    "data.opponent_champion_tip",
    "data.recommended_play_style",
    "data.lane_advantage_champion",
)

# Champions com nomes que não seguem o padrão camelCase da Live API.
# Live API name → OP.GG MCP name (UPPER_SNAKE_CASE).
_CHAMPION_NAME_OVERRIDES = {
    "MonkeyKing": "WUKONG",  # Live API usa MonkeyKing, OP.GG usa WUKONG
    "Wukong": "WUKONG",
}

# Live API position → OP.GG MCP position.
# Live API: TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY (uppercase)
# MCP:      top, jungle, mid, adc, support (lowercase)
_POSITION_MAP = {
    "TOP": "top",
    "JUNGLE": "jungle",
    "MIDDLE": "mid",
    "BOTTOM": "adc",
    "UTILITY": "support",
}


def position_to_mcp(live_api_position: str) -> str:
    """Converte posição da Live API ('MIDDLE') para o formato do MCP ('mid')."""
    normalized = (live_api_position or "").upper()
    return _POSITION_MAP.get(normalized, normalized.lower())


class OpggMcpError(Exception):
    """Erro na comunicação com o MCP."""


def champion_to_mcp_name(live_api_name: str) -> str:
    """Converte nome do champion da Live API para o formato esperado pelo MCP.

    Examples:
        Diana -> DIANA
        MissFortune -> MISS_FORTUNE
        KhaZix -> KHA_ZIX
        JarvanIV -> JARVAN_IV
        TwistedFate -> TWISTED_FATE
        Wukong/MonkeyKing -> WUKONG
    """
    if live_api_name in _CHAMPION_NAME_OVERRIDES:
        return _CHAMPION_NAME_OVERRIDES[live_api_name]
    # Insere underscore antes de cada letra maiúscula (exceto a primeira)
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", live_api_name)
    return snake.upper()


class OpggMcpClient:
    """Cliente do OP.GG MCP com cache em memória (TTL 1h)."""

    def __init__(self, timeout_seconds: float = _TIMEOUT_SECONDS) -> None:
        self._timeout = timeout_seconds
        self._cache: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}
        self._cache_lock = Lock()
        self._request_id = 0

    def matchup_guide(
        self,
        my_champion: str,
        opponent: str,
        position: str,
    ) -> dict[str, Any]:
        """Busca lol_get_lane_matchup_guide para o matchup.

        Args:
            my_champion: Nome do champ no formato da Live API (ex: "Diana", "MissFortune")
            opponent: Nome do adversário no formato da Live API
            position: "top" | "mid" | "jungle" | "adc" | "support"

        Returns:
            Dict com a estrutura data.* do MCP (já desempacotado de content[0].text).

        Raises:
            OpggMcpError: timeout, status != 200, JSON inválido, ou erro JSON-RPC.
        """
        my = champion_to_mcp_name(my_champion)
        opp = champion_to_mcp_name(opponent)
        pos = position_to_mcp(position)
        cache_key = (my, opp, pos)

        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info(f"[OpggMcp] Cache hit: {my} vs {opp} {pos}")
            return cached

        logger.info(f"[OpggMcp] Buscando matchup_guide: {my} vs {opp} {pos}")
        raw = self._call_tool(
            "lol_get_lane_matchup_guide",
            {
                "my_champion": my,
                "opponent_champion": opp,
                "position": pos,
                "lang": "en_US",  # pt_BR retorna 422 nesse endpoint
            },
        )
        # Desempacota o nível `data` (que contém starter_items, core_items, etc.)
        # Top-level traz lang/position/my_champion/opponent_champion/data.
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        if not data:
            logger.warning(f"[OpggMcp] Resposta sem campo 'data': keys={list(raw.keys()) if isinstance(raw, dict) else type(raw)}")
        self._put_cached(cache_key, data)
        return data

    def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Faz uma chamada tools/call e retorna o dict desempacotado."""
        self._request_id += 1
        body = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        last_error: Exception | None = None
        for attempt in range(2):  # 1 retry
            try:
                resp = httpx.post(
                    _ENDPOINT,
                    headers=headers,
                    json=body,
                    timeout=self._timeout,
                )
                if resp.status_code == 429 and attempt == 0:
                    logger.warning(f"[OpggMcp] 429 — retentando uma vez")
                    time.sleep(2.0)
                    continue
                if resp.status_code >= 500 and attempt == 0:
                    logger.warning(f"[OpggMcp] {resp.status_code} — retentando uma vez")
                    time.sleep(1.0)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    raise OpggMcpError(f"JSON-RPC error: {data['error']}")
                content = data["result"]["content"]
                if not content or not isinstance(content, list):
                    raise OpggMcpError("Resposta sem content")
                text = content[0].get("text", "")
                return json.loads(text)
            except OpggMcpError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"[OpggMcp] Tentativa {attempt + 1} falhou: {e}")
                if attempt == 0:
                    time.sleep(1.0)

        raise OpggMcpError(f"Falha após retries: {last_error}")

    def _get_cached(self, key: tuple[str, str, str]) -> dict[str, Any] | None:
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            ts, data = entry
            if time.time() - ts > _CACHE_TTL_SECONDS:
                del self._cache[key]
                return None
            return data

    def _put_cached(self, key: tuple[str, str, str], data: dict[str, Any]) -> None:
        with self._cache_lock:
            self._cache[key] = (time.time(), data)
