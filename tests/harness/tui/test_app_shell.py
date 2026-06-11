"""M9-02 VossTUIApp shell tests — mount + focus + 80x24 layout.

R5 rebaseline (spec §5.1-§5.3): HeaderBar deleted; StatusLine is two-zone
(budget in the right zone); toasts render in the overlay Toast widget.
"""
from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import (
    InputBar,
    SideRegion,
    StatusLine,
    Toast,
    TranscriptView,
)


@pytest.mark.asyncio
async def test_app_mounts_all_regions() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        # R5: no #header — HeaderBar deleted (spec §5.1).
        assert not pilot.app.query("#header")
        assert pilot.app.query_one("#main", TranscriptView) is not None
        assert pilot.app.query_one("#status", StatusLine) is not None
        assert pilot.app.query_one("#input", InputBar) is not None
        assert pilot.app.query_one("#toast", Toast) is not None
        # side region exists but is hidden via display: none in styles.tcss
        assert pilot.app.query_one("#side", SideRegion) is not None


@pytest.mark.asyncio
async def test_app_default_focus_is_input_bar() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        focused = pilot.app.focused
        assert focused is not None
        # InputBar forwards focus to its child TextArea so editing bindings
        # (backspace, etc.) fire without the user clicking in first.
        assert focused.id == "input-textarea"


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
            ("main", TranscriptView),
            ("status", StatusLine),
            ("input", InputBar),
        ):
            pilot.app.query_one(f"#{region_id}", cls)


@pytest.mark.asyncio
async def test_status_line_right_zone_shows_budget_from_old_header() -> None:
    """R5 spec §5.1: the HeaderBar's budget used/total moved to the
    StatusLine right zone (`12.4k/32k` text when budget_total is set)."""
    status = StatusLine()
    status.set_status(
        model="claude-opus-4-7",
        tokens=1024,
        budget_total=4000,
        git_status="clean",
    )
    text = status.plain_text()
    assert "claude-opus-4-7" in text
    assert "1.0k/4.0k" in text
    assert "clean" in text


@pytest.mark.asyncio
async def test_status_line_renders_tokens_cost_ctx() -> None:
    status = StatusLine()
    status.set_status(model="m", tokens=1234, cost_usd=0.012, ctx_pct=0.42)
    text = status.plain_text()
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
    text = status.plain_text()
    assert "anthropic / claude-sonnet-4" in text
    assert "auto" in text
    assert "dirty" in text
    assert "84%" in text
    assert "$1.23" in text


def test_status_line_context_bar_cells_and_brand() -> None:
    """R5 spec §5.2: left brand `▌ voss`; right 4-cell context bar."""
    from voss.harness.tui import glyphs

    status = StatusLine()
    status.set_status(ctx_pct=0.5)
    text = status.plain_text()
    assert f"{glyphs.PROMPT} voss" in text
    bar = glyphs.BUDGET_FILL * 2 + glyphs.BUDGET_EMPTY * 2
    assert f"{bar} 50%" in text


@pytest.mark.asyncio
async def test_status_line_toast_kwarg_delegates_to_overlay() -> None:
    """R5 spec §5.3: `toast=` is a deprecation shim — the text renders in
    the overlay Toast widget and status metadata never jumps."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        status = pilot.app.query_one("#status", StatusLine)
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
        await pilot.pause()
        text = status.plain_text()
        assert "openai / gpt-4.1" in text
        assert "plan" in text
        assert "clean" in text
        assert "20%" in text
        assert "$0.01" in text
        assert "thinking" not in text  # toast no longer in the status row
        toast = pilot.app.query_one("#toast", Toast)
        assert toast.text_content == "thinking"
        assert toast.display


@pytest.mark.asyncio
async def test_persistent_toast_shim_stays_until_cleared() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        status = pilot.app.query_one("#status", StatusLine)
        status.set_persistent_toast("permission required")
        await pilot.pause()
        toast = pilot.app.query_one("#toast", Toast)
        assert toast.text_content == "permission required"
        status.clear_toast()
        assert toast.text_content is None
        assert not toast.display


@pytest.mark.asyncio
async def test_input_bar_prompt_uses_locked_glyph() -> None:
    from voss.harness.tui import glyphs

    app = VossTUIApp()
    async with app.run_test() as pilot:
        bar = pilot.app.query_one("#input", InputBar)
        assert bar._prompt_text.startswith(glyphs.PROMPT)


@pytest.mark.asyncio
async def test_input_bar_mode_border_and_placeholder() -> None:
    """R5 spec §5.5: plan/restricted mode → $warn border + mode title;
    placeholder shows only while the buffer is empty."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        bar = pilot.app.query_one("#input", InputBar)
        bar.set_mode("plan")
        assert bar.has_class("mode-warn")
        assert str(bar.border_title) == "plan"
        bar.set_mode("edit")
        assert not bar.has_class("mode-warn")
        placeholder = bar.query_one("#input-placeholder")
        assert placeholder.display
        await pilot.press("h", "i")
        await pilot.pause()
        assert not placeholder.display
        bar.load_text("")
        await pilot.pause()
        assert placeholder.display
