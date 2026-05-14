"""Constantes do projeto agrupadas por área de responsabilidade.

Centralizar aqui evita números mágicos espalhados pelos detectores e clientes.
Cada grupo é uma classe sem instâncias — funciona como namespace tipado.
"""
from __future__ import annotations


class Timing:
    """Intervalos, timeouts e TTLs (em segundos, salvo indicação)."""

    POLL_INTERVAL_SECONDS = 1.0
    MIN_GAP_BETWEEN_SPEECHES_SECONDS = 2.0

    SKILL_REMINDER_INTERVAL_SECONDS = 5.0
    NEXT_ITEM_PERIODIC_INTERVAL_SECONDS = 120.0
    NEXT_ITEM_FIRST_REMINDER_SECONDS = 5.0

    MINIMAP_REMINDER_MIN_INTERVAL_SECONDS = 45.0
    MINIMAP_REMINDER_MAX_INTERVAL_SECONDS = 90.0

    TRINKET_REMINDER_IDLE_SECONDS = 60.0

    HTTP_REQUEST_TIMEOUT_SECONDS = 2.0
    DATA_DRAGON_HTTP_TIMEOUT_SECONDS = 10.0
    DEEPLOL_HTTP_TIMEOUT_SECONDS = 8.0
    DATA_DRAGON_VERSION_CACHE_TTL_SECONDS = 3600.0

    LOG_POLL_INTERVAL_MS = 200


class GameRules:
    """Regras do League of Legends que afetam a lógica de detecção."""

    MAX_BASIC_ABILITY_LEVEL = 5
    MAX_ULTIMATE_LEVEL = 3
    ULTIMATE_UNLOCK_LEVELS = (6, 11, 16)

    DRAGON_INITIAL_SPAWN_SECONDS = 300.0
    DRAGON_RESPAWN_SECONDS = 300.0
    BARON_INITIAL_SPAWN_SECONDS = 1200.0
    BARON_RESPAWN_SECONDS = 420.0
    HERALD_INITIAL_SPAWN_SECONDS = 600.0
    HERALD_RESPAWN_SECONDS = 360.0
    VOIDGRUBS_INITIAL_SPAWN_SECONDS = 300.0

    OBJECTIVE_DEFAULT_WARN_OFFSETS_SECONDS = (60, 30, 10)


class Network:
    """Endpoints e parâmetros de rede."""

    MAX_CONSECUTIVE_API_FAILURES = 10

    LIVE_CLIENT_BASE_URL = "https://127.0.0.1:2999/liveclientdata"

    DATA_DRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
    DATA_DRAGON_CHAMPION_URL_TEMPLATE = (
        "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
    )
    DATA_DRAGON_ITEM_URL_TEMPLATE = (
        "https://ddragon.leagueoflegends.com/cdn/{version}/data/pt_BR/item.json"
    )
    DATA_DRAGON_RUNES_URL_TEMPLATE = (
        "https://ddragon.leagueoflegends.com/cdn/{version}/data/pt_BR/runesReforged.json"
    )

    DEEPLOL_BUILD_URL = "https://b2c-api-cdn.deeplol.gg/champion/build"
    DEEPLOL_VERSION_URL = "https://b2c-api-cdn.deeplol.gg/champion/version?cnt=5"
    DEEPLOL_TIER = "Emerald+"
    DEEPLOL_PLATFORM_ID = "KR"


class EventPriority:
    """Prioridades dos eventos falados (maior = mais urgente)."""

    BUILD_ANNOUNCE = 9
    OBJECTIVE_IMMINENT = 8       # 10s ou menos
    SKILL_GAINED = 7
    OBJECTIVE_SOON = 7           # 30s
    NEXT_ITEM_AFFORDABLE = 6
    OBJECTIVE_APPROACHING = 6    # 60s
    SKILL_REMINDER = 4
    NEXT_ITEM_PERIODIC = 3
    MINIMAP_REMINDER = 3
    TRINKET_REMINDER = 3


class EventTags:
    """Tags para cancelamento em lote de eventos na fila de fala."""

    SKILL = "skill"
    NEXT_ITEM = "next_item"
    TRINKET = "trinket"


class Defaults:
    """Valores padrão de configuração."""

    EDGE_TTS_VOICE = "pt-BR-AntonioNeural"
    EDGE_TTS_RATE = "+10%"
    MAX_LOG_LINES = 200
    APP_VERSION = "0.1.0-beta"
