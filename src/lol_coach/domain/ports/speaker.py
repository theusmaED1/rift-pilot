"""Contrato para qualquer engine de TTS."""
from __future__ import annotations

from typing import Protocol


class Speaker(Protocol):
    """Sintetiza e reproduz texto de forma síncrona."""

    def speak(self, text: str) -> None: ...
