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
