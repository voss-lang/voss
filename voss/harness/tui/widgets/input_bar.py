"""InputBar widget - bottom multi-line input with locked prompt glyph."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, TextArea

from voss.harness import sandbox, voss_md

from .. import glyphs
from .local_block import LocalBlockNote, LocalBlockShell


class _InputTextArea(TextArea):
    """TextArea child with M9 main-context collisions stripped."""

    BINDINGS = [
        binding
        for binding in TextArea.BINDINGS
        if binding.key not in {"ctrl+f", "ctrl+u"}
    ]


class InputBar(Widget):
    """TextArea-backed input with locked prompt glyph + Submitted contract."""

    BINDINGS = [("slash", "open_palette", "Open slash palette")]
    can_focus = True

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._prompt_text = f"{glyphs.PROMPT} "
        self._search_mode = False

    def compose(self) -> ComposeResult:
        yield Static(self._prompt_text, id="prompt-glyph", classes="accent")
        yield _InputTextArea(
            "",
            id="input-textarea",
            show_line_numbers=False,
            soft_wrap=True,
        )

    @property
    def text(self) -> str:
        return self.query_one("#input-textarea", TextArea).text

    def load_text(self, text: str) -> None:
        textarea = self.query_one("#input-textarea", TextArea)
        textarea.load_text(text)
        lines = text.split("\n")
        textarea.move_cursor((len(lines) - 1, len(lines[-1])))

    def insert(self, text: str) -> None:
        self.query_one("#input-textarea", TextArea).insert(text)

    async def _on_key(self, event) -> None:
        textarea = self.query_one("#input-textarea", TextArea)
        if event.key == "enter" and not self._search_mode:
            event.prevent_default()
            event.stop()
            await self.action_submit()
            return
        if event.key == "shift+enter":
            event.prevent_default()
            event.stop()
            textarea.insert("\n")
            return
        if event.key == "slash" and not textarea.text.strip():
            event.prevent_default()
            event.stop()
            self.action_open_palette()
            return
        await textarea._on_key(event)  # noqa: SLF001 - delegate editing to child TextArea.

    class Submitted(Message):
        """Posted when user presses Enter on a non-empty input."""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    async def action_submit(self) -> None:
        value = self.text
        self.load_text("")
        stripped = value.strip()
        if not stripped:
            return
        if stripped.startswith("!"):
            cmd = stripped[1:].strip()
            if cmd:
                await self._dispatch_shell(cmd)
            return
        if stripped.startswith("#"):
            note = stripped[1:].strip()
            if note:
                await self._dispatch_note(note)
            return
        self.post_message(self.Submitted(value))

    async def _dispatch_shell(self, cmd: str) -> None:
        allowed, reason = sandbox.shell_allowed(cmd)
        if not allowed:
            self._append_local_block(LocalBlockShell(cmd, reason, "", 1))
            return

        proc = await asyncio.create_subprocess_exec(
            *sandbox.split_command(cmd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await proc.communicate()
        stdout = stdout_b.decode(errors="replace")
        stderr = stderr_b.decode(errors="replace")
        exit_code = int(proc.returncode or 0)
        self._append_local_block(LocalBlockShell(cmd, stdout, stderr, exit_code))
        bridge = getattr(self.app, "recorder_bridge", None)
        if bridge is not None:
            bridge.emit(
                "shell.local",
                {
                    "cmd": cmd,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )

    async def _dispatch_note(self, note: str) -> None:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        cwd = Path(getattr(self.app, "cwd", Path.cwd()))
        voss_md.append_voss_notes_bullet(cwd / "VOSS.md", note, timestamp)
        self._append_local_block(LocalBlockNote())
        bridge = getattr(self.app, "recorder_bridge", None)
        if bridge is not None:
            bridge.emit("memory.note", {"text": note, "timestamp": timestamp})

    def _append_local_block(self, block) -> None:
        try:
            from .turn_view import TurnView

            turn_view = self.app.query_one("#main", TurnView)
        except Exception:  # noqa: BLE001
            return
        if getattr(turn_view, "_turn_count", 0) == 0:
            turn_view.clear()
        turn_view._turn_count += 1  # noqa: SLF001 - matches TurnView append protocol.
        turn_view.write(block.render())

    def action_open_palette(self) -> None:
        """Open the slash palette only when the input is empty."""
        textarea = self.query_one("#input-textarea", TextArea)
        if textarea.text.strip():
            textarea.insert("/")
            return
        from .slash_palette import SlashPalette

        registry = getattr(self.app, "slash_registry", None)
        if registry is None:
            return
        try:
            existing = self.app.query_one(SlashPalette)
        except Exception:  # noqa: BLE001
            existing = None
        if existing is not None:
            return
        palette = SlashPalette(registry)
        self.app.mount(palette, before=self)
