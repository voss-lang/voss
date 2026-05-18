"""T8 INPUT-04 reverse-search acceptance tests."""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.xfail(
    reason="T8 Wave 3 - reverse search not yet implemented",
    strict=False,
)


def test_build_corpus_dedupes_user_turns_by_recency(seeded_history) -> None:
    from voss.harness.tui.widgets.input_bar import _build_corpus

    history = seeded_history("alpha", "beta", "alpha")
    history.add("assistant text", role="assistant")

    assert _build_corpus(history) == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_ctrl_r_enters_search_mode_and_prefills_match(seeded_history) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp()
    app.episodic_memory = seeded_history("pytest tests", "ship it")
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.focus()
        await pilot.press("ctrl+r", "p", "y")
        await pilot.pause()

        assert input_bar.search_mode is True
        assert "pytest tests" in input_bar.text


def test_snap8_reverse_search_prompt_anchor(snap_compare) -> None:
    from voss.harness.tui.app import VossTUIApp

    assert snap_compare(VossTUIApp(), press=["ctrl+r"], terminal_size=(80, 24))
