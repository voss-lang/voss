"""StatusLine widget — bottom-row dense session metadata.

UI-SPEC region "Status line" (1 row, full width).
Uses Textual markup (not Rich.Text) so CSS color rules apply correctly.
Toast field flashes for 1500ms then clears.
"""
from __future__ import annotations

from textual.widgets import Static

from .. import glyphs

# Status line accent glyph — matches InputBar prompt for visual consistency.
_BRAND_GLYPH = glyphs.PROMPT


def _esc(s: str) -> str:
    """Escape Textual markup characters in user-supplied strings."""
    return s.replace("[", "\\[").replace("]", "\\]")


class StatusLine(Static):

    def __init__(self, **kw) -> None:
        super().__init__("", markup=True, **kw)
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
            if self._toast_timer is not None:
                try:
                    self._toast_timer.stop()
                except Exception:  # noqa: BLE001
                    pass
                self._toast_timer = None
            try:
                self._toast_timer = self.set_timer(1.5, self._clear_toast)
            except Exception:  # noqa: BLE001 — set_timer needs a running app loop
                self._toast_timer = None
        self.update(self._render_markup())

    def set_persistent_toast(self, text: str) -> None:
        """Set a toast that stays until explicitly cleared."""
        if self._toast_timer is not None:
            try:
                self._toast_timer.stop()
            except Exception:  # noqa: BLE001
                pass
            self._toast_timer = None
        self._toast = text
        self.update(self._render_markup())

    def clear_toast(self) -> None:
        """Clear any active toast (persistent or timed)."""
        self._clear_toast()

    def _clear_toast(self) -> None:
        self._toast = None
        self.update(self._render_markup())

    def _render_markup(self) -> str:
        parts: list[str] = []

        # Brand
        parts.append(f"[bold #ff5b1f] {_esc(_BRAND_GLYPH)} voss[/]")

        # Provider / model
        pm = self._provider_model()
        if pm:
            parts.append(f"[#888888] | [/]{_esc(pm)}")

        # Context usage
        total_k = self._tokens / 1000 if self._tokens else 0
        ctx_color = "#FFD75F" if self._ctx_pct > 0.8 else "#cccccc"
        if 0 < self._ctx_pct <= 1 and self._tokens > 0:
            ctx_total = int(self._tokens / self._ctx_pct) if self._ctx_pct > 0 else 0
            ctx_total_k = ctx_total / 1000
            ctx_text = f"{self._ctx_pct:.0%} ({total_k:.0f}K/{ctx_total_k:.0f}K)"
        else:
            ctx_text = f"{self._ctx_pct:.0%} ({total_k:.0f}K)"
        parts.append(f"[#888888] | [/][{ctx_color}]{ctx_text}[/]")

        # Cwd / git
        if self._git_status:
            parts.append(f"[#888888] | {_esc(self._git_status)}[/]")

        # Cost
        cost_color = "#FF5F5F" if self._cost_usd > 1.0 else "#cccccc"
        parts.append(f"[#888888] | [/][{cost_color}]${self._cost_usd:.2f}[/]")

        # Mode
        if self._mode:
            parts.append(f"[#888888] | {_esc(self._mode)}[/]")

        # Toast
        if self._toast:
            parts.append(f"  [#ff5b1f]{_esc(self._toast)}[/]")

        return "".join(parts)

    def _provider_model(self) -> str:
        if self._provider and self._model:
            return f"{self._provider} / {self._model}"
        return self._provider or self._model
