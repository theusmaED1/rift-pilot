"""Card "STATUS" — dot colorido + texto descritivo."""
from __future__ import annotations

import tkinter as tk

from rift_pilot.presentation.gui.theme import Colors, Fonts
from rift_pilot.settings.messages import UILabels


class StatusView:
    """Indica o estado atual da sessão (aguardando, conectando, monitorando)."""

    def __init__(self, parent: tk.Widget) -> None:
        outer = tk.Frame(parent, bg=Colors.BACKGROUND_PRIMARY, padx=12)
        outer.pack(fill="x", pady=8)

        card = tk.Frame(outer, bg=Colors.BACKGROUND_CARD, pady=14)
        card.pack(fill="x")

        tk.Label(
            card, text=UILabels.STATUS_HEADER,
            font=Fonts.SECTION_LABEL,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_CARD,
        ).pack()

        dot_row = tk.Frame(card, bg=Colors.BACKGROUND_CARD)
        dot_row.pack(pady=(8, 0))
        self._status_dot = tk.Label(
            dot_row, text="●", font=Fonts.STATUS_DOT,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_CARD,
        )
        self._status_dot.pack(side="left", padx=(0, 6))
        self._status_label = tk.Label(
            dot_row, text=UILabels.STATUS_WAITING,
            font=Fonts.BODY_LABEL,
            fg=Colors.TEXT_PRIMARY, bg=Colors.BACKGROUND_CARD,
        )
        self._status_label.pack(side="left")

    def set(self, text: str, dot_color: str) -> None:
        self._status_label.config(text=text)
        self._status_dot.config(fg=dot_color)
