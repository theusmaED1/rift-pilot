"""Modo CLI: roda o coach contra um replay `.jsonl` ou contra a Live API.

Útil para regredir bugs sobre partidas gravadas sem precisar entrar no jogo.
"""
from __future__ import annotations

import argparse
import threading
from pathlib import Path

from lol_coach.application.build_loader import BuildLoader
from lol_coach.application.coach_session import (
    CoachSession,
    SessionCallbacks,
    SessionStatus,
)
from lol_coach.application.session_options import SessionOptions
from lol_coach.domain.entities.recommended_build import RecommendedBuild
from lol_coach.domain.ports.game_data_source import GameDataSource
from lol_coach.infrastructure.build_providers.deeplol_build_provider import (
    DeeplolBuildProvider,
)
from lol_coach.infrastructure.recommended_build_service import RecommendedBuildService
from lol_coach.infrastructure.riot.data_dragon_client import DataDragonClient
from lol_coach.infrastructure.riot.live_client_data_api import LiveClientDataApi
from lol_coach.infrastructure.riot.replay_data_source import ReplayDataSource
from lol_coach.infrastructure.tts.edge_tts_speaker import EdgeTtsSpeaker
from lol_coach.infrastructure.tts.speech_priority_queue import SpeechPriorityQueue
from lol_coach.settings.config_loader import load_app_config
from lol_coach.settings.constants import Defaults
from lol_coach.settings.messages import LogMessages, UILabels


def main() -> None:
    parser = argparse.ArgumentParser(description=UILabels.CLI_DESCRIPTION)
    parser.add_argument("--replay", type=Path, default=None, help=UILabels.CLI_REPLAY_HELP)
    parser.add_argument("--voice", default=Defaults.EDGE_TTS_VOICE, help=UILabels.CLI_VOICE_HELP)
    args = parser.parse_args()

    config = load_app_config()

    data_source = _resolve_data_source(args.replay)

    speaker = EdgeTtsSpeaker(voice=args.voice)
    speech_queue = SpeechPriorityQueue(
        speaker=speaker, min_gap_seconds=config.speaker.min_gap_seconds
    )

    data_dragon = DataDragonClient()
    build_loader = BuildLoader(
        build_service=RecommendedBuildService(
            build_provider=DeeplolBuildProvider(data_dragon=data_dragon),
            data_dragon=data_dragon,
        ),
        data_dragon=data_dragon,
    )

    callbacks = SessionCallbacks(
        on_status_change=_print_status,
        on_log_message=print,
        on_build_loaded=_print_build_loaded,
    )

    session = CoachSession(
        data_source=data_source,
        speech_queue=speech_queue,
        build_loader=build_loader,
        options=SessionOptions(),
        callbacks=callbacks,
        poll_interval_seconds=config.api.poll_interval_seconds,
        warn_offsets_seconds=config.objectives.warn_seconds,
    )

    stop_signal = threading.Event()
    print(LogMessages.CLI_MONITORING)
    try:
        session.run(stop_signal)
    except KeyboardInterrupt:
        stop_signal.set()
        print()
        print(LogMessages.CLI_STOPPED_BY_USER)


def _resolve_data_source(replay_path: Path | None) -> GameDataSource:
    if replay_path:
        return ReplayDataSource(replay_path, realtime=True)
    return LiveClientDataApi()


def _print_status(status: SessionStatus) -> None:
    pass


def _print_build_loaded(build: RecommendedBuild) -> None:
    pass


if __name__ == "__main__":
    main()
