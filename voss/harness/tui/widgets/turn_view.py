"""TranscriptView widget — block transcript (main pane).

TUI redesign spec §3.1/§3.2 (docs/tui-redesign-spec.md, phase R1). Replaces
the RichLog-based TurnView: every transcript entry is a discrete, mutable
child widget (UserBlock / AssistantBlock / RoleBlock / LocalBlock*), so later
phases can update entries in place (tool cards R3, live markdown R2).
Auto-scrolls to tail unless the user scrolled up; a new user message
re-engages follow.
"""
from __future__ import annotations

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

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


class HomeScreen(Static):
    """Empty-state splash (spec §5.4, R1-minimal: logo + version + hint).

    Mounted as TranscriptView's first child; removed (not cleared) on the
    first real append. Data rows (cwd/model/resume) arrive in R6.
    """

    DEFAULT_CLASSES = ""

    def render(self) -> Text:
        width = max(40, getattr(self.app.console.size, "width", 80))
        height = max(12, getattr(self.app.console.size, "height", 24))
        out = Text()
        for _ in range(max(1, min(4, height // 8))):
            out.append("\n")
        if width >= 70:
            for line in VOSS_LOGO:
                out.append(_center(line, width) + "\n", style=f"bold {IGNITE_ORANGE}")
        else:
            out.append(_center("VOSS", width) + "\n", style=f"bold {IGNITE_ORANGE}")
        out.append(_center("v1", width) + "\n", style="dim")
        out.append("\n")
        out.append(_center(EMPTY_HEADING, width), style="dim")
        return out


class UserBlock(Static):
    """User message block — ❯ glyph + dim text, continuation lines indented.

    Spec §3.2. Surface background styling comes in R5; R1 preserves the
    plain dim look of the old `_write_user`.
    """

    def __init__(self, body: str, **kw) -> None:
        lines = body.split("\n") or [""]
        text = Text()
        text.append(f"{glyphs.USER_INPUT} ", style="dim")
        text.append(lines[0], style="dim")
        for ln in lines[1:]:
            text.append("\n")
            text.append(f"  {ln}", style="dim")
        super().__init__(text, **kw)
        self._plain = text.plain

    def plain_text(self) -> str:
        return self._plain


class AssistantBlock(Static):
    """Assistant block — 1-cell ● accent gutter + body column (spec §3.3).

    R1 interim streaming: deltas accumulate into a buffer and the block is
    updated in place (one widget per response, no per-delta writes).
    `finalize` swaps the body to Markdown when the accumulated text is
    provided and appends a dim metadata footer BELOW the body — fixing the
    old header-below-body RichLog workaround. Throttled live markdown is R2.
    """

    def __init__(self, body=None, *, plain: str = "", **kw) -> None:
        self._body = body if body is not None else Text("")
        self._footer: Text | None = None
        self._buffer: str = plain
        super().__init__(self._compose_renderable(), **kw)

    def _compose_renderable(self):
        from rich.console import Group
        from rich.table import Table

        grid = Table.grid(padding=(0, 1, 0, 0))
        grid.add_column(width=1, vertical="top")
        grid.add_column(ratio=1)
        grid.add_row(Text(glyphs.ASSISTANT, style=f"bold {IGNITE_ORANGE}"), self._body)
        if self._footer is None:
            return grid
        return Group(grid, self._footer)

    def stream_update(self, delta: str) -> None:
        """Append one text delta and re-render the block in place."""
        self._buffer += delta
        self._body = Text(self._buffer, no_wrap=False)
        self.update(self._compose_renderable())

    def finalize(
        self,
        *,
        role: str,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
        accumulated_text: str | None = None,
    ) -> None:
        """Seal the block: optional markdown swap + dim footer line.

        Footer fields: role · timestamp · cost · conf — only present fields.
        """
        if accumulated_text:
            from rich.markdown import Markdown

            self._body = Markdown(accumulated_text, code_theme="monokai")
            self._buffer = accumulated_text
        footer = Text(style="dim")
        footer.append(role)
        if timestamp:
            footer.append(f" · {timestamp}")
        if cost_usd is not None:
            footer.append(f" · ${cost_usd:.4f}")
        if confidence is not None:
            footer.append(f" · conf {confidence:.2f}")
        self._footer = footer
        self.update(self._compose_renderable())

    def plain_text(self) -> str:
        parts = [self._buffer]
        if self._footer is not None:
            parts.append(self._footer.plain)
        return "\n".join(p for p in parts if p)


class RoleBlock(Static):
    """Non user/assistant roles (tool, gather, inspect, change, notice, …).

    Renders as today: dim role label line + indented dim body.
    """

    def __init__(self, role: str, body: str, *, markdown: bool = False, **kw) -> None:
        if markdown:
            from rich.console import Group
            from rich.markdown import Markdown
            from rich.padding import Padding

            renderable = Group(
                Text(role, style="dim"),
                Padding(Markdown(body, code_theme="monokai"), (0, 0, 0, ASSISTANT_INDENT)),
            )
        else:
            text = Text(role, style="dim")
            for ln in body.split("\n"):
                text.append("\n")
                text.append(f"{' ' * ASSISTANT_INDENT}{ln}", style="dim")
            renderable = text
        super().__init__(renderable, **kw)
        self._plain = f"{role}\n{body}"

    def plain_text(self) -> str:
        return self._plain


class TranscriptView(VerticalScroll):
    """Scrollable block transcript (spec §3.2) — keeps id `#main`.

    Append API mirrors the old TurnView entry points (`append_turn`,
    `append_markdown_turn`, `stream_delta`, `finalize_stream`) plus the
    spec block factories (`add_user`, `add_local_block`). Scroll policy:
    follow tail only when pinned to bottom; user scroll-up disengages;
    a new user message re-engages.
    """

    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._turn_count = 0
        self._streaming: bool = False
        self._stream_block: AssistantBlock | None = None

    def compose(self):
        yield HomeScreen()

    # ------------------------------------------------------------------
    # internal append plumbing + scroll policy
    # ------------------------------------------------------------------

    def _remove_home(self) -> None:
        for home in self.query(HomeScreen):
            home.remove()

    def _append_block(
        self, widget: Widget, *, separate: bool, force_follow: bool = False
    ) -> None:
        """Mount one transcript block; scroll to tail only when pinned.

        `separate` reproduces the old `_begin_turn` blank-line gap between
        turns (margin-top on every block after the first).
        """
        self._remove_home()
        if separate and self._turn_count > 0:
            widget.styles.margin = (1, 0, 0, 0)
        pinned = force_follow or self.is_vertical_scroll_end
        self._turn_count += 1
        self.mount(widget)
        if pinned:
            self.call_after_refresh(self.scroll_end, animate=False)

    # ------------------------------------------------------------------
    # block factories (spec §3.2)
    # ------------------------------------------------------------------

    def add_user(self, body: str) -> None:
        # Programmatic scroll-to-end on a new user message re-engages follow.
        self._append_block(UserBlock(body), separate=True, force_follow=True)

    def add_local_block(self, widget: Widget) -> None:
        """Mount an existing LocalBlock* (shell/note/notice) as a child."""
        self._append_block(widget, separate=False)

    # ------------------------------------------------------------------
    # append entry points (TextualRenderer non-stream paths)
    # ------------------------------------------------------------------

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
        if role == "user":
            self.add_user(body)
            return
        if role == "assistant":
            # `body` is untrusted (LLM output) — render via plain Text, no markup.
            self._append_block(
                AssistantBlock(Text(body, no_wrap=False), plain=body), separate=True
            )
            return
        self._append_block(RoleBlock(role, body), separate=True)

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

        if role == "user":
            self.add_user(body)
            return
        if role == "assistant":
            self._append_block(
                AssistantBlock(Markdown(body, code_theme="monokai"), plain=body),
                separate=True,
            )
            return
        self._append_block(RoleBlock(role, body, markdown=True), separate=True)

    # ------------------------------------------------------------------
    # streaming entry points consumed by the iteration loop (T1-05).
    # R1 interim (spec §8 R1): first delta creates an AssistantBlock;
    # subsequent deltas update it in place — no per-delta widget growth.
    # Throttling / live markdown is R2.
    # ------------------------------------------------------------------

    def stream_delta(self, text: str) -> None:
        """Route one incremental text delta into the live AssistantBlock."""
        if not self._streaming or self._stream_block is None:
            block = AssistantBlock()
            self._streaming = True
            self._stream_block = block
            self._append_block(block, separate=False)
            block.stream_update(text)
            return
        self._stream_block.stream_update(text)
        if self.is_vertical_scroll_end:
            self.call_after_refresh(self.scroll_end, animate=False)

    def finalize_stream(
        self,
        *,
        role: str,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
        accumulated_text: str | None = None,
    ) -> None:
        """Seal the active streaming block (markdown swap + dim footer).

        The metadata lands as a footer BELOW the body inside the block —
        the old below-body "header" RichLog workaround is gone. Subsequent
        stream_delta calls start a new block.
        """
        if not self._streaming:
            return
        if self._stream_block is not None:
            self._stream_block.finalize(
                role=role,
                confidence=confidence,
                cost_usd=cost_usd,
                timestamp=timestamp,
                accumulated_text=accumulated_text,
            )
            if self.is_vertical_scroll_end:
                self.call_after_refresh(self.scroll_end, animate=False)
        self._streaming = False
        self._stream_block = None

    # ------------------------------------------------------------------
    # test/introspection helper
    # ------------------------------------------------------------------

    def plain_text(self) -> str:
        """Flatten every mounted block to plain text (tests + copy paths)."""
        parts: list[str] = []
        for child in self.children:
            getter = getattr(child, "plain_text", None)
            if getter is not None:
                parts.append(getter())
                continue
            try:
                rendered = child.render()
            except Exception:  # noqa: BLE001 — non-text child (e.g. bars)
                continue
            parts.append(rendered.plain if isinstance(rendered, Text) else str(rendered))
        return "\n".join(parts)


class SideRegion(VerticalScroll):
    """Side region container — SubAgentPanel / CodeIntelPanel mount inside.

    Plain scroll container so the M9-02 layout test's `query_one("#side")`
    still finds a widget; panels are mounted as children when spawn fires.
    """

    DEFAULT_CLASSES = ""
