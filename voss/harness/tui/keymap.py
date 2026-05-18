"""Locked keymap table — single source of truth for VossTUIApp.BINDINGS.

UI-SPEC "Keybindings" rows. Diff modal + permission modal keys live on
those modals themselves (M9-05); KEYMAP holds global + main + input +
modal-dismiss baseline.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Binding:
    key: str
    context: str  # "global" | "input" | "main" | "modal"
    action: str
    description: str


KEYMAP: tuple[Binding, ...] = (
    Binding("tab", "global", "focus_next", "Cycle focus to next region"),
    Binding("shift+tab", "global", "focus_previous", "Cycle focus to previous region"),
    Binding("enter", "input", "submit", "Submit task"),
    Binding("shift+enter", "input", "newline", "Insert newline"),
    Binding("slash", "input", "open_palette", "Open slash command palette"),
    Binding("ctrl+r", "input", "reverse_search", "Reverse-search input history"),
    Binding("escape", "modal", "dismiss_modal", "Close modal / cancel"),
    Binding("question_mark", "global", "open_help", "Open help overlay"),
    Binding("j", "main", "scroll_down", "Scroll one row down"),
    Binding("k", "main", "scroll_up", "Scroll one row up"),
    Binding("ctrl+d", "main", "half_page_down", "Half-page down"),
    Binding("ctrl+u", "main", "half_page_up", "Half-page up"),
    Binding("g", "main", "jump_top", "Jump to top of history"),
    Binding("G", "main", "jump_bottom", "Jump to bottom of history"),
    Binding("f", "main", "fork_turn", "Fork session from focused turn"),
    Binding("ctrl+f", "main", "open_search", "Open in-pane search"),
    Binding("ctrl+c", "global", "interrupt", "Interrupt turn; press again to exit"),
    Binding("ctrl+l", "global", "redraw", "Redraw screen"),
)
