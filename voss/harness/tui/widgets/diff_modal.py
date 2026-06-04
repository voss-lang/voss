"""DiffModal — per-hunk diff approval modal (M9-05, TUI-06).

UI-SPEC heading copy locked: `Review changes · {n} hunks · {file_count} files`.
Key bindings locked per UI-SPEC destructive-actions inventory:
  [y] Accept · [n] Reject · [s] Skip · [a] Accept all · [q] Reject all · [Esc] Cancel review.

Diff marker glyphs (`+` `-` `~`) are bare ASCII to keep --no-unicode fallback
byte-identical.
"""
from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static


@dataclass(frozen=True)
class Hunk:
    file: str
    start: int
    lines: list[str]


@dataclass(frozen=True)
class DiffDecision:
    file: str
    decision: str  # 'accept' | 'reject' | 'skip'


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
        with Vertical(id="diff-body"):
            yield Static(heading, id="diff-title", classes="modal-title")
            yield Static("")
            for i, h in enumerate(self.hunks):
                cursor = "~" if i == 0 else " "
                yield Static(
                    f"{cursor} {h.file}:{h.start}", id=f"diff-hunk-header-{i}"
                )
                for j, line in enumerate(h.lines):
                    yield Static(f"  {line}", id=f"diff-hunk-line-{i}-{j}")
            yield Static("")
            yield Static(
                "[y] Accept · [n] Reject · [s] Skip · [a] Accept all · "
                "[q] Reject all · [Esc] Cancel review",
                id="diff-footer",
            )

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

    def action_accept_one(self) -> None:
        if self.index >= len(self.hunks):
            return
        self._record("accept")
        if self.index >= len(self.hunks):
            self._finish()

    def action_reject_one(self) -> None:
        if self.index >= len(self.hunks):
            return
        self._record("reject")
        if self.index >= len(self.hunks):
            self._finish()

    def action_skip_one(self) -> None:
        if self.index >= len(self.hunks):
            return
        self._record("skip")
        if self.index >= len(self.hunks):
            self._finish()

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
