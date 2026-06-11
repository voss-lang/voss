"""R1 TranscriptView streaming entry points (ITER-03 delta render).

tui-redesign-spec §3.2/§8 R1 replaces the append-only RichLog with a block
transcript: deltas accumulate into ONE in-place-updated AssistantBlock, and
finalize_stream writes the metadata as a dim footer BELOW the body inside
the block. These tests assert delta accumulation, empty-state (HomeScreen)
removal on first delta, multi-block separation, append_turn parity, and a
1000-delta smoke test.
"""
from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import turn_view
from voss.harness.tui.widgets import AssistantBlock, HomeScreen, TranscriptView


def _flatten(tv: TranscriptView) -> str:
    return tv.plain_text()


@pytest.mark.asyncio
async def test_stream_delta_accumulates_into_single_block() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.stream_delta("hel")
        tv.stream_delta("lo")
        tv.finalize_stream(role="assistant", confidence=0.92, cost_usd=0.01)
        await pilot.pause()

        flat = _flatten(tv)
        # Deltas accumulate in-place into one AssistantBlock buffer.
        assert "hello" in flat
        assert len(list(tv.query(AssistantBlock))) == 1
        # Footer lands BELOW the streamed body, with role + cost + conf.
        assert "assistant" in flat
        assert "0.0100" in flat
        assert "0.92" in flat


@pytest.mark.asyncio
async def test_first_stream_delta_clears_empty_state() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        await pilot.pause()
        # compose has mounted the branded HomeScreen empty state.
        before = _flatten(tv)
        assert "type a message below to begin" in before
        assert len(list(tv.query(HomeScreen))) == 1

        tv.stream_delta("first token")
        await pilot.pause()
        after = _flatten(tv)
        assert "type a message below to begin" not in after
        assert not list(tv.query(HomeScreen))
        assert "first token" in after


def test_empty_state_copy_is_terminal_safe_and_concise() -> None:
    copy = turn_view.EMPTY_HEADING

    assert copy.isascii() or "·" in copy  # · is non-ASCII but allowed
    assert "No turns yet" not in copy
    # R5 (spec §4.1): the brand orange lives in palette.py, not turn_view.
    from voss.harness.tui import palette

    assert palette.ACCENT == "#ff5b1f"
    assert len(copy) <= 80


@pytest.mark.asyncio
async def test_stream_delta_after_finalize_starts_new_block() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.stream_delta("alpha")
        tv.finalize_stream(role="assistant", cost_usd=0.01)
        # After finalize, the next stream_delta starts a fresh block.
        tv.stream_delta("bravo")
        tv.finalize_stream(role="assistant", cost_usd=0.02)
        await pilot.pause()
        flat = _flatten(tv)
        assert "alpha" in flat
        assert "bravo" in flat
        assert len(list(tv.query(AssistantBlock))) == 2
        # Both footers present and distinguishable by cost.
        assert "0.0100" in flat
        assert "0.0200" in flat


@pytest.mark.asyncio
async def test_append_turn_path_still_works() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.append_turn("user", "write hello.py")
        await pilot.pause()
        flat = _flatten(tv)
        # Chat layout: user turns render with the prompt glyph, not a "user"
        # label (metadata/role text moved off the transcript).
        from voss.harness.tui import glyphs
        assert glyphs.USER_INPUT in flat
        assert "write hello.py" in flat


@pytest.mark.asyncio
async def test_thousand_delta_smoke() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        for _ in range(1000):
            tv.stream_delta("x")
        tv.finalize_stream(role="assistant", cost_usd=0.0)
        await pilot.pause()
        flat = _flatten(tv)
        # 1000 'x' all present, accumulated into a single block.
        assert flat.count("x") >= 1000
        assert len(list(tv.query(AssistantBlock))) == 1
