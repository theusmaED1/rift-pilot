"""Evento que o coach deve falar em voz alta."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoachEvent:
    """Aviso a ser anunciado pela fila de fala.

    Maior `priority` = mais urgente. `tag` permite cancelar em lote eventos
    obsoletos antes que sejam falados (ex.: cancelar lembretes de skill quando
    o jogador acabou de gastar o ponto).
    """

    message: str
    priority: int = 0
    tag: str = ""
