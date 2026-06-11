"""Toast widget — 1-line overlay notification (R5, spec §5.3).

Top-right, `$raised` background, overlay layer (styling lives in
styles.tcss). Auto-dismisses after 1.5 s; a persistent variant stays
until `clear()` — the permissions/thinking paths use it via the
StatusLine deprecation shims. Replaces the old status-line toast field
so session metadata never jumps.
"""
from __future__ import annotations

from textual.widgets import Static

TOAST_DISMISS_S = 1.5


class Toast(Static):
    """Ephemeral overlay notice. Hidden whenever no toast is active."""

    def __init__(self, **kw) -> None:
        super().__init__("", markup=False, **kw)
        self._text: str | None = None
        self._persistent: bool = False
        self._timer = None

    @property
    def text_content(self) -> str | None:
        """The active toast text, or None when hidden (test/introspection)."""
        return self._text

    def show_toast(self, text: str, *, persistent: bool = False) -> None:
        """Show `text`; auto-dismiss after 1.5 s unless `persistent`."""
        self._stop_timer()
        self._text = text
        self._persistent = persistent
        self.update(text)
        self.display = True
        if not persistent:
            try:
                self._timer = self.set_timer(TOAST_DISMISS_S, self.clear)
            except Exception:  # noqa: BLE001 — set_timer needs a running app loop
                self._timer = None

    def clear(self) -> None:
        """Dismiss the active toast (timed or persistent)."""
        self._stop_timer()
        self._text = None
        self._persistent = False
        self.update("")
        self.display = False

    def _stop_timer(self) -> None:
        if self._timer is not None:
            try:
                self._timer.stop()
            except Exception:  # noqa: BLE001
                pass
            self._timer = None
