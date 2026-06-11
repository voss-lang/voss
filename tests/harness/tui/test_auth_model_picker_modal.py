"""R8 pilot tests for the AuthModelPickerModal (rows/nav/quick-pick/esc)."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from voss.harness.subscription_models import SUBSCRIPTION_MODELS
from voss.harness.tui import glyphs
from voss.harness.tui.widgets.auth_model_picker_modal import AuthModelPickerModal

CLAUDE = SUBSCRIPTION_MODELS["claude"]
CODEX = SUBSCRIPTION_MODELS["codex"]


class _Host(App):
    """Hosts the modal and records the dismissed value."""

    def __init__(self) -> None:
        super().__init__()
        self.picked = "UNSET"

    def compose(self) -> ComposeResult:
        return []

    def open(self, current="claude-sonnet-4-5", models=CLAUDE):
        def _cb(value):
            self.picked = value

        self.push_screen(
            AuthModelPickerModal(models, current, subtitle="Switch models."),
            _cb,
        )


def _row_text(item) -> str:
    st = item.query_one("Static")
    r = st.renderable
    return r.plain if hasattr(r, "plain") else str(r)


@pytest.mark.asyncio
async def test_rows_render_numbered_with_current_check() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="claude-sonnet-4-5")
        await pilot.pause()
        rows = list(app.query_one("#auth-picker-list").children)
        assert len(rows) == len(CLAUDE)
        first = _row_text(rows[0])
        assert "1." in first
        assert CLAUDE[0].label in first
        assert glyphs.CHECK in first  # current model marked
        # non-current rows carry no check
        assert glyphs.CHECK not in _row_text(rows[1])


@pytest.mark.asyncio
async def test_initial_highlight_is_current() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="claude-haiku-4-5")
        await pilot.pause()
        lst = app.query_one("#auth-picker-list")
        assert lst.index == [m.id for m in CLAUDE].index("claude-haiku-4-5")


@pytest.mark.asyncio
async def test_enter_selects_highlighted() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="claude-sonnet-4-5")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert app.picked is not None
    assert app.picked.id == "claude-sonnet-4-5"


@pytest.mark.asyncio
async def test_jk_moves_then_enter_selects() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="claude-sonnet-4-5")
        await pilot.pause()
        await pilot.press("j")  # → row 2 (opus)
        await pilot.press("j")  # → row 3 (fable)
        await pilot.press("k")  # ← row 2 (opus)
        await pilot.press("enter")
        await pilot.pause()
    assert app.picked.id == "claude-opus-4-8"


@pytest.mark.asyncio
async def test_digit_quick_pick() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="claude-sonnet-4-5")
        await pilot.pause()
        await pilot.press("4")
        await pilot.pause()
    assert app.picked.id == CLAUDE[3].id


@pytest.mark.asyncio
async def test_out_of_range_digit_is_ignored() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="gpt-5.5", models=CODEX)
        await pilot.pause()
        await pilot.press("9")  # only 2 codex rows
        await pilot.pause()
        assert app.picked == "UNSET"
        await pilot.press("escape")
        await pilot.pause()
    assert app.picked is None


@pytest.mark.asyncio
async def test_codex_list_variant() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="gpt-5.5", models=CODEX)
        await pilot.pause()
        rows = list(app.query_one("#auth-picker-list").children)
        assert len(rows) == len(CODEX)
        assert "gpt-5.5" in _row_text(rows[0])
        assert glyphs.CHECK in _row_text(rows[0])
        await pilot.press("2")
        await pilot.pause()
    assert app.picked.id == "gpt-5.5-mini"


@pytest.mark.asyncio
async def test_escape_cancels_with_none() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert app.picked is None
