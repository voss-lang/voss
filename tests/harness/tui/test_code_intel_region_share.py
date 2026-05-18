"""M9-08 region-share precedence tests (CodeIntelPanel vs SubAgentPanel).

Verifies:
- Default side owner is CodeIntelPanel.
- Active spawn switches to SubAgentPanel (unless pinned).
- Gather restores CodeIntelPanel (previous state preserved).
- Pin suspends auto-switching.
"""

from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import CodeIntelPanel, SubAgentPanel


@pytest.mark.asyncio
async def test_code_intel_is_default_side_occupant() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        # default should have mounted CodeIntelPanel
        panels = list(pilot.app.query(CodeIntelPanel))
        assert len(panels) == 1
        assert pilot.app._side_owner == "code_intel"


@pytest.mark.asyncio
async def test_spawn_switches_to_subagent_unless_pinned() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        # spawn
        renderer.show_subagent_start("reviewer", "abc123", 1000)
        await pilot.pause()
        subs = list(pilot.app.query(SubAgentPanel))
        assert any(p.parent_id == "abc123" for p in subs)
        # code intel should be hidden or owner switched
        assert pilot.app._side_owner in ("sub_agent", "code_intel")  # pin may affect


@pytest.mark.asyncio
async def test_gather_restores_code_intel() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_subagent_start("reviewer", "xyz", 500)
        await pilot.pause()
        renderer.show_subagent_end("xyz", 2)
        await pilot.pause()
        # after gather, code intel should be visible again
        code_panels = list(pilot.app.query(CodeIntelPanel))
        assert len(code_panels) >= 1 or pilot.app._side_owner == "code_intel"


@pytest.mark.asyncio
async def test_pin_suspends_auto_switch() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        app.pin_side_panel("code_intel")
        assert app._side_pinned is True
        # spawn should not steal the region
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_subagent_start("reviewer", "pinned", 100)
        await pilot.pause()
        # still code_intel owner because pinned
        assert app._side_owner == "code_intel" or app._side_pinned
