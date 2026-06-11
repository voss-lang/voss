"""R4 simplified side region — CodeIntelPanel is #side's only occupant.

Rewrites the M9-08 region-share precedence tests: the pin/owner state
machine is deleted (tui-redesign-spec §5.6). Spawns render inline in the
transcript (§3.5) and never touch #side; show/hide is the whole API.
"""

from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import AgentTreeCard, CodeIntelPanel


@pytest.mark.asyncio
async def test_code_intel_is_sole_side_occupant() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        side = pilot.app.query_one("#side")
        panels = list(pilot.app.query(CodeIntelPanel))
        assert len(panels) == 1
        assert list(side.children) == [panels[0]]
        # Hidden by default (focused composer layout).
        assert str(side.styles.display) == "none"


@pytest.mark.asyncio
async def test_show_and_hide_code_intel_panel() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        pilot.app.show_code_intel_panel()
        await pilot.pause()
        side = pilot.app.query_one("#side")
        assert str(side.styles.display) == "block"

        pilot.app.hide_code_intel_panel()
        await pilot.pause()
        assert str(side.styles.display) == "none"


@pytest.mark.asyncio
async def test_spawn_and_gather_never_touch_side_region() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_subagent_start("reviewer", "abc123", 1000)
        await pilot.pause()
        # Spawn renders inline, not in #side.
        side = pilot.app.query_one("#side")
        assert str(side.styles.display) == "none"
        assert len(list(pilot.app.query(AgentTreeCard))) == 1
        assert all(isinstance(c, CodeIntelPanel) for c in side.children)

        renderer.show_subagent_end("abc123", 2)
        await pilot.pause()
        assert str(side.styles.display) == "none"
        assert all(isinstance(c, CodeIntelPanel) for c in side.children)
