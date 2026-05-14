"""M9-05 BudgetExhaustedModal tests (TUI-07)."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from voss.harness.tui.widgets.budget_modal import BudgetExhaustedModal


class _Host(App):
    def __init__(self):
        super().__init__()
        self.result: str | None = None

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(
            BudgetExhaustedModal(tokens_used=4000, tokens_limit=4000),
            lambda c: setattr(self, "result", c),
        )


@pytest.mark.asyncio
async def test_heading_locked() -> None:
    app = _Host()
    async with app.run_test():
        t = app.query_one("#budget-title")
        assert str(t.renderable) == "Budget exhausted"


@pytest.mark.asyncio
async def test_body_locked_copy() -> None:
    app = _Host()
    async with app.run_test():
        body = app.query_one("#budget-message")
        assert (
            "Turn stopped at 4000 / 4000 tokens. Continue with a new "
            "budget, or end the turn."
        ) in str(body.renderable)


@pytest.mark.asyncio
async def test_c_returns_continue() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        await pilot.press("c")
        await pilot.pause()
    assert app.result == "continue"


@pytest.mark.asyncio
async def test_e_returns_end() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        await pilot.press("e")
        await pilot.pause()
    assert app.result == "end"


@pytest.mark.asyncio
async def test_escape_returns_cancel() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
    assert app.result == "cancel"


@pytest.mark.asyncio
async def test_title_modal_title_class() -> None:
    app = _Host()
    async with app.run_test():
        assert "modal-title" in app.query_one("#budget-title").classes
