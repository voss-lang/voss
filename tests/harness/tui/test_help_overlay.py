"""M9-03 HelpOverlay tests."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from voss.harness.slash import SlashCommand, SlashRegistry
from voss.harness.tui.keymap import KEYMAP
from voss.harness.tui.widgets.help_overlay import HEADING, HelpOverlay


def _fake_registry() -> SlashRegistry:
    reg = SlashRegistry()
    reg.register(SlashCommand("/help", "show help", lambda *a: None))
    reg.register(SlashCommand("/save", "memory note", lambda *a: None))
    reg.register(
        SlashCommand("/save-session", "persist session snapshot", lambda *a: None)
    )
    return reg


class _HostApp(App):
    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(HelpOverlay(KEYMAP, _fake_registry()))


@pytest.mark.asyncio
async def test_help_overlay_renders_heading_and_rows() -> None:
    app = _HostApp()
    async with app.run_test() as pilot:
        title = pilot.app.query_one("#help-title", expect_type=None)
        assert HEADING in str(title.renderable)
        # Locate at least one binding line + one command line.
        all_text = "\n".join(
            str(getattr(w, "renderable", "")) for w in pilot.app.query("Static")
        )
        assert any(b.key in all_text for b in KEYMAP)
        assert "/help" in all_text
        assert "/save" in all_text
        assert "/save-session" in all_text


@pytest.mark.asyncio
async def test_help_overlay_esc_dismisses() -> None:
    app = _HostApp()
    async with app.run_test() as pilot:
        assert pilot.app.screen.__class__.__name__ == "HelpOverlay"
        await pilot.press("escape")
        assert pilot.app.screen.__class__.__name__ != "HelpOverlay"
