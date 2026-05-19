"""TTS via Kokoro — síntese local rápida com reprodução síncrona (hexgrad/kokoro)."""
from __future__ import annotations

import ctypes
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from kokoro import KPipeline


class KokoroTtsSpeaker:
    """Implementação de `Speaker` usando Kokoro-82M (local, offline, rápido).

    Síntese é síncrona; gera WAV e reproduz via WinMM.
    """

    def __init__(self, lang: str = "p", voice: str = "pf_dora", speed: float = 1.0) -> None:
        """Inicializa Kokoro-82M.

        Args:
            lang: Código de idioma ('p'=português, 'a'=en-us, 'b'=en-gb, 'e'=español, etc.)
            voice: Voz ('pm_alex', 'pf_dora', 'pm_santa', etc. — prefixo 'p' = português)
            speed: Velocidade de fala (1.0 = normal)
        """
        self._lang = lang
        self._voice = voice
        self._speed = speed
        self._pipeline = KPipeline(lang_code=lang)

    def speak(self, text: str) -> None:
        """Sintetiza e reproduz texto imediatamente."""
        # Kokoro retorna áudio em 24kHz
        try:
            # generator retorna (gs, ps, audio) para cada chunk
            audio_chunks = []
            for gs, ps, audio in self._pipeline(text, voice=self._voice):
                audio_chunks.append(audio)

            # Concatena chunks e reproduz
            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                _play_wav_synchronously(full_audio)
        except Exception as e:
            raise RuntimeError(f"Kokoro síntese falhou: {e}") from e


def _play_wav_synchronously(audio: np.ndarray, sample_rate: int = 24000) -> None:
    """Reproduz áudio NumPy via WinMM, sem arquivo permanente."""
    # Normaliza e converte para int16
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)

    # Escreve WAV temporário
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = Path(tmp.name)

    try:
        sf.write(str(path), audio_int16, sample_rate)

        # Reproduz via WinMM
        winmm = ctypes.windll.winmm
        alias = b"rift_kokoro_snd"
        wav_path_bytes = str(path).encode("mbcs")

        winmm.mciSendStringA(
            b"open " + wav_path_bytes + b" type waveaudio alias " + alias, None, 0, None
        )
        winmm.mciSendStringA(b"play " + alias + b" wait", None, 0, None)
        winmm.mciSendStringA(b"close " + alias, None, 0, None)
    finally:
        path.unlink(missing_ok=True)
