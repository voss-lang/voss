"""SubAgentPanel widget — side-region card for an active spawn.

UI-SPEC "Component Inventory" SubAgentPanel row. Accent-colored header
(allow-list item 4). Embedded BudgetMeter inherits the M9-02 W5 zero-total
contract (em-dash placeholder when `budget_total <= 0`).
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from .budget_meter import BudgetMeter


class SubAgentPanel(Vertical):
    DEFAULT_CSS = """
    SubAgentPanel {
        border-left: solid $dim;
        padding: 1 2;
        height: auto;
        min-height: 4;
    }
    SubAgentPanel .agent-header {
        color: $accent;
        text-style: bold;
    }
    SubAgentPanel .mini-status {
        color: $dim;
    }
    SubAgentPanel .agent-body {
        padding: 0 0;
        display: none;
    }
    """

    def __init__(
        self,
        *,
        name: str,
        parent_id: str,
        budget_used: int = 0,
        budget_total: int = 0,
        **kw,
    ) -> None:
        super().__init__(**kw)
        self.agent_name = name
        self.parent_id = parent_id
        self.budget_used = budget_used
        self.budget_total = budget_total

    def compose(self) -> ComposeResult:
        yield Static(self.agent_name, classes="agent-header")
        yield BudgetMeter(
            used=self.budget_used,
            total=self.budget_total,
            classes="mini-status",
            id=f"panel-budget-{self.parent_id}",
        )
        yield Vertical(id=f"panel-body-{self.parent_id}", classes="agent-body")

    def on_mount(self) -> None:
        # D-09 quiet-by-default. The DEFAULT_CSS `.agent-body { display:
        # none; }` rule above documents intent, but Textual resolves
        # `widget.styles.display` from the INLINE style object (a
        # descendant DEFAULT_CSS rule does not populate it — same as the
        # styles.tcss `#side { display: none; }` precedent). Set the body
        # Vertical's inline display so the panel is genuinely quiet by
        # default; `append_body` still mounts captured Static step lines
        # while hidden (capture-not-render), and
        # `VossTUIApp.action_toggle_subagent_detail` flips this inline
        # value on Ctrl+O. compose/append_body/update_budget unchanged.
        try:
            self.query_one(
                f"#panel-body-{self.parent_id}", Vertical
            ).styles.display = "none"
        except Exception:  # noqa: BLE001 — body not composed yet (defensive)
            pass

    def append_body(self, line: str) -> None:
        body = self.query_one(f"#panel-body-{self.parent_id}", Vertical)
        # markup=False so LLM-emitted ANSI escapes / brackets stay literal.
        body.mount(Static(line, markup=False))

    def update_budget(self, used: int) -> None:
        self.budget_used = max(0, int(used))
        meter = self.query_one(f"#panel-budget-{self.parent_id}", BudgetMeter)
        meter.used = self.budget_used
        meter.total = self.budget_total
        meter.refresh()
