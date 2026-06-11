"""R2 WorkingIndicator + live-stream throttle + interrupt footer.

tui-redesign-spec §3.3/§3.6/§8 R2: the WorkingIndicator mounts on turn
dispatch, stays the last TranscriptView child across appends, and is removed
on finalize AND on interrupt; AssistantBlock streaming renders live markdown
coalesced to ≤10 Hz with exactly one final render on finalize; an
interrupted stream keeps its content and gains a `· interrupted` footer.
"""
from __future__ import annotations

import asyncio

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import (
    AssistantBlock,
    InputBar,
    TranscriptView,
    WorkingIndicator,
)
from voss.harness.tui.renderer import TextualRenderer


# ----------------------------------------------------------------------
# lifecycle: mounted on dispatch, removed on finalize / interrupt
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_indicator_mounts_on_dispatch_and_unmounts_on_finish() -> None:
    app = VossTUIApp()
    gate: asyncio.Event = asyncio.Event()

    async def _dispatch(_value: str) -> None:
        await gate.wait()

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        app.on_input_bar_submitted(InputBar.Submitted("do a thing"))
        await pilot.pause()
        # Mounted while the turn task runs.
        assert len(list(tv.query(WorkingIndicator))) == 1
        assert tv.working_active
        # Turn finishes → done callback removes the indicator.
        gate.set()
        await pilot.pause()
        await pilot.pause()
        assert not list(tv.query(WorkingIndicator))
        assert not tv.working_active


@pytest.mark.asyncio
async def test_indicator_removed_on_interrupt() -> None:
    app = VossTUIApp()

    async def _dispatch(_value: str) -> None:
        await asyncio.sleep(60)

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        app.on_input_bar_submitted(InputBar.Submitted("long turn"))
        await pilot.pause()
        assert tv.working_active
        app.action_interrupt()
        await pilot.pause()
        await pilot.pause()
        assert not list(tv.query(WorkingIndicator))
        assert not tv.working_active


@pytest.mark.asyncio
async def test_indicator_stays_last_child_across_appends() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.show_working()
        await pilot.pause()
        tv.append_turn("user", "hello")
        tv.stream_delta("answer")
        await pilot.pause()
        children = list(tv.children)
        assert children, "transcript has children"
        assert isinstance(children[-1], WorkingIndicator)
        tv.hide_working()
        await pilot.pause()
        assert not list(tv.query(WorkingIndicator))


@pytest.mark.asyncio
async def test_show_working_is_idempotent_and_updates_label() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.show_working()
        tv.show_working("tool: shell")
        await pilot.pause()
        indicators = list(tv.query(WorkingIndicator))
        assert len(indicators) == 1
        assert "tool: shell" in indicators[0].plain_text()


@pytest.mark.asyncio
async def test_update_working_threads_token_count() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.show_working()
        tv.update_working(8.0, 2100)
        await pilot.pause()
        line = tv.query_one(WorkingIndicator).plain_text()
        assert "2.1k tok" in line
        assert "8s" in line
        assert "interrupt" in line


@pytest.mark.asyncio
async def test_renderer_pending_tool_call_updates_label_only_when_active() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        renderer = TextualRenderer(app=pilot.app)
        # Inactive indicator: a pending tool call must NOT mount one.
        renderer.show_tool_call("w1", "shell", {"cmd": "ls"}, "running…", "pending")
        await pilot.pause()
        assert not list(tv.query(WorkingIndicator))
        # Active indicator: pending updates the label, settle resets it.
        tv.show_working()
        renderer.show_tool_call("w2", "shell", {"cmd": "ls"}, "running…", "pending")
        await pilot.pause()
        assert "tool: shell" in tv.query_one(WorkingIndicator).plain_text()
        renderer.show_tool_call("w2", "shell", {"cmd": "ls"}, "done", "ok")
        await pilot.pause()
        line = tv.query_one(WorkingIndicator).plain_text()
        assert "tool: shell" not in line
        assert "working" in line


# ----------------------------------------------------------------------
# live markdown stream throttle (spec §3.3: ≤10 Hz, final flush once)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rapid_deltas_coalesce_to_bounded_render_count() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        for i in range(200):
            tv.stream_delta(f"word{i} ")
        block = tv.query_one(AssistantBlock)
        # 200 immediate deltas → first renders, the rest coalesce into ONE
        # pending timer render. Allow a little slack for slow CI clocks.
        assert block._live_render_count <= 5, block._live_render_count
        await pilot.pause(0.3)
        # The coalesced timer flushed the full buffer.
        assert "word199" in tv.plain_text()
        count_before_finalize = block._live_render_count
        tv.finalize_stream(role="assistant", cost_usd=0.01)
        await pilot.pause()
        # Finalize renders the complete markdown exactly once more and
        # detaches the throttle (no further live renders).
        assert block._live_render_count == count_before_finalize
        assert block._finalized
        flat = tv.plain_text()
        assert "word0" in flat and "word199" in flat
        assert "0.0100" in flat


@pytest.mark.asyncio
async def test_stream_renders_live_markdown_before_finalize() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.stream_delta("# heading\n\nsome **bold** text")
        await pilot.pause(0.2)
        block = tv.query_one(AssistantBlock)
        from rich.markdown import Markdown

        # Live body is already a Markdown renderable — no finalize reflow pop.
        assert isinstance(block._body, Markdown)


# ----------------------------------------------------------------------
# interrupt footer (spec §3.3: keep streamed content, `· interrupted`)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_interrupt_mid_stream_keeps_content_and_marks_footer() -> None:
    app = VossTUIApp()

    async def _dispatch(_value: str) -> None:
        await asyncio.sleep(60)

    app._turn_dispatch = _dispatch
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        app.on_input_bar_submitted(InputBar.Submitted("stream then interrupt"))
        await pilot.pause()
        tv.stream_delta("partial answer")
        # ctrl+c: action_interrupt marks the transcript, then the agent's
        # CancelledError handler finalizes the stream (simulated below).
        app.action_interrupt()
        tv.finalize_stream(role="system")
        await pilot.pause()
        flat = tv.plain_text()
        assert "partial answer" in flat  # streamed content kept
        assert "interrupted" in flat  # footer marker
        block = tv.query_one(AssistantBlock)
        assert block._footer is not None
        assert block._footer.plain.endswith("· interrupted")


@pytest.mark.asyncio
async def test_normal_finalize_has_no_interrupted_marker() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.stream_delta("complete answer")
        tv.finalize_stream(role="assistant", cost_usd=0.01)
        await pilot.pause()
        assert "interrupted" not in tv.plain_text()


# ----------------------------------------------------------------------
# plain renderer parity (spec §3.6: one `working...` line, nothing else)
# ----------------------------------------------------------------------


def test_plain_renderer_prints_single_working_line(capsys) -> None:
    from voss.harness.render import PlainRenderer

    r = PlainRenderer()
    r.show_working("working")
    r.update_working(1.0, 500)
    r.update_working(2.0, 900)
    r.hide_working()
    captured = capsys.readouterr()
    assert captured.err.count("working...") == 1
    assert captured.out == ""


def test_indicator_render_uses_locked_glyphs() -> None:
    """Headless render: brand glyph before animation, spinner frames after."""
    from voss.harness.tui import glyphs

    w = WorkingIndicator()
    assert w.plain_text().startswith(glyphs.WORKING)
    w._frame = 2
    assert w.plain_text().startswith(glyphs.SPINNER_FRAMES[2])
    w._frame = 2 + len(glyphs.SPINNER_FRAMES)  # wraps by index
    assert w.plain_text().startswith(glyphs.SPINNER_FRAMES[2])
