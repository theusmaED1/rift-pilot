"""Card "LOG DE EVENTOS" — Text widget com timestamping e botão LIMPAR."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime

from lol_coach.presentation.gui.theme import Colors, Dimensions, Fonts
from lol_coach.settings.constants import Defaults
from lol_coach.settings.messages import UILabels


class LogView:
    """Painel de log que recebe linhas via `append()` e prefixa o horário."""

    def __init__(self, parent: tk.Widget) -> None:
        outer = tk.Frame(parent, bg=Colors.BACKGROUND_PRIMARY, padx=12)
        outer.pack(fill="both", expand=True, pady=(0, 6))

        header = tk.Frame(outer, bg=Colors.BACKGROUND_PRIMARY, pady=4)
        header.pack(fill="x")

        title_row = tk.Frame(header, bg=Colors.BACKGROUND_PRIMARY)
        title_row.pack(side="left")
        tk.Label(
            title_row, text="◷ ",
            font=Fonts.SUBTITLE,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(side="left")
        tk.Label(
            title_row, text=UILabels.SECTION_LOG,
            font=Fonts.SECTION_HEADER,
            fg=Colors.GOLD_DIM, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(side="left")

        tk.Button(
            header, text=UILabels.BUTTON_CLEAR_LOG,
            font=Fonts.BUTTON_SMALL,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_BADGE,
            activeforeground=Colors.TEXT_PRIMARY,
            activebackground=Colors.BACKGROUND_CARD,
            relief="flat", cursor="hand2",
            padx=8, pady=2, bd=0,
            command=self.clear,
        ).pack(side="right")

        self._text_widget = tk.Text(
            outer,
            height=Dimensions.LOG_HEIGHT_LINES,
            width=Dimensions.LOG_WRAP_WIDTH,
            bg=Colors.BACKGROUND_CARD,
            fg=Colors.TEXT_PRIMARY,
            font=Fonts.LOG_LINE,
            relief="flat", state="disabled",
            wrap="word", bd=0, padx=8, pady=6,
        )
        self._text_widget.pack(fill="both", expand=True)

    def append(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._text_widget.config(state="normal")
        self._text_widget.insert("end", f"[{timestamp}] {message}\n")
        line_count = int(self._text_widget.index("end-1c").split(".")[0])
        if line_count > Defaults.MAX_LOG_LINES:
            self._text_widget.delete("1.0", f"{line_count - Defaults.MAX_LOG_LINES}.0")
        self._text_widget.see("end")
        self._text_widget.config(state="disabled")

    def clear(self) -> None:
        self._text_widget.config(state="normal")
        self._text_widget.delete("1.0", "end")
        self._text_widget.config(state="disabled")
