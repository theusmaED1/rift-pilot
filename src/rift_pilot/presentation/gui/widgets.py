"""Widgets customizados: toggle iOS e badges de ícone."""
from __future__ import annotations

import tkinter as tk

from rift_pilot.presentation.gui.theme import Colors, Dimensions, Fonts


class ToggleSwitch(tk.Canvas):
    """Toggle no estilo iOS controlado por uma `BooleanVar`."""

    def __init__(self, parent: tk.Widget, variable: tk.BooleanVar) -> None:
        super().__init__(
            parent,
            width=Dimensions.TOGGLE_WIDTH,
            height=Dimensions.TOGGLE_HEIGHT,
            bg=Colors.BACKGROUND_CARD,
            highlightthickness=0,
            cursor="hand2",
        )
        self._variable = variable
        self._redraw()
        self.bind("<Button-1>", self._handle_click)
        variable.trace_add("write", lambda *_: self._redraw())

    def _handle_click(self, _event: tk.Event) -> None:
        self._variable.set(not self._variable.get())

    def _redraw(self) -> None:
        self.delete("all")
        is_on = self._variable.get()
        fill_color = Colors.GOLD if is_on else Colors.TOGGLE_OFF
        radius = Dimensions.TOGGLE_HEIGHT // 2

        self.create_oval(
            0, 0, Dimensions.TOGGLE_HEIGHT, Dimensions.TOGGLE_HEIGHT,
            fill=fill_color, outline="",
        )
        self.create_oval(
            Dimensions.TOGGLE_WIDTH - Dimensions.TOGGLE_HEIGHT, 0,
            Dimensions.TOGGLE_WIDTH, Dimensions.TOGGLE_HEIGHT,
            fill=fill_color, outline="",
        )
        self.create_rectangle(
            radius, 0,
            Dimensions.TOGGLE_WIDTH - radius, Dimensions.TOGGLE_HEIGHT,
            fill=fill_color, outline="",
        )

        knob_padding = 3
        knob_center_x = (
            Dimensions.TOGGLE_WIDTH - radius if is_on else radius
        )
        self.create_oval(
            knob_center_x - radius + knob_padding,
            knob_padding,
            knob_center_x + radius - knob_padding,
            Dimensions.TOGGLE_HEIGHT - knob_padding,
            fill=Colors.KNOB_WHITE,
            outline="",
        )


def build_badge(parent: tk.Widget, icon: str) -> tk.Canvas:
    """Badge pequeno usado nas linhas da seção BUILD (borda dourada vazada)."""
    size = Dimensions.BADGE_BUILD_SIZE
    canvas = tk.Canvas(
        parent, width=size, height=size,
        bg=Colors.BACKGROUND_CARD, highlightthickness=0,
    )
    canvas.create_rectangle(
        1, 1, size - 1, size - 1,
        outline=Colors.GOLD_DIM, fill="", width=1,
    )
    canvas.create_text(
        size // 2, size // 2,
        text=icon, fill=Colors.GOLD, font=Fonts.BADGE_SMALL,
    )
    return canvas


def feature_badge(parent: tk.Widget, icon: str) -> tk.Canvas:
    """Badge maior usado nas linhas de AVISOS ATIVOS (fundo cinza preenchido)."""
    size = Dimensions.BADGE_FEATURE_SIZE
    canvas = tk.Canvas(
        parent, width=size, height=size,
        bg=Colors.BACKGROUND_CARD, highlightthickness=0,
    )
    canvas.create_rectangle(
        1, 1, size - 1, size - 1,
        fill=Colors.BACKGROUND_BADGE, outline="",
    )
    canvas.create_text(
        size // 2, size // 2,
        text=icon, fill=Colors.GOLD, font=Fonts.BADGE_LARGE,
    )
    return canvas


def horizontal_separator(parent: tk.Widget) -> None:
    tk.Frame(parent, bg=Colors.BORDER, height=1).pack(fill="x")
