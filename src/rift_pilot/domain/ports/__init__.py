"""Interfaces (Protocols) que a infraestrutura precisa implementar."""

from rift_pilot.domain.ports.build_provider import BuildProvider
from rift_pilot.domain.ports.data_dragon_repository import DataDragonRepository
from rift_pilot.domain.ports.game_data_source import (
    GameDataSource,
    GameDataSourceUnavailable,
)
from rift_pilot.domain.ports.speaker import Speaker
from rift_pilot.domain.ports.speech_queue import SpeechQueue

__all__ = [
    "BuildProvider",
    "DataDragonRepository",
    "GameDataSource",
    "GameDataSourceUnavailable",
    "Speaker",
    "SpeechQueue",
]
