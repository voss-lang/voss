"""TranscriptView widget — block transcript (main pane).

TUI redesign spec §3.1/§3.2 (docs/tui-redesign-spec.md, phases R1+R2).
Replaces the RichLog-based TurnView: every transcript entry is a discrete,
mutable child widget (UserBlock / AssistantBlock / RoleBlock / LocalBlock*),
so later phases can update entries in place (tool cards R3). R2 adds live
markdown streaming (throttled ≤10 Hz) and the ephemeral WorkingIndicator
(always last child while a turn runs). Auto-scrolls to tail unless the user
scrolled up; a new user message re-engages follow.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from .. import glyphs, palette
from .agent_tree import AgentTreeCard
from .tool_card import ToolCard
from .working_indicator import WorkingIndicator


EMPTY_HEADING = "type a message below to begin · / for commands"
ASSISTANT_INDENT = 2
RESUME_TASK_CHARS = 40  # spec §5.4: first-user-message truncated to 40 chars


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


def _relative_age(iso_ts: str) -> str:
    """`updated_at` ISO timestamp → coarse relative age ("2h ago")."""
    try:
        ts = datetime.fromisoformat(iso_ts)
    except (TypeError, ValueError):
        return ""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now(timezone.utc) - ts).total_seconds()))
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


class HomeScreen(Static):
    """Empty-state splash (spec §5.4): logo + version + data rows + hint.

    Mounted as TranscriptView's first child; removed (not cleared) on the
    first real append. R6 data rows (cwd / model / resume) are computed once
    on mount from the app fields cli.py seeds before `app.run()`; each row is
    omitted when its data is absent (so the bare test-app splash is
    unchanged). The resume row reads the same `.voss/sessions` store the
    /resume command uses (voss.harness.session.list_sessions) — newest
    non-current session as `⎇ <shortid> "<first task>" · <age>`.
    """

    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._info_rows: list[tuple[str, str]] = []

    def on_mount(self) -> None:
        self._info_rows = self._compute_info_rows()
        if self._info_rows:
            self.refresh()

    def _compute_info_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        try:
            app = self.app
        except Exception:  # noqa: BLE001 — unmounted (headless tests)
            return rows
        cwd = getattr(app, "cwd", None)
        if cwd is not None:
            try:
                cwd_text = str(cwd).replace(str(Path.home()), "~", 1)
            except Exception:  # noqa: BLE001
                cwd_text = str(cwd)
            git = getattr(app, "git_status", "") or ""
            rows.append(("cwd", f"{cwd_text}  ({git})" if git else cwd_text))
        provider = getattr(app, "provider", "") or ""
        model = getattr(app, "model", "") or ""
        if provider or model:
            label = f"{provider} / {model}" if provider and model else provider or model
            rows.append(("model", label))
        resume = self._resume_row(app)
        if resume:
            rows.append(("resume", resume))
        return rows

    def _resume_row(self, app) -> str:
        """Newest non-current session line, or "" when none exists."""
        cwd = getattr(app, "cwd", None)
        if cwd is None:
            return ""
        record = getattr(app, "record", None)
        current_id = getattr(record, "id", "") or getattr(app, "session_id", "")
        try:
            from voss.harness import session as session_store

            records = session_store.list_sessions(Path(cwd))
        except Exception:  # noqa: BLE001 — store unreadable ⇒ omit the row
            return ""
        for rec in records:  # list_sessions returns newest-first
            if current_id and rec.id == current_id:
                continue
            task = rec.first_task()
            if len(task) > RESUME_TASK_CHARS:
                task = task[: RESUME_TASK_CHARS - 1] + "…"
            line = f'{glyphs.FORK} {rec.id[:6]} "{task}"'
            age = _relative_age(rec.updated_at)
            if age:
                line += f" · {age}"
            return line
        return ""

    def render(self) -> Text:
        width = max(40, getattr(self.app.console.size, "width", 80))
        height = max(12, getattr(self.app.console.size, "height", 24))
        out = Text()
        for _ in range(max(1, min(4, height // 8))):
            out.append("\n")
        if width >= 70:
            for line in VOSS_LOGO:
                out.append(_center(line, width) + "\n", style=f"bold {palette.ACCENT}")
        else:
            out.append(_center("VOSS", width) + "\n", style=f"bold {palette.ACCENT}")
        out.append(_center("v1", width) + "\n", style="dim")
        out.append("\n")
        if self._info_rows:
            lines = [f"{label:<9}{value}" for label, value in self._info_rows]
            pad = " " * max(0, (width - max(len(ln) for ln in lines)) // 2)
            for ln in lines:
                out.append(f"{pad}{ln}\n", style="dim")
            out.append("\n")
        out.append(_center(EMPTY_HEADING, width), style="dim")
        return out


class UserBlock(Static):
    """User message block — ❯ glyph + dim text, continuation lines indented.

    Spec §3.2. R5 surface styling lives in styles.tcss (`UserBlock` rule):
    $surface background + $accent 6% left-edge tint (Open Q2 tint-only
    default — not an accent allow-list site).
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


# Live-stream re-render throttle (spec §3.3): coalesce markdown re-parses to
# ≤10 Hz. Chosen by R2 measurement: Rich Markdown re-render of a 20 KB doc
# at width 100 is ~40 ms p95 (< 50 ms budget); Textual's Markdown widget
# `update()` measured ~1.8 s at 20 KB and was rejected.
STREAM_RENDER_INTERVAL_S = 0.1


class AssistantBlock(Static):
    """Assistant block — 1-cell ● accent gutter + body column (spec §3.3).

    R2 streaming: deltas accumulate into a buffer and the block re-renders
    the buffer as live Rich Markdown in place, throttled to ≤10 Hz via a
    coalescing `set_timer` (live markdown from the first token; no finalize
    reflow pop). `finalize` cancels any pending coalesced render, renders the
    complete final markdown exactly once more, and appends a dim metadata
    footer BELOW the body — fixing the old header-below-body RichLog
    workaround. On interrupt the streamed content is kept and the footer
    reads `· interrupted`.
    """

    def __init__(self, body=None, *, plain: str = "", **kw) -> None:
        self._body = body if body is not None else Text("")
        self._footer: Text | None = None
        self._buffer: str = plain
        self._finalized: bool = False
        self._last_live_render: float = 0.0
        self._live_timer = None
        self._live_render_count: int = 0  # test hook: bounded by the throttle
        super().__init__(self._compose_renderable(), **kw)

    def _compose_renderable(self):
        from rich.console import Group
        from rich.table import Table

        grid = Table.grid(padding=(0, 1, 0, 0))
        grid.add_column(width=1, vertical="top")
        grid.add_column(ratio=1)
        grid.add_row(Text(glyphs.ASSISTANT, style=f"bold {palette.ACCENT}"), self._body)
        if self._footer is None:
            return grid
        return Group(grid, self._footer)

    def stream_update(self, delta: str) -> None:
        """Append one text delta; re-render live markdown, throttled ≤10 Hz.

        The first delta renders immediately (live markdown from the first
        token). Subsequent deltas inside the throttle window coalesce into
        one pending `set_timer` render; headless callers (no running app
        loop) fall back to rendering inline so content is never lost.
        """
        self._buffer += delta
        if self._finalized:
            return
        remaining = STREAM_RENDER_INTERVAL_S - (
            time.monotonic() - self._last_live_render
        )
        if remaining <= 0:
            if self._live_timer is not None:
                try:
                    self._live_timer.stop()
                except Exception:  # noqa: BLE001
                    pass
                self._live_timer = None
            self._render_live()
            return
        if self._live_timer is None:
            try:
                self._live_timer = self.set_timer(remaining, self._render_live)
            except Exception:  # noqa: BLE001 — set_timer needs a running app loop
                self._render_live()

    def _render_live(self) -> None:
        """Re-render the accumulated buffer as live markdown, in place."""
        from rich.markdown import Markdown

        self._live_timer = None
        if self._finalized:
            return
        self._last_live_render = time.monotonic()
        self._live_render_count += 1
        self._body = Markdown(self._buffer, code_theme="monokai")
        self.update(self._compose_renderable())

    def finalize(
        self,
        *,
        role: str,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
        accumulated_text: str | None = None,
        interrupted: bool = False,
    ) -> None:
        """Seal the block: final markdown render (exactly once) + dim footer.

        Footer fields: role · timestamp · cost · conf — only present fields.
        On interrupt the streamed content is kept and the footer gains a
        trailing `· interrupted` marker (spec §3.3).
        """
        from rich.markdown import Markdown

        if self._live_timer is not None:
            try:
                self._live_timer.stop()
            except Exception:  # noqa: BLE001
                pass
            self._live_timer = None
        self._finalized = True
        if accumulated_text:
            self._buffer = accumulated_text
        self._body = Markdown(self._buffer, code_theme="monokai")
        footer = Text(style="dim")
        footer.append(role)
        if timestamp:
            footer.append(f" · {timestamp}")
        if cost_usd is not None:
            footer.append(f" · ${cost_usd:.4f}")
        if confidence is not None:
            footer.append(f" · conf {confidence:.2f}")
        if interrupted:
            footer.append(" · interrupted")
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


# Trim policy (spec §3.2, R7): above TRIM_THRESHOLD mounted blocks the
# oldest blocks are flattened into one static placeholder, keeping the
# newest TRIM_KEEP — bounds widget count on long sessions (RichLog had
# `max_lines`; a widget transcript needs an equivalent).
TRIM_THRESHOLD = 500
TRIM_KEEP = 400


class TrimPlaceholder(Static):
    """Static stand-in for trimmed-away oldest blocks (spec §3.2, R7).

    Always TranscriptView's first child once trimming has tripped; its
    count grows on every subsequent trim:

        ≈ 110 earlier turns · /resume to reload
    """

    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._count = 0

    def set_count(self, count: int) -> None:
        self._count = count
        self.update(Text(self.plain_text(), style="dim"))

    def plain_text(self) -> str:
        return f"{glyphs.APPROX} {self._count} earlier turns · /resume to reload"


class TranscriptView(VerticalScroll):
    """Scrollable block transcript (spec §3.2) — keeps id `#main`.

    Append API mirrors the old TurnView entry points (`append_turn`,
    `append_markdown_turn`, `stream_delta`, `finalize_stream`) plus the
    spec block factories (`add_user`, `add_local_block`). Scroll policy:
    follow tail only when pinned to bottom; user scroll-up disengages;
    a new user message re-engages.

    R6 nav mode (spec §7.1): focusable; `esc` from an idle input bar lands
    here. j/k (or arrows) move block focus (`.nav-focus` accent tint),
    `enter` toggles the focused ToolCard, `y` copies the focused block,
    `g g`/`G` jump top/bottom (G re-engages auto-follow), and `i`/`esc`/any
    printable returns to the input (printables are forwarded so the first
    keystroke is never lost).
    """

    DEFAULT_CLASSES = ""
    can_focus = True  # R6 nav mode (spec §7.1)

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._turn_count = 0
        # R6 nav mode state: index into _nav_blocks(), None = no focus ring.
        self._nav_index: int | None = None
        self._pending_g: bool = False  # `g g` double-tap state machine
        self._streaming: bool = False
        self._stream_block: AssistantBlock | None = None
        # R2 working indicator (spec §3.6) — ephemeral, always last child
        # while active. `_pending_interrupt` is set by app.action_interrupt
        # so the cancellation path's finalize_stream gains the interrupted
        # footer without a Renderer-protocol signature change.
        self._working: WorkingIndicator | None = None
        self._pending_interrupt: bool = False
        # R3 tool cards (spec §3.4): one mutable card per call, keyed by the
        # harness-minted call_id so the settled event updates in place.
        self._tool_cards: dict[str, ToolCard] = {}
        # R4 inline agent trees (spec §3.5): one spawn parent card per
        # parent_id; child progress lines + gather mutate it in place.
        self._agent_trees: dict[str, AgentTreeCard] = {}
        # R7 trim policy (spec §3.2): one placeholder, cumulative count.
        self._trim_placeholder: TrimPlaceholder | None = None
        self._trimmed_count = 0

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
        # WorkingIndicator stays the last child (spec §3.2): while active,
        # every append mounts BEFORE it.
        if self._working is not None and self._working in list(self.children):
            try:
                self.mount(widget, before=self._working)
            except Exception:  # noqa: BLE001 — indicator mid-removal
                self.mount(widget)
        else:
            self.mount(widget)
        if len(self.children) > TRIM_THRESHOLD:  # cheap count check (R7)
            self._trim()
        if pinned:
            self.call_after_refresh(self.scroll_end, animate=False)

    def _trim(self) -> None:
        """Flatten the oldest blocks into the static placeholder (spec §3.2).

        Keeps the newest TRIM_KEEP real blocks; HomeScreen / WorkingIndicator
        / the placeholder itself are never trimmed. Trimmed ToolCard /
        AgentTreeCard ids are dropped from the in-place-update registries so
        a late settle for a trimmed call is a no-op, not a crash.

        `remove_children` is asynchronous — doomed children linger in
        `self.children` until the loop ticks — so each doomed widget is
        marked with `_trim_doomed` and excluded from later trims to keep
        the count exact across back-to-back appends.
        """
        blocks = [
            c
            for c in self.children
            if not isinstance(c, (HomeScreen, WorkingIndicator, TrimPlaceholder))
            and not getattr(c, "_trim_doomed", False)
        ]
        doomed = blocks[:-TRIM_KEEP]
        if not doomed:
            return
        doomed_set = set(doomed)
        for c in doomed:
            c._trim_doomed = True
        self._tool_cards = {
            k: v for k, v in self._tool_cards.items() if v not in doomed_set
        }
        self._agent_trees = {
            k: v for k, v in self._agent_trees.items() if v not in doomed_set
        }
        self._trimmed_count += len(doomed)
        self.remove_children(doomed)
        if self._trim_placeholder is None:
            self._trim_placeholder = TrimPlaceholder()
            self.mount(self._trim_placeholder, before=0)
        self._trim_placeholder.set_count(self._trimmed_count)

    # ------------------------------------------------------------------
    # block factories (spec §3.2)
    # ------------------------------------------------------------------

    def add_user(self, body: str) -> None:
        # Programmatic scroll-to-end on a new user message re-engages follow.
        self._append_block(UserBlock(body), separate=True, force_follow=True)

    def add_local_block(self, widget: Widget) -> None:
        """Mount an existing LocalBlock* (shell/note/notice) as a child."""
        self._append_block(widget, separate=False)

    def add_tool_card(self, call_id: str, name: str, args: dict) -> ToolCard:
        """Mount one ToolCard keyed by call_id (spec §3.2, R3)."""
        card = ToolCard(call_id, name, args)
        if self._detail_mode_on():
            card._expanded = True
        self._tool_cards[call_id] = card
        self._append_block(card, separate=False)
        return card

    def get_tool_card(self, call_id: str) -> ToolCard | None:
        return self._tool_cards.get(call_id)

    def _detail_mode_on(self) -> bool:
        """App-scoped ctrl+o expand-all state (spec §7.2): cards mounted
        while expanded-mode is on mount expanded."""
        try:
            return bool(getattr(self.app, "_detail_expanded", False))
        except Exception:  # noqa: BLE001 — unmounted (headless tests)
            return False

    # ------------------------------------------------------------------
    # inline agent trees (spec §3.5, R4)
    # ------------------------------------------------------------------

    def add_agent_tree(
        self, parent_id: str, agent_name: str, budget_total: int = 0
    ) -> AgentTreeCard:
        """Mount one spawn parent card keyed by parent_id (idempotent while
        the existing tree for that id is still running)."""
        existing = self._agent_trees.get(parent_id)
        if existing is not None and existing.state == "running":
            return existing
        card = AgentTreeCard(parent_id, agent_name, budget_total)
        if self._detail_mode_on():
            card._expanded = True
        self._agent_trees[parent_id] = card
        self._append_block(card, separate=False)
        return card

    def get_agent_tree(self, parent_id: str) -> AgentTreeCard | None:
        return self._agent_trees.get(parent_id)

    def update_agent_tree(self, parent_id: str, body_line: str, used: int = 0) -> None:
        """Append a child step row + tick the parent's live budget metric."""
        card = self._agent_trees.get(parent_id)
        if card is not None:
            card.add_child(body_line, used)

    def settle_agent_tree(self, parent_id: str, n_results: int = 0) -> None:
        """Final gather: settle the parent in place (idempotent)."""
        card = self._agent_trees.get(parent_id)
        if card is not None:
            card.gather(n_results)

    # ------------------------------------------------------------------
    # working indicator (spec §3.2 / §3.6, R2)
    # ------------------------------------------------------------------

    @property
    def working_active(self) -> bool:
        return self._working is not None

    def show_working(self, label: str = "working") -> None:
        """Mount the WorkingIndicator as last child, or update its label.

        Idempotent: dispatch (app) and turn start (renderer) may both call
        this; the second call only updates the label.
        """
        if self._working is not None:
            self._working.set_label(label)
            return
        indicator = WorkingIndicator(label)
        self._working = indicator
        self.mount(indicator)
        if self.is_vertical_scroll_end:
            self.call_after_refresh(self.scroll_end, animate=False)

    def update_working(self, elapsed_s: float, tokens: int) -> None:
        """Update the live metrics line (no-op when no indicator is active)."""
        if self._working is not None:
            self._working.update_metrics(elapsed_s, tokens)

    def hide_working(self) -> None:
        """Remove the WorkingIndicator (turn finalized or interrupted)."""
        indicator, self._working = self._working, None
        if indicator is not None:
            try:
                indicator.remove()
            except Exception:  # noqa: BLE001 — already unmounted
                pass

    def mark_interrupted(self) -> None:
        """Flag the in-flight turn as interrupted (app.action_interrupt).

        Consumed by the next finalize_stream so the sealed AssistantBlock's
        footer reads `· interrupted` (spec §3.3) — the agent's CancelledError
        handler still drives the actual finalize call.
        """
        self._pending_interrupt = True

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
        interrupted: bool = False,
    ) -> None:
        """Seal the active streaming block (final markdown + dim footer).

        The metadata lands as a footer BELOW the body inside the block —
        the old below-body "header" RichLog workaround is gone. Subsequent
        stream_delta calls start a new block. `interrupted` (or a pending
        mark_interrupted flag) adds the `· interrupted` footer marker.
        """
        interrupted = interrupted or self._pending_interrupt
        self._pending_interrupt = False
        if not self._streaming:
            return
        if self._stream_block is not None:
            self._stream_block.finalize(
                role=role,
                confidence=confidence,
                cost_usd=cost_usd,
                timestamp=timestamp,
                accumulated_text=accumulated_text,
                interrupted=interrupted,
            )
            if self.is_vertical_scroll_end:
                self.call_after_refresh(self.scroll_end, animate=False)
        self._streaming = False
        self._stream_block = None

    # ------------------------------------------------------------------
    # nav mode (spec §7.1, R6) — block focus while TranscriptView holds
    # real keyboard focus. Keymap rows live in keymap.py under the
    # "transcript" context tier; they resolve here via on_key.
    # ------------------------------------------------------------------

    def _nav_blocks(self) -> list[Widget]:
        """Navigable children — skips HomeScreen, WorkingIndicator and the
        static trim placeholder."""
        return [
            c
            for c in self.children
            if not isinstance(c, (HomeScreen, WorkingIndicator, TrimPlaceholder))
        ]

    def focused_block(self) -> Widget | None:
        blocks = self._nav_blocks()
        if not blocks or self._nav_index is None:
            return None
        return blocks[min(self._nav_index, len(blocks) - 1)]

    def _nav_set(self, index: int) -> None:
        blocks = self._nav_blocks()
        if not blocks:
            self._nav_index = None
            return
        index = max(0, min(len(blocks) - 1, index))
        for i, block in enumerate(blocks):
            block.set_class(i == index, "nav-focus")
        self._nav_index = index
        try:
            blocks[index].scroll_visible(animate=False)
        except Exception:  # noqa: BLE001 — headless/unmounted
            pass

    def _nav_clear(self) -> None:
        for block in self.query(".nav-focus"):
            block.remove_class("nav-focus")
        self._nav_index = None
        self._pending_g = False

    def focus_block(self, delta: int) -> None:
        """Move block focus by `delta` (spec §3.2 — j/k, up/down)."""
        blocks = self._nav_blocks()
        if not blocks:
            return
        if self._nav_index is None:
            self._nav_set(len(blocks) - 1)
            return
        self._nav_set(self._nav_index + delta)

    def toggle_focused(self) -> None:
        """Expand/collapse the focused ToolCard (no-op on other blocks)."""
        block = self.focused_block()
        if isinstance(block, ToolCard):
            block.toggle()

    def _nav_copy(self) -> None:
        """Copy the focused block's text to the clipboard + toast."""
        block = self.focused_block()
        if block is None:
            return
        toast = getattr(self.app, "_toast", lambda _m: None)
        getter = getattr(block, "plain_text", None)
        text = getter() if getter is not None else ""
        if not text:
            toast("nothing to copy")
            return
        try:
            self.app.copy_to_clipboard(text)
        except Exception:  # noqa: BLE001 — clipboard unavailable (no OSC52)
            toast("copy failed")
            return
        toast("copied block")

    def _nav_focus_input(self, forward_char: str | None = None) -> None:
        """Return focus to the input bar, forwarding a printable key."""
        try:
            bar = self.app.query_one("#input")
        except Exception:  # noqa: BLE001 — input absent in tests
            return
        bar.focus()
        if forward_char:
            try:
                bar.insert(forward_char)
            except Exception:  # noqa: BLE001
                pass

    def on_focus(self, event) -> None:
        # Entering nav mode lands on the newest block.
        if self._nav_index is None:
            blocks = self._nav_blocks()
            if blocks:
                self._nav_set(len(blocks) - 1)

    def on_blur(self, event) -> None:
        self._nav_clear()

    def on_key(self, event) -> None:
        key = event.key
        pending_g, self._pending_g = self._pending_g, False
        if key in ("escape", "i"):
            event.prevent_default()
            event.stop()
            self._nav_focus_input()
            return
        if key in ("j", "down"):
            event.prevent_default()
            event.stop()
            self.focus_block(1)
            return
        if key in ("k", "up"):
            event.prevent_default()
            event.stop()
            self.focus_block(-1)
            return
        if key == "enter":
            event.prevent_default()
            event.stop()
            self.toggle_focused()
            return
        if key == "y":
            event.prevent_default()
            event.stop()
            self._nav_copy()
            return
        if key == "g":
            event.prevent_default()
            event.stop()
            if pending_g:
                self._nav_set(0)
                self.scroll_home(animate=False)
            else:
                self._pending_g = True
            return
        if key in ("G", "upper_g"):
            # Bottom + re-engage auto-follow (scroll_end pins to tail).
            event.prevent_default()
            event.stop()
            blocks = self._nav_blocks()
            if blocks:
                self._nav_set(len(blocks) - 1)
            self.scroll_end(animate=False)
            return
        char = getattr(event, "character", None)
        if char and char.isprintable():
            # Any other printable lands in the input (spec §7.1).
            event.prevent_default()
            event.stop()
            self._nav_focus_input(forward_char=char)

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
    """Side region container — CodeIntelPanel is the sole occupant (R4 §5.6).

    Plain scroll container so the M9-02 layout test's `query_one("#side")`
    still finds a widget.
    """

    DEFAULT_CLASSES = ""
