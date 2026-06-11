"""R7 trim policy tests (tui-redesign-spec §3.2).

Above TRIM_THRESHOLD mounted blocks, TranscriptView flattens the oldest
blocks into a single static `≈ N earlier turns · /resume to reload`
placeholder (always first child), keeping the newest TRIM_KEEP real blocks —
bounds widget count on long sessions (RichLog had `max_lines`). Trimmed
ToolCard / AgentTreeCard ids are dropped from the in-place-update
registries; the working indicator and auto-follow are untouched.
"""
from __future__ import annotations

import pytest

from voss.harness.tui import glyphs
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import ToolCard, TranscriptView, TrimPlaceholder
from voss.harness.tui.widgets.turn_view import TRIM_KEEP, TRIM_THRESHOLD


@pytest.mark.asyncio
async def test_trim_flattens_oldest_blocks_into_placeholder() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        total = TRIM_THRESHOLD + 10
        for i in range(total):
            tv.append_turn("user", f"msg {i}")
        await pilot.pause()
        placeholders = list(tv.query(TrimPlaceholder))
        assert len(placeholders) == 1
        assert tv.children[0] is placeholders[0]
        # Bounded: TRIM_KEEP real blocks + the placeholder.
        assert len(tv.children) <= TRIM_KEEP + 1
        trimmed = total - (len(tv.children) - 1)
        assert placeholders[0].plain_text() == (
            f"{glyphs.APPROX} {trimmed} earlier turns · /resume to reload"
        )
        # Oldest flattened, newest kept.
        text = tv.plain_text()
        assert "msg 0" not in text
        assert f"msg {total - 1}" in text


@pytest.mark.asyncio
async def test_trim_count_accumulates_across_trims() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        for i in range(TRIM_THRESHOLD + 1):
            tv.append_turn("user", f"a {i}")
        await pilot.pause()
        first_count = tv.query_one(TrimPlaceholder)._count
        assert first_count == TRIM_THRESHOLD + 1 - TRIM_KEEP
        # Push past the threshold again — same placeholder, larger N.
        for i in range(TRIM_THRESHOLD - TRIM_KEEP + 1):
            tv.append_turn("user", f"b {i}")
        await pilot.pause()
        placeholders = list(tv.query(TrimPlaceholder))
        assert len(placeholders) == 1
        assert placeholders[0]._count > first_count
        assert len(tv.children) <= TRIM_KEEP + 1


@pytest.mark.asyncio
async def test_trim_drops_tool_card_registry_entries() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        old_card = tv.add_tool_card("old-call", "fs_read", {"path": "x"})
        old_card.settle("ok", "done", output="done")
        for i in range(TRIM_THRESHOLD + 5):
            tv.append_turn("user", f"msg {i}")
        await pilot.pause()
        # The oldest block (the tool card) was trimmed and unregistered:
        # a late settle for its call_id must be a lookup miss, not a crash.
        assert tv.get_tool_card("old-call") is None
        # A fresh card mounted post-trim registers normally.
        new_card = tv.add_tool_card("new-call", "fs_read", {"path": "y"})
        await pilot.pause()
        assert tv.get_tool_card("new-call") is new_card
        assert new_card in list(tv.query(ToolCard))


@pytest.mark.asyncio
async def test_trim_preserves_working_indicator_and_follow() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.show_working("working")
        for i in range(TRIM_THRESHOLD + 3):
            tv.append_turn("user", f"msg {i}")
        await pilot.pause()
        # Indicator survives the trim and stays the last child.
        assert tv.working_active
        assert tv.children[-1] is tv._working
        assert isinstance(tv.children[0], TrimPlaceholder)
        # Auto-follow stayed pinned through the trim churn.
        assert tv.is_vertical_scroll_end
