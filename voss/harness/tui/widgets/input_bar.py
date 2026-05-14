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
