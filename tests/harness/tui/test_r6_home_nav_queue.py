"""R6 — Home screen data rows + transcript nav mode + queued input + paste chip.

tui-redesign-spec §5.4 (cwd/model/resume rows), §7.1 (nav mode), §7.3
(queued input), §5.5 (paste chip). Acceptance: fresh launch shows the
resume row when a prior session exists and omits it otherwise; nav mode is
reachable only when idle; the queue dispatches FIFO after finalize and
clears on interrupt.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual import events
from textual.widgets import Static

from voss.harness import session as session_store
from voss.harness.session import SessionRecord
from voss.harness.tui import glyphs
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import (
    HomeScreen,
    InputBar,
    ToolCard,
    TranscriptView,
    UserBlock,
)
from voss_runtime.memory.episodic import EpisodicMemory


def _save_session(cwd: Path, *, first_task: str = "", model: str = "m") -> SessionRecord:
    record = SessionRecord.new(cwd=cwd, model=model)
    history = EpisodicMemory(capacity=40)
    if first_task:
        history.add(first_task, role="user")
    session_store.save(record, history)
    return record


# ----------------------------------------------------------------------
# §5.4 HomeScreen data rows
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_home_rows_cwd_and_model(tmp_path) -> None:
    app = VossTUIApp(model="claude-fable-5")
    app.cwd = tmp_path
    app.git_status = "clean"
    app.provider = "anthropic"
    async with app.run_test(size=(80, 24)) as pilot:
        home = pilot.app.query_one(HomeScreen)
        flat = home.render().plain
        assert str(tmp_path) in flat or "~" in flat
        assert "(clean)" in flat
        assert "anthropic / claude-fable-5" in flat
        # No ctrl+k binding exists — hint text stays the R1 version.
        assert "ctrl+k" not in flat


@pytest.mark.asyncio
async def test_home_resume_row_shows_newest_non_current_session(tmp_path) -> None:
    prior = _save_session(
        tmp_path, first_task="harness refactor plus a very long tail that truncates"
    )
    app = VossTUIApp()
    app.cwd = tmp_path
    app.record = SessionRecord.new(cwd=tmp_path, model="m")  # current, unsaved
    async with app.run_test(size=(80, 24)) as pilot:
        home = pilot.app.query_one(HomeScreen)
        flat = home.render().plain
        assert "resume" in flat
        assert glyphs.FORK in flat
        assert prior.id[:6] in flat
        # first-user-message truncated to 40 chars (spec §5.4)
        assert "harness refactor" in flat
        assert "very long tail that truncates" not in flat
        assert "ago" in flat or "just now" in flat


@pytest.mark.asyncio
async def test_home_resume_row_omitted_when_no_prior_session(tmp_path) -> None:
    # Only the CURRENT session exists in the store — the row must be omitted.
    app = VossTUIApp()
    app.cwd = tmp_path
    record = _save_session(tmp_path, first_task="current task")
    app.record = record
    async with app.run_test(size=(80, 24)) as pilot:
        home = pilot.app.query_one(HomeScreen)
        assert "resume" not in [label for label, _ in home._info_rows]
        assert glyphs.FORK not in home.render().plain


@pytest.mark.asyncio
async def test_home_bare_app_has_no_data_rows() -> None:
    app = VossTUIApp()
    async with app.run_test(size=(80, 24)) as pilot:
        home = pilot.app.query_one(HomeScreen)
        assert home._info_rows == []


# ----------------------------------------------------------------------
# §7.1 transcript nav mode
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_esc_focuses_transcript_only_when_idle() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        assert pilot.app.focused.id == "input-textarea"
        await pilot.press("escape")
        assert isinstance(pilot.app.focused, TranscriptView)


@pytest.mark.asyncio
async def test_esc_inert_while_turn_running() -> None:
    app = VossTUIApp()
    gate: asyncio.Event = asyncio.Event()

    async def _dispatch(_value: str) -> None:
        await gate.wait()

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        app.on_input_bar_submitted(InputBar.Submitted("go"))
        await pilot.pause()
        await pilot.press("escape")
        # Nav mode is reachable only when idle (spec §8 R6 acceptance).
        assert pilot.app.focused.id == "input-textarea"
        gate.set()
        await pilot.pause()


@pytest.mark.asyncio
async def test_nav_j_k_move_block_focus_and_skip_home() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.append_turn("user", "one")
        tv.append_turn("assistant", "two")
        tv.append_turn("user", "three")
        await pilot.pause()
        await pilot.press("escape")
        blocks = tv._nav_blocks()
        assert len(blocks) == 3
        # Entry lands on the newest block.
        assert tv.focused_block() is blocks[-1]
        assert blocks[-1].has_class("nav-focus")
        await pilot.press("k")
        assert tv.focused_block() is blocks[-2]
        assert blocks[-2].has_class("nav-focus")
        assert not blocks[-1].has_class("nav-focus")
        await pilot.press("k", "k", "k")  # clamps at the top
        assert tv.focused_block() is blocks[0]
        await pilot.press("j")
        assert tv.focused_block() is blocks[1]


@pytest.mark.asyncio
async def test_nav_enter_toggles_focused_tool_card() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        card = tv.add_tool_card("c1", "shell_run", {"cmd": "ls"})
        card.settle("ok", "[exit 0]", output="[exit 0]\nfile_a\nfile_b")
        await pilot.pause()
        await pilot.press("escape")
        assert isinstance(tv.focused_block(), ToolCard)
        assert not card.expanded
        await pilot.press("enter")
        assert card.expanded
        await pilot.press("enter")
        assert not card.expanded
        # enter on a non-card block is a no-op (must not raise)
        tv.append_turn("user", "hello")
        await pilot.pause()
        await pilot.press("escape") if not isinstance(pilot.app.focused, TranscriptView) else None
        await pilot.press("j", "enter")
        assert isinstance(tv.focused_block(), UserBlock)


@pytest.mark.asyncio
async def test_nav_y_copies_focused_block() -> None:
    app = VossTUIApp()
    copied: list[str] = []
    async with app.run_test() as pilot:
        pilot.app.copy_to_clipboard = copied.append  # type: ignore[method-assign]
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.append_turn("user", "copy me")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.press("y")
        assert copied and "copy me" in copied[0]


@pytest.mark.asyncio
async def test_nav_gg_top_and_G_reengages_follow() -> None:
    app = VossTUIApp()
    async with app.run_test(size=(80, 12)) as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        for i in range(30):
            tv.append_turn("user", f"line {i}")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.press("g", "g")
        await pilot.pause()
        blocks = tv._nav_blocks()
        assert tv.focused_block() is blocks[0]
        assert not tv.is_vertical_scroll_end
        await pilot.press("G")
        await pilot.pause()
        assert tv.focused_block() is blocks[-1]
        # G re-engages auto-follow (pinned to tail).
        assert tv.is_vertical_scroll_end


@pytest.mark.asyncio
async def test_nav_printable_returns_to_input_and_forwards_key() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.append_turn("user", "hi")
        await pilot.pause()
        await pilot.press("escape")
        assert isinstance(pilot.app.focused, TranscriptView)
        await pilot.press("x")
        await pilot.pause()
        bar = pilot.app.query_one("#input", InputBar)
        assert pilot.app.focused.id == "input-textarea"
        assert bar.text == "x"  # first keystroke is never lost
        # Highlight cleared on blur.
        assert not list(tv.query(".nav-focus"))
        # `i` returns without inserting.
        await pilot.press("escape")
        await pilot.press("i")
        assert pilot.app.focused.id == "input-textarea"
        assert bar.text == "x"


# ----------------------------------------------------------------------
# §7.3 queued input
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_during_turn_queues_and_renders_chip() -> None:
    app = VossTUIApp()
    calls: list[str] = []
    gate: asyncio.Event = asyncio.Event()

    async def _dispatch(value: str) -> None:
        calls.append(value)
        await gate.wait()

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        app.on_input_bar_submitted(InputBar.Submitted("first"))
        await pilot.pause()
        app.on_input_bar_submitted(InputBar.Submitted("second"))
        await pilot.pause()
        assert calls == ["first"]  # second NOT dispatched
        assert app._queued_inputs == ["second"]
        chips = pilot.app.query_one("#queued-chips", Static)
        assert chips.display
        assert 'queued: "second"' in str(chips.render())
        # A third queues behind it — single-chip collapse shows the count.
        app.on_input_bar_submitted(InputBar.Submitted("third"))
        await pilot.pause()
        assert 'queued (2): "third"' in str(chips.render())
        gate.set()
        await pilot.pause()


@pytest.mark.asyncio
async def test_queue_dispatches_fifo_after_finalize() -> None:
    app = VossTUIApp()
    calls: list[str] = []
    gates = [asyncio.Event() for _ in range(3)]

    async def _dispatch(value: str) -> None:
        calls.append(value)
        await gates[len(calls) - 1].wait()

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        app.on_input_bar_submitted(InputBar.Submitted("first"))
        await pilot.pause()
        app.on_input_bar_submitted(InputBar.Submitted("second"))
        app.on_input_bar_submitted(InputBar.Submitted("/cost"))
        await pilot.pause()
        # Finish turn 1 → queue head dispatches through the same path.
        gates[0].set()
        await pilot.pause()
        await pilot.pause()
        assert calls == ["first", "second"]
        assert app._queued_inputs == ["/cost"]  # one at a time
        # Finish turn 2 → slash command dispatches too (uniform queueing).
        gates[1].set()
        await pilot.pause()
        await pilot.pause()
        assert calls == ["first", "second", "/cost"]
        assert app._queued_inputs == []
        chips = pilot.app.query_one("#queued-chips", Static)
        assert not chips.display
        gates[2].set()
        await pilot.pause()


@pytest.mark.asyncio
async def test_ctrl_c_clears_queue_before_interrupt() -> None:
    app = VossTUIApp()
    calls: list[str] = []

    async def _dispatch(value: str) -> None:
        calls.append(value)
        await asyncio.sleep(60)

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        app.on_input_bar_submitted(InputBar.Submitted("first"))
        await pilot.pause()
        app.on_input_bar_submitted(InputBar.Submitted("second"))
        await pilot.pause()
        assert app._queued_inputs == ["second"]
        app.action_interrupt()
        await pilot.pause()
        await pilot.pause()
        # Queue cleared BEFORE the cancel → the done-callback dispatched nothing.
        assert app._queued_inputs == []
        assert calls == ["first"]
        assert app.active_turn_task is None
        assert not pilot.app.query_one("#queued-chips", Static).display


# ----------------------------------------------------------------------
# §5.5 paste chip
# ----------------------------------------------------------------------

BIG_PASTE = "\n".join(f"line {i}" for i in range(8))  # 8 lines > threshold
SMALL_PASTE = "one\ntwo\nthree"


@pytest.mark.asyncio
async def test_paste_over_threshold_collapses_to_chip() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        bar = pilot.app.query_one("#input", InputBar)
        ta = bar.query_one("#input-textarea")
        ta.post_message(events.Paste(BIG_PASTE))
        await pilot.pause()
        assert bar.text == "[pasted 8 lines]"
        assert bar._pasted_blobs["[pasted 8 lines]"] == BIG_PASTE


@pytest.mark.asyncio
async def test_paste_under_threshold_inserts_raw() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        bar = pilot.app.query_one("#input", InputBar)
        ta = bar.query_one("#input-textarea")
        ta.post_message(events.Paste(SMALL_PASTE))
        await pilot.pause()
        assert bar.text == SMALL_PASTE
        assert bar._pasted_blobs == {}


@pytest.mark.asyncio
async def test_paste_chip_expands_on_submit() -> None:
    app = VossTUIApp()
    calls: list[str] = []

    async def _dispatch(value: str) -> None:
        calls.append(value)

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        bar = pilot.app.query_one("#input", InputBar)
        ta = bar.query_one("#input-textarea")
        ta.insert("context: ")
        ta.post_message(events.Paste(BIG_PASTE))
        await pilot.pause()
        await bar.action_submit()
        await pilot.pause()
        assert calls == [f"context: {BIG_PASTE}"]
        assert bar._pasted_blobs == {}


@pytest.mark.asyncio
async def test_backspace_at_chip_boundary_deletes_whole_chip() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        bar = pilot.app.query_one("#input", InputBar)
        ta = bar.query_one("#input-textarea")
        ta.insert("keep ")
        ta.post_message(events.Paste(BIG_PASTE))
        await pilot.pause()
        assert bar.text == "keep [pasted 8 lines]"
        await pilot.press("backspace")
        assert bar.text == "keep "
        assert bar._pasted_blobs == {}
        # Plain backspace still deletes one char.
        await pilot.press("backspace")
        assert bar.text == "keep"
