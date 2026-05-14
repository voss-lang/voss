"""PermissionModal — three-choice permission prompt (M9-05, TUI-07).

UI-SPEC locked copy:
  Heading: `Permission required`
  Body:    `Tool {tool_name} wants to {action_verb} {target}.`
  Buttons: `[a] Allow once · [A] Allow always · [d] Deny · [Esc] Deny`

Plus the scope-expand variant matching permissions._interactive_expand_prompt:
  [y] yes once · [a] always (this session) · [n] no · [Esc] no.
"""
from __future__ import annotations

from typing import Literal

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Static


PermissionChoice = Literal["a", "A", "d"]


class PermissionModal(ModalScreen):
    BINDINGS = [
        ("a", "once", "Allow once"),
        ("A", "always", "Allow always"),
        ("d", "deny", "Deny"),
        ("escape", "deny", "Deny"),
    ]

    class PermissionDecision(Message):
        def __init__(self, choice: PermissionChoice) -> None:
            super().__init__()
            self.choice = choice

    def __init__(
        self, tool_name: str, action_verb: str, target: str, **kw
    ) -> None:
        super().__init__(**kw)
        self.tool_name = tool_name
        self.action_verb = action_verb
        self.target = target

    def compose(self) -> ComposeResult:
        body = f"Tool {self.tool_name} wants to {self.action_verb} {self.target}."
        with Vertical(id="permission-body"):
            yield Static("Permission required", id="permission-title", classes="modal-title")
            yield Static("")
            yield Static(body, id="permission-message")
            yield Static("")
            yield Static(
                "[a] Allow once · [A] Allow always · [d] Deny · [Esc] Deny",
                id="permission-footer",
            )

    def _finish(self, choice: PermissionChoice) -> None:
        self.post_message(self.PermissionDecision(choice))
        self.dismiss(choice)

    def action_once(self) -> None:
        self._finish("a")

    def action_always(self) -> None:
        self._finish("A")

    def action_deny(self) -> None:
        self._finish("d")


ScopeChoice = Literal["once", "always", "n"]


class ScopeExpandModal(ModalScreen):
    """Mirrors `_interactive_expand_prompt`: [y] once · [a] always · [n]/Esc no."""

    BINDINGS = [
        ("y", "once", "Yes once"),
        ("a", "always", "Always this session"),
        ("n", "deny", "No"),
        ("escape", "deny", "No"),
    ]

    class ScopeDecision(Message):
        def __init__(self, choice: ScopeChoice) -> None:
            super().__init__()
            self.choice = choice

    def __init__(self, target: str, **kw) -> None:
        super().__init__(**kw)
        self.target = target

    def compose(self) -> ComposeResult:
        with Vertical(id="scope-body"):
            yield Static("Expand edit scope?", id="scope-title", classes="modal-title")
            yield Static("")
            yield Static(
                f"Allow writes to {self.target}?", id="scope-message"
            )
            yield Static("")
            yield Static(
                "[y] yes once · [a] always (this session) · [n] no · [Esc] no",
                id="scope-footer",
            )

    def _finish(self, choice: ScopeChoice) -> None:
        self.post_message(self.ScopeDecision(choice))
        self.dismiss(choice)

    def action_once(self) -> None:
        self._finish("once")

    def action_always(self) -> None:
        self._finish("always")

    def action_deny(self) -> None:
        self._finish("n")
