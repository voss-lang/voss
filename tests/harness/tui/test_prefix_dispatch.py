"""T8 INPUT-02/03 local prefix dispatch acceptance tests."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_bang_command_renders_local_block_and_emits_recorder(
    mock_recorder_bridge,
) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar, TurnView

    app = VossTUIApp()
    app.recorder_bridge = mock_recorder_bridge
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("!python3 -c 'print(123)'")
        await input_bar.action_submit()
        await pilot.pause()

        payload = mock_recorder_bridge.emit.call_args.args[1]
        assert mock_recorder_bridge.emit.call_args.args[0] == "shell.local"
        assert payload["cmd"] == "python3 -c 'print(123)'"
        assert payload["exit_code"] == 0
        assert "123" in payload["stdout"]
        flat = "".join(str(line) for line in pilot.app.query_one("#main", TurnView).lines)
        assert "! python3 -c 'print(123)'" in flat
        assert "· exit 0" in flat


@pytest.mark.asyncio
async def test_bang_command_denied_does_not_exec(monkeypatch) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar, TurnView

    calls: list[tuple] = []

    async def fake_exec(*args, **kwargs):
        calls.append(args)
        raise AssertionError("exec should not be called")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    app = VossTUIApp()
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("!rm -rf /")
        await input_bar.action_submit()
        await pilot.pause()

        assert calls == []
        flat = "".join(str(line) for line in pilot.app.query_one("#main", TurnView).lines)
        assert "denied token" in flat


@pytest.mark.asyncio
async def test_hash_note_confirms_and_emits_memory_note(tmp_path, mock_recorder_bridge) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar, TurnView

    app = VossTUIApp()
    app.cwd = tmp_path
    app.recorder_bridge = mock_recorder_bridge
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("#remember this")
        await input_bar.action_submit()
        await pilot.pause()

        event_name, payload = mock_recorder_bridge.emit.call_args.args
        assert event_name == "memory.note"
        assert payload["text"] == "remember this"
        assert "timestamp" in payload
        assert "- [" in (tmp_path / "VOSS.md").read_text()
        assert "remember this" in (tmp_path / "VOSS.md").read_text()
        flat = "".join(str(line) for line in pilot.app.query_one("#main", TurnView).lines)
        assert "# note saved" in flat


@pytest.mark.asyncio
async def test_empty_prefixes_are_silent_noops(mock_recorder_bridge) -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp()
    app.recorder_bridge = mock_recorder_bridge
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        for value in ("!", "#", "!   "):
            input_bar.load_text(value)
            await input_bar.action_submit()

        mock_recorder_bridge.emit.assert_not_called()


@pytest.mark.asyncio
async def test_plain_text_still_posts_submitted() -> None:
    from voss.harness.tui.app import VossTUIApp
    from voss.harness.tui.widgets import InputBar

    app = VossTUIApp()
    async with app.run_test() as pilot:
        input_bar = pilot.app.query_one("#input", InputBar)
        input_bar.load_text("normal prompt")
        messages: list[InputBar.Submitted] = []
        original_post_message = input_bar.post_message

        def capture(message) -> bool:
            if isinstance(message, InputBar.Submitted):
                messages.append(message)
            return original_post_message(message)

        input_bar.post_message = capture
        await input_bar.action_submit()

        assert messages[0].value == "normal prompt"


def test_voss_md_notes_append_preserves_machine_fence(tmp_path) -> None:
    from voss.harness.voss_md import append_voss_notes_bullet, parse, write_fence_body

    path = tmp_path / "VOSS.md"
    write_fence_body(path, fence_id="architecture", body="machine body\n")
    before = parse(path.read_text())
    machine_before = [b for b in before if b.kind == "machine"][0]

    append_voss_notes_bullet(path, "ship it", "2026-05-18T00:00:00+00:00")

    blocks = parse(path.read_text())
    machine_after = [b for b in blocks if b.kind == "machine"][0]
    assert machine_after.recorded_hash == machine_before.recorded_hash
    assert machine_after.body == machine_before.body
    assert any(b.kind == "human" and "ship it" in b.body for b in blocks)


def test_recorder_bridge_emit_delegates_and_never_raises() -> None:
    from voss.harness.recorder import RunRecorder
    from voss.harness.tui.recorder_bridge import RecorderBridge

    app = MagicMock()
    bridge = RecorderBridge(RunRecorder.start(), app)
    bridge.emit("shell.local", {"cmd": "pwd"})
    app.on_local_event.assert_called_once_with("shell.local", {"cmd": "pwd"})

    app.on_local_event.side_effect = RuntimeError("boom")
    bridge.emit("memory.note", {"text": "x"})


def test_snap5_shell_exit_zero_anchor(snap_compare) -> None:
    from voss.harness.tui.app import VossTUIApp

    async def run_before(pilot) -> None:
        input_bar = pilot.app.query_one("#input")
        input_bar.load_text("!python3 -c 'print(123)'")
        await input_bar.action_submit()

    assert snap_compare(VossTUIApp(), run_before=run_before, terminal_size=(80, 24))


def test_snap6_shell_nonzero_anchor(snap_compare) -> None:
    from voss.harness.tui.app import VossTUIApp

    async def run_before(pilot) -> None:
        input_bar = pilot.app.query_one("#input")
        input_bar.load_text("!python3 -c 'import sys; sys.exit(1)'")
        await input_bar.action_submit()

    assert snap_compare(VossTUIApp(), run_before=run_before, terminal_size=(80, 24))


def test_snap7_note_saved_anchor(snap_compare, tmp_path) -> None:
    from voss.harness.tui.app import VossTUIApp

    async def run_before(pilot) -> None:
        pilot.app.cwd = tmp_path
        input_bar = pilot.app.query_one("#input")
        input_bar.load_text("#remember this")
        await input_bar.action_submit()

    assert snap_compare(VossTUIApp(), run_before=run_before, terminal_size=(80, 24))
