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


IMAGE_INDICATOR = "[image attached · 1 image]"
NO_VISION_NOTICE = "current model has no vision — image not attached"


def _build_corpus(history) -> list[str]:
    if history is None:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for turn in reversed(getattr(history, "turns", [])):
        if getattr(turn, "role", None) != "user":
            continue
        content = str(getattr(turn, "content", ""))
        if not content or content in seen:
            continue
        seen.add(content)
        out.append(content)
    return out


def _read_clipboard_image():
    from PIL import Image, ImageGrab

    result = ImageGrab.grabclipboard()
    if isinstance(result, Image.Image):
        return result
    return None


def _probe_clipboard_image():
    try:
        return _read_clipboard_image()
    except (ImportError, NotImplementedError, ChildProcessError, OSError):
        return None


def _model_supports_vision(model_name: str) -> bool:
    # [ASSUMED] No provider capability API exists; T8 gates by known model prefixes.
    name = (model_name or "").lower()
    return name.startswith(("claude-3", "claude-opus", "gpt-4o", "gpt-4-vision", "gemini"))


class _InputTextArea(TextArea):
    """TextArea child with M9 main-context collisions stripped.

    Intercepts Enter/Shift+Enter/slash/Ctrl+R and delegates to the parent
    InputBar. This is necessary because clicking the TextArea gives it focus
    directly, bypassing InputBar's _on_key handler.
    """

    BINDINGS = [
        binding
        for binding in TextArea.BINDINGS
        if binding.key not in {"ctrl+f", "ctrl+u"}
    ]

    async def _on_key(self, event) -> None:
        bar = self.parent
        if bar is None or not isinstance(bar, InputBar):
            await super()._on_key(event)
            return
        # Delegate special keys to InputBar.
        if event.key == "ctrl+r":
            event.prevent_default()
            event.stop()
            bar.action_reverse_search()
            return
        if getattr(bar, "_search_mode", False):
            # Reverse-search mode — let InputBar handle all keys.
            event.prevent_default()
            event.stop()
            await bar._on_key(event)
            return
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            await bar.action_submit()
            return
        if event.key == "shift+enter":
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return
        await super()._on_key(event)


class InputBar(Widget):
    """TextArea-backed input with locked prompt glyph + Submitted contract."""

    DEFAULT_CSS = """
    InputBar {
        layout: horizontal;
        height: auto;
        min-height: 3;
        max-height: 8;
        margin: 0 1;
        padding: 0;
        border: solid #ff5b1f;
        background: transparent;
    }

    InputBar:focus {
        border-top: solid #ff5b1f;
    }

    InputBar > #prompt-glyph {
        width: 3;
        height: auto;
        content-align: center top;
        text-style: bold;
        padding-top: 0;
    }

    InputBar:focus > #prompt-glyph {
        background: #ff5b1f 15%;
    }

    InputBar > #input-textarea {
        height: auto;
        min-height: 1;
        max-height: 6;
        border: none;
        padding: 0 1 0 0;
        background: transparent;
    }

    InputBar > #input-textarea:focus {
        border: none;
    }

    InputBar > #input-textarea .text-area--cursor {
        background: #ff5b1f;
        text-style: none;
    }

    InputBar > #input-textarea .text-area--cursor-line {
        background: transparent;
    }
    """

    BINDINGS = [
        ("ctrl+r", "reverse_search", "Reverse-search input history"),
    ]
    can_focus = True

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._prompt_text = f"{glyphs.PROMPT} "
        self._search_mode = False
        self._search_query = ""
        self._search_saved_text = ""
        self._search_matches: list[str] = []
        self._search_idx = 0
        self._search_corpus: list[str] = []
        self._pending_image = None

    def compose(self) -> ComposeResult:
        yield Static(self._prompt_text, id="prompt-glyph", classes="accent")
        yield _InputTextArea(
            "",
            id="input-textarea",
            show_line_numbers=False,
            soft_wrap=True,
            tooltip=(
                "Enter submits · Shift+Enter newline · / commands · Ctrl-R history"
            ),
        )

    @property
    def text(self) -> str:
        return self.query_one("#input-textarea", _InputTextArea).text

    @property
    def search_mode(self) -> bool:
        return self._search_mode

    def load_text(self, text: str) -> None:
        textarea = self.query_one("#input-textarea", _InputTextArea)
        textarea.load_text(text)
        lines = text.split("\n")
        textarea.move_cursor((len(lines) - 1, len(lines[-1])))

    def insert(self, text: str) -> None:
        self.query_one("#input-textarea", _InputTextArea).insert(text)

    async def _on_key(self, event) -> None:
        textarea = self.query_one("#input-textarea", _InputTextArea)
        if event.key == "ctrl+r":
            event.prevent_default()
            event.stop()
            self.action_reverse_search()
            return
        if self._search_mode:
            event.prevent_default()
            event.stop()
            if event.key == "enter":
                self._accept_reverse_search()
            elif event.key == "escape":
                self._exit_reverse_search(restore=True)
            elif event.key in {"backspace", "ctrl+h"}:
                self._search_query = self._search_query[:-1]
                self._refresh_reverse_search()
            else:
                char = getattr(event, "character", None)
                if char is None and len(event.key) == 1:
                    char = event.key
                if char and char.isprintable():
                    self._search_query += char
                    self._refresh_reverse_search()
            return
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
        await textarea._on_key(event)  # noqa: SLF001 - delegate editing to child TextArea.

    class Submitted(Message):
        """Posted when user presses Enter on a non-empty input."""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    async def action_submit(self) -> None:
        value = self.text
        self.load_text("")
        pending_image = self._pending_image
        self._pending_image = None
        stripped = value.strip()
        if pending_image is not None and stripped == IMAGE_INDICATOR:
            return
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

    async def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area is not self.query_one("#input-textarea", _InputTextArea):
            return
        await self._sync_slash_palette()
        event.text_area.focus()

    async def _sync_slash_palette(self) -> None:
        from .slash_palette import SlashPalette

        try:
            existing = self.app.query_one(SlashPalette)
        except Exception:  # noqa: BLE001
            existing = None

        text = self.text
        if not text.startswith("/"):
            if existing is not None:
                existing.remove()
            return

        registry = getattr(self.app, "slash_registry", None)
        if registry is None:
            return
        palette = existing
        if palette is None:
            palette = SlashPalette(registry)
            await self.app.mount(palette, before=self)
        palette.update_query(text)

    def action_reverse_search(self) -> None:
        if not self._search_mode:
            self._search_mode = True
            self._search_query = ""
            self._search_saved_text = self.text
            self._search_corpus = _build_corpus(getattr(self.app, "history", None))
            self._search_idx = 0
            self.query_one("#input-textarea", _InputTextArea).read_only = True
            self._refresh_reverse_search()
            return
        if self._search_matches and self._search_idx < len(self._search_matches) - 1:
            self._search_idx += 1
        else:
            self._search_idx = len(self._search_matches)
        self._render_reverse_search()

    def _refresh_reverse_search(self) -> None:
        query = self._search_query.lower()
        self._search_matches = [
            item for item in self._search_corpus if query in item.lower()
        ]
        self._search_idx = 0
        self._render_reverse_search()

    def _render_reverse_search(self) -> None:
        if self._search_matches and self._search_idx < len(self._search_matches):
            match = self._search_matches[self._search_idx]
        else:
            match = "(no match)"
        self.load_text(f"{glyphs.PROMPT} (reverse-i-search)`{self._search_query}': {match}")

    def _accept_reverse_search(self) -> None:
        match = (
            self._search_matches[self._search_idx]
            if self._search_matches and self._search_idx < len(self._search_matches)
            else ""
        )
        self._exit_reverse_search(restore=False)
        self.load_text(match)

    def _exit_reverse_search(self, *, restore: bool) -> None:
        self._search_mode = False
        self.query_one("#input-textarea", _InputTextArea).read_only = False
        self.load_text(self._search_saved_text if restore else "")

    async def action_paste(self) -> None:
        image = _probe_clipboard_image()
        if image is None:
            textarea = self.query_one("#input-textarea", _InputTextArea)
            action = getattr(textarea, "action_paste", None)
            if action is not None:
                result = action()
                if asyncio.iscoroutine(result):
                    await result
            return
        if _model_supports_vision(getattr(self.app, "model", "")):
            self._pending_image = image
            self.load_text(IMAGE_INDICATOR)
            return
        self._pending_image = None
        handler = getattr(self.app, "on_local_event", None)
        if handler is not None:
            handler("notice", {"message": NO_VISION_NOTICE})

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
        """Insert slash text so TextArea.Changed owns palette sync."""
        textarea = self.query_one("#input-textarea", _InputTextArea)
        textarea.insert("/")
