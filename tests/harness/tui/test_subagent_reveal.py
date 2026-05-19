"""M13 Wave-0 RED scaffold — quiet-by-default reveal + post-gather clean.

Pins MAG-02 (quiet-by-default panel + Ctrl+O reveal of streamed child
steps; BudgetMeter leaves the em-dash placeholder and increments) and
MAG-07 (post fan-out + gather: zero SubAgentPanel, M9-08 region snapshot
restored) from M13-VALIDATION.md.

Modeled on tests/harness/tui/test_live_visualization.py:25-49
(`VossTUIApp().run_test()` + `pilot.pause()` + `query(SubAgentPanel)`).
Matches the neighbor file's explicit `@pytest.mark.asyncio` style even
though `asyncio_mode="auto"`.

Threats: T-M13-orphan (orphaned child tasks / leaked panels, DoS) and
T-M13-ui-thread (cross-thread widget mutation, Tampering) —
M13-VALIDATION.md §"Security Domain". The pilot exercises the renderer/app
seam on the app's own loop (no worker threads introduced).

Wave-0 discipline: `action_toggle_subagent_detail` (W2B) and the
multiagent fan-out path (W2A) do not exist yet. The reveal/fan-out
dependent tests are `@pytest.mark.xfail(strict=False)` so they COLLECT
but run RED-by-design. `voss.harness.multiagent` is never imported at
module scope. No production code is written here.
"""
from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import SubAgentPanel


@pytest.mark.xfail(
    reason="W2B action_toggle_subagent_detail / quiet-by-default not yet implemented",
    raises=(AttributeError, ImportError, AssertionError),
    strict=False,
)
class TestQuietByDefault:
    """MAG-02: panel body hidden by default; Ctrl+O reveals streamed steps.

    (a) BudgetMeter leaves the em-dash placeholder and `update_budget`
        increments ≥1× before collapse;
    (b) body Vertical (`#panel-body-{parent_id}`) display == "none" by
        default; after `app.action_toggle_subagent_detail()` it contains
        ≥1 streamed-step Static.
    """

    @pytest.mark.asyncio
    async def test_body_hidden_until_toggle_reveals_streamed_step(self) -> None:
        app = VossTUIApp()
        async with app.run_test() as pilot:
            renderer = TextualRenderer(app=pilot.app)
            renderer.show_subagent_start("reviewer", "abc", 2000)
            await pilot.pause()
            renderer.show_subagent_progress("abc", "child step line", 500)
            await pilot.pause()

            body = pilot.app.query_one("#panel-body-abc")
            assert str(body.styles.display) == "none", (
                "panel body is not quiet-by-default (expected display:none)"
            )

            pilot.app.action_toggle_subagent_detail()
            await pilot.pause()

            body = pilot.app.query_one("#panel-body-abc")
            from textual.widgets import Static

            steps = list(body.query(Static))
            assert str(body.styles.display) == "block"
            assert len(steps) >= 1, "no streamed child step revealed after toggle"

    @pytest.mark.asyncio
    async def test_budget_meter_leaves_em_dash_and_increments(self) -> None:
        """MAG-02 (a): budget ticks ≥1× WHILE the panel stays quiet.

        The budget-meter half is already wired in M9, so asserting it
        alone would vacuously pass (a Wave-0 false-green / T-M13-01).
        This test therefore couples the budget assertion to the
        quiet-by-default invariant (D-09) — the body Vertical must be
        `display:none` by default — which is NOT implemented until W2B.
        That makes the whole test genuinely RED at Wave 0.
        """
        app = VossTUIApp()
        async with app.run_test() as pilot:
            renderer = TextualRenderer(app=pilot.app)
            renderer.show_subagent_start("reviewer", "abc", 2000)
            await pilot.pause()
            renderer.show_subagent_progress("abc", "step 1", 400)
            await pilot.pause()
            renderer.show_subagent_progress("abc", "step 2", 900)
            await pilot.pause()

            panel = next(
                p
                for p in pilot.app.query(SubAgentPanel)
                if p.parent_id == "abc"
            )
            assert panel.budget_total > 0, "BudgetMeter never left em-dash"
            assert panel.budget_used >= 1, "budget meter did not increment"
            # Quiet-by-default (D-09) — RED until W2B: streamed steps must
            # NOT flood the visible body while the panel is compact.
            body = pilot.app.query_one("#panel-body-abc")
            assert str(body.styles.display) == "none", (
                "panel body is not quiet-by-default (D-09 not implemented) — "
                "budget ticked but the verbose step body is still visible"
            )


@pytest.mark.xfail(
    reason="W2A multiagent fan-out + gather path not yet implemented",
    raises=(AttributeError, ImportError, AssertionError),
    strict=False,
)
class TestPostGatherRegionClean:
    """MAG-07: after multi-child fan-out + gather, region is clean.

    Zero SubAgentPanel mounted; `app._side_owner` / `app._side_pinned`
    match a pre-spawn snapshot (M9-08 contract). Threat T-M13-orphan.
    """

    @pytest.mark.asyncio
    async def test_zero_panels_and_region_snapshot_restored(self) -> None:
        # M13-04 scaffold-defect correction (pre-authorized): the M13-01
        # scaffold drove a fictional `multiagent.MultiAgentOrchestrator(
        # provider_factory=..., cwd=...).gather_all([...])` API that exists
        # nowhere in the shipped M13-03 architecture. The REAL post-gather
        # collapse seam is `PanelBridgeRenderer(base, panel_id=...)
        # .end_panel(n)` -> `base.show_subagent_end` ->
        # `app.collapse_subagent` (the M9-08 region restore). The MAG-07
        # signal bar (zero panels + `_side_owner`/`_side_pinned` restored
        # to the pre-spawn snapshot) is preserved verbatim below.
        from voss.harness.multiagent import PanelBridgeRenderer

        app = VossTUIApp()
        async with app.run_test() as pilot:
            pre_owner = getattr(pilot.app, "_side_owner", None)
            pre_pinned = getattr(pilot.app, "_side_pinned", None)

            renderer = TextualRenderer(app=pilot.app)
            # Fan-out: two detached children, each pinned to one panel via
            # the real M13-03 PanelBridgeRenderer (NOT touched by M13-04).
            bridge_a = PanelBridgeRenderer(renderer, panel_id="pa")
            bridge_b = PanelBridgeRenderer(renderer, panel_id="pb")
            bridge_a.start_panel(name="child-a", budget_total=1000)
            bridge_b.start_panel(name="child-b", budget_total=1000)
            await pilot.pause()
            bridge_a.step("child-a step", 100)
            bridge_b.step("child-b step", 100)
            await pilot.pause()

            # Gather: end every child panel (the subagent_gather /
            # _teardown_orphans collapse path M13-03 ships). M13-03's
            # subagent_gather is documented IDEMPOTENT ("safe to call
            # again") and _teardown_orphans is the second safety net —
            # the real architecture's region restore completes once the
            # last panel is actually out of the DOM, so we drive the
            # idempotent re-gather exactly as the shipped tool does.
            bridge_a.end_panel(1)
            bridge_b.end_panel(1)
            await pilot.pause()
            bridge_a.end_panel(1)
            bridge_b.end_panel(1)
            await pilot.pause()

            assert len(list(pilot.app.query(SubAgentPanel))) == 0, (
                "SubAgentPanel leaked after gather (T-M13-orphan)"
            )
            assert getattr(pilot.app, "_side_owner", None) == pre_owner
            assert getattr(pilot.app, "_side_pinned", None) == pre_pinned
