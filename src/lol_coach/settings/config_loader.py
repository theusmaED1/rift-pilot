"""Carregamento do `config.yaml` em um objeto tipado."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from lol_coach.settings.constants import GameRules, Timing

_DEFAULT_CONFIG_PATH = Path("config.yaml")


@dataclass(frozen=True)
class ApiConfig:
    poll_interval_seconds: float = Timing.POLL_INTERVAL_SECONDS


@dataclass(frozen=True)
class SpeakerConfig:
    min_gap_seconds: float = Timing.MIN_GAP_BETWEEN_SPEECHES_SECONDS


@dataclass(frozen=True)
class ObjectivesConfig:
    warn_seconds: tuple[int, ...] = GameRules.OBJECTIVE_DEFAULT_WARN_OFFSETS_SECONDS


@dataclass(frozen=True)
class AppConfig:
    api: ApiConfig = field(default_factory=ApiConfig)
    speaker: SpeakerConfig = field(default_factory=SpeakerConfig)
    objectives: ObjectivesConfig = field(default_factory=ObjectivesConfig)


def load_app_config(path: Path = _DEFAULT_CONFIG_PATH) -> AppConfig:
    """Lê `config.yaml` se presente; retorna defaults caso contrário."""
    if not path.exists():
        return AppConfig()

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    api_raw = raw.get("api", {}) or {}
    speaker_raw = raw.get("speaker", {}) or {}
    objectives_raw = (raw.get("events", {}) or {}).get("objectives", {}) or {}

    return AppConfig(
        api=ApiConfig(
            poll_interval_seconds=float(
                api_raw.get("poll_interval_seconds", Timing.POLL_INTERVAL_SECONDS)
            ),
        ),
        speaker=SpeakerConfig(
            min_gap_seconds=float(
                speaker_raw.get("min_gap_seconds", Timing.MIN_GAP_BETWEEN_SPEECHES_SECONDS)
            ),
        ),
        objectives=ObjectivesConfig(
            warn_seconds=tuple(
                objectives_raw.get(
                    "warn_seconds", GameRules.OBJECTIVE_DEFAULT_WARN_OFFSETS_SECONDS
                )
            ),
        ),
    )
