"""Teste in-game: detecta pontos de skill e objetivos, fala em voz alta.

Uso:
    python scripts/test_ingame.py
    python scripts/test_ingame.py --replay recordings/game_xxx.jsonl
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from lol_coach.client.live_api import GameNotRunning, LiveApiClient
from lol_coach.client.replay import ReplayApiClient
from lol_coach.events.skill_points import SkillPointDetector
from lol_coach.events.objectives import ObjectiveDetector
from lol_coach.state.game_state import GameState, StateDiff
from lol_coach.speaker.edge_tts import EdgeSpeaker
from lol_coach.speaker.piper_tts import PiperSpeaker

VOICE_PATH = Path("voices/pt_BR-faber-medium.onnx")
POLL_INTERVAL = 1.0


def run(client: LiveApiClient | ReplayApiClient, speaker: EdgeSpeaker) -> None:
    detectors = [SkillPointDetector(), ObjectiveDetector()]
    prev_state: GameState | None = None
    consecutive_failures = 0

    print("Monitorando... (Ctrl+C para parar)\n")
    while True:
        try:
            data = client.get_all_data()
        except GameNotRunning:
            consecutive_failures += 1
            if consecutive_failures >= 10:
                print("Jogo encerrado.")
                break
            time.sleep(POLL_INTERVAL)
            continue

        consecutive_failures = 0
        cur_state = GameState.from_api(data)

        if prev_state is not None:
            diff = StateDiff(previous=prev_state, current=cur_state)
            coach_events = []
            for det in detectors:
                coach_events.extend(det.detect(diff))
            coach_events.sort(key=lambda e: e.priority, reverse=True)
            for event in coach_events:
                print(f"[t={cur_state.game_time:.0f}s] {event.message}")
                speaker.speak(event.message)

        prev_state = cur_state
        time.sleep(POLL_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, help="Arquivo .jsonl para replay")
    parser.add_argument("--piper", action="store_true", help="Usar Piper TTS local ao invés de Edge TTS")
    args = parser.parse_args()

    if args.piper:
        if not VOICE_PATH.exists():
            raise SystemExit(f"Modelo de voz não encontrado: {VOICE_PATH}")
        speaker = PiperSpeaker(VOICE_PATH)
        print("Voz: Piper (local)")
    else:
        speaker = EdgeSpeaker()
        print("Voz: Edge TTS — pt-BR-AntonioNeural (Microsoft)")

    if args.replay:
        client = ReplayApiClient(args.replay, realtime=True)
        print(f"Replay: {args.replay} ({client.total_ticks} ticks)")
    else:
        client = LiveApiClient()
        print("Conectando ao jogo ao vivo...")

    try:
        run(client, speaker)
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
