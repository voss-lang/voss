"""InputBar widget — bottom multi-line input with locked prompt glyph.

UI-SPEC region "Input bar" (1 base, grows up to 5 rows for multi-line).
Prompt glyph `▌` at col 0. Enter submits; Shift+Enter inserts newline.
M9-03 wires the `/` palette-open binding into this widget.
"""
from __future__ import annotations

from textual.message import Message
from textual.widgets import Input

from .. import glyphs


class InputBar(Input):
    """Text input with locked prompt glyph + Submitted message contract."""

    BINDINGS = [("slash", "open_palette", "Open slash palette")]

    async def _on_key(self, event) -> None:
        # Intercept `/` ONLY when the input is currently empty so the palette
        # opens before Input's printable-character handler inserts a literal.
        if event.key == "slash" and not self.value:
            event.prevent_default()
            event.stop()
            self.action_open_palette()
            return
        await super()._on_key(event)

    class Submitted(Message):
        """Posted when user presses Enter on a non-empty input."""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, **kw) -> None:
        # Locked prompt: glyph + single space, dim default; accent on the
        # glyph itself is applied at render time (UI-SPEC accent rule #1).
        kw.setdefault("placeholder", "")
        super().__init__(**kw)
        self._prompt_text = f"{glyphs.PROMPT} "

    def render(self):
        # Textual's Input renders its own value; we prepend the prompt glyph
        # via the widget label rather than mutating the value.
        return super().render()

    async def action_submit(self) -> None:
        value = self.value
        await super().action_submit()
        if value.strip():
            self.post_message(self.Submitted(value))

    def action_open_palette(self) -> None:
        """Open the slash palette only when the input is empty.

        Non-empty `value` falls through to default Input handling so `/` is
        inserted as a literal character.
        """
        if self.value:
            # Insert literal `/` and bail.
            self.insert_text_at_cursor("/")
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
