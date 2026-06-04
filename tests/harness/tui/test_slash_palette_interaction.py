"""Pilot tests for slash-palette KEYBOARD interaction (review HIGH/MEDIUM fix).

The 15 existing palette tests never drove selection via keystrokes, so a
non-interactive palette (focus stolen back to the textarea, nav/select/dismiss
keys never reaching it) shipped green. These tests press real keys through the
mounted palette: filter → navigate → select, plus the two dismiss paths.
"""

from __future__ import annotations

import pytest

from voss.harness.slash import SlashCommand, SlashRegistry
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets.slash_palette import SlashPalette


def _registry() -> SlashRegistry:
    reg = SlashRegistry()
    for name, help_text in (
        ("agent", "spawn a subagent"),
        ("agents", "list subagents"),
        ("analyze", "refresh cognition"),
        ("budget", "set budget"),
    ):
        reg.register(SlashCommand(name, help_text, lambda *a: None))
    return reg


def _palette(app) -> SlashPalette | None:
    found = app.query(SlashPalette)
    return found.first() if found else None


@pytest.mark.asyncio
async def test_slash_opens_filters_navigates_selects() -> None:
    app = VossTUIApp(slash_registry=_registry())
    submitted: list[str] = []
    async with app.run_test() as pilot:
        # capture what the palette submits
        orig = type(app).on_slash_palette_palette_submitted

        def _spy(self, message):  # handler is sync — do not await
            submitted.append(message.value)
            return orig(self, message)

        type(app).on_slash_palette_palette_submitted = _spy  # type: ignore[assignment]
        try:
            await pilot.press("slash")  # "/"
            await pilot.pause()
            assert _palette(pilot.app) is not None, "palette should open on /"

            await pilot.press("a", "g")  # filter to /agent /agents
            await pilot.pause()
            pal = _palette(pilot.app)
            assert pal is not None
            assert all(n.startswith("/ag") or "ag" in n for n in pal._names), pal._names

            await pilot.press("down")  # navigate
            await pilot.press("enter")  # SELECT highlighted (must NOT submit raw text)
            await pilot.pause()

            assert submitted, "enter should select a palette command, not submit raw text"
            assert submitted[0] in ("agent", "agents")
            assert _palette(pilot.app) is None, "palette dismissed after select"
        finally:
            type(app).on_slash_palette_palette_submitted = orig  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_backspacing_slash_dismisses() -> None:
    app = VossTUIApp(slash_registry=_registry())
    async with app.run_test() as pilot:
        await pilot.press("slash")
        await pilot.pause()
        assert _palette(pilot.app) is not None
        await pilot.press("backspace")  # remove the leading "/"
        await pilot.pause()
        assert _palette(pilot.app) is None, "palette dismissed when / removed"


@pytest.mark.asyncio
async def test_escape_dismisses_palette() -> None:
    app = VossTUIApp(slash_registry=_registry())
    async with app.run_test() as pilot:
        await pilot.press("slash")
        await pilot.pause()
        assert _palette(pilot.app) is not None
        await pilot.press("escape")
        await pilot.pause()
        assert _palette(pilot.app) is None, "escape should dismiss the palette"


@pytest.mark.asyncio
async def test_backspace_deletes_chars_with_palette_open() -> None:
    app = VossTUIApp(slash_registry=_registry())
    async with app.run_test() as pilot:
        await pilot.press("slash", "a", "g")
        await pilot.pause()
        ta = pilot.app.query_one("#input-textarea")
        assert ta.text == "/ag", f"typing got {ta.text!r}"
        await pilot.press("backspace")
        await pilot.pause()
        assert ta.text == "/a", f"backspace should delete; got {ta.text!r}"
        await pilot.press("backspace", "backspace")
        await pilot.pause()
        assert ta.text == "", f"backspace to empty; got {ta.text!r}"
        assert _palette(pilot.app) is None, "palette dismissed when empty"
