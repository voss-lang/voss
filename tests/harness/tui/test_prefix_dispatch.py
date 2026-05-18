"""T8 INPUT-02/03 local prefix dispatch acceptance tests."""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.xfail(
    reason="T8 Wave 2 - prefix dispatch not yet implemented",
    strict=False,
)


@pytest.mark.asyncio
async def test_bang_command_renders_local_block_and_emits_recorder(
    mock_recorder_bridge,
) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp()
    app.recorder_bridge = mock_recorder_bridge
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("!printf ok")
        await input_bar.action_submit()

        mock_recorder_bridge.emit.assert_called_with(
            "shell.local",
            {"cmd": "printf ok", "exit_code": 0},
        )


@pytest.mark.asyncio
async def test_hash_note_confirms_and_emits_memory_note(mock_recorder_bridge) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp()
    app.recorder_bridge = mock_recorder_bridge
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("#remember this")
        await input_bar.action_submit()

        mock_recorder_bridge.emit.assert_called_with(
            "memory.note",
            {"body": "remember this"},
        )
