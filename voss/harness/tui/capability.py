"""TUI activation decision shim.

Pure-Python capability probe. The `textual` import is deferred inside
`tui_available()` so importing this module never pays the Textual bootstrap
cost when the PlainRenderer path is taken.

The decision order in `tui_should_activate` is locked (first match wins):
  1. `--plain` in argv
  2. `VOSS_PLAIN=1` in env
  3. `json_mode` True
  4. stdout is not a TTY
  5. terminal size < 80x24
  6. `textual` import unavailable
  7. activate
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Optional


_MIN_COLS = 80
_MIN_ROWS = 24

_AVAILABLE: Optional[bool] = None


@dataclass(frozen=True)
class TUIDecision:
    activate: bool
    reason: str


def tui_available() -> bool:
    """Return True iff `textual` is importable in this process.

    Deferred import: never touches textual unless this function is called.
    Result is cached for the process lifetime.
    """
    global _AVAILABLE
    if _AVAILABLE is not None:
        return _AVAILABLE
    try:
        import textual  # noqa: F401
    except ImportError:
        _AVAILABLE = False
        return False
    _AVAILABLE = True
    return True


def tui_should_activate(
    *,
    argv: list[str] | None = None,
    env: dict[str, str] | None = None,
    stdout_isatty: bool | None = None,
    json_mode: bool = False,
    size: tuple[int, int] | None = None,
) -> TUIDecision:
    """Decide whether to bootstrap the TUI.

    Each kwarg defaults to a live system probe (`sys.argv[1:]`,
    `os.environ`, `sys.stdout.isatty()`, `shutil.get_terminal_size()`)
    when None; tests inject synthetic values.
    """
    argv = sys.argv[1:] if argv is None else argv
    env = dict(os.environ) if env is None else env
    if stdout_isatty is None:
        stdout_isatty = sys.stdout.isatty()
    if size is None:
        ts = shutil.get_terminal_size(fallback=(80, 24))
        size = (ts.columns, ts.lines)

    if "--plain" in argv:
        return TUIDecision(activate=False, reason="--plain flag")
    if env.get("VOSS_PLAIN") == "1":
        return TUIDecision(activate=False, reason="VOSS_PLAIN env")
    if json_mode:
        return TUIDecision(activate=False, reason="--json mode")
    if not stdout_isatty:
        return TUIDecision(activate=False, reason="non-TTY stdout")
    if size[0] < _MIN_COLS or size[1] < _MIN_ROWS:
        return TUIDecision(activate=False, reason="terminal below 80x24")
    if not tui_available():
        return TUIDecision(activate=False, reason="textual not installed")
    return TUIDecision(activate=True, reason="ok")


def min_size_guard(size: tuple[int, int]) -> str:
    """Return the locked stderr string for a too-small terminal (UI-SPEC line 198)."""
    return (
        f"voss: terminal must be at least 80×24 "
        f"(current: {size[0]}×{size[1]}). Resize or use --plain."
    )
