"""HelpOverlay — `?` modal showing keymap + visible slash commands.

UI-SPEC heading copy locked: `voss tui · keys + commands`.
Dismissed by Esc.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


HEADING = "voss tui · keys + commands"


class HelpOverlay(ModalScreen):
    BINDINGS = [("escape", "app.pop_screen", "Close help")]

    def __init__(self, keymap, registry, **kw) -> None:
        super().__init__(**kw)
        self.keymap = keymap
        self.registry = registry

    def compose(self) -> ComposeResult:
        with Vertical(id="help-body"):
            yield Static(HEADING, id="help-title")
            yield Static("")
            yield Static("keys")
            for b in self.keymap:
                yield Static(f"  {b.key:<14} {b.context:<8} {b.description}")
            yield Static("")
            yield Static("commands")
            for name in self.registry.ids():
                cmd = self.registry.lookup(name)
                yield Static(f"  {name:<16} {cmd.help if cmd else ''}")
            yield Static("")
            yield Static("press Esc to close")
