"""Read-only budget trace modal (M11-05)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from .budget_meter import BudgetMeter


@dataclass(frozen=True)
class BudgetTraceRow:
    label: str
    used: int
    total: int | None = None
    detail: str = ""


class BudgetTraceModal(ModalScreen):
    """Display recorded budget frames without accept/reject controls."""

    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def __init__(
        self,
        text: str,
        rows: Iterable[BudgetTraceRow] | None = None,
        *,
        used: int = 0,
        total: int = 0,
        title: str = "Budget trace",
        **kw: Any,
    ) -> None:
        super().__init__(**kw)
        self.text = text
        self.rows = list(rows or [])
        if not self.rows and (used or total):
            self.rows.append(BudgetTraceRow("cumulative", used=used, total=total))
        self.title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="budget-trace-body"):
            yield Static(self.title, id="budget-trace-title", classes="modal-title")
            yield Static("")
            yield Static(self.text, id="budget-trace-text")
            if self.rows:
                yield Static("")
                for index, row in enumerate(self.rows):
                    yield Static(
                        _row_label(row),
                        id=f"budget-trace-row-label-{index}",
                    )
                    if row.total is not None and row.total > 0:
                        yield BudgetMeter(
                            used=row.used,
                            total=row.total,
                            id=f"budget-trace-row-meter-{index}",
                        )
                    else:
                        yield Static(
                            f"cumulative tokens: {row.used}",
                            id=f"budget-trace-row-fallback-{index}",
                        )
            yield Static("")
            yield Static("Press Esc to close", id="budget-trace-footer")


def _row_label(row: BudgetTraceRow) -> str:
    if row.detail:
        return f"{row.label}: {row.detail}"
    return row.label
