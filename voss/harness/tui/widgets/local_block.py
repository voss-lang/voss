"""Local-only TUI blocks for input-bar shortcut results."""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class LocalBlock(Static):
    """Base class for local blocks that never enter model history."""

    DEFAULT_CLASSES = "local-block"

    def __init__(self, text: Text, **kw) -> None:
        super().__init__("", **kw)
        self._text = text

    def render(self) -> Text:
        return self._text


class LocalBlockShell(LocalBlock):
    """Render a `!cmd` local shell result."""

    def __init__(
        self,
        cmd: str,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        **kw,
    ) -> None:
        text = Text()
        text.append("! ", style="bold")
        text.append(cmd)
        body = "\n".join(part for part in (stdout.rstrip(), stderr.rstrip()) if part)
        if body:
            text.append("\n")
            text.append(body)
        text.append("\n")
        text.append(f"· exit {exit_code}", style="signal-good" if exit_code == 0 else "signal-error")
        super().__init__(text, classes="local-block local-block--shell", **kw)


class LocalBlockNote(LocalBlock):
    """Render the `#note` saved confirmation."""

    def __init__(self, **kw) -> None:
        text = Text("# note saved", style="dim")
        super().__init__(text, classes="local-block local-block--note", **kw)


class LocalBlockNotice(LocalBlock):
    """Render a transient local warning notice."""

    def __init__(self, message: str, **kw) -> None:
        text = Text(message, style="signal-warn")
        super().__init__(text, classes="local-block local-block--notice", **kw)
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_timer(3.0, self.remove)

    def dismiss(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.remove()
