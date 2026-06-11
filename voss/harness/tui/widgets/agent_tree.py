"""AgentTreeCard widget — inline sub-agent spawn card (spec §3.5, R4).

Replaces the retired side-panel SubAgentPanel: a spawn renders as a parent
ToolCard in the transcript; child step lines (`show_subagent_progress`
payloads, already-settled text) nest under it with the locked
NEST_MID/NEST_LAST glyphs; the final gather settles the parent in place.

    ⏺ spawn researcher                                12.4k/32k tok
      ├─ read docs/sdk.md
      ├─ grep "max_turns" · 7 matches
      └─ ⏺ gathered · 3 results

Quiet-by-default (D-09 preserved): collapsed shows ONLY the spawn line +
live budget counter (right metric). Child rows reveal via click or the
global ctrl+o expand/collapse-all action — there is no expander hint line,
unlike the base ToolCard, so the collapsed card stays a single row.
"""
from __future__ import annotations

import time

from rich.console import Group
from rich.table import Table
from rich.text import Text

from .. import glyphs
from .tool_card import ToolCard, _fmt_duration


def _fmt_tok(n: int) -> str:
    """Token count for the budget metric: 12400 -> `12.4k`, 900 -> `900`."""
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


class AgentTreeCard(ToolCard):
    """Parent spawn card with nested child rows (spec §3.5).

    Child rows are lightweight renderable lines inside the parent card
    (NOT nested ToolCard widgets): progress lines arrive as already-settled
    text, so full child widgets would buy nothing but layout churn.
    """

    def __init__(
        self, parent_id: str, agent_name: str, budget_total: int = 0, **kw
    ) -> None:
        super().__init__(parent_id, f"spawn {agent_name}", {}, **kw)
        self.parent_id = parent_id
        self.agent_name = agent_name
        self.budget_total = max(0, int(budget_total or 0))
        self.budget_used = 0
        self._child_lines: list[str] = []

    # ------------------------------------------------------------------
    # child rows + gather
    # ------------------------------------------------------------------

    def add_child(self, line: str, used: int = 0) -> None:
        """Append one child step row; tick the live budget counter."""
        self._child_lines.append(str(line))
        if used:
            self.budget_used = max(self.budget_used, int(used))
        self.refresh(layout=True)

    def gather(self, n_results: int = 0) -> None:
        """Final gather: settled summary row + settle the parent (spec mock).

        Idempotent — the fan-out gather path is documented safe to re-drive
        (MAG-07); a second gather on a settled card is a no-op.
        """
        if self._state != "running":
            return
        summary = f"gathered · {n_results} result{'s' if n_results != 1 else ''}"
        self._child_lines.append(f"{glyphs.TOOL_OK} {summary}")
        self.settle("ok", summary)

    # ------------------------------------------------------------------
    # ToolCard overrides
    # ------------------------------------------------------------------

    def _has_body(self) -> bool:
        # Unlike the base card, child rows are expandable WHILE running.
        return bool(self._child_lines)

    def _budget_text(self) -> str:
        if self.budget_total > 0:
            return f"{_fmt_tok(self.budget_used)}/{_fmt_tok(self.budget_total)} tok"
        if self.budget_used > 0:
            return f"{_fmt_tok(self.budget_used)} tok"
        return ""

    def _head(self) -> Table:
        grid = Table.grid(padding=(0, 1, 0, 0), expand=True)
        grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        grid.add_column(justify="right", no_wrap=True)
        left = Text()
        if self._state == "running":
            frames = glyphs.SPINNER_FRAMES
            left.append(frames[self._frame % len(frames)], style="dim")
            left.append(f" {self._tool_name}", style="dim")
            fallback = _fmt_duration(time.monotonic() - self._started)
        else:
            klass = "signal-good" if self._state == "ok" else "signal-error"
            left.append(glyphs.TOOL_OK, style=klass)
            left.append(f" {self._tool_name}")
            fallback = _fmt_duration(self._elapsed)
        # Right metric = live budget `used/total tok` (replaces the retired
        # BudgetMeter-in-panel); duration when no budget signal exists.
        grid.add_row(left, Text(self._budget_text() or fallback, style="dim"))
        return grid

    def _child_rows(self) -> list[Text]:
        rows: list[Text] = []
        last = len(self._child_lines) - 1
        for i, line in enumerate(self._child_lines):
            nest = glyphs.NEST_LAST if i == last else glyphs.NEST_MID
            rows.append(Text(f"  {nest} {line}", style="dim"))
        return rows

    def render(self):
        # D-09: collapsed = the spawn line + budget counter, nothing else.
        if not self._expanded or not self._child_lines:
            return self._head()
        return Group(self._head(), *self._child_rows())

    def plain_text(self) -> str:
        if self._state == "running":
            frames = glyphs.SPINNER_FRAMES
            glyph = frames[self._frame % len(frames)]
        else:
            glyph = glyphs.TOOL_OK
        head = f"{glyph} {self._tool_name}"
        budget = self._budget_text()
        if budget:
            head += f"  {budget}"
        parts = [head]
        if self._expanded:
            parts.extend(t.plain for t in self._child_rows())
        return "\n".join(parts)
