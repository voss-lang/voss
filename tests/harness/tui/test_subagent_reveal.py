"""R4 inline AgentTree — quiet-by-default reveal + post-gather settle.

Rewrites the M13 Wave-0 SubAgentPanel scaffold to the inline model
(tui-redesign-spec §3.5): the side panel is retired; a spawn renders as
an AgentTreeCard parent in the transcript, child step lines nest under it
with the locked NEST glyphs, ctrl+o (action_toggle_detail, spec §7.2)
reveals them, and the final gather settles the parent in place.

Intent preserved from the scaffold:
- MAG-02 / D-09 quiet-by-default: child steps stay hidden while the live
  budget counter ticks; the global toggle reveals them.
- MAG-07 post-gather clean: gather settles every parent (idempotent
  re-gather is a no-op) and the side region is never touched by spawns.
"""
from __future__ import annotations

import pytest

from voss.harness.tui import glyphs
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import AgentTreeCard, TranscriptView


class TestQuietByDefault:
    """D-09: collapsed parent shows ONLY the spawn line + budget counter;
    ctrl+o reveals the streamed child step rows."""

    @pytest.mark.asyncio
    async def test_children_hidden_until_toggle_reveals_streamed_step(self) -> None:
        app = VossTUIApp()
        async with app.run_test() as pilot:
            renderer = TextualRenderer(app=pilot.app)
            renderer.show_subagent_start("reviewer", "abc", 2000)
            await pilot.pause()
            renderer.show_subagent_progress("abc", "child step line", 500)
            await pilot.pause()

            tv = pilot.app.query_one("#main", TranscriptView)
            card = tv.get_agent_tree("abc")
            assert card is not None, "spawn did not mount an inline AgentTreeCard"
            assert card.expanded is False
            text = card.plain_text()
            assert "spawn reviewer" in text
            assert "child step line" not in text, (
                "child step visible while collapsed (D-09 quiet-by-default breach)"
            )

            pilot.app.action_toggle_detail()
            await pilot.pause()

            assert card.expanded is True
            text = card.plain_text()
            assert "child step line" in text, "toggle did not reveal the child step"
            assert glyphs.NEST_LAST in text, "child row lacks the locked NEST glyph"

            # Toggle back: collapsed again (global expand/collapse-all).
            pilot.app.action_toggle_detail()
            await pilot.pause()
            assert card.expanded is False

    @pytest.mark.asyncio
    async def test_budget_counter_ticks_while_quiet(self) -> None:
        """MAG-02 (a): the live budget metric increments on the parent's
        right metric WHILE the child rows stay hidden."""
        app = VossTUIApp()
        async with app.run_test() as pilot:
            renderer = TextualRenderer(app=pilot.app)
            renderer.show_subagent_start("reviewer", "abc", 2000)
            await pilot.pause()
            renderer.show_subagent_progress("abc", "step 1", 400)
            await pilot.pause()
            renderer.show_subagent_progress("abc", "step 2", 900)
            await pilot.pause()

            card = pilot.app.query_one("#main", TranscriptView).get_agent_tree("abc")
            assert card is not None
            assert card.budget_total == 2000
            assert card.budget_used == 900, "budget counter did not increment"
            text = card.plain_text()
            assert "900/2.0k tok" in text, f"live budget metric missing: {text!r}"
            # Quiet-by-default — the verbose step body must not be visible.
            assert "step 1" not in text
            assert "step 2" not in text

    @pytest.mark.asyncio
    async def test_card_mounted_while_expanded_mode_mounts_expanded(self) -> None:
        """Spec §7.2: newly mounted cards while expanded-mode is on mount
        expanded (mirrors the old `_subagent_detail_visible` semantics)."""
        app = VossTUIApp()
        async with app.run_test() as pilot:
            pilot.app.action_toggle_detail()  # expanded mode ON
            renderer = TextualRenderer(app=pilot.app)
            renderer.show_subagent_start("reviewer", "late", 1000)
            await pilot.pause()
            renderer.show_subagent_progress("late", "late step", 100)
            await pilot.pause()

            card = pilot.app.query_one("#main", TranscriptView).get_agent_tree("late")
            assert card is not None
            assert card.expanded is True
            assert "late step" in card.plain_text()


class TestPostGatherSettle:
    """MAG-07 (inline model): gather settles every parent in place; spawns
    never touch the side region; re-gather is idempotent."""

    @pytest.mark.asyncio
    async def test_gather_settles_parents_idempotently_and_side_untouched(self) -> None:
        from voss.harness.multiagent import PanelBridgeRenderer

        app = VossTUIApp()
        async with app.run_test() as pilot:
            renderer = TextualRenderer(app=pilot.app)
            # Fan-out: two detached children via the real M13-03 bridge.
            bridge_a = PanelBridgeRenderer(renderer, panel_id="pa")
            bridge_b = PanelBridgeRenderer(renderer, panel_id="pb")
            bridge_a.start_panel(name="child-a", budget_total=1000)
            bridge_b.start_panel(name="child-b", budget_total=1000)
            await pilot.pause()
            bridge_a.step("child-a step", 100)
            bridge_b.step("child-b step", 100)
            await pilot.pause()

            cards = list(pilot.app.query(AgentTreeCard))
            assert len(cards) == 2, "fan-out did not mount one card per child"
            assert all(c.state == "running" for c in cards)

            # Gather every child; the shipped gather path is documented
            # idempotent — drive it twice exactly as the tool does.
            bridge_a.end_panel(1)
            bridge_b.end_panel(1)
            await pilot.pause()
            bridge_a.end_panel(1)
            bridge_b.end_panel(1)
            await pilot.pause()

            tv = pilot.app.query_one("#main", TranscriptView)
            cards = list(pilot.app.query(AgentTreeCard))
            assert len(cards) == 2, "cards must persist inline after gather"
            assert all(c.state == "ok" for c in cards), "gather did not settle"

            card_a = tv.get_agent_tree("pa")
            assert card_a is not None
            card_a.expand()
            text = card_a.plain_text()
            assert text.count("gathered · 1 result") == 1, (
                "re-gather appended a duplicate gathered row (not idempotent)"
            )
            assert f"{glyphs.NEST_LAST} {glyphs.TOOL_OK} gathered" in text

            # The side region is never touched by spawn/gather (spec §5.6).
            side = pilot.app.query_one("#side")
            assert str(side.styles.display) == "none"
