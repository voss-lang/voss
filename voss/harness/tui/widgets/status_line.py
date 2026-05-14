"""StatusLine widget — bottom-row metadata: model · tokens · cost · ctx%.

UI-SPEC region "Status line" (1 row, full width, dim accent background).
Toast field flashes for 1500ms then clears.
"""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class StatusLine(Static):
    DEFAULT_CLASSES = "dim"

    def __init__(self, **kw) -> None:
        super().__init__("", **kw)
        self._model: str = ""
        self._tokens: int = 0
        self._cost_usd: float = 0.0
        self._ctx_pct: float = 0.0
        self._toast: str | None = None
        self._toast_timer = None

    def set_status(
        self,
        *,
        model: str = "",
        tokens: int = 0,
        cost_usd: float = 0.0,
        ctx_pct: float = 0.0,
        toast: str | None = None,
    ) -> None:
        self._model = model
        self._tokens = tokens
        self._cost_usd = cost_usd
        self._ctx_pct = ctx_pct
        if toast is not None:
            self._toast = toast
            try:
                self._toast_timer = self.set_timer(1.5, self._clear_toast)
            except Exception:  # noqa: BLE001 — set_timer needs a running app loop
                self._toast_timer = None
        self.update(self._render_text())

    def _clear_toast(self) -> None:
        self._toast = None
        self.update(self._render_text())

    def _render_text(self) -> Text:
        text = Text(no_wrap=True, overflow="ellipsis")
        if self._model:
            text.append(self._model, style="bold")
            text.append(" · ", style="dim")
        text.append(f"{self._tokens:,} tok", style="dim")
        text.append(" · ", style="dim")
        cost_style = "signal-error" if self._cost_usd > 1.0 else "dim"
        text.append(f"${self._cost_usd:.3f}", style=cost_style)
        text.append(" · ", style="dim")
        ctx_style = "signal-warn" if self._ctx_pct > 0.8 else "dim"
        text.append(f"ctx {self._ctx_pct:.0%}", style=ctx_style)
        if self._toast:
            text.append("  ")
            text.append(self._toast, style="bold")
        return text
