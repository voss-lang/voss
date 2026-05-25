"""M9-02 VossTUIApp shell tests — mount + focus + 80x24 layout."""
from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import (
    HeaderBar,
    InputBar,
    SideRegion,
    StatusLine,
    TurnView,
)


@pytest.mark.asyncio
async def test_app_mounts_all_regions() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        assert pilot.app.query_one("#header", HeaderBar) is not None
        assert pilot.app.query_one("#main", TurnView) is not None
        assert pilot.app.query_one("#status", StatusLine) is not None
        assert pilot.app.query_one("#input", InputBar) is not None
        # side region exists but is hidden via display: none in styles.tcss
        assert pilot.app.query_one("#side", SideRegion) is not None


@pytest.mark.asyncio
async def test_app_default_focus_is_input_bar() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        focused = pilot.app.focused
        assert focused is not None
        assert focused.id == "input"


@pytest.mark.asyncio
async def test_app_renders_at_80x24() -> None:
    app = VossTUIApp()
    async with app.run_test(size=(80, 24)) as pilot:
        size = pilot.app.console.size
        assert size.width == 80
        # Textual may reserve an extra row for its driver; both 24 and 25 ok.
        assert size.height in (24, 25)
        # Every region renders without raising.
        for region_id, cls in (
            ("header", HeaderBar),
            ("main", TurnView),
            ("status", StatusLine),
            ("input", InputBar),
        ):
            pilot.app.query_one(f"#{region_id}", cls)


@pytest.mark.asyncio
async def test_header_renders_session_model_budget_git() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        header = pilot.app.query_one("#header", HeaderBar)
        header.update_header(
            session_id="abc123def456",
            model="claude-opus-4-7",
            budget_used=1024,
            budget_total=4000,
            git_status="clean",
        )
        text = str(header._render_text())
        assert "abc123de" in text
        assert "claude-opus-4-7" in text
        assert "1.0k / 4.0k" in text
        assert "clean" in text
        assert len(text) <= 80 * 4  # tolerant of ANSI overhead


@pytest.mark.asyncio
async def test_status_line_renders_tokens_cost_ctx() -> None:
    status = StatusLine()
    status.set_status(model="m", tokens=1234, cost_usd=0.012, ctx_pct=0.42)
    text = str(status._render_markup())
    assert "m" in text
    assert "$0.01" in text
    assert "42%" in text


@pytest.mark.asyncio
async def test_status_line_renders_dense_footer_metadata() -> None:
    status = StatusLine()
    status.set_status(
        provider="anthropic",
        model="claude-sonnet-4",
        mode="auto",
        git_status="dirty",
        tokens=12_345,
        cost_usd=1.234,
        ctx_pct=0.84,
    )
    text = str(status._render_markup())
    assert "anthropic / claude-sonnet-4" in text
    assert "auto" in text
    assert "dirty" in text
    assert "84%" in text
    assert "$1.23" in text


@pytest.mark.asyncio
async def test_status_line_toast_only_preserves_existing_status() -> None:
    status = StatusLine()
    status.set_status(
        provider="openai",
        model="gpt-4.1",
        mode="plan",
        git_status="clean",
        tokens=900,
        cost_usd=0.010,
        ctx_pct=0.2,
    )
    status.set_status(toast="thinking")
    text = str(status._render_markup())
    assert "openai / gpt-4.1" in text
    assert "plan" in text
    assert "clean" in text
    assert "20%" in text
    assert "$0.01" in text
    assert "thinking" in text


@pytest.mark.asyncio
async def test_input_bar_prompt_uses_locked_glyph() -> None:
    from voss.harness.tui import glyphs

    app = VossTUIApp()
    async with app.run_test() as pilot:
        bar = pilot.app.query_one("#input", InputBar)
        assert bar._prompt_text.startswith(glyphs.PROMPT)
