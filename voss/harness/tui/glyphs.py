"""Locked TUI glyph vocabulary (UI-SPEC, M9-02).

This module is the SINGLE import surface for any glyph used in the Voss TUI.
Accessing an attribute that is not in the allow-list raises AttributeError —
the auditor in M9-07 greps for any `from .glyphs import EMOJI_*` style use
and this `__getattr__` shim catches it at runtime as well.

Codepoints are pinned per UI-SPEC. When `VOSS_NO_UNICODE=1` is set in the
environment at module import time (or `--no-unicode` flag is passed via the
CLI, which sets that env var before make_renderer fires), every locked
constant is replaced with its ASCII fallback from `NO_UNICODE_FALLBACK`.
"""
from __future__ import annotations

import os


# UI-SPEC locked Unicode codepoints — the default values used when the
# `VOSS_NO_UNICODE` env var is NOT set.
PROMPT = "▌"         # U+258C  prompt
USER_INPUT = "❯"     # U+276F  input-bar echo marker
TOOL_CALL = "⏵"      # U+23F5  tool call
WARN = "⚠"           # U+26A0  warning
BAR_FILL = "█"       # U+2588  confidence bar filled
BAR_EMPTY = "░"      # U+2591  confidence bar empty
BUDGET_FILL = "▰"    # U+25B0  budget bar filled
BUDGET_EMPTY = "▱"   # U+25B1  budget bar empty
NEST_LAST = "└─"     # U+2514 + U+2500  nested spawn last child
NEST_MID = "├─"      # U+251C + U+2500  nested spawn sibling
FORK = "⎇"           # U+2387  session-list fork marker


# UI-SPEC `--no-unicode` fallback table (M9-07 plan §interfaces).
# Each entry downgrades to an ASCII codepoint distinguishable on every
# 16-color terminal without locale support.
NO_UNICODE_FALLBACK: dict[str, str] = {
    "PROMPT": "|",
    "USER_INPUT": ">",
    "TOOL_CALL": ">",
    "WARN": "!",
    "BAR_FILL": "#",
    "BAR_EMPTY": ".",
    "BUDGET_FILL": "=",
    "BUDGET_EMPTY": "-",
    "NEST_LAST": "+-",
    "NEST_MID": "+-",
    "FORK": "+",
}


_ALLOWLIST = frozenset(
    {
        "PROMPT",
        "USER_INPUT",
        "TOOL_CALL",
        "WARN",
        "BAR_FILL",
        "BAR_EMPTY",
        "BUDGET_FILL",
        "BUDGET_EMPTY",
        "NEST_LAST",
        "NEST_MID",
        "FORK",
    }
)


# Import-time `--no-unicode` env check. Replaces every locked constant with
# its NO_UNICODE_FALLBACK value when VOSS_NO_UNICODE=1 is set BEFORE this
# module is first imported.
if os.environ.get("VOSS_NO_UNICODE") == "1":
    _globals = globals()
    for _name, _ascii in NO_UNICODE_FALLBACK.items():
        _globals[_name] = _ascii
    del _name, _ascii, _globals


def __getattr__(name: str) -> str:
    """Reject any glyph not in the locked allow-list (UI-SPEC contract)."""
    if name.startswith("_") or name in _ALLOWLIST:
        raise AttributeError(name)
    raise AttributeError(
        f"voss.harness.tui.glyphs: '{name}' is not in the locked glyph allow-list. "
        f"Allowed: {sorted(_ALLOWLIST)}"
    )


__all__ = sorted(_ALLOWLIST)
