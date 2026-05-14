"""BudgetMeter widget — locked em-dash placeholder on zero-total (W5).

Format (normal): `{bar:10}  {used}k / {total}k ` — 10 + 2 + numeric + 1 trailing.
Format (no signal, total<=0): `{empty_bar}  —  ` — 10 + 2 + 1 + 2 = 15 cells.
NEVER derives `total = used / pct`; em-dash explicitly signals "no budget yet".
"""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from .. import glyphs


class BudgetMeter(Static):
    DEFAULT_CLASSES = ""

    def __init__(self, used: int = 0, total: int = 0, **kw) -> None:
        super().__init__("", **kw)
        self.used = max(0, int(used))
        self.total = max(0, int(total))

    def render(self):
        # W5: no budget signal yet — render em-dash placeholder; no division.
        if self.total <= 0:
            empty_bar = glyphs.BUDGET_EMPTY * 10
            return Text(f"{empty_bar}  —  ")
        pct = self.used / self.total
        filled = round(min(pct, 1.0) * 10)
        bar = glyphs.BUDGET_FILL * filled + glyphs.BUDGET_EMPTY * (10 - filled)
        numeric = f"{self.used / 1000:.1f}k / {self.total / 1000:.1f}k"
        if pct >= 1.0:
            klass = "signal-error"
        elif pct >= 0.75:
            klass = "signal-warn"
        else:
            klass = ""
        text = Text(f"{bar}  {numeric} ")
        if klass:
            text.stylize(klass)
        return text
