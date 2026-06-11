"""WorkingIndicator widget — ephemeral turn-activity line (spec §3.6, R2).

One dim line, always the last TranscriptView child while a turn runs:

    ✦ working · 8s · 2.1k tok · ctrl+c to interrupt

The glyph slot starts as the `WORKING` brand glyph and animates through
`SPINNER_FRAMES` (iterated by index) at ~2 Hz once the app loop ticks.
Elapsed time refreshes at 1 Hz from the widget's own mount time, so the
renderer only needs to thread token updates (`update_working`). Timers are
guarded like status_line.py — headless unit tests construct the widget
without a running app and must not explode.

No accent color: the entire line (glyph included) renders dim — the locked
accent allow-list does not include the working indicator.
"""
from __future__ import annotations

import time

from rich.text import Text
from textual.widgets import Static

from .. import glyphs


SPINNER_INTERVAL_S = 0.5  # ~2 Hz glyph animation (spec §3.6)
ELAPSED_INTERVAL_S = 1.0  # 1 Hz elapsed refresh


def _fmt_tokens(tokens: int) -> str:
    if tokens >= 1000:
        return f"{tokens / 1000:.1f}k"
    return str(tokens)


class WorkingIndicator(Static):
    """Ephemeral last-child activity line; mounted/removed by TranscriptView."""

    DEFAULT_CLASSES = ""

    def __init__(self, label: str = "working", **kw) -> None:
        super().__init__(**kw)
        self._label = label
        self._tokens = 0
        self._started = time.monotonic()
        self._elapsed_override: float | None = None
        self._frame = -1  # -1 → brand glyph until the first animation tick
        self._spin_timer = None
        self._tick_timer = None

    def on_mount(self) -> None:
        try:
            self._spin_timer = self.set_interval(
                SPINNER_INTERVAL_S, self._advance_frame
            )
            self._tick_timer = self.set_interval(ELAPSED_INTERVAL_S, self.refresh)
        except Exception:  # noqa: BLE001 — set_interval needs a running app loop
            self._spin_timer = None
            self._tick_timer = None

    def _advance_frame(self) -> None:
        self._frame += 1
        self.refresh()

    # ------------------------------------------------------------------
    # state mutators (called by TranscriptView.show_working/update_working)
    # ------------------------------------------------------------------

    def set_label(self, label: str) -> None:
        self._label = label
        self.refresh()

    def update_metrics(self, elapsed_s: float, tokens: int) -> None:
        # elapsed_s <= 0 means "no caller-side clock" — keep self-timing.
        if elapsed_s > 0:
            self._elapsed_override = elapsed_s
        if tokens > 0:
            self._tokens = tokens
        self.refresh()

    def _elapsed(self) -> float:
        if self._elapsed_override is not None:
            return self._elapsed_override
        return time.monotonic() - self._started

    def render(self) -> Text:
        if self._frame < 0:
            glyph = glyphs.WORKING
        else:
            frames = glyphs.SPINNER_FRAMES
            glyph = frames[self._frame % len(frames)]
        out = Text(style="dim")
        out.append(glyph)
        out.append(f" {self._label} · {int(self._elapsed())}s")
        if self._tokens > 0:
            out.append(f" · {_fmt_tokens(self._tokens)} tok")
        out.append(" · ctrl+c to interrupt")
        return out

    def plain_text(self) -> str:
        return self.render().plain
