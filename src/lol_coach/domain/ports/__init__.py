"""Interfaces (Protocols) que a infraestrutura precisa implementar."""

from lol_coach.domain.ports.build_provider import BuildProvider
from lol_coach.domain.ports.data_dragon_repository import DataDragonRepository
from lol_coach.domain.ports.game_data_source import (
    GameDataSource,
    GameDataSourceUnavailable,
)
from lol_coach.domain.ports.speaker import Speaker
from lol_coach.domain.ports.speech_queue import SpeechQueue

__all__ = [
    "BuildProvider",
    "DataDragonRepository",
    "GameDataSource",
    "GameDataSourceUnavailable",
    "Speaker",
    "SpeechQueue",
]
