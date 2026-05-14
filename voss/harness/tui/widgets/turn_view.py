"""TurnView widget — scrollable history of turns (main pane).

UI-SPEC region "Main pane". Auto-scrolls to tail unless user scrolled up.
M9-03 adds sticky-top mode; this plan ships the append + empty-state copy.
"""
from __future__ import annotations

from typing import Iterable

from rich.text import Text
from textual.widgets import RichLog


EMPTY_HEADING = "No turns yet"
EMPTY_BODY = "Type a task below to start. Use / for commands, ? for help."


class TurnView(RichLog):
    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(highlight=False, markup=False, wrap=True, **kw)
        self._turn_count = 0

    def on_mount(self) -> None:
        if self._turn_count == 0:
            heading = Text(EMPTY_HEADING, style="bold")
            body = Text(EMPTY_BODY, style="dim")
            self.write(heading)
            self.write(body)

    def append_turn(
        self,
        role: str,
        body: str,
        *,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
    ) -> None:
        if self._turn_count == 0:
            self.clear()
        self._turn_count += 1
        head = Text()
        head.append(role, style="bold")
        if timestamp:
            head.append(f"  · {timestamp}", style="dim")
        if cost_usd is not None:
            head.append(f"  · ${cost_usd:.4f}", style="dim")
        if confidence is not None:
            head.append(f"  · conf {confidence:.2f}", style="dim")
        self.write(head)
        # `body` is untrusted (LLM output) — render via plain Text, no markup.
        self.write(Text(body, no_wrap=False))


class SubAgentPanel(RichLog):
    """Side panel placeholder. M9-04 fills with spawn/gather state."""

    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(highlight=False, markup=False, wrap=True, **kw)
