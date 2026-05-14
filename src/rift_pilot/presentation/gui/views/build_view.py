"""Card "BUILD RECOMENDADA" — campeão e 5 linhas (Início/Core/Botas/Skills/Runas)."""
from __future__ import annotations

import tkinter as tk

from rift_pilot.domain.entities.recommended_build import RecommendedBuild
from rift_pilot.presentation.gui.theme import Colors, Fonts
from rift_pilot.presentation.gui.widgets import build_badge
from rift_pilot.settings.messages import UILabels


_ROWS_DEFINITION = (
    ("starters", UILabels.BUILD_ROW_STARTERS),
    ("core", UILabels.BUILD_ROW_CORE),
    ("boots", UILabels.BUILD_ROW_BOOTS),
    ("skills", UILabels.BUILD_ROW_SKILLS),
    ("runes", UILabels.BUILD_ROW_RUNES),
)


class BuildView:
    """Mostra a build atual carregada do deeplol (ou — quando vazia)."""

    def __init__(self, parent: tk.Widget) -> None:
        outer = tk.Frame(parent, bg=Colors.BACKGROUND_PRIMARY, padx=12)
        outer.pack(fill="x", pady=(10, 4))

        tk.Label(
            outer, text=UILabels.SECTION_BUILD,
            font=Fonts.SECTION_HEADER,
            fg=Colors.GOLD_DIM, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        card = tk.Frame(outer, bg=Colors.BACKGROUND_CARD)
        card.pack(fill="x")

        self._champion_label = tk.Label(
            card, text=UILabels.BUILD_PLACEHOLDER,
            font=Fonts.BODY_LABEL,
            fg=Colors.TEXT_PRIMARY, bg=Colors.BACKGROUND_CARD,
            anchor="w", padx=12, pady=6,
        )
        self._champion_label.pack(fill="x")
        tk.Frame(card, bg=Colors.BORDER, height=1).pack(fill="x")

        self._value_labels: dict[str, tk.Label] = {}
        for index, (row_key, (row_label, icon)) in enumerate(_ROWS_DEFINITION):
            if index > 0:
                tk.Frame(card, bg=Colors.BORDER, height=1).pack(fill="x")
            row = tk.Frame(card, bg=Colors.BACKGROUND_CARD)
            row.pack(fill="x")

            badge = build_badge(row, icon)
            badge.pack(side="left", padx=(12, 8), pady=8)

            tk.Label(
                row, text=row_label,
                font=Fonts.BODY_TEXT,
                fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_CARD,
                width=6, anchor="w",
            ).pack(side="left")

            value_label = tk.Label(
                row, text=UILabels.BUILD_PLACEHOLDER,
                font=Fonts.BODY_TEXT,
                fg=Colors.TEXT_PRIMARY, bg=Colors.BACKGROUND_CARD,
                anchor="w", justify="left", wraplength=240,
            )
            value_label.pack(side="left", fill="x", expand=True, padx=(0, 12))
            self._value_labels[row_key] = value_label

    def reset(self) -> None:
        self._champion_label.config(text=UILabels.BUILD_PLACEHOLDER)
        for label in self._value_labels.values():
            label.config(text=UILabels.BUILD_PLACEHOLDER)

    def display(self, build: RecommendedBuild) -> None:
        title = build.champion
        if build.position and build.position.upper() != "NONE":
            title = f"{build.champion} — {build.position.lower()}"
        self._champion_label.config(text=title)

        self._value_labels["starters"].config(
            text=" + ".join(build.starter_items) if build.starter_items else UILabels.BUILD_PLACEHOLDER
        )
        self._value_labels["core"].config(
            text=" → ".join(build.core_items) if build.core_items else UILabels.BUILD_PLACEHOLDER
        )
        self._value_labels["boots"].config(text=build.boots or UILabels.BUILD_PLACEHOLDER)
        self._value_labels["skills"].config(
            text=" > ".join(build.skill_priority) if build.skill_priority else UILabels.BUILD_PLACEHOLDER
        )
        runes_text = " / ".join(filter(None, [build.runes_primary, build.runes_secondary]))
        self._value_labels["runes"].config(text=runes_text or UILabels.BUILD_PLACEHOLDER)
