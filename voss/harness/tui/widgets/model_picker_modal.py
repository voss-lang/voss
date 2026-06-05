"""ModelPickerModal — OpenCode-style "Select model" picker.

A searchable, provider-grouped modal over the models.dev catalog. Type to
filter, up/down to move (group headers are skipped), enter/click to choose,
esc to cancel. `dismiss(entry)` returns the chosen `ModelEntry` (or None); the
caller (cli `/models`) applies it via the model router.

Design contract: no accent-color literal in this file — all such styling lives
in styles.tcss under `.model-picker-*` / `ModelPickerModal` (the allow-listed
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
        self._header_static: dict[str, Static] = {}
        self._group_label: dict[str, str] = {}

    def _header_text(self, group_id: str, label: str) -> Text:
        mark = "" if self._connected.get(group_id, True) else "   (needs key)"
        return Text(f"{label}{mark}")

    def on_mount(self) -> None:
        for g in self._groups:
            self._group_label[g.id] = g.label
            header_static = Static(self._header_text(g.id, g.label))
            self._header_static[g.id] = header_static
            header = ListItem(header_static, classes="model-picker-group")
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
        # ListView assigns its own default index after mount; set the current
        # model's row once that has settled.
        self.call_after_refresh(self._highlight_current)

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
        self._select_first_visible()

    def _rows(self) -> list[ListItem]:
        return list(self.children)  # type: ignore[return-value]

    def _is_selectable(self, i: int) -> bool:
        rows = self._rows()
        return (
            0 <= i < len(rows)
            and not self._is_header[i]
            and rows[i].display
        )

    def _select_first_visible(self) -> None:
        for i in range(len(self._rows())):
            if self._is_selectable(i):
                self.index = i
                return
        self.index = None

    def _highlight_current(self) -> None:
        for i, entry in enumerate(self._entries):
            if entry is not None and self._is_selectable(i) and self._matches_current(entry):
                self.index = i
                return

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

    def set_connected(self, group_id: str, value: bool) -> None:
        """Update a provider's connected state + refresh its header marker."""
        self._connected[group_id] = value
        static = self._header_static.get(group_id)
        if static is not None:
            static.update(self._header_text(group_id, self._group_label.get(group_id, group_id)))


class ConnectProviderModal(ModalScreen):
    """Prompt for + store a provider API key (keyring). dismiss(key|None)."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, label: str, env_key: str, **kw) -> None:
        super().__init__(**kw)
        self._label = label
        self._env_key = env_key

    def compose(self) -> ComposeResult:
        with Vertical(id="connect-box"):
            yield Static(f"Connect {self._label}", classes="modal-title")
            yield Static(f"Paste your API key ({self._env_key}).", id="connect-help")
            yield Input(password=True, placeholder=self._env_key, id="connect-key")
            yield Static("enter save · esc cancel", id="connect-footer")

    def on_mount(self) -> None:
        self.query_one("#connect-key", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        key = (event.value or "").strip()
        self.dismiss(key or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ModelPickerModal(ModalScreen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("down", "cursor_down", "Down"),
        ("up", "cursor_up", "Up"),
        ("ctrl+a", "connect", "Connect provider"),
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
                "type to filter · up/down move · enter select · "
                "ctrl+a connect · esc cancel",
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

    def action_connect(self) -> None:
        """Connect the highlighted row's provider: prompt for a key, store it,
        and re-activate the group in place."""
        entry = self._list().current_entry()
        if entry is None:
            return
        if entry.env_key is None:
            self.notify("No API key needed for this provider.")
            return
        if self._connected.get(entry.provider_id):
            self.notify(f"{entry.provider_label} is already connected.")
            return

        provider_id = entry.provider_id
        env_key = entry.env_key
        label = entry.provider_label

        def _on_key(key: Optional[str]) -> None:
            if not key:
                return
            from ... import auth

            if not auth.save_provider_key(env_key, key):
                self.notify("Keyring unavailable — couldn't store the key.", severity="error")
                return
            self._connected[provider_id] = True
            self._list().set_connected(provider_id, True)
            self.notify(f"{label} connected.")

        self.app.push_screen(ConnectProviderModal(label, env_key), _on_key)

    def _select_current(self) -> None:
        entry = self._list().current_entry()
        if entry is not None:
            self.dismiss(entry)

    def action_cancel(self) -> None:
        self.dismiss(None)
