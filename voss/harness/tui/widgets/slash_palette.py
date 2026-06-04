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
        self._labels: list[str] = []
        self._names: list[str] = []
        self._items_by_name: dict[str, ListItem] = {}
        self._labels_by_name: dict[str, str] = {}
        self._empty_item: ListItem | None = None

    async def on_mount(self) -> None:
        self.update_query("")

    def update_query(self, query: str) -> None:
        self.query_text = query
        self._ensure_items()
        ranked = rank_commands(query, self.registry.ids(), recency=self.recency)
        visible = set(ranked)
        self._names = ranked
        self._labels = [self._labels_by_name[name] for name in ranked]

        for name, item in self._items_by_name.items():
            is_visible = name in visible
            item.display = is_visible
            item.disabled = not is_visible

        if not ranked:
            if self._empty_item is not None:
                self._empty_item.display = True
            self.index = None
            return

        if self._empty_item is not None:
            self._empty_item.display = False
        self._reconcile_index(ranked)

    def _ensure_items(self) -> None:
        for name in self.registry.ids():
            if name in self._items_by_name:
                continue
            cmd = self.registry.lookup(name)
            label = f"{name:<16} {cmd.help if cmd else ''}"
            item = ListItem(Static(label), name=name)
            item.display = False
            item.disabled = True
            item._voss_command_name = name  # type: ignore[attr-defined]
            self._items_by_name[name] = item
            self._labels_by_name[name] = label
            self.append(item)

        if self._empty_item is None:
            self._empty_item = ListItem(Static("no matching commands"), disabled=True)
            self._empty_item.display = False
            self.append(self._empty_item)

    def _reconcile_index(self, ranked: list[str]) -> None:
        current = self.highlighted_child
        if current is not None and self._command_name(current) in ranked:
            return
        first = self._items_by_name.get(ranked[0])
        self.index = self._index_of(first)

    def _index_of(self, item: ListItem | None) -> int | None:
        if item is None:
            return None
        try:
            return list(self._nodes).index(item)
        except ValueError:
            return None

    @staticmethod
    def _command_name(item: ListItem | None) -> str | None:
        return getattr(item, "_voss_command_name", None)

    def action_select_cursor(self) -> None:
        self._submit_current()

    def _submit_current(self) -> None:
        item = self.highlighted_child
        name = self._command_name(item)
        if name not in self._names:
            if not self._names:
                return
            item = self._items_by_name.get(self._names[0])
            name = self._command_name(item)
            self.index = self._index_of(item)
        if name not in self._names:
            return
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
