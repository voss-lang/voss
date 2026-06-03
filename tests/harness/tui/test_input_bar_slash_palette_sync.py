"""InputBar slash palette text-change sync tests."""
from __future__ import annotations

import pytest

from voss.harness.slash import SlashCommand, SlashRegistry
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets import InputBar, SlashPalette


def _registry() -> SlashRegistry:
    registry = SlashRegistry()
    registry.register(SlashCommand("/agents", "show agents", lambda *a: None))
    registry.register(SlashCommand("/help", "show help", lambda *a: None))
    registry.register(SlashCommand("/cost", "show cost", lambda *a: None))
    return registry


def _palette_labels(palette: SlashPalette) -> list[str]:
    return list(getattr(palette, "_labels", []))


@pytest.mark.asyncio
async def test_slash_palette_syncs_filter_and_empty_backspace_dismiss() -> None:
    app = VossTUIApp(slash_registry=_registry())
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.focus()

        await pilot.press("/")
        await pilot.pause()

        palette = pilot.app.query_one(SlashPalette)
        assert input_bar.text == "/"
        assert any("/agents" in label for label in _palette_labels(palette))
        assert any("/help" in label for label in _palette_labels(palette))

        await pilot.press("a", "g")
        await pilot.pause()

        labels = _palette_labels(palette)
        assert any("/agents" in label for label in labels)
        assert all("/help" not in label for label in labels)

        await pilot.press("backspace", "backspace", "backspace")
        await pilot.pause()

        assert input_bar.text == ""
        assert not list(pilot.app.query(SlashPalette))


@pytest.mark.asyncio
async def test_slash_palette_dismisses_when_leading_slash_is_deleted() -> None:
    app = VossTUIApp(slash_registry=_registry())
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        textarea = input_bar.query_one("#input-textarea")

        input_bar.load_text("/foo")
        await pilot.pause()
        assert pilot.app.query_one(SlashPalette) is not None

        textarea.move_cursor((0, 1))
        await pilot.press("backspace")
        await pilot.pause()

        assert input_bar.text == "foo"
        assert not list(pilot.app.query(SlashPalette))
