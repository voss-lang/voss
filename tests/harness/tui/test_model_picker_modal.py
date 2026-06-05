"""P4 pilot tests for the ModelPickerModal (search/nav/select/esc)."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from voss.harness.model_catalog import ModelEntry, ProviderGroup
from voss.harness.tui.widgets.model_picker_modal import ModelPickerModal


def _entry(pid, mid, **kw):
    base = dict(
        id=mid, name=mid, provider_id=pid, provider_label=pid,
        api_base=None, env_key=None, free=False, subscription=False,
        context=200000, tool_call=True,
    )
    base.update(kw)
    return ModelEntry(**base)


GROUPS = [
    ProviderGroup("anthropic", "Anthropic", None, "ANTHROPIC_API_KEY", (
        _entry("anthropic", "claude-sonnet-4-5"),
    )),
    ProviderGroup("opencode", "OpenCode Zen", "https://opencode.ai/zen/v1", "OPENCODE_API_KEY", (
        _entry("opencode", "mimo-v2-flash-free", free=True),
        _entry("opencode", "kimi-k2.5-free", free=True),
    )),
    ProviderGroup("ollama-cloud", "Ollama Cloud", "https://ollama.com/v1", "OLLAMA_API_KEY", (
        _entry("ollama-cloud", "gemma3:27b"),
    )),
]
CONNECTED = {"anthropic": True, "opencode": False, "ollama-cloud": True}


class _Host(App):
    """Hosts the modal and records the dismissed value."""

    def __init__(self) -> None:
        super().__init__()
        self.picked = "UNSET"

    def compose(self) -> ComposeResult:
        return []

    def open(self, current="claude-sonnet-4-5"):
        def _cb(value):
            self.picked = value
        self.push_screen(ModelPickerModal(GROUPS, CONNECTED, current), _cb)


@pytest.mark.asyncio
async def test_initial_highlight_is_current() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="gemma3:27b")
        await pilot.pause()
        lst = app.query_one("#picker-list")
        assert lst.current_entry().id == "gemma3:27b"


@pytest.mark.asyncio
async def test_search_filters_and_enter_selects() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open()
        await pilot.pause()
        await pilot.press("k", "i", "m", "i")  # -> "kimi"
        await pilot.pause()
        lst = app.query_one("#picker-list")
        assert lst.current_entry().id == "kimi-k2.5-free"
        await pilot.press("enter")
        await pilot.pause()
    assert app.picked is not None
    assert app.picked.id == "kimi-k2.5-free"


@pytest.mark.asyncio
async def test_down_skips_group_headers() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open(current="claude-sonnet-4-5")
        await pilot.pause()
        lst = app.query_one("#picker-list")
        # from the only anthropic row, down should land on the first zen row
        # (skipping the "OpenCode Zen" header), not a header.
        await pilot.press("down")
        await pilot.pause()
        entry = lst.current_entry()
        assert entry is not None and entry.id == "mimo-v2-flash-free"


@pytest.mark.asyncio
async def test_escape_cancels_with_none() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        app.open()
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert app.picked is None
