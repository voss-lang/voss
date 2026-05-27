"""SlashPalette — popup palette anchored above the InputBar.

`rank_commands` factors out the pure ranking logic so it can be unit-tested
without a Textual app fixture. The widget itself is a `ListView` that
filters by query, sorts by substring-position + recency + alphabetical,
and emits a `PaletteSubmitted` message on Enter.
"""
from __future__ import annotations

from textual.message import Message
from textual.widgets import ListItem, ListView, Static

from voss.harness.slash import SlashRegistry
from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES


# `/save` is M8-owned (memory note); the deprecation-alias era from the
# original plan was retired when M8 shipped. The palette still surfaces
# `/save` because it is a live command — bypass the reserved filter.
_PALETTE_KEEP_ALIVE: tuple[str, ...] = ("/save",)

_MAX_RESULTS = 8


def rank_commands(
    query: str,
    names: list[str],
    *,
    recency: list[str] | None = None,
    reserved: tuple[str, ...] = RESERVED_SLASH_NAMES,
    keep_alive: tuple[str, ...] = _PALETTE_KEEP_ALIVE,
) -> list[str]:
    """Rank: substring match, recency, alphabetical. Reserved names excluded
    unless they appear in `keep_alive`."""
    blocked = tuple(n for n in reserved if n not in keep_alive)
    filtered = [n for n in names if n not in blocked]
    if not query:
        recency_hits = [n for n in (recency or []) if n in filtered]
        rest = sorted(n for n in filtered if n not in recency_hits)
        return (recency_hits + rest)[:_MAX_RESULTS]
    q = query.lower().lstrip("/")
    scored: list[tuple[int, str]] = []
    for name in filtered:
        idx = name.lower().lstrip("/").find(q)
        if idx >= 0:
            scored.append((idx, name))
    scored.sort()
    return [n for _, n in scored[:_MAX_RESULTS]]


class SlashPalette(ListView):
    DEFAULT_CSS = """
    SlashPalette {
        dock: bottom;
        offset-y: -1;
        height: auto;
        max-height: 8;
        border: round $accent;
    }
    """

    BINDINGS = [("escape", "dismiss", "Close palette")]

    class PaletteSubmitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, registry: SlashRegistry, **kw) -> None:
        super().__init__(**kw)
        self.registry = registry
        self.query_text = ""
        self.recency: list[str] = []

    async def on_mount(self) -> None:
        self.update_query("")

    def update_query(self, query: str) -> None:
        self.query_text = query
        self._labels: list[str] = []
        self._names: list[str] = []
        # ListView.clear is async; remove children directly so the new
        # appends never collide with stale ids.
        self._nodes._clear()  # type: ignore[attr-defined]
        ranked = rank_commands(query, self.registry.ids(), recency=self.recency)
        if not ranked:
            self.append(ListItem(Static("no matching commands")))
            return
        for name in ranked:
            cmd = self.registry.lookup(name)
            label = f"{name:<16} {cmd.help if cmd else ''}"
            self._labels.append(label)
            self._names.append(name)
            self.append(ListItem(Static(label)))

    def action_select_cursor(self) -> None:
        self._submit_current()

    def _submit_current(self) -> None:
        idx = self.index
        if idx is None or idx >= len(self._names):
            return
        name = self._names[idx]
        self.recency.insert(0, name)
        self.recency = self.recency[:10]
        self.post_message(self.PaletteSubmitted(name))
        self.action_dismiss()

    def action_dismiss(self) -> None:
        # Refocus InputBar before removal so user can keep typing.
        try:
            input_bar = self.app.query_one("#input")
            self.remove()
            input_bar.focus()
        except Exception:  # noqa: BLE001
            self.remove()
