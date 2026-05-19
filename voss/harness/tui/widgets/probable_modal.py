"""Read-only probable decision inspector modal (M11-05)."""
from __future__ import annotations

import re
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from .confidence_bar import ConfidenceBar


_CONFIDENCE_RE = re.compile(r"^confidence:\s*([0-9]*\.?[0-9]+)\s*$", re.MULTILINE)


class ProbableInspectModal(ModalScreen):
    """Display a recorded probable decision sequence without actions."""

    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def __init__(
        self,
        text: str,
        confidence: float | None = None,
        title: str = "Probable decision",
        **kw: Any,
    ) -> None:
        super().__init__(**kw)
        self.text = text
        self.confidence = _confidence_value(confidence, text)
        self.title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="probable-body"):
            yield Static(self.title, id="probable-title", classes="modal-title")
            yield Static("")
            yield ConfidenceBar(
                value=self.confidence,
                is_final=True,
                id="probable-confidence",
            )
            yield Static("")
            yield Static(self.text, id="probable-sequence")
            yield Static("")
            yield Static("Press Esc to close", id="probable-footer")


def _confidence_value(confidence: float | None, text: str) -> float:
    if confidence is not None:
        return confidence
    match = _CONFIDENCE_RE.search(text)
    if match is None:
        return 0.0
    try:
        return float(match.group(1))
    except ValueError:
        return 0.0
