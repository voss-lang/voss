"""StatusLine widget — single-row, two-zone session metadata (R5, spec §5.2).

Left zone: brand `▌ voss` (accent, allow-listed site) + provider/model +
phase. Right zone: 4-cell context bar + percent ($warn ≥ 75%, $error at
100%), budget `used/total` when a budget is set, session cost, git. The
left zone truncates first (Rich grid: left column ratio, right column
content-width).

Toasts no longer render here (spec §5.3): the `toast=` kwarg and the
`set_persistent_toast`/`clear_toast` methods are deprecation shims that
delegate to the app's Toast overlay widget so call sites (permissions
bridge / show_thinking / fork flash) keep working unchanged.

Colors come from the palette.py mirror — Rich Text cannot read tcss vars.
"""
from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from .. import glyphs, palette

# Status line accent glyph — matches InputBar prompt for visual consistency.
_BRAND_GLYPH = glyphs.PROMPT

# Context-bar width in cells (spec §5.2 mock: `▰▰▱▱ 34%`).
_CTX_CELLS = 4


class StatusLine(Static):

    def __init__(self, **kw) -> None:
        super().__init__("", **kw)
        self._provider: str = ""
        self._model: str = ""
        self._mode: str = ""
        self._phase: str = ""
        self._git_status: str = ""
        self._tokens: int = 0
        self._cost_usd: float = 0.0
        self._ctx_pct: float = 0.0
        self._budget_total: int = 0

    def set_status(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        mode: str | None = None,
        phase: str | None = None,
        git_status: str | None = None,
        tokens: int | None = None,
        cost_usd: float | None = None,
        ctx_pct: float | None = None,
        budget_total: int | None = None,
        toast: str | None = None,
    ) -> None:
        if provider is not None:
            self._provider = provider
        if model is not None:
            self._model = model
        if mode is not None:
            self._mode = mode
        if phase is not None:
            self._phase = phase
        if git_status is not None:
            self._git_status = git_status
        if tokens is not None:
            self._tokens = tokens
        if cost_usd is not None:
            self._cost_usd = cost_usd
        if ctx_pct is not None:
            self._ctx_pct = ctx_pct
        if budget_total is not None:
            self._budget_total = budget_total
        if toast is not None:
            # Deprecation shim (spec §5.2/§5.3): toasts moved to the overlay.
            self._delegate_toast(toast, persistent=False)
        self.update(self._render_grid())

    # ------------------------------------------------------------------
    # Toast deprecation shims — delegate to the app's Toast overlay so the
    # renderer / permissions-bridge / fork call sites stay unchanged.
    # ------------------------------------------------------------------

    def set_persistent_toast(self, text: str) -> None:
        """Shim: show a toast that stays until explicitly cleared."""
        self._delegate_toast(text, persistent=True)

    def clear_toast(self) -> None:
        """Shim: clear any active toast (persistent or timed)."""
        toast = self._toast_widget()
        if toast is not None:
            toast.clear()

    def _delegate_toast(self, text: str, *, persistent: bool) -> None:
        toast = self._toast_widget()
        if toast is not None:
            toast.show_toast(text, persistent=persistent)

    def _toast_widget(self):
        from .toast import Toast

        try:
            return self.app.query_one("#toast", Toast)
        except Exception:  # noqa: BLE001 — headless StatusLine / no overlay mounted
            return None

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------

    def _render_grid(self) -> Table:
        grid = Table.grid(expand=True, padding=(0, 0))
        grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        grid.add_column(justify="right", no_wrap=True, overflow="crop")
        grid.add_row(self._left_text(), self._right_text())
        return grid

    def _left_text(self) -> Text:
        t = Text(no_wrap=True)
        t.append(f"{_BRAND_GLYPH} voss", style=f"bold {palette.ACCENT}")
        pm = self._provider_model()
        if pm:
            t.append(" · ", style=palette.DIM)
            t.append(pm, style=palette.TEXT)
        phase = self._phase or self._mode
        if phase:
            t.append(" · ", style=palette.DIM)
            t.append(phase, style=palette.DIM)
        return t

    def _right_text(self) -> Text:
        t = Text(no_wrap=True)
        # Context bar — thresholds match the locked color contract rows:
        # $warn at 75..99%, $error at 100%.
        pct = max(0.0, self._ctx_pct)
        filled = min(_CTX_CELLS, int(round(min(pct, 1.0) * _CTX_CELLS)))
        if pct >= 1.0:
            bar_style = palette.ERROR
        elif pct >= 0.75:
            bar_style = palette.WARN
        else:
            bar_style = palette.DIM
        bar = glyphs.BUDGET_FILL * filled + glyphs.BUDGET_EMPTY * (_CTX_CELLS - filled)
        t.append(f"{bar} {pct:.0%}", style=bar_style)
        # Budget used/total — from the old HeaderBar (R5 spec §5.1).
        if self._budget_total > 0:
            t.append(" · ", style=palette.DIM)
            t.append(
                f"{self._tokens / 1000:.1f}k/{self._budget_total / 1000:.1f}k",
                style=palette.DIM,
            )
        # Cost
        cost_style = palette.ERROR if self._cost_usd > 1.0 else palette.TEXT
        t.append(" · ", style=palette.DIM)
        t.append(f"${self._cost_usd:.2f}", style=cost_style)
        # Git branch / dirty marker (or cwd fallback fed by the renderer)
        if self._git_status:
            t.append(" · ", style=palette.DIM)
            t.append(self._git_status, style=palette.DIM)
        return t

    def plain_text(self) -> str:
        """Flatten both zones for tests/introspection."""
        return f"{self._left_text().plain}  {self._right_text().plain}"

    def _provider_model(self) -> str:
        if self._provider and self._model:
            return f"{self._provider} / {self._model}"
        return self._provider or self._model
