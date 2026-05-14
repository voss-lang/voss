"""HeaderBar widget — single-row session/model/budget/git summary.

UI-SPEC region "Header" (1 row, full width). Truncates from the right
with `…` when total content exceeds terminal width.
"""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class HeaderBar(Static):
    DEFAULT_CLASSES = ""

    def __init__(self, **kw) -> None:
        super().__init__("", **kw)
        self._session_id: str = ""
        self._model: str = ""
        self._budget_used: int = 0
        self._budget_total: int = 0
        self._git_status: str = ""

    def update_header(
        self,
        *,
        session_id: str = "",
        model: str = "",
        budget_used: int = 0,
        budget_total: int = 0,
        git_status: str = "",
    ) -> None:
        self._session_id = session_id
        self._model = model
        self._budget_used = budget_used
        self._budget_total = budget_total
        self._git_status = git_status
        self.update(self._render_text())

    def _render_text(self) -> Text:
        sid = (self._session_id or "")[:8]
        if self._budget_total > 0:
            budget = (
                f"{self._budget_used / 1000:.1f}k / "
                f"{self._budget_total / 1000:.1f}k"
            )
        else:
            budget = "—"
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(sid, style="bold")
        text.append(" · ", style="dim")
        text.append(self._model)
        text.append(" · ", style="dim")
        text.append(budget, style="dim")
        text.append(" · ", style="dim")
        text.append(self._git_status, style="dim")
        return text
