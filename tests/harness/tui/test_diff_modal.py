"""M9-05 DiffModal tests (TUI-06)."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from voss.harness.tui.widgets.diff_modal import DiffDecision, DiffModal, Hunk


HUNKS = [
    Hunk(file="a.py", start=10, lines=["-old", "+new"]),
    Hunk(file="b.py", start=5, lines=["+added"]),
]


class _HostApp(App):
    def __init__(self, hunks):
        super().__init__()
        self._hunks = hunks
        self.result: list[DiffDecision] | None = None
        self.cancelled = False

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        def _cb(decisions):
            self.result = decisions

        self.push_screen(DiffModal(self._hunks), _cb)

    def on_diff_modal_diff_submitted(
        self, message: DiffModal.DiffSubmitted
    ) -> None:
        self.cancelled = message.cancelled


@pytest.mark.asyncio
async def test_heading_locked_copy() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test():
        title = app.query_one("#diff-title")
        assert "Review changes · 2 hunks · 2 files" in str(title.renderable)


@pytest.mark.asyncio
async def test_accept_each_advances_then_dismisses() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test() as pilot:
        await pilot.press("y")
        await pilot.press("y")
        await pilot.pause()
    assert app.result == [
        DiffDecision(file="a.py", decision="accept"),
        DiffDecision(file="b.py", decision="accept"),
    ]


@pytest.mark.asyncio
async def test_accept_all_fills_remaining() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test() as pilot:
        await pilot.press("a")
        await pilot.pause()
    assert app.result == [
        DiffDecision(file="a.py", decision="accept"),
        DiffDecision(file="b.py", decision="accept"),
    ]


@pytest.mark.asyncio
async def test_reject_all_fills_remaining() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test() as pilot:
        await pilot.press("q")
        await pilot.pause()
    assert app.result == [
        DiffDecision(file="a.py", decision="reject"),
        DiffDecision(file="b.py", decision="reject"),
    ]


@pytest.mark.asyncio
async def test_skip_then_reject_records_both() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test() as pilot:
        await pilot.press("s")
        await pilot.press("n")
        await pilot.pause()
    assert app.result == [
        DiffDecision(file="a.py", decision="skip"),
        DiffDecision(file="b.py", decision="reject"),
    ]


@pytest.mark.asyncio
async def test_escape_cancels_with_empty_decisions() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
    assert app.result == []
    assert app.cancelled is True


@pytest.mark.asyncio
async def test_title_uses_modal_title_class_not_accent() -> None:
    app = _HostApp(HUNKS)
    async with app.run_test():
        title = app.query_one("#diff-title")
        assert "modal-title" in title.classes
