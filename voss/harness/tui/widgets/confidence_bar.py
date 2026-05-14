"""ConfidenceBar widget — locked 16-cell width (W4).

Format: `{bar:10} {value:.2f} ` — 10 bar + 1 space + 4 numeric + 1 trailing = 16.
Tier class chosen by value; `.accent` only when `is_final=True AND value >= 0.85`
(UI-SPEC accent allow-list item 6).
"""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from .. import glyphs


class ConfidenceBar(Static):
    DEFAULT_CLASSES = ""

    def __init__(self, value: float = 0.0, is_final: bool = False, **kw) -> None:
        super().__init__("", **kw)
        self.value = max(0.0, min(1.0, value))
        self.is_final = is_final

    def render(self):
        filled = round(self.value * 10)
        bar = glyphs.BAR_FILL * filled + glyphs.BAR_EMPTY * (10 - filled)
        numeric = f"{self.value:.2f}"  # exactly 4 chars: d.dd
        # Tier — UI-SPEC Color Contract thresholds.
        if self.is_final and self.value >= 0.85:
            klass = "accent"
        elif self.value >= 0.85:
            klass = "signal-good"
        elif self.value >= 0.50:
            klass = "signal-warn"
        else:
            klass = "signal-error"
        # LOCKED WIDTH: 10 bar + 1 space + 4 numeric + 1 trailing = 16 cells (W4).
        text = Text(f"{bar} {numeric} ")
        text.stylize(klass)
        return text
