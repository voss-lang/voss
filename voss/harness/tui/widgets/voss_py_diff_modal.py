"""Read-only `.voss` source vs generated Python modal (M11-05)."""
from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


class VossPyDiffModal(ModalScreen):
    """Display source and generated Python without apply actions."""

    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def __init__(
        self,
        text: str,
        *,
        source_text: str | None = None,
        generated_text: str | None = None,
        title: str = "Voss source vs generated Python",
        **kw: Any,
    ) -> None:
        super().__init__(**kw)
        self.text = text
        self.source_text = source_text
        self.generated_text = generated_text
        self.title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="voss-py-diff-body"):
            yield Static(self.title, id="voss-py-diff-title", classes="modal-title")
            yield Static("")
            if self.source_text is not None and self.generated_text is not None:
                with Horizontal(id="voss-py-diff-panes"):
                    with Vertical(id="voss-py-diff-source-pane"):
                        yield Static("Voss source", id="voss-py-diff-source-title")
                        yield Static(self.source_text, id="voss-py-diff-source")
                    with Vertical(id="voss-py-diff-generated-pane"):
                        yield Static(
                            "Generated Python",
                            id="voss-py-diff-generated-title",
                        )
                        yield Static(
                            self.generated_text,
                            id="voss-py-diff-generated",
                        )
            else:
                yield Static(self.text, id="voss-py-diff-stacked")
            yield Static("")
            yield Static("Press Esc to close", id="voss-py-diff-footer")
