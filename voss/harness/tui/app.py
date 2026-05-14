"""VossTUIApp — Textual app shell mounting the locked region grid.

UI-SPEC region grid (1 row header, scrollable main pane + collapsible side
panel, 1 row status, 1+ row input). M9-02 ships the empty shell; later
plans wire palette (M9-03), recorder (M9-04), modals (M9-05), resume
(M9-06).
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal

from .widgets import HeaderBar, InputBar, StatusLine, SubAgentPanel, TurnView


class VossTUIApp(App):
    CSS_PATH = "styles.tcss"
    BINDINGS: list = []  # M9-03 fills via KEYMAP.

    def __init__(
        self,
        *,
        session_id: str = "",
        model: str = "",
        budget_total: int = 0,
        **kw,
    ) -> None:
        super().__init__(**kw)
        self.session_id = session_id
        self.model = model
        self.budget_total = budget_total

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header")
        with Horizontal():
            yield TurnView(id="main")
            yield SubAgentPanel(id="side")
        yield StatusLine(id="status")
        yield InputBar(id="input")

    def on_mount(self) -> None:
        # Locked default focus = input bar.
        self.query_one("#input", InputBar).focus()
        # Seed header so an unbound app still renders something useful.
        self.query_one("#header", HeaderBar).update_header(
            session_id=self.session_id,
            model=self.model,
            budget_used=0,
            budget_total=self.budget_total,
            git_status="",
        )
