"""R3 ToolCard tests — in-place tool cards (tui-redesign-spec §3.4/§6.1).

Covers the R3 acceptance rules: one tool call occupies exactly ONE card
pending→settled (no duplicate lines), error output auto-expands, settled-only
paths create a settled-first card, and concurrent same-name calls (read
batches run via asyncio.gather) stay on distinct cards keyed by call_id.
"""
from __future__ import annotations

import pytest

from voss.harness.tui import glyphs
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.renderer import TextualRenderer
from voss.harness.tui.widgets import ToolCard, TranscriptView
from voss.harness.tui.widgets.tool_card import _diff_hunks, _metric


# ----------------------------------------------------------------------
# metric parsing (pure helper)
# ----------------------------------------------------------------------


def test_metric_shell_exit_code() -> None:
    assert _metric("shell_run", {}, "[exit 0]", 1.23, "[exit 0]\nout").startswith(
        "exit 0 · "
    )
    assert _metric("shell_run", {}, "[exit 1]", 0.4, "[exit 1]\nboom").startswith(
        "exit 1 · "
    )


def test_metric_read_counts_output_lines() -> None:
    assert _metric("fs_read", {}, "first", 0.5, "a\nb\nc") == "3 lines"


def test_metric_grep_counts_matches() -> None:
    assert _metric("fs_grep", {}, "", 0.5, "f.py:1: x\nf.py:2: y") == "2 matches"
    assert _metric("fs_grep", {}, "", 0.5, "<no matches>") == "0 matches"
    assert _metric("fs_glob", {}, "", 0.5, "a.py") == "1 match"


def test_metric_edit_adds_dels_from_args() -> None:
    assert _metric("fs_edit", {"old": "a\nb", "new": "c"}, "", 0.5) == "+1 -2"
    assert (
        _metric(
            "fs_edit_many",
            {"edits": [{"old": "a", "new": "b\nc"}, {"old": "d", "new": "e"}]},
            "",
            0.5,
        )
        == "+3 -2"
    )
    assert _metric("fs_write", {"content": "x\ny"}, "", 0.5) == "+2 -0"


def test_metric_edit_anchor_falls_back_to_summary_delta() -> None:
    # Anchor-based fs_edit has no `old` arg — parse the result line delta.
    assert (
        _metric("fs_edit", {"anchor": "h#1", "new": "x"}, "edited f.py (+3 lines)", 0.5)
        == "+3 lines"
    )


def test_metric_default_is_duration() -> None:
    assert _metric("voss_check", {}, "ok", 1.5) == "1.5s"
    assert _metric("voss_check", {}, "ok", 12.0) == "12s"


def test_diff_hunks_capped_at_three() -> None:
    edits = [{"old": f"o{i}", "new": f"n{i}"} for i in range(5)]
    assert len(_diff_hunks("fs_edit_many", {"edits": edits})) == 3
    assert _diff_hunks("fs_read", {"path": "x"}) == []
    # Anchor-based edits carry no old text — no mini-diff.
    assert _diff_hunks("fs_edit", {"anchor": "h#1", "new": "x"}) == []


# ----------------------------------------------------------------------
# one call = exactly one card, pending → settled in place
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_tool_call_one_card_pending_to_settled() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_tool_call("c1", "fs_read", {"path": "x.py"}, "running…", "pending")
        await pilot.pause()
        cards = list(pilot.app.query(ToolCard))
        assert len(cards) == 1
        assert cards[0].state == "running"
        renderer.show_tool_call(
            "c1", "fs_read", {"path": "x.py"}, "line1", "ok", output="line1\nline2"
        )
        await pilot.pause()
        cards = list(pilot.app.query(ToolCard))
        assert len(cards) == 1, "settle must mutate the pending card, not append"
        assert cards[0].state == "ok"
        text = cards[0].plain_text()
        assert glyphs.TOOL_OK in text
        assert "2 lines" in text  # read-class right metric


@pytest.mark.asyncio
async def test_settled_first_card_for_unknown_call_id() -> None:
    """Unknown-tool / denied paths emit a settle with no prior pending."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_tool_call(
            "never-pended", "bogus_tool", {}, "<unknown tool>", "error",
            output="<error: unknown tool 'bogus_tool'>",
        )
        await pilot.pause()
        cards = list(pilot.app.query(ToolCard))
        assert len(cards) == 1
        assert cards[0].state == "error"


@pytest.mark.asyncio
async def test_call_id_none_creates_settled_first_card() -> None:
    """Legacy callers passing call_id=None get a settled-first card."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_tool_call(None, "fs_read", {"path": "x"}, "done", "ok")
        await pilot.pause()
        cards = list(pilot.app.query(ToolCard))
        assert len(cards) == 1
        assert cards[0].state == "ok"


@pytest.mark.asyncio
async def test_concurrent_same_name_calls_keep_distinct_cards() -> None:
    """Read batches gather concurrently — settle in reverse arrival order."""
    app = VossTUIApp()
    async with app.run_test() as pilot:
        renderer = TextualRenderer(app=pilot.app)
        renderer.show_tool_call("a1", "fs_read", {"path": "a.py"}, "running…", "pending")
        renderer.show_tool_call("a2", "fs_read", {"path": "b.py"}, "running…", "pending")
        await pilot.pause()
        # Settle the SECOND call first (reverse order).
        renderer.show_tool_call("a2", "fs_read", {"path": "b.py"}, "x", "error", output="boom")
        await pilot.pause()
        tv = pilot.app.query_one("#main", TranscriptView)
        card1, card2 = tv.get_tool_card("a1"), tv.get_tool_card("a2")
        assert card1 is not None and card2 is not None
        assert card1.state == "running"
        assert card2.state == "error"
        renderer.show_tool_call("a1", "fs_read", {"path": "a.py"}, "x", "ok", output="x\ny\nz")
        await pilot.pause()
        assert card1.state == "ok"
        assert len(list(pilot.app.query(ToolCard))) == 2
        assert "3 lines" in card1.plain_text()


# ----------------------------------------------------------------------
# output body: collapse / expand
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ok_output_collapsed_by_default_and_toggles() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        card = tv.add_tool_card("t1", "fs_read", {"path": "x"})
        card.settle("ok", "l1", output="l1\nl2\nl3")
        await pilot.pause()
        assert not card.expanded
        text = card.plain_text()
        assert glyphs.OUTPUT_ELBOW in text
        assert glyphs.CHEVRON_CLOSED in text
        assert "l3" not in text  # body hidden while collapsed
        card.toggle()
        await pilot.pause()
        assert card.expanded
        text = card.plain_text()
        assert glyphs.CHEVRON_OPEN in text
        assert "l3" in text  # output tail visible
        card.toggle()
        assert not card.expanded


@pytest.mark.asyncio
async def test_error_auto_expands_first_lines() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        card = tv.add_tool_card("e1", "shell_run", {"cmd": "pytest -x"})
        output = "[exit 1]\n" + "\n".join(f"line{i}" for i in range(30))
        card.settle("error", "[exit 1]", output=output)
        await pilot.pause()
        assert card.expanded, "errors auto-expand"
        text = card.plain_text()
        assert glyphs.CHEVRON_OPEN in text
        assert "line0" in text       # first lines shown…
        assert "line25" not in text  # …capped at ERROR_HEAD_LINES
        assert "exit 1" in text      # shell right metric


@pytest.mark.asyncio
async def test_ok_expanded_shows_output_tail() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        card = tv.add_tool_card("t2", "fs_read", {"path": "big.txt"})
        card.settle("ok", "line0", output="\n".join(f"line{i}" for i in range(40)))
        card.expand()
        await pilot.pause()
        body_lines = {ln.strip() for ln in card.plain_text().splitlines()}
        assert "line39" in body_lines  # tail…
        assert "line20" in body_lines
        assert "line19" not in body_lines  # …last 20 lines only (20-39)
        assert "…" in body_lines  # truncation marker


# ----------------------------------------------------------------------
# inline mini-diff (edit-class tools)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_card_inline_mini_diff() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        card = tv.add_tool_card(
            "d1", "fs_edit", {"path": "f.py", "old": "a = 1", "new": "a = 2"}
        )
        card.settle("ok", "edited f.py (+0 lines)")
        await pilot.pause()
        assert "+1 -1" in card.plain_text()  # edit-class metric from args
        assert "1 hunk · ctrl+d full diff" in card.plain_text()
        card.expand()
        text = card.plain_text()
        assert "- a = 1" in text
        assert "+ a = 2" in text


# ----------------------------------------------------------------------
# TranscriptView API
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transcript_keys_cards_and_keeps_indicator_last() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        tv = pilot.app.query_one("#main", TranscriptView)
        tv.show_working()
        card = tv.add_tool_card("k1", "fs_read", {"path": "x"})
        await pilot.pause()
        assert tv.get_tool_card("k1") is card
        assert tv.get_tool_card("nope") is None
        children = list(tv.children)
        assert children[-1] is tv._working  # WorkingIndicator stays last
        assert card in children
