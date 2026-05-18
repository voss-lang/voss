"""InputBar widget - bottom multi-line input with locked prompt glyph."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, TextArea

from .. import glyphs


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
        self.query_one("#input-textarea", TextArea).load_text(text)

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
        if value.strip():
            self.post_message(self.Submitted(value))

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
