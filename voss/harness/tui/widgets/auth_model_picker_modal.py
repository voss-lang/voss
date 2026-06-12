"""AuthModelPickerModal — Claude-CLI-style `/model` picker (R8).

A small numbered picker over the curated subscription model list
(`subscription_models.SUBSCRIPTION_MODELS`) for the ACTIVE auth — Claude
subscription (Agent SDK) or Codex (ChatGPT backend). Unlike the searchable
catalog ModelPickerModal (`/models`, API-key providers), rows here are a
fixed handful: number keys 1-9 quick-pick, j/k/arrows + enter select, esc
cancels. `dismiss(model)` returns the chosen `SubscriptionModel` (or None);
the caller (cli `/model`) applies + persists it.

Design contract: no accent-color literal in this file — styling lives in
styles.tcss under `AuthModelPickerModal` (declaration site). The current
marker uses `glyphs.CHECK` (R8 allow-list addition) so --no-unicode holds.
"""
from __future__ import annotations

from typing import Optional, Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import ListItem, ListView, Static

from ...subscription_models import SubscriptionModel
from .. import glyphs


class AuthModelPickerModal(ModalScreen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("down", "cursor_down", "Down"),
        ("up", "cursor_up", "Up"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("enter", "select", "Select"),
    ]

    def __init__(
        self,
        models: Sequence[SubscriptionModel],
        current: str,
        *,
        subtitle: str = "",
        **kw,
    ) -> None:
        super().__init__(**kw)
        self._models = list(models)
        self._current = current
        self._subtitle = subtitle

    def _row_text(self, index: int, m: SubscriptionModel) -> Text:
        t = Text()
        t.append(f"{index + 1}. ", style="dim")
        t.append(m.label, style="bold" if m.recommended else "")
        if m.id == self._current:
            t.append(f" {glyphs.CHECK}", style="bold")
        t.append(f"  {m.id} · {m.description}", style="dim")
        return t

    def compose(self) -> ComposeResult:
        with Vertical(id="auth-picker-box"):
            yield Static("Select model", id="auth-picker-title", classes="modal-title")
            if self._subtitle:
                yield Static(self._subtitle, id="auth-picker-subtitle")
            yield ListView(
                *(
                    ListItem(
                        Static(self._row_text(i, m)),
                        classes="auth-model-row",
                    )
                    for i, m in enumerate(self._models)
                ),
                id="auth-picker-list",
            )
            yield Static(
                "1-9 quick pick · j/k or up/down move · enter select · esc cancel",
                id="auth-picker-footer",
            )

    def on_mount(self) -> None:
        self.query_one("#auth-picker-list", ListView).focus()
        # ListView assigns its own default index after mount; set the current
        # model's row once that has settled (same dance as ModelPickerModal).
        self.call_after_refresh(self._highlight_current)

    def _highlight_current(self) -> None:
        for i, m in enumerate(self._models):
            if m.id == self._current:
                self._list().index = i
                return

    def _list(self) -> ListView:
        return self.query_one("#auth-picker-list", ListView)

    def on_key(self, event) -> None:
        # 1-9 quick-pick (rows are at most a handful; no 10+ paging).
        if event.key in "123456789":
            i = int(event.key) - 1
            if i < len(self._models):
                event.stop()
                self.dismiss(self._models[i])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Mouse click / enter on a row.
        self._dismiss_index(self._list().index)

    def action_cursor_down(self) -> None:
        lst = self._list()
        i = lst.index if lst.index is not None else -1
        lst.index = min(i + 1, len(self._models) - 1)

    def action_cursor_up(self) -> None:
        lst = self._list()
        i = lst.index if lst.index is not None else 1
        lst.index = max(i - 1, 0)

    def action_select(self) -> None:
        self._dismiss_index(self._list().index)

    def _dismiss_index(self, index: Optional[int]) -> None:
        if index is not None and 0 <= index < len(self._models):
            self.dismiss(self._models[index])

    def action_cancel(self) -> None:
        self.dismiss(None)
