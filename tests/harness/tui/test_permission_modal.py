"""M9-05 PermissionModal + ScopeExpandModal tests (TUI-07)."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from voss.harness.tui.widgets.permission_modal import (
    PermissionModal,
    ScopeExpandModal,
)


class _PermHost(App):
    def __init__(self):
        super().__init__()
        self.result: str | None = None

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(
            PermissionModal(
                tool_name="shell_run", action_verb="run", target="ls -la"
            ),
            lambda c: setattr(self, "result", c),
        )


@pytest.mark.asyncio
async def test_body_matches_ui_spec_copy() -> None:
    app = _PermHost()
    async with app.run_test():
        msg = app.query_one("#permission-message")
        assert "Tool shell_run wants to run ls -la." in str(msg.renderable)


@pytest.mark.asyncio
async def test_heading_locked() -> None:
    app = _PermHost()
    async with app.run_test():
        t = app.query_one("#permission-title")
        assert "Permission required" in str(t.renderable)


@pytest.mark.asyncio
async def test_a_returns_allow_once() -> None:
    app = _PermHost()
    async with app.run_test() as pilot:
        await pilot.press("a")
        await pilot.pause()
    assert app.result == "a"


@pytest.mark.asyncio
async def test_shift_a_returns_allow_always() -> None:
    app = _PermHost()
    async with app.run_test() as pilot:
        await pilot.press("A")
        await pilot.pause()
    assert app.result == "A"


@pytest.mark.asyncio
async def test_d_returns_deny() -> None:
    app = _PermHost()
    async with app.run_test() as pilot:
        await pilot.press("d")
        await pilot.pause()
    assert app.result == "d"


@pytest.mark.asyncio
async def test_escape_returns_deny() -> None:
    app = _PermHost()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
    assert app.result == "d"


@pytest.mark.asyncio
async def test_title_modal_title_class() -> None:
    app = _PermHost()
    async with app.run_test():
        assert "modal-title" in app.query_one("#permission-title").classes


class _ScopeHost(App):
    def __init__(self):
        super().__init__()
        self.result: str | None = None

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(
            ScopeExpandModal(target="foo/bar.py"),
            lambda c: setattr(self, "result", c),
        )


@pytest.mark.asyncio
async def test_scope_y_returns_once() -> None:
    app = _ScopeHost()
    async with app.run_test() as pilot:
        await pilot.press("y")
        await pilot.pause()
    assert app.result == "once"


@pytest.mark.asyncio
async def test_scope_a_returns_always() -> None:
    app = _ScopeHost()
    async with app.run_test() as pilot:
        await pilot.press("a")
        await pilot.pause()
    assert app.result == "always"


@pytest.mark.asyncio
async def test_scope_n_returns_deny() -> None:
    app = _ScopeHost()
    async with app.run_test() as pilot:
        await pilot.press("n")
        await pilot.pause()
    assert app.result == "n"


@pytest.mark.asyncio
async def test_scope_escape_returns_deny() -> None:
    app = _ScopeHost()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.pause()
    assert app.result == "n"
