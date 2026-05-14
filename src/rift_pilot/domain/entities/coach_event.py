"""Evento que o coach deve falar em voz alta."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoachEvent:
    """Aviso a ser anunciado pela fila de fala.

    Maior `priority` = mais urgente. `tag` permite cancelar em lote eventos
    obsoletos antes que sejam falados (ex.: cancelar lembretes de skill quando
    o jogador acabou de gastar o ponto).

    `expires_at` é um timestamp `time.monotonic()`. Se definido e já passou
    quando o evento for retirado da fila, ele é descartado silenciosamente —
    evita que avisos de tempo expirem enquanto aguardam na fila.
    """

    message: str
    priority: int = 0
    tag: str = ""
    expires_at: float | None = None
