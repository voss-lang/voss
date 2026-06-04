"""MentionPalette — @-mention file finder anchored above the InputBar.

Ported from OpenCode's @-file autocomplete. Reuses Voss's own slash-palette
plumbing (a mounted ListView routed nav keys from the InputBar) rather than
forking anything: typing `@` opens a fuzzy file picker over the working tree;
selecting inserts the path into the prompt.

`gather_files` and `rank_files` are pure so they can be unit-tested without a
Textual app.
"""
from __future__ import annotations

import os

from textual.message import Message
from textual.widgets import ListItem, ListView, Static


_MAX_RESULTS = 8
_WALK_LIMIT = 4000

# Directories never worth surfacing in a file finder.
_IGNORE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "target",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".voss",
        ".voss-cache",
        ".idea",
        ".vscode",
        ".cursor",
        ".next",
        ".turbo",
    }
)


def gather_files(root: str, *, limit: int = _WALK_LIMIT) -> list[str]:
    """Walk `root` and return repo-relative file paths (POSIX separators).

    Skips dot-directories and known build/vendor dirs; bounded by `limit` so a
    huge tree never stalls the UI. Symlinked dirs are not followed.
    """
    out: list[str] = []
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in _IGNORE_DIRS and not d.startswith(".")
        ]
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            out.append(rel.replace(os.sep, "/"))
            if len(out) >= limit:
                return out
    return out


def rank_files(query: str, paths: list[str], *, limit: int = _MAX_RESULTS) -> list[str]:
    """Rank paths for a query: basename matches first, then full-path matches,
    earlier match position and shorter path winning ties. Empty query returns
    shallow paths alphabetically."""
    if not query:
        return sorted(paths, key=lambda p: (p.count("/"), p.lower()))[:limit]
    q = query.lower()
    scored: list[tuple[int, int, int, str]] = []
    for path in paths:
        low = path.lower()
        base = low.rsplit("/", 1)[-1]
        b = base.find(q)
        if b >= 0:
            scored.append((0, b, len(path), path))
            continue
        f = low.find(q)
        if f >= 0:
            scored.append((1, f, len(path), path))
    scored.sort()
    return [p for *_, p in scored[:limit]]


def find_mention_token(text: str, cursor: int) -> tuple[int, str] | None:
    """If the whitespace-delimited token ending at `cursor` contains a leading
    `@`, return (at_index, query_after_at); else None.

    `cursor` is a flat character offset into `text`.
    """
    if cursor < 0 or cursor > len(text):
        return None
    i = cursor - 1
    while i >= 0 and not text[i].isspace():
        if text[i] == "@":
            return i, text[i + 1 : cursor]
        i -= 1
    return None


class MentionPalette(ListView):
    DEFAULT_CSS = """
    MentionPalette {
        dock: bottom;
        offset-y: -1;
        height: auto;
        max-height: 8;
        border: round $accent;
    }
    """

    BINDINGS = [("escape", "dismiss", "Close file finder")]

    class MentionSubmitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, files: list[str], **kw) -> None:
        super().__init__(**kw)
        self._files = files
        self.query_text = ""
        self._names: list[str] = []

    async def update_query(self, query: str) -> None:
        self.query_text = query
        ranked = rank_files(query, self._files)
        self._names = ranked
        await self.clear()
        if not ranked:
            await self.append(ListItem(Static("no matching files"), disabled=True))
            self.index = None
            return
        for path in ranked:
            item = ListItem(Static(path), name=path)
            item._voss_path = path  # type: ignore[attr-defined]
            await self.append(item)
        self.index = 0

    @staticmethod
    def _path_of(item: ListItem | None) -> str | None:
        return getattr(item, "_voss_path", None)

    def action_select_cursor(self) -> None:
        self._submit_current()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Mouse: clicking a file row inserts it."""
        event.stop()
        self._submit_current(self._path_of(event.item))

    def _submit_current(self, path: str | None = None) -> None:
        if path is None:
            path = self._path_of(self.highlighted_child)
        if path is None:
            if not self._names:
                return
            path = self._names[0]
        self.post_message(self.MentionSubmitted(path))
        self.action_dismiss()

    def action_dismiss(self) -> None:
        try:
            input_bar = self.app.query_one("#input")
            self.remove()
            input_bar.focus()
        except Exception:  # noqa: BLE001
            self.remove()
