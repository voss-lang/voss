"""DiffModal — per-hunk diff approval modal (M9-05, TUI-06).

UI-SPEC heading copy locked: `Review changes · {n} hunks · {file_count} files`.
Key bindings locked per UI-SPEC destructive-actions inventory:
  [y] Accept · [n] Reject · [s] Skip · [a] Accept all · [q] Reject all · [Esc] Cancel review.

Diff marker glyphs (`+` `-`) are bare ASCII to keep --no-unicode fallback
byte-identical. Line CONTENT is unchanged from upstream; color + syntax
highlighting are style overlays only, and the decided-state labels
(`[accepted]` etc.) are ASCII so the no-unicode contract holds.

The per-hunk approve-BEFORE-write gate is a Voss differentiator (OpenCode
applies-then-undoes); this module upgrades only the *rendering* — colored
+/- lines, syntax-highlighted code, and a cursor that actually tracks the
hunk under decision — without touching the decision flow.
"""
from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static

# Mirror of the styles.tcss locked 5-color contract for Rich-side rendering
# (Rich Text cannot reference TCSS `$vars`). Kept in lock-step with
# styles.tcss; turn_view.py sets the same precedent (IGNITE_ORANGE).
_C_ADD = "#5FD75F"     # $good   — added lines
_C_DEL = "#FF5F5F"     # $error  — removed lines
_C_DIM = "#888888"     # $dim    — context / metadata
_C_ACCENT = "#ff5b1f"  # $accent — hunk header / active cursor


@dataclass(frozen=True)
class Hunk:
    file: str
    start: int
    lines: list[str]


@dataclass(frozen=True)
class DiffDecision:
    file: str
    decision: str  # 'accept' | 'reject' | 'skip'


def _guess_lexer(file: str) -> str | None:
    """Best-effort lexer name from a filename; None if undeterminable."""
    try:
        from rich.syntax import Syntax

        return Syntax.guess_lexer(file)
    except Exception:  # noqa: BLE001 — guess is advisory; plain render on failure
        return None


def _highlight_code(code: str, lexer: str | None) -> Text:
    """Syntax-highlight a single code fragment, falling back to plain text.

    Guarded end-to-end: a missing lexer, an unknown language, or any Rich
    error degrades to an unstyled Text so a render hiccup never breaks the
    approval gate.
    """
    if not lexer or not code.strip():
        return Text(code)
    try:
        from rich.syntax import Syntax

        syntax = Syntax(code, lexer, theme="monokai", background_color="default")
        highlighted = syntax.highlight(code)
        highlighted.rstrip()  # drop the trailing newline Syntax appends
        return highlighted
    except Exception:  # noqa: BLE001
        return Text(code)


def render_diff_line(line: str, *, lexer: str | None = None) -> Text:
    """Render one diff line as colored (and, for adds/context, syntax-highlighted)
    Rich Text. Pure — unit-testable without a Textual app.

    Marker is re-emitted as bare ASCII `+`/`-`/space (no glyph from outside
    the locked vocabulary), so the line's visible characters match upstream.
    """
    marker = line[:1]
    if marker == "+":
        out = Text("+", style=f"bold {_C_ADD}")
        out.append(_highlight_code(line[1:], lexer))
        return out
    if marker == "-":
        out = Text("-", style=f"bold {_C_DEL}")
        out.append(Text(line[1:], style=_C_DEL))
        return out
    # context (producer emits only +/- today; handle gracefully regardless)
    body = line[1:] if marker == " " else line
    out = Text(" " if marker == " " else "", style=_C_DIM)
    out.append(Text(body, style=_C_DIM))
    return out


_STATE_LABEL = {
    "accept": ("  [accepted]", _C_ADD),
    "reject": ("  [rejected]", _C_DEL),
    "skip": ("  [skipped]", _C_DIM),
}


class DiffModal(ModalScreen):
    BINDINGS = [
        ("y", "accept_one", "Accept hunk"),
        ("n", "reject_one", "Reject hunk"),
        ("s", "skip_one", "Skip hunk"),
        ("a", "accept_all", "Accept all"),
        ("q", "reject_all", "Reject all"),
        ("escape", "cancel", "Cancel review"),
    ]

    class DiffSubmitted(Message):
        def __init__(self, decisions: list[DiffDecision], cancelled: bool) -> None:
            super().__init__()
            self.decisions = decisions
            self.cancelled = cancelled

    def __init__(self, hunks: list[Hunk], **kw) -> None:
        super().__init__(**kw)
        self.hunks: list[Hunk] = list(hunks)
        self.index = 0
        self.decisions: list[DiffDecision] = []

    def compose(self) -> ComposeResult:
        files = {h.file for h in self.hunks}
        heading = f"Review changes · {len(self.hunks)} hunks · {len(files)} files"
        with VerticalScroll(id="diff-body"):
            yield Static(heading, id="diff-title", classes="modal-title")
            yield Static("")
            for i, h in enumerate(self.hunks):
                lexer = _guess_lexer(h.file)
                with Vertical(id=f"diff-hunk-{i}", classes="diff-hunk"):
                    yield Static(
                        Text(f"{h.file}:{h.start}", style=f"bold {_C_ACCENT}"),
                        id=f"diff-hunk-header-{i}",
                        classes="diff-hunk-header",
                    )
                    for j, line in enumerate(h.lines):
                        yield Static(
                            render_diff_line(line, lexer=lexer),
                            id=f"diff-hunk-line-{i}-{j}",
                        )
            yield Static("")
            yield Static(
                "[y] Accept · [n] Reject · [s] Skip · [a] Accept all · "
                "[q] Reject all · [Esc] Cancel review",
                id="diff-footer",
            )

    def on_mount(self) -> None:
        self._refresh_marks()

    # ------------------------------------------------------------------
    # cursor / decided-state rendering (display only — no decision logic)
    # ------------------------------------------------------------------

    def _refresh_marks(self) -> None:
        """Highlight the hunk currently under decision, label decided hunks,
        and scroll the active hunk into view."""
        decided_by_pos = [d.decision for d in self.decisions]
        for i, h in enumerate(self.hunks):
            try:
                container = self.query_one(f"#diff-hunk-{i}", Vertical)
                header = self.query_one(f"#diff-hunk-header-{i}", Static)
            except Exception:  # noqa: BLE001 — mid-mount / test host
                continue
            container.set_class(i == self.index, "current")
            base = Text(f"{h.file}:{h.start}", style=f"bold {_C_ACCENT}")
            if i < len(decided_by_pos):
                label, color = _STATE_LABEL.get(decided_by_pos[i], ("", _C_DIM))
                base.append(label, style=color)
            elif i == self.index:
                base.append("  < deciding", style=_C_ACCENT)
            header.update(base)
        if 0 <= self.index < len(self.hunks):
            try:
                self.query_one(f"#diff-hunk-{self.index}", Vertical).scroll_visible()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def _record(self, decision: str) -> None:
        h = self.hunks[self.index]
        self.decisions.append(DiffDecision(file=h.file, decision=decision))
        self.index += 1

    def _finish(self, cancelled: bool = False) -> None:
        msg = self.DiffSubmitted(self.decisions, cancelled=cancelled)
        self.post_message(msg)
        self.dismiss(self.decisions if not cancelled else [])

    def _decide_one(self, decision: str) -> None:
        if self.index >= len(self.hunks):
            return
        self._record(decision)
        if self.index >= len(self.hunks):
            self._finish()
        else:
            self._refresh_marks()

    def action_accept_one(self) -> None:
        self._decide_one("accept")

    def action_reject_one(self) -> None:
        self._decide_one("reject")

    def action_skip_one(self) -> None:
        self._decide_one("skip")

    def action_accept_all(self) -> None:
        while self.index < len(self.hunks):
            self._record("accept")
        self._finish()

    def action_reject_all(self) -> None:
        while self.index < len(self.hunks):
            self._record("reject")
        self._finish()

    def action_cancel(self) -> None:
        self.decisions = []
        self._finish(cancelled=True)
