"""TurnView widget — scrollable history of turns (main pane).

UI-SPEC region "Main pane". Auto-scrolls to tail unless user scrolled up.
M9-03 adds sticky-top mode; this plan ships the append + empty-state copy.
"""
from __future__ import annotations

from typing import Iterable

from rich.text import Text
from textual.widgets import RichLog


EMPTY_BRAND = "VOSS"
EMPTY_HEADING = "type a message below to begin - / for commands"
EMPTY_BODY = "Ask Voss anything..."
IGNITE_ORANGE = "#ff5b1f"


VOSS_LOGO = [
    "__      ______   _____ _____",
    "\\ \\    / / __ \\ / ____/ ____|",
    " \\ \\  / / |  | | (___| (___",
    "  \\ \\/ /| |  | |\\___ \\\\___ \\",
    "   \\  / | |__| |____) |___) |",
    "    \\/   \\____/|_____/_____/",
]


def _center(line: str, width: int) -> str:
    if width <= len(line):
        return line
    return " " * ((width - len(line)) // 2) + line


class TurnView(RichLog):
    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(highlight=False, markup=False, wrap=True, **kw)
        self._turn_count = 0
        self._streaming: bool = False

    def on_mount(self) -> None:
        if self._turn_count == 0:
            width = max(40, getattr(self.app.console.size, "width", 80))
            height = max(12, getattr(self.app.console.size, "height", 24))
            for _ in range(max(1, min(4, height // 8))):
                self.write(Text(""))
            if width >= 70:
                self.write(Text(_center(EMPTY_BRAND, width), style=f"bold {IGNITE_ORANGE}"))
                self.write(Text(""))
                for line in VOSS_LOGO:
                    self.write(Text(_center(line, width), style=f"bold {IGNITE_ORANGE}"))
            else:
                self.write(Text(_center(EMPTY_BRAND, width), style=f"bold {IGNITE_ORANGE}"))
            self.write(Text(_center("v1", width), style="dim"))
            self.write(Text(""))
            self.write(Text(_center(EMPTY_HEADING, width), style="dim"))

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

    # T1-04: streaming entry points consumed by the iteration loop (T1-05).
    # CONTEXT.md locks "Append-only via RichLog.write on every TextDelta. No
    # in-place edits, no scroll jumps." RichLog has no edit-previous-line
    # API, so streaming writes one delta at a time and finalize_stream
    # writes the role/cost/confidence header AFTER the streamed body. Header
    # placement intentionally diverges from append_turn (which writes the
    # header first); ITER-03's 500ms first-token target rules out waiting
    # for cost/confidence before showing any text.

    def stream_delta(self, text: str) -> None:
        """Write one incremental text delta into the live streaming block."""
        if self._turn_count == 0 and not self._streaming:
            self.clear()
        self._streaming = True
        self.write(Text(text, no_wrap=False))

    def finalize_stream(
        self,
        *,
        role: str,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Seal the active streaming block by writing its trailing header.

        Header lands BELOW the streamed body — RichLog is append-only, so
        the role/cost/confidence row cannot be retro-prepended. Subsequent
        stream_delta calls start a new block.
        """
        if not self._streaming:
            return
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
        self._streaming = False


class SideRegion(RichLog):
    """Side region container — M9-04 mounts real SubAgentPanels inside.

    Kept as a RichLog so the M9-02 layout test's `query_one("#side")` still
    finds a widget; SubAgentPanels are mounted as children when spawn fires.
    """

    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(highlight=False, markup=False, wrap=True, **kw)
