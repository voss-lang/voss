"""ModelPickerModal — OpenCode-style "Select model" picker.

A searchable, provider-grouped modal over the models.dev catalog. Type to
filter, up/down to move (group headers are skipped), enter/click to choose,
esc to cancel. `dismiss(entry)` returns the chosen `ModelEntry` (or None); the
caller (cli `/models`) applies it via the model router.

Design contract: NO accent literal here — all `$accent` styling lives in
styles.tcss under `.model-picker-*` / `ModelPickerModal` (the allow-listed
site), so the accent audit stays clean. Tags/markers are ASCII so the
--no-unicode contract holds.

Connect-provider (ctrl+a) and favorites (ctrl+f) land in P5; this ship is the
searchable grouped picker + selection.
"""
from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static

from ...model_catalog import ModelEntry, ProviderGroup
from ... import model_router


def _row_text(entry: ModelEntry) -> Text:
    """`model-id` with a trailing dim tag (Free / context), ASCII-safe."""
    t = Text(entry.id)
    if entry.free:
        t.append("  · Free", style="dim")
    elif entry.context:
        t.append(f"  · {entry.context // 1000}k", style="dim")
    return t


class _PickerList(ListView):
    """ListView of interleaved group headers (skipped) + model rows."""

    def __init__(self, groups: list[ProviderGroup], connected: dict[str, bool],
                 current: str, **kw) -> None:
        super().__init__(**kw)
        self._groups = groups
        self._connected = connected
        self._current = current
        # Parallel arrays describing every appended item.
        self._is_header: list[bool] = []
        self._entries: list[Optional[ModelEntry]] = []
        self._group_of: list[str] = []

    def on_mount(self) -> None:
        for g in self._groups:
            mark = "" if self._connected.get(g.id, True) else "   (needs key)"
            header = ListItem(Static(Text(f"{g.label}{mark}")), classes="model-picker-group")
            header.disabled = True
            self.append(header)
            self._is_header.append(True)
            self._entries.append(None)
            self._group_of.append(g.id)
            for m in g.models:
                item = ListItem(Static(_row_text(m)), classes="model-picker-row")
                item._voss_entry = m  # type: ignore[attr-defined]
                self.append(item)
                self._is_header.append(False)
                self._entries.append(m)
                self._group_of.append(g.id)
        self.filter("")

    # -- filtering -------------------------------------------------------
    def filter(self, query: str) -> None:
        q = query.strip().lower()
        matched = {
            id(m)
            for m in model_router.match_models(self._groups, q)
        }
        # rows visible if matched; headers visible if any child row visible
        group_has_visible: dict[str, bool] = {}
        for i, entry in enumerate(self._entries):
            if entry is None:
                continue
            vis = (not q) or id(entry) in matched
            self._rows()[i].display = vis
            self._rows()[i].disabled = not vis
            if vis:
                group_has_visible[self._group_of[i]] = True
        for i, is_h in enumerate(self._is_header):
            if is_h:
                self._rows()[i].display = group_has_visible.get(self._group_of[i], False)
        self._select_first_visible(prefer_current=True)

    def _rows(self) -> list[ListItem]:
        return list(self.children)  # type: ignore[return-value]

    def _is_selectable(self, i: int) -> bool:
        rows = self._rows()
        return (
            0 <= i < len(rows)
            and not self._is_header[i]
            and rows[i].display
        )

    def _select_first_visible(self, *, prefer_current: bool) -> None:
        if prefer_current:
            for i, entry in enumerate(self._entries):
                if entry is not None and self._is_selectable(i) and self._matches_current(entry):
                    self.index = i
                    return
        for i in range(len(self._rows())):
            if self._is_selectable(i):
                self.index = i
                return
        self.index = None

    def _matches_current(self, entry: ModelEntry) -> bool:
        return entry.id == self._current or f"openai/{entry.id}" == self._current

    # -- header-skipping cursor movement --------------------------------
    def move(self, delta: int) -> None:
        rows = self._rows()
        if not rows:
            return
        i = self.index if self.index is not None else -1
        i += delta
        while 0 <= i < len(rows) and not self._is_selectable(i):
            i += delta
        if self._is_selectable(i):
            self.index = i

    def current_entry(self) -> Optional[ModelEntry]:
        child = self.highlighted_child
        return getattr(child, "_voss_entry", None) if child is not None else None


class ModelPickerModal(ModalScreen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("down", "cursor_down", "Down"),
        ("up", "cursor_up", "Up"),
    ]

    def __init__(
        self,
        groups: list[ProviderGroup],
        connected: dict[str, bool],
        current: str,
        **kw,
    ) -> None:
        super().__init__(**kw)
        self._groups = groups
        self._connected = connected
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-box"):
            yield Static("Select model", id="picker-title", classes="modal-title")
            yield Input(placeholder="Search", id="picker-search")
            yield _PickerList(self._groups, self._connected, self._current, id="picker-list")
            yield Static(
                "type to filter · up/down move · enter select · esc cancel",
                id="picker-footer",
            )

    def on_mount(self) -> None:
        self.query_one("#picker-search", Input).focus()

    def _list(self) -> _PickerList:
        return self.query_one("#picker-list", _PickerList)

    def on_input_changed(self, event: Input.Changed) -> None:
        self._list().filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._select_current()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Mouse click / enter on a row.
        entry = getattr(event.item, "_voss_entry", None)
        if entry is not None:
            self.dismiss(entry)

    def action_cursor_down(self) -> None:
        self._list().move(1)

    def action_cursor_up(self) -> None:
        self._list().move(-1)

    def _select_current(self) -> None:
        entry = self._list().current_entry()
        if entry is not None:
            self.dismiss(entry)

    def action_cancel(self) -> None:
        self.dismiss(None)
