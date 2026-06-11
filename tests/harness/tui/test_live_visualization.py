"""M9-04 live visualization tests — ConfidenceBar / inline AgentTree (R4)."""
from __future__ import annotations

import inspect

import pytest

from voss.harness.render import Renderer
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import AgentTreeCard, ConfidenceBar


def test_subagent_methods_not_on_protocol() -> None:
    proto_methods = {n for n, _ in inspect.getmembers(Renderer, predicate=inspect.isfunction)}
    for forbidden in ("show_subagent_start", "show_subagent_progress", "show_subagent_end"):
        assert forbidden not in proto_methods


def test_subagent_methods_present_on_textual_renderer() -> None:
    for name in ("show_subagent_start", "show_subagent_progress", "show_subagent_end"):
        assert hasattr(TextualRenderer, name)


@pytest.mark.asyncio
async def test_subagent_start_mounts_inline_tree_card() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_subagent_start("reviewer", "abc", 2000)
        await pilot.pause()
        cards = [c for c in pilot.app.query(AgentTreeCard) if c.parent_id == "abc"]
        assert len(cards) == 1
        assert cards[0].state == "running"
        assert "spawn reviewer" in cards[0].plain_text()


@pytest.mark.asyncio
async def test_subagent_end_settles_tree_with_gather_row() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_subagent_start("reviewer", "abc", 2000)
        await pilot.pause()
        renderer.show_subagent_end("abc", 3)
        await pilot.pause()
        cards = [c for c in pilot.app.query(AgentTreeCard) if c.parent_id == "abc"]
        assert len(cards) == 1, "card must persist inline after gather (R4)"
        card = cards[0]
        assert card.state == "ok"
        card.expand()
        assert "gathered · 3 results" in card.plain_text()


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
        renderer.show_tool_call("lv1", "fs_read", {"path": "x"}, "ok", "ok")
        await pilot.pause()
