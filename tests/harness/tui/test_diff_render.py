"""Unit tests for the upgraded DiffModal rendering (colored + syntax diffs).

Covers the pure render helper and the decision-cursor tracking, the two
things the OpenCode-leverage port added on top of the locked approval gate.
"""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.containers import Vertical

from voss.harness.tui.widgets.diff_modal import (
    DiffModal,
    Hunk,
    render_diff_line,
    _C_ADD,
    _C_DEL,
)


HUNKS = [
    Hunk(file="a.py", start=10, lines=["- old = 1", "+ new = 2"]),
    Hunk(file="b.py", start=5, lines=["+ added = 3"]),
]


def _spans_styles(text) -> str:
    """Concatenate the base style + every span style of a Rich Text."""
    return " ".join([str(text.style)] + [str(s.style) for s in text.spans])


def test_add_line_marker_is_green_and_ascii() -> None:
    out = render_diff_line("+ new = 2", lexer="python")
    assert out.plain == "+ new = 2"  # content byte-identical to upstream
    assert _C_ADD in _spans_styles(out)


def test_del_line_marker_is_red_and_ascii() -> None:
    out = render_diff_line("- old = 1", lexer="python")
    assert out.plain == "- old = 1"
    assert _C_DEL in _spans_styles(out)


def test_render_never_introduces_unicode_glyphs() -> None:
    # --no-unicode contract: only the bare ASCII +/- markers, no fancy glyphs.
    out = render_diff_line("+ x", lexer=None)
    assert out.plain.isascii()
    assert out.plain.startswith("+")


def test_unknown_lexer_degrades_to_plain_text() -> None:
    out = render_diff_line("+ <<<not real code>>>", lexer="this-lexer-does-not-exist")
    assert out.plain == "+ <<<not real code>>>"


class _HostApp(App):
    def __init__(self, hunks):
        super().__init__()
        self._hunks = hunks

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(DiffModal(self._hunks))


@pytest.mark.asyncio
async def test_cursor_tracks_active_hunk() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test() as pilot:
        await pilot.pause()
        modal = app.screen
        # hunk 0 starts as the active "current" decision target
        assert modal.query_one("#diff-hunk-0", Vertical).has_class("current")
        assert not modal.query_one("#diff-hunk-1", Vertical).has_class("current")
        # accepting hunk 0 advances the cursor to hunk 1
        await pilot.press("y")
        await pilot.pause()
        assert not modal.query_one("#diff-hunk-0", Vertical).has_class("current")
        assert modal.query_one("#diff-hunk-1", Vertical).has_class("current")
        header0 = modal.query_one("#diff-hunk-header-0")
        assert "[accepted]" in str(header0.renderable)
