"""M9-04 live visualization tests — ConfidenceBar / SubAgentPanel / BudgetMeter."""
from __future__ import annotations

import inspect

import pytest

from voss.harness.render import Renderer
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import BudgetMeter, ConfidenceBar, SubAgentPanel


def test_subagent_methods_not_on_protocol() -> None:
    proto_methods = {n for n, _ in inspect.getmembers(Renderer, predicate=inspect.isfunction)}
    for forbidden in ("show_subagent_start", "show_subagent_progress", "show_subagent_end"):
        assert forbidden not in proto_methods


def test_subagent_methods_present_on_textual_renderer() -> None:
    for name in ("show_subagent_start", "show_subagent_progress", "show_subagent_end"):
        assert hasattr(TextualRenderer, name)


@pytest.mark.asyncio
async def test_subagent_start_mounts_panel_and_reveals_side() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_subagent_start("reviewer", "abc", 2000)
        await pilot.pause()
        panels = list(pilot.app.query(SubAgentPanel))
        assert any(p.parent_id == "abc" for p in panels)
        # Side region is revealed when at least one panel is mounted.
        assert len([p for p in pilot.app.query(SubAgentPanel) if p.parent_id == "abc"]) == 1


@pytest.mark.asyncio
async def test_subagent_end_removes_panel_and_emits_gather_line() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_subagent_start("reviewer", "abc", 2000)
        await pilot.pause()
        renderer.show_subagent_end("abc", 3)
        await pilot.pause()
        panels = [p for p in pilot.app.query(SubAgentPanel) if p.parent_id == "abc"]
        assert not panels
        assert not list(pilot.app.query(SubAgentPanel))


@pytest.mark.asyncio
async def test_show_clarify_mounts_confidence_bar() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_clarify("are you sure?", 0.42)
        await pilot.pause()
        bars = list(pilot.app.query(ConfidenceBar))
        assert bars
        assert bars[-1].value == pytest.approx(0.42)
        assert bars[-1].is_final is False


@pytest.mark.asyncio
async def test_show_final_omits_inline_confidence_bar() -> None:
    # Chat-clean: a final answer no longer mounts an inline ConfidenceBar
    # (it read as agent metadata). Confidence still flows to telemetry/status.
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_final("done", confidence=0.92, cost_usd=0.0)
        await pilot.pause()
        assert list(pilot.app.query(ConfidenceBar)) == []


@pytest.mark.asyncio
async def test_status_zero_ctx_pct_does_not_raise() -> None:
    """W5: ctx_pct == 0 must not raise and must not derive total."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.status(model="m", tokens=10, cost_usd=0.0, ctx_pct=0.0)
        await pilot.pause()


@pytest.mark.asyncio
async def test_spawn_tool_name_missing_degrades_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """W3 option b: deleting SPAWN_TOOL_NAME must not raise from show_tool_call."""
    from voss.harness import subagents as subagents_mod

    monkeypatch.delattr(subagents_mod, "SPAWN_TOOL_NAME", raising=False)
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_tool_call("fs_read", {"path": "x"}, "ok", "ok")
        await pilot.pause()
