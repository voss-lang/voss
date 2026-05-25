"""StatusLine widget — bottom-row dense session metadata.

UI-SPEC region "Status line" (1 row, full width, dim accent background).
Toast field flashes for 1500ms then clears.
"""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from .. import glyphs

# Status line accent glyph — matches InputBar prompt for visual consistency.
_BRAND_GLYPH = glyphs.PROMPT


class StatusLine(Static):

    def __init__(self, **kw) -> None:
        super().__init__("", **kw)
        self._provider: str = ""
        self._model: str = ""
        self._mode: str = ""
        self._git_status: str = ""
        self._tokens: int = 0
        self._cost_usd: float = 0.0
        self._ctx_pct: float = 0.0
        self._toast: str | None = None
        self._toast_timer = None

    def set_status(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        mode: str | None = None,
        git_status: str | None = None,
        tokens: int | None = None,
        cost_usd: float | None = None,
        ctx_pct: float | None = None,
        toast: str | None = None,
    ) -> None:
        if provider is not None:
            self._provider = provider
        if model is not None:
            self._model = model
        if mode is not None:
            self._mode = mode
        if git_status is not None:
            self._git_status = git_status
        if tokens is not None:
            self._tokens = tokens
        if cost_usd is not None:
            self._cost_usd = cost_usd
        if ctx_pct is not None:
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

        # Brand glyph
        text.append(f" {_BRAND_GLYPH} voss", style="bold #ff5b1f")

        # Provider / model
        provider_model = self._provider_model()
        if provider_model:
            text.append(" | ", style="dim")
            text.append(provider_model)

        # Context usage
        text.append(" | ", style="dim")
        ctx_style = "bold #FFD75F" if self._ctx_pct > 0.8 else ""
        total_k = self._tokens / 1000 if self._tokens else 0
        if 0 < self._ctx_pct <= 1 and self._tokens > 0:
            ctx_total = int(self._tokens / self._ctx_pct) if self._ctx_pct > 0 else 0
            ctx_total_k = ctx_total / 1000
            text.append(f"{self._ctx_pct:.0%} ({total_k:.0f}K/{ctx_total_k:.0f}K)", style=ctx_style)
        else:
            text.append(f"{self._ctx_pct:.0%} ({total_k:.0f}K)", style=ctx_style)

        # Cwd / git
        if self._git_status:
            text.append(" | ", style="dim")
            text.append(self._git_status, style="dim")

        # Cost
        text.append(" | ", style="dim")
        cost_style = "bold #FF5F5F" if self._cost_usd > 1.0 else ""
        text.append(f"${self._cost_usd:.2f}", style=cost_style)

        # Mode
        if self._mode:
            text.append(" | ", style="dim")
            text.append(self._mode, style="dim")

        # Toast
        if self._toast:
            text.append("  ")
            text.append(self._toast, style="#ff5b1f")
        return text

    def _provider_model(self) -> str:
        if self._provider and self._model:
            return f"{self._provider} / {self._model}"
        return self._provider or self._model
