"""M9-03 SlashPalette + rank_commands tests."""
from __future__ import annotations

import pytest
from textual.widgets import ListItem, Static

from voss.harness.slash import SlashCommand, SlashRegistry
from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES
from voss.harness.tui.widgets import SlashPalette, rank_commands


def _input_text(input_bar) -> str:
    if hasattr(input_bar, "text"):
        return input_bar.text
    return input_bar.value


def _set_input_text(input_bar, text: str) -> None:
    if hasattr(input_bar, "load_text"):
        input_bar.load_text(text)
    elif hasattr(input_bar, "text"):
        input_bar.query_one("#input-textarea").load_text(text)
    else:
        input_bar.value = text


# ----------------------------------------------------------------------
# rank_commands — pure logic
# ----------------------------------------------------------------------


def test_rank_substring_match_first() -> None:
    out = rank_commands("he", ["/help", "/cost", "/exit", "/agents"])
    assert out[0] == "/help"


def test_rank_substring_mid_match() -> None:
    out = rank_commands("cl", ["/help", "/clear", "/cost"])
    assert out[0] == "/clear"


def test_rank_empty_query_uses_recency_then_alpha() -> None:
    out = rank_commands(
        "",
        ["/agents", "/clear", "/cost", "/exit", "/help"],
        recency=["/help", "/cost"],
    )
    assert out[:2] == ["/help", "/cost"]
    assert out[2:] == ["/agents", "/clear", "/exit"]


def test_rank_filters_reserved_m8_names() -> None:
    out = rank_commands(
        "recall",
        ["/recall", "/help"],
        reserved=RESERVED_SLASH_NAMES,
    )
    assert "/recall" not in out


def test_rank_filters_forget_and_memory() -> None:
    for q, name in (("forget", "/forget"), ("mem", "/memory")):
        out = rank_commands(q, [name, "/help"], reserved=RESERVED_SLASH_NAMES)
        assert name not in out


def test_rank_keeps_save_alive() -> None:
    out = rank_commands(
        "sa",
        ["/save", "/save-session", "/help"],
        reserved=RESERVED_SLASH_NAMES,
    )
    assert "/save" in out
    assert "/save-session" in out


def test_rank_caps_results_at_eight() -> None:
    names = [f"/cmd{i:02d}" for i in range(50)]
    out = rank_commands("cmd", names)
    assert len(out) <= 8


# ----------------------------------------------------------------------
# SlashPalette widget — DOM behavior
# ----------------------------------------------------------------------


def _registry_with(*entries: tuple[str, str]) -> SlashRegistry:
    reg = SlashRegistry()
    for name, help_text in entries:
        reg.register(SlashCommand(name, help_text, lambda *a: None))
    return reg


@pytest.mark.asyncio
async def test_palette_mount_shows_filtered_results() -> None:
    registry = _registry_with(
        ("/help", "show this list"),
        ("/cost", "session cost so far"),
        ("/clear", "drop episodic memory"),
        ("/save-session", "persist session snapshot"),
    )
    app = VossTUIApp(slash_registry=registry)
    async with app.run_test() as pilot:
        palette = SlashPalette(registry)
        await pilot.app.mount(palette)
        palette.update_query("he")
        labels = getattr(palette, "_labels", []) or [
            "no matching commands" for _ in palette.children
        ]
        assert any("/help" in label for label in labels)
        assert all("/cost" not in label for label in labels)


@pytest.mark.asyncio
async def test_palette_empty_state_copy() -> None:
    registry = _registry_with(("/help", "show help"))
    app = VossTUIApp(slash_registry=registry)
    async with app.run_test() as pilot:
        palette = SlashPalette(registry)
        await pilot.app.mount(palette)
        palette.update_query("zzzzz")
        labels = getattr(palette, "_labels", []) or [
            "no matching commands" for _ in palette.children
        ]
        assert any("no matching commands" in label for label in labels)


@pytest.mark.asyncio
async def test_palette_update_query_toggles_existing_items() -> None:
    registry = _registry_with(
        ("/help", "show this list"),
        ("/cost", "session cost so far"),
        ("/clear", "clear transcript"),
    )
    app = VossTUIApp(slash_registry=registry)
    async with app.run_test() as pilot:
        palette = SlashPalette(registry)
        await pilot.app.mount(palette)
        children_before = tuple(palette.children)

        palette.update_query("he")

        assert tuple(palette.children) == children_before
        by_name = {
            getattr(item, "_voss_command_name", None): item
            for item in palette.children
        }
        assert by_name["/help"].display is True
        assert by_name["/help"].disabled is False
        assert by_name["/cost"].display is False
        assert by_name["/cost"].disabled is True
        assert by_name["/clear"].display is False
        assert by_name["/clear"].disabled is True


def test_palette_submit_uses_highlighted_item_command_name() -> None:
    class SubmitOnlyPalette(SlashPalette):
        def __init__(self, registry: SlashRegistry) -> None:
            super().__init__(registry)
            self.messages: list[SlashPalette.PaletteSubmitted] = []
            self.highlighted_for_test = None

        @property
        def highlighted_child(self):
            return self.highlighted_for_test

        def post_message(self, message) -> bool:
            self.messages.append(message)
            return True

        def action_dismiss(self) -> None:
            return None

    registry = _registry_with(
        ("/clear", "clear transcript"),
        ("/cost", "session cost so far"),
        ("/help", "show this list"),
    )
    palette = SubmitOnlyPalette(registry)
    help_item = ListItem(Static("/help"))
    help_item._voss_command_name = "/help"  # type: ignore[attr-defined]
    palette.highlighted_for_test = help_item
    palette._names = ["/help"]
    palette._items_by_name = {"/help": help_item}
    palette.index = 2

    palette._submit_current()

    assert [message.value for message in palette.messages] == ["/help"]


@pytest.mark.asyncio
async def test_input_bar_open_palette_only_when_empty() -> None:
    registry = _registry_with(("/help", "show help"))
    app = VossTUIApp(slash_registry=registry)
    async with app.run_test() as pilot:
        from voss.harness.tui.widgets import InputBar

        input_bar = pilot.app.query_one("#input", InputBar)
        _set_input_text(input_bar, "")
        input_bar.focus()
        await pilot.press("/")
        await pilot.pause()
        try:
            pilot.app.query_one(SlashPalette)
            opened = True
        except Exception:
            opened = False
        assert opened, "palette did not open on `/` with empty input"
        assert _input_text(input_bar) == "/"


def test_app_bindings_populated_from_keymap() -> None:
    assert VossTUIApp.BINDINGS, "VossTUIApp.BINDINGS must not be empty"
    keys = {b[0] if isinstance(b, tuple) else b.key for b in VossTUIApp.BINDINGS}
    for required in ("escape", "question_mark", "ctrl+c", "ctrl+l", "tab", "shift+tab"):
        assert required in keys, f"missing binding for {required!r}"
