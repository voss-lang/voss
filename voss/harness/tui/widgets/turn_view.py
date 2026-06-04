"""TurnView widget — scrollable history of turns (main pane).

UI-SPEC region "Main pane". Auto-scrolls to tail unless user scrolled up.
M9-03 adds sticky-top mode; this plan ships the append + empty-state copy.
"""
from __future__ import annotations

from typing import Iterable

from rich.text import Text
from textual.widgets import RichLog

from .. import glyphs


EMPTY_HEADING = "type a message below to begin · / for commands"
IGNITE_ORANGE = "#ff5b1f"
ASSISTANT_INDENT = 2


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
                for line in VOSS_LOGO:
                    self.write(Text(_center(line, width), style=f"bold {IGNITE_ORANGE}"))
            else:
                self.write(Text(_center("VOSS", width), style=f"bold {IGNITE_ORANGE}"))
            self.write(Text(_center("v1", width), style="dim"))
            self.write(Text(""))
            self.write(Text(_center(EMPTY_HEADING, width), style="dim"))

    def _begin_turn(self) -> None:
        """Clear the splash on the first turn; otherwise blank-line separate."""
        if self._turn_count == 0:
            self.clear()
        else:
            self.write(Text(""))
        self._turn_count += 1

    def _write_user(self, body: str) -> None:
        """Render a user message: accent prompt glyph + indented continuation."""
        lines = body.split("\n") or [""]
        first = Text(f"{glyphs.USER_INPUT} ", style=f"bold {IGNITE_ORANGE}")
        first.append(lines[0])
        self.write(first)
        for ln in lines[1:]:
            self.write(Text(f"  {ln}", no_wrap=False))

    def append_turn(
        self,
        role: str,
        body: str,
        *,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
    ) -> None:
        # Chat layout: user gets a prompt glyph, everything else is indented
        # under a dim role label. Cost/confidence/timestamp live on the status
        # line, never inline (keeps the transcript reading like a chat).
        self._begin_turn()
        if role == "user":
            self._write_user(body)
            return
        if role != "assistant":
            self.write(Text(role, style="dim"))
        # `body` is untrusted (LLM output) — render via plain Text, no markup.
        for ln in body.split("\n"):
            self.write(Text(f"{' ' * ASSISTANT_INDENT}{ln}", no_wrap=False))

    def append_markdown_turn(
        self,
        role: str,
        body: str,
        *,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Like append_turn but renders body as markdown with code highlighting."""
        from rich.markdown import Markdown
        from rich.padding import Padding

        self._begin_turn()
        if role == "user":
            self._write_user(body)
            return
        if role != "assistant":
            self.write(Text(role, style="dim"))
        # Indent the whole rendered block (incl. code fences) under the turn.
        self.write(Padding(Markdown(body, code_theme="monokai"), (0, 0, 0, ASSISTANT_INDENT)))

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
        accumulated_text: str | None = None,
    ) -> None:
        """Seal the active streaming block by writing its trailing header.

        Header lands BELOW the streamed body — RichLog is append-only, so
        the role/cost/confidence row cannot be retro-prepended. Subsequent
        stream_delta calls start a new block.

        If accumulated_text is provided, renders the complete response as
        markdown with syntax-highlighted code blocks below the header.
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
        if accumulated_text:
            from rich.markdown import Markdown

            self.write(Markdown(accumulated_text, code_theme="monokai"))
        self._streaming = False


class SideRegion(RichLog):
    """Side region container — M9-04 mounts real SubAgentPanels inside.

    Kept as a RichLog so the M9-02 layout test's `query_one("#side")` still
    finds a widget; SubAgentPanels are mounted as children when spawn fires.
    """

    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(highlight=False, markup=False, wrap=True, **kw)
