"""Tests for the OpenCode-leverage ports: copy-code-block + mouse-clickable
slash palette rows."""
from __future__ import annotations

import pytest

from voss.harness.slash import SlashCommand, SlashRegistry
from voss.harness.tui.app import VossTUIApp, extract_last_code_block
from voss.harness.tui.widgets.slash_palette import SlashPalette


# ---------------------------------------------------------------------------
# pure extractor
# ---------------------------------------------------------------------------

def test_extract_last_code_block_basic() -> None:
    text = "intro\n```python\nx = 1\ny = 2\n```\noutro"
    assert extract_last_code_block(text) == "x = 1\ny = 2"


def test_extract_last_code_block_picks_last() -> None:
    text = "```\nfirst\n```\nmid\n```js\nsecond\n```"
    assert extract_last_code_block(text) == "second"


def test_extract_last_code_block_none_when_absent() -> None:
    assert extract_last_code_block("no fences here") is None
    assert extract_last_code_block("") is None


# ---------------------------------------------------------------------------
# copy action
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_copy_code_yanks_last_block(monkeypatch) -> None:
    app = VossTUIApp()
    captured: dict[str, str] = {}
    async with app.run_test() as pilot:
        monkeypatch.setattr(
            app, "copy_to_clipboard", lambda s: captured.__setitem__("v", s)
        )
        app.note_response_text("hi\n```py\nprint(1)\n```\nbye")
        app.action_copy_code()
        await pilot.pause()
    assert captured.get("v") == "print(1)"


@pytest.mark.asyncio
async def test_copy_code_falls_back_to_whole_response(monkeypatch) -> None:
    app = VossTUIApp()
    captured: dict[str, str] = {}
    async with app.run_test() as pilot:
        monkeypatch.setattr(
            app, "copy_to_clipboard", lambda s: captured.__setitem__("v", s)
        )
        app.note_response_text("just prose, no code")
        app.action_copy_code()
        await pilot.pause()
    assert captured.get("v") == "just prose, no code"


@pytest.mark.asyncio
async def test_ctrl_y_keybinding_triggers_copy(monkeypatch) -> None:
    app = VossTUIApp()
    captured: dict[str, str] = {}
    async with app.run_test() as pilot:
        monkeypatch.setattr(
            app, "copy_to_clipboard", lambda s: captured.__setitem__("v", s)
        )
        app.note_response_text("```\ncode-via-key\n```")
        await pilot.press("ctrl+y")
        await pilot.pause()
    assert captured.get("v") == "code-via-key"


# ---------------------------------------------------------------------------
# mouse: clicking a palette row runs the command
# ---------------------------------------------------------------------------

def _registry() -> SlashRegistry:
    reg = SlashRegistry()
    for name, help_text in (("agent", "spawn"), ("agents", "list"), ("budget", "set")):
        reg.register(SlashCommand(name, help_text, lambda *a: None))
    return reg


@pytest.mark.asyncio
async def test_clicking_palette_row_runs_command() -> None:
    app = VossTUIApp(slash_registry=_registry())
    submitted: list[str] = []
    async with app.run_test() as pilot:
        orig = type(app).on_slash_palette_palette_submitted

        def _spy(self, message):
            submitted.append(message.value)
            return orig(self, message)

        type(app).on_slash_palette_palette_submitted = _spy  # type: ignore[assignment]
        try:
            await pilot.press("slash", "a", "g")
            await pilot.pause()
            pal = app.query(SlashPalette).first()
            assert pal is not None and pal._names
            item = pal._items_by_name[pal._names[0]]
            await pilot.click(item)
            await pilot.pause()
            assert submitted and submitted[0] in ("agent", "agents")
            assert not app.query(SlashPalette), "palette dismissed after click"
        finally:
            type(app).on_slash_palette_palette_submitted = orig  # type: ignore[assignment]
