"""T8 INPUT-04 reverse-search acceptance tests."""
from __future__ import annotations

import pytest


def test_build_corpus_dedupes_user_turns_by_recency(seeded_history) -> None:
    from voss.harness.tui.widgets.input_bar import _build_corpus

    history = seeded_history("alpha", "beta", "alpha")
    history.add("assistant text", role="assistant")

    assert _build_corpus(history) == ["alpha", "beta"]


def test_build_corpus_empty_history() -> None:
    from voss.harness.tui.widgets.input_bar import _build_corpus

    assert _build_corpus(None) == []


@pytest.mark.asyncio
async def test_ctrl_r_enters_search_mode_and_prefills_match(seeded_history) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp(history=seeded_history("pytest tests", "ship it"))
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.focus()
        await pilot.press("ctrl+r", "p", "y")
        await pilot.pause()

        assert input_bar.search_mode is True
        assert "pytest tests" in input_bar.text
        assert "(reverse-i-search)`py':" in input_bar.text


@pytest.mark.asyncio
async def test_ctrl_r_enter_loads_match_without_submitting(seeded_history) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp(history=seeded_history("pytest tests"))
    calls: list[str] = []

    async def dispatch(value: str) -> None:
        calls.append(value)

    async with app.run_test() as pilot:
        pilot.app._turn_dispatch = dispatch
        input_bar = pilot.app.query_one("#input", InputBar)
        await pilot.press("ctrl+r", "p", "y", "enter")
        await pilot.pause()

        assert input_bar.search_mode is False
        assert input_bar.text == "pytest tests"
        assert calls == []


@pytest.mark.asyncio
async def test_ctrl_r_escape_restores_saved_text(seeded_history) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp(history=seeded_history("pytest tests"))
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("draft")
        await pilot.press("ctrl+r", "p", "escape")
        await pilot.pause()

        assert input_bar.search_mode is False
        assert input_bar.text == "draft"


def test_snap8_reverse_search_prompt_anchor(snap_compare, seeded_history) -> None:
    from voss.harness.tui.app import VossTUIApp

    assert snap_compare(
        VossTUIApp(history=seeded_history("pytest tests")),
        press=["ctrl+r", "p"],
        terminal_size=(80, 24),
    )


def test_snap9_reverse_search_no_match_anchor(snap_compare, seeded_history) -> None:
    from voss.harness.tui.app import VossTUIApp

    assert snap_compare(
        VossTUIApp(history=seeded_history("pytest tests")),
        press=["ctrl+r", "z"],
        terminal_size=(80, 24),
    )
