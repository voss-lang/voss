"""Tests for the @-mention file finder (OpenCode-leverage port).

Pure ranking/token logic + a pilot-driven open→select→insert flow and the
dismiss/precedence edges.
"""
from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets.mention_palette import (
    MentionPalette,
    find_mention_token,
    rank_files,
)


# ---------------------------------------------------------------------------
# pure logic
# ---------------------------------------------------------------------------

def test_find_token_in_word_before_cursor() -> None:
    assert find_mention_token("see @inp here", 8) == (4, "inp")


def test_find_token_at_start() -> None:
    assert find_mention_token("@foo", 4) == (0, "foo")


def test_no_token_without_at() -> None:
    assert find_mention_token("plain text", 10) is None


def test_no_token_when_space_breaks_word() -> None:
    # cursor is after "bar"; the @ is in a previous token → no active mention
    assert find_mention_token("@foo bar", 8) is None


def test_rank_prefers_basename_match() -> None:
    paths = ["src/input_bar.py", "x/y/inputs.py", "README.md"]
    ranked = rank_files("inp", paths)
    assert ranked[0] == "x/y/inputs.py"  # shorter basename match wins
    assert "README.md" not in ranked


def test_rank_empty_query_returns_shallow_first() -> None:
    paths = ["a/b/c/deep.py", "top.py", "a/mid.py"]
    assert rank_files("", paths)[0] == "top.py"


# ---------------------------------------------------------------------------
# pilot flow
# ---------------------------------------------------------------------------

def _mk_app(tmp_path) -> VossTUIApp:
    (tmp_path / "alpha.py").write_text("x = 1\n")
    (tmp_path / "beta.txt").write_text("y\n")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "alpaca.py").write_text("z\n")
    app = VossTUIApp()
    app.cwd = tmp_path
    return app


@pytest.mark.asyncio
async def test_at_opens_finder(tmp_path) -> None:
    app = _mk_app(tmp_path)
    async with app.run_test() as pilot:
        ta = app.query_one("#input-textarea")
        ta.insert("@alp")
        await pilot.pause()
        pal = app.query(MentionPalette).first() if app.query(MentionPalette) else None
        assert pal is not None, "@ should open the file finder"
        assert any("alpha.py" in n or "alpaca.py" in n for n in pal._names), pal._names


@pytest.mark.asyncio
async def test_enter_inserts_selected_path(tmp_path) -> None:
    app = _mk_app(tmp_path)
    async with app.run_test() as pilot:
        ta = app.query_one("#input-textarea")
        ta.insert("@alpha")
        await pilot.pause()
        pal = app.query(MentionPalette).first()
        assert pal is not None and pal._names
        chosen = pal._names[0]
        await pilot.press("enter")
        await pilot.pause()
        assert ta.text == f"{chosen} ", f"got {ta.text!r}"
        assert not app.query(MentionPalette), "finder dismissed after select"


@pytest.mark.asyncio
async def test_space_dismisses_finder(tmp_path) -> None:
    app = _mk_app(tmp_path)
    async with app.run_test() as pilot:
        ta = app.query_one("#input-textarea")
        ta.insert("@alp")
        await pilot.pause()
        assert app.query(MentionPalette).first() is not None
        ta.insert(" ")
        await pilot.pause()
        assert not app.query(MentionPalette), "space breaks the @token → dismiss"


@pytest.mark.asyncio
async def test_slash_takes_precedence_over_mention(tmp_path) -> None:
    app = _mk_app(tmp_path)
    async with app.run_test() as pilot:
        ta = app.query_one("#input-textarea")
        ta.insert("/foo")
        await pilot.pause()
        assert not app.query(MentionPalette), "slash line must not open the file finder"


@pytest.mark.asyncio
async def test_click_inserts_path(tmp_path) -> None:
    app = _mk_app(tmp_path)
    async with app.run_test() as pilot:
        ta = app.query_one("#input-textarea")
        ta.insert("@alpha")
        await pilot.pause()
        pal = app.query(MentionPalette).first()
        assert pal is not None and pal._names
        item = pal.highlighted_child
        await pilot.click(item)
        await pilot.pause()
        assert ta.text.endswith(" ") and ta.text.strip() in pal._names + [ta.text.strip()]
        assert not app.query(MentionPalette)
