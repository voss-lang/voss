"""Locked TUI glyph vocabulary — single import surface for TUI glyphs."""
from __future__ import annotations

import os


# locked Unicode codepoints the default values used when the
# `VOSS_NO_UNICODE` env var is NOT set
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
ASSISTANT = "●"      # U+25CF  assistant message marker
WORKING = "✦"        # U+2726  working indicator brand glyph (contract v2, R2)
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧"  # U+2800-block running spinner, iterated by index
TOOL_OK = "⏺"        # U+23FA  settled tool card (contract v2, R3)
OUTPUT_ELBOW = "⎿"   # U+23BF  tool output lead-in (contract v2, R3)
CHEVRON_CLOSED = "▸"  # U+25B8  collapsed output expander (contract v2, R3)
CHEVRON_OPEN = "▾"   # U+25BE  expanded output expander (contract v2, R3)
APPROX = "≈"         # U+2248  trim-placeholder lead-in (contract v2, R7)
CHECK = "✓"          # U+2713  current-selection marker (contract v2, R8)


# `--no-unicode` fallback table ( plan §interfaces)
# Each entry downgrades to an ASCII codepoint distinguishable on every
# 16-color terminal without locale support
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
    "ASSISTANT": "*",
    "WORKING": "*",
    "SPINNER_FRAMES": "|/-\\",
    "TOOL_OK": "*",
    "OUTPUT_ELBOW": "|_",
    "CHEVRON_CLOSED": ">",
    "CHEVRON_OPEN": "v",
    "APPROX": "~",
    "CHECK": "*",
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
        "ASSISTANT",
        "WORKING",
        "SPINNER_FRAMES",
        "TOOL_OK",
        "OUTPUT_ELBOW",
        "CHEVRON_CLOSED",
        "CHEVRON_OPEN",
        "APPROX",
        "CHECK",
    }
)


# Import-time `--no-unicode` env check. Replaces every locked constant with
# its NO_UNICODE_FALLBACK value when VOSS_NO_UNICODE=1 is set BEFORE this
# module is first imported
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
