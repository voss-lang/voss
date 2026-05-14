"""BudgetExhaustedModal — turn-budget exhaustion modal (M9-05, TUI-07).

UI-SPEC locked copy:
  Heading: `Budget exhausted`
  Body:    `Turn stopped at {tokens} / {limit} tokens. Continue with a new budget, or end the turn.`
  Buttons: `[c] Continue +2000 · [e] End turn · [Esc] Cancel`
"""
from __future__ import annotations

from typing import Literal

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static


BudgetChoice = Literal["continue", "end", "cancel"]


class BudgetExhaustedModal(ModalScreen):
    BINDINGS = [
        ("c", "continue_turn", "Continue +2000"),
        ("e", "end_turn", "End turn"),
        ("escape", "cancel", "Cancel"),
    ]

    class BudgetDecision(Message):
        def __init__(self, choice: BudgetChoice) -> None:
            super().__init__()
            self.choice = choice

    def __init__(self, tokens_used: int, tokens_limit: int, **kw) -> None:
        super().__init__(**kw)
        self.tokens_used = tokens_used
        self.tokens_limit = tokens_limit

    def compose(self) -> ComposeResult:
        body = (
            f"Turn stopped at {self.tokens_used} / {self.tokens_limit} tokens. "
            "Continue with a new budget, or end the turn."
        )
        with Vertical(id="budget-body"):
            yield Static("Budget exhausted", id="budget-title", classes="modal-title")
            yield Static("")
            yield Static(body, id="budget-message")
            yield Static("")
            yield Static(
                "[c] Continue +2000 · [e] End turn · [Esc] Cancel",
                id="budget-footer",
            )

    def _finish(self, choice: BudgetChoice) -> None:
        self.post_message(self.BudgetDecision(choice))
        self.dismiss(choice)

    def action_continue_turn(self) -> None:
        self._finish("continue")

    def action_end_turn(self) -> None:
        self._finish("end")

    def action_cancel(self) -> None:
        self._finish("cancel")
