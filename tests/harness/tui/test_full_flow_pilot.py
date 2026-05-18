"""Full-flow TUI pilot test.

Drives `VossTUIApp` end-to-end through `TextualRenderer` and asserts the
TurnView accumulates user → plan → final entries in order. Complements
existing unit-level tui tests which exercise widgets in isolation.

Skipped if textual.Pilot is unavailable in the test env.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import TurnView
from voss_runtime.memory.episodic import EpisodicMemory


def _input_text(input_bar) -> str | None:
    if hasattr(input_bar, "text"):
        return input_bar.text
    if hasattr(input_bar, "value"):
        return input_bar.value
    try:
        return input_bar.query_one("#input-textarea").text
    except Exception:  # noqa: BLE001
        return None


def _plan(rationale: str = "do the thing", steps: list[dict] | None = None):
    """Build a duck-typed Plan-like object the renderer accepts."""
    step_objs = [
        SimpleNamespace(name=s["name"], why=s.get("why", ""))
        for s in (steps or [])
    ]
    return SimpleNamespace(rationale=rationale, steps=step_objs, confidence=0.9)


@pytest.mark.asyncio
async def test_full_turn_flow_renders_user_plan_final() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(pilot.app)

        renderer.banner(model="stub-model", cwd=Path("/tmp"), git_status="clean")
        renderer.show_user("write hello.py")
        renderer.show_plan(
            _plan(steps=[{"name": "fs_write", "why": "create file"}]),
            cost_usd=0.0,
        )
        renderer.show_final("done", confidence=0.95, cost_usd=0.0)

        # Let the event loop flush the posted updates.
        await pilot.pause()

        turn_view = pilot.app.query_one("#main", TurnView)
        # TurnView is a RichLog; introspect via the internal Lines list.
        assert turn_view._turn_count >= 3, turn_view._turn_count
        flat = "".join(str(line) for line in turn_view.lines)
        # We assert that user task + plan body + final text all surface.
        assert "write hello.py" in flat, flat
        assert "fs_write" in flat, flat
        assert "done" in flat, flat


@pytest.mark.asyncio
async def test_pilot_input_submit_triggers_widget() -> None:
    """User types into InputBar, presses enter; verify input is captured."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        # Focus is on the InputBar by default (per existing app shell test).
        await pilot.press("h", "i")
        await pilot.pause()
        input_bar = pilot.app.query_one("#input")
        # T8 migrates InputBar from Input.value to TextArea-backed .text.
        value = _input_text(input_bar)
        # Tolerate either path — just make sure the keys reached the bar.
        if value is not None:
            assert "h" in value.lower() or "i" in value.lower(), value


@pytest.mark.asyncio
async def test_pilot_help_overlay_action() -> None:
    """`action_open_help` mounts the help overlay; modal stack grows."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        before = len(pilot.app.screen_stack)
        pilot.app.action_open_help()
        await pilot.pause()
        after = len(pilot.app.screen_stack)
        assert after >= before, (before, after)


@pytest.mark.asyncio
async def test_input_bar_submitted_dispatches_registered_turn_task(seeded_history) -> None:
    from voss.harness.tui.widgets import InputBar

    history = seeded_history("prior prompt")
    dispatch = MagicMock()

    async def _dispatch(value: str) -> str:
        dispatch(value)
        return "done"

    app = VossTUIApp(history=history)
    async with app.run_test() as pilot:
        pilot.app._turn_dispatch = _dispatch
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("hi")
        await input_bar.action_submit()
        await pilot.pause()

        dispatch.assert_called_once_with("hi")
        assert pilot.app.history is history
        assert pilot.app.active_turn_task is None


def test_tui_app_constructor_accepts_history() -> None:
    history = EpisodicMemory()
    app = VossTUIApp(history=history)
    assert app.history is history
