"""Card "AVISOS ATIVOS" — switches para ligar/desligar cada feature."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from rift_pilot.presentation.gui.theme import Colors, Fonts
from rift_pilot.presentation.gui.widgets import ToggleSwitch, feature_badge
from rift_pilot.settings.messages import UILabels


@dataclass(frozen=True)
class FeatureToggles:
    """Conjunto de `BooleanVar` ligados aos switches da interface."""

    skill_points: tk.BooleanVar
    objectives: tk.BooleanVar
    build_announce: tk.BooleanVar
    next_item: tk.BooleanVar
    minimap: tk.BooleanVar
    trinket: tk.BooleanVar


class FeaturesView:
    """Renderiza uma linha por feature, com ícone, título, descrição e toggle."""

    def __init__(self, parent: tk.Widget, toggles: FeatureToggles) -> None:
        outer = tk.Frame(parent, bg=Colors.BACKGROUND_PRIMARY, padx=12)
        outer.pack(fill="x", pady=(10, 4))

        tk.Label(
            outer, text=UILabels.SECTION_FEATURES,
            font=Fonts.SECTION_HEADER,
            fg=Colors.GOLD_DIM, bg=Colors.BACKGROUND_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        card = tk.Frame(outer, bg=Colors.BACKGROUND_CARD)
        card.pack(fill="x")

        rows = (
            (
                toggles.skill_points,
                UILabels.FEATURE_SKILL_ICON,
                UILabels.FEATURE_SKILL_TITLE,
                UILabels.FEATURE_SKILL_DESCRIPTION,
            ),
            (
                toggles.objectives,
                UILabels.FEATURE_OBJECTIVES_ICON,
                UILabels.FEATURE_OBJECTIVES_TITLE,
                UILabels.FEATURE_OBJECTIVES_DESCRIPTION,
            ),
            (
                toggles.build_announce,
                UILabels.FEATURE_BUILD_ANNOUNCE_ICON,
                UILabels.FEATURE_BUILD_ANNOUNCE_TITLE,
                UILabels.FEATURE_BUILD_ANNOUNCE_DESCRIPTION,
            ),
            (
                toggles.next_item,
                UILabels.FEATURE_NEXT_ITEM_ICON,
                UILabels.FEATURE_NEXT_ITEM_TITLE,
                UILabels.FEATURE_NEXT_ITEM_DESCRIPTION,
            ),
            (
                toggles.minimap,
                UILabels.FEATURE_MINIMAP_ICON,
                UILabels.FEATURE_MINIMAP_TITLE,
                UILabels.FEATURE_MINIMAP_DESCRIPTION,
            ),
            (
                toggles.trinket,
                UILabels.FEATURE_TRINKET_ICON,
                UILabels.FEATURE_TRINKET_TITLE,
                UILabels.FEATURE_TRINKET_DESCRIPTION,
            ),
        )

        for index, (variable, icon, title, description) in enumerate(rows):
            if index > 0:
                tk.Frame(card, bg=Colors.BORDER, height=1).pack(fill="x")
            self._build_feature_row(card, variable, icon, title, description)

    @staticmethod
    def _build_feature_row(
        parent: tk.Widget,
        variable: tk.BooleanVar,
        icon: str,
        title: str,
        description: str,
    ) -> None:
        row = tk.Frame(parent, bg=Colors.BACKGROUND_CARD)
        row.pack(fill="x")

        badge = feature_badge(row, icon)
        badge.pack(side="left", padx=(12, 10), pady=10)

        text_frame = tk.Frame(row, bg=Colors.BACKGROUND_CARD)
        text_frame.pack(side="left", fill="x", expand=True)
        tk.Label(
            text_frame, text=title,
            font=Fonts.BODY_LABEL,
            fg=Colors.TEXT_PRIMARY, bg=Colors.BACKGROUND_CARD,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            text_frame, text=description,
            font=Fonts.DESCRIPTION,
            fg=Colors.TEXT_DIMMED, bg=Colors.BACKGROUND_CARD,
            anchor="w", wraplength=240,
        ).pack(fill="x")

        ToggleSwitch(row, variable).pack(side="right", padx=12, pady=10)
