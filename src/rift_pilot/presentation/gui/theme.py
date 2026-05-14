"""Paleta de cores, fontes e dimensões da interface gráfica."""
from __future__ import annotations


class Colors:
    BACKGROUND_PRIMARY = "#0f0f0f"
    BACKGROUND_CARD = "#1a1a1a"
    BACKGROUND_BADGE = "#252525"
    BORDER = "#2a2a2a"

    GOLD = "#c89b3c"
    GOLD_DIM = "#8a6a28"
    GOLD_DARK_ACTIVE = "#a07b1f"

    TEXT_PRIMARY = "#d4c4a0"
    TEXT_DIMMED = "#7a6a50"

    ACCENT_GREEN = "#4caf50"
    ACCENT_RED = "#ef5350"
    ACCENT_RED_PRESSED = "#b71c1c"
    TOGGLE_OFF = "#444444"
    KNOB_WHITE = "white"


class Fonts:
    TITLE = ("Segoe UI", 20, "bold")
    SUBTITLE = ("Segoe UI", 9)
    SECTION_HEADER = ("Segoe UI", 8, "bold")
    SECTION_LABEL = ("Segoe UI", 7, "bold")
    BODY_LABEL = ("Segoe UI", 10, "bold")
    BODY_TEXT = ("Segoe UI", 8)
    DESCRIPTION = ("Segoe UI", 7)
    BUTTON_PRIMARY = ("Segoe UI", 12, "bold")
    BUTTON_SMALL = ("Segoe UI", 7)
    LOG_LINE = ("Consolas", 8)
    FOOTER = ("Segoe UI", 7)
    BADGE_SMALL = ("Segoe UI", 11)
    BADGE_LARGE = ("Segoe UI", 14)
    STATUS_DOT = ("Segoe UI", 11)


class Dimensions:
    WINDOW_GEOMETRY = "420x960"
    TOGGLE_WIDTH = 44
    TOGGLE_HEIGHT = 24
    BADGE_BUILD_SIZE = 30
    BADGE_FEATURE_SIZE = 36
    LOG_HEIGHT_LINES = 7
    LOG_WRAP_WIDTH = 52
