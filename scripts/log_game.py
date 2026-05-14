"""Fase 1: grava ticks da Live Client API em um arquivo JSON Lines.

Uso:
    python scripts/log_game.py              # aguarda partida e grava automaticamente
    python scripts/log_game.py --out path   # arquivo de saída customizado

O arquivo gerado em recordings/ pode ser usado como fixture nos testes.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from lol_coach.domain.ports.game_data_source import GameDataSourceUnavailable
from lol_coach.infrastructure.riot.live_client_data_api import LiveClientDataApi

RECORDINGS_DIR = Path("recordings")
POLL_INTERVAL = 1.0  # segundos
MAX_CONSECUTIVE_FAILURES = 10  # ~10s de API caída antes de considerar fim de partida


def main() -> None:
    parser = argparse.ArgumentParser(description="Grava partida LoL em JSON Lines.")
    parser.add_argument("--out", type=Path, help="Caminho do arquivo de saída.")
    args = parser.parse_args()

    RECORDINGS_DIR.mkdir(exist_ok=True)
    output_path: Path = args.out or RECORDINGS_DIR / f"game_{datetime.now():%Y%m%d_%H%M%S}.jsonl"

    print("Aguardando partida iniciar... (Ctrl+C para cancelar)")

    with LiveClientDataApi() as client:
        while not client.is_game_running():
            time.sleep(2)

        print(f"Partida detectada! Gravando em {output_path}")
        print("Jogue normalmente. Ctrl+C ou encerre o jogo para parar.")

        tick = 0
        consecutive_failures = 0
        try:
            with output_path.open("w", encoding="utf-8") as f:
                while True:
                    try:
                        data = client.get_all_data()
                    except GameDataSourceUnavailable:
                        consecutive_failures += 1
                        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            print(f"\nPartida encerrada (API offline por {consecutive_failures}s). {tick} ticks gravados.")
                            break
                        print(f"  [tick perdido — {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}]")
                        time.sleep(POLL_INTERVAL)
                        continue

                    consecutive_failures = 0
                    f.write(json.dumps({"tick": tick, "ts": time.time(), "data": data}, ensure_ascii=False))
                    f.write("\n")
                    f.flush()
                    tick += 1
                    time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print(f"\nEncerrado pelo usuário após {tick} ticks.")

    print(f"Arquivo salvo: {output_path}")


if __name__ == "__main__":
    main()
