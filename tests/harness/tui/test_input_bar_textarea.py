"""T8 INPUT-01 TextArea-backed InputBar acceptance tests."""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.xfail(
    reason="T8 Wave 1 - TextArea input bar not yet implemented",
    strict=False,
)


@pytest.mark.asyncio
async def test_enter_submits_multiline_value() -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets.input_bar import InputBar

    app = VossTUIApp()
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("first\nsecond")
        messages: list[InputBar.Submitted] = []
        input_bar.post_message = messages.append

        await input_bar.action_submit()

        assert messages[0].value == "first\nsecond"
        assert input_bar.text == ""
        assert not hasattr(input_bar, "value")


@pytest.mark.asyncio
async def test_shift_enter_inserts_newline_without_submit() -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets.input_bar import InputBar

    app = VossTUIApp()
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("hello")
        messages: list[InputBar.Submitted] = []
        input_bar.post_message = messages.append

        await pilot.press("shift+enter")
        await pilot.pause()

        assert "\n" in input_bar.text
        assert messages == []


@pytest.mark.asyncio
async def test_slash_guard_only_opens_palette_when_empty() -> None:
    from voss.harness.slash import SlashCommand, SlashRegistry
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar, SlashPalette

    registry = SlashRegistry()
    registry.register(SlashCommand("/help", "show help", lambda *a: None))
    app = VossTUIApp(slash_registry=registry)
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("echo")
        input_bar.focus()
        await pilot.press("/")
        await pilot.pause()
        assert input_bar.text.endswith("/")
        assert not list(pilot.app.query(SlashPalette))


def test_snap1_single_line_prompt_anchor(snap_compare) -> None:
    from voss.harness.tui.app import VossTUIApp

    assert snap_compare(VossTUIApp(), terminal_size=(80, 24))


def test_snap2_three_row_multiline_anchor(snap_compare) -> None:
    from voss.harness.tui.app import VossTUIApp

    async def run_before(pilot) -> None:
        input_bar = pilot.app.query_one("#input")
        input_bar.load_text("one\ntwo\nthree")

    assert snap_compare(VossTUIApp(), run_before=run_before, terminal_size=(80, 24))


def test_snap3_five_row_cap_anchor(snap_compare) -> None:
    from voss.harness.tui.app import VossTUIApp

    async def run_before(pilot) -> None:
        input_bar = pilot.app.query_one("#input")
        input_bar.load_text("1\n2\n3\n4\n5\n6")

    assert snap_compare(VossTUIApp(), run_before=run_before, terminal_size=(80, 24))


def test_snap4_slash_palette_guard_anchor(snap_compare) -> None:
    from voss.harness.slash import SlashCommand, SlashRegistry
    from voss.harness.tui.app import VossTUIApp

    registry = SlashRegistry()
    registry.register(SlashCommand("/help", "show help", lambda *a: None))

    assert snap_compare(
        VossTUIApp(slash_registry=registry),
        press=["/"],
        terminal_size=(80, 24),
    )
