"""TTS via Microsoft Edge — síntese online com reprodução síncrona no Windows."""
from __future__ import annotations

import asyncio
import ctypes
import logging
import tempfile
from pathlib import Path

import edge_tts

from rift_pilot.settings.constants import Defaults

logger = logging.getLogger(__name__)


class EdgeTtsSpeaker:
    """Implementação de `Speaker` usando o serviço Edge TTS da Microsoft.

    A síntese é assíncrona; aqui é encapsulada em `asyncio.run()` para expor
    uma interface síncrona à fila de fala.
    """

    def __init__(
        self,
        voice: str = Defaults.EDGE_TTS_VOICE,
        rate: str = Defaults.EDGE_TTS_RATE,
    ) -> None:
        self._voice = voice
        self._rate = rate

    def speak(self, text: str) -> None:
        logger.info(f"[EdgeTtsSpeaker] Iniciando síntese: {text[:60]}...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio_path = Path(tmp.name)
        try:
            logger.info(f"[EdgeTtsSpeaker] Sintetizando para {audio_path}...")
            asyncio.run(self._synthesize_to_file(text, str(audio_path)))
            logger.info(f"[EdgeTtsSpeaker] Síntese concluída, tocando áudio...")
            _play_mp3_synchronously(audio_path)
            logger.info(f"[EdgeTtsSpeaker] Áudio tocado com sucesso")
        except Exception as e:
            logger.error(f"[EdgeTtsSpeaker] Erro ao sintetizar/tocar: {e}", exc_info=True)
        finally:
            audio_path.unlink(missing_ok=True)

    async def _synthesize_to_file(self, text: str, output_path: str) -> None:
        communicator = edge_tts.Communicate(text, self._voice, rate=self._rate)
        await communicator.save(output_path)


def _play_mp3_synchronously(path: Path) -> None:
    """Reproduz um MP3 via WinMM (`mciSendString`), sem dependências externas."""
    winmm = ctypes.windll.winmm
    alias = b"rift_pilot_snd"
    mp3_path_bytes = str(path).encode("mbcs")

    winmm.mciSendStringA(
        b"open " + mp3_path_bytes + b" type mpegvideo alias " + alias, None, 0, None
    )
    winmm.mciSendStringA(b"play " + alias + b" wait", None, 0, None)
    winmm.mciSendStringA(b"close " + alias, None, 0, None)
