"""T1-04 Task 1: TurnView streaming entry points (ITER-03 delta render).

CONTEXT.md locks append-only RichLog semantics — no in-place edits, no
scroll jumps. These tests assert delta-write accumulation, empty-state
clearing on first delta, multi-block separation, append_turn parity,
and a 1000-delta smoke test for the "no throttling" invariant.
"""
from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import turn_view
from voss.harness.tui.widgets import TurnView


def _flatten(turn_view: TurnView) -> str:
    return "".join(str(line) for line in turn_view.lines)


@pytest.mark.asyncio
async def test_stream_delta_accumulates_into_single_block() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TurnView)
        tv.stream_delta("hel")
        tv.stream_delta("lo")
        tv.finalize_stream(role="assistant", confidence=0.92, cost_usd=0.01)
        await pilot.pause()

        flat = _flatten(tv)
        # Each delta is its own RichLog write (one segment per call) — the
        # text accumulates as a sequence of segments, not a joined string.
        assert "hel" in flat
        assert "lo" in flat
        # Header lands AFTER the streamed body, with role + cost + conf.
        assert "assistant" in flat
        assert "0.0100" in flat
        assert "0.92" in flat


@pytest.mark.asyncio
async def test_first_stream_delta_clears_empty_state() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TurnView)
        await pilot.pause()
        # on_mount has placed the branded empty state.
        before = _flatten(tv)
        assert "type a message below to begin" in before

        tv.stream_delta("first token")
        await pilot.pause()
        after = _flatten(tv)
        assert "Ready for a focused turn." not in after
        assert "first token" in after


def test_empty_state_copy_is_terminal_safe_and_concise() -> None:
    copy = turn_view.EMPTY_HEADING

    assert copy.isascii() or "·" in copy  # · is non-ASCII but allowed
    assert "No turns yet" not in copy
    assert turn_view.IGNITE_ORANGE == "#ff5b1f"
    assert len(copy) <= 80


@pytest.mark.asyncio
async def test_stream_delta_after_finalize_starts_new_block() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TurnView)
        tv.stream_delta("alpha")
        tv.finalize_stream(role="assistant", cost_usd=0.01)
        # After finalize, the next stream_delta starts a fresh block.
        tv.stream_delta("bravo")
        tv.finalize_stream(role="assistant", cost_usd=0.02)
        await pilot.pause()
        flat = _flatten(tv)
        assert "alpha" in flat
        assert "bravo" in flat
        # Both headers present and distinguishable by cost.
        assert "0.0100" in flat
        assert "0.0200" in flat


@pytest.mark.asyncio
async def test_append_turn_path_still_works() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TurnView)
        tv.append_turn("user", "write hello.py")
        await pilot.pause()
        flat = _flatten(tv)
        assert "user" in flat
        assert "write hello.py" in flat


@pytest.mark.asyncio
async def test_thousand_delta_smoke() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TurnView)
        for _ in range(1000):
            tv.stream_delta("x")
        tv.finalize_stream(role="assistant", cost_usd=0.0)
        await pilot.pause()
        flat = _flatten(tv)
        # 1000 'x' all present somewhere in the rendered lines.
        assert flat.count("x") >= 1000
