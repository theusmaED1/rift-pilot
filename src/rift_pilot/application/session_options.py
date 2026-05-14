"""Flags que controlam quais features do coach estão ativas."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionOptions:
    """Conjunto de toggles para uma sessão do coach.

    Mapeia 1-para-1 com os switches da interface gráfica.
    """

    skill_points: bool = True
    objectives: bool = True
    build_announce: bool = True
    next_item: bool = True
    minimap: bool = True
    trinket: bool = True
