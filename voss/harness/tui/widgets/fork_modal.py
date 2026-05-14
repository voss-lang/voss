"""ForkConfirmModal — confirm fork-from-turn (M9-06, TUI-08).

UI-SPEC locked copy:
  Heading: `Fork session from turn {n}?`
  Body:    `Creates a new session starting from this turn. The current session keeps its history.`
  Buttons: `[Enter] Fork · [Esc] Cancel`
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static


class ForkConfirmModal(ModalScreen):
    BINDINGS = [
        ("enter", "confirm", "Fork"),
        ("escape", "cancel", "Cancel"),
    ]

    class ForkConfirmed(Message):
        def __init__(self, turn_n: int) -> None:
            super().__init__()
            self.turn_n = turn_n

    class ForkCancelled(Message):
        pass

    def __init__(self, turn_n: int, **kw) -> None:
        super().__init__(**kw)
        self.turn_n = turn_n

    def compose(self) -> ComposeResult:
        with Vertical(id="fork-body"):
            yield Static(
                f"Fork session from turn {self.turn_n}?",
                id="fork-title",
                classes="modal-title",
            )
            yield Static("")
            yield Static(
                "Creates a new session starting from this turn. "
                "The current session keeps its history.",
                id="fork-message",
            )
            yield Static("")
            yield Static(
                "[Enter] Fork · [Esc] Cancel",
                id="fork-footer",
            )

    def action_confirm(self) -> None:
        self.post_message(self.ForkConfirmed(self.turn_n))
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.post_message(self.ForkCancelled())
        self.dismiss(False)
