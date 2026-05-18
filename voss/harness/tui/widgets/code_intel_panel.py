"""CodeIntelPanel — M9-08 side-region default widget for codebase intelligence landing zone.

Standalone (no imports from voss.harness.code or any M10 backend).
Accepts plain dict/list payloads from M10 later via the three setters.
Renders in three stable modes: idle (tree), results, focused (excerpt).
Uses only existing M9 palette tokens ($accent, $dim) and no new glyphs.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static


class CodeIntelPanel(Vertical):
    """Side-region panel showing project index / search results.

    Default occupant of the side region when no SubAgentPanel is active.
    State is preserved across spawn/gather cycles (M9-08 region-share contract).
    """

    # CSS rules live in styles.tcss (M9 palette tokens $accent / $dim).
    # Widget declares only the class names used by the rules.
    DEFAULT_CSS = """"""

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self._mode: str = "idle"
        self._last_query: str | None = None
        self._body = Vertical(id="intel-body", classes="intel-body")

    def compose(self) -> ComposeResult:
        yield Static("Code Intel", classes="intel-header", id="intel-header")
        yield self._body

    def _clear_body(self) -> None:
        self._body.remove_children()

    def _add_line(self, text: str, *, meta: bool = False, empty: bool = False) -> None:
        cls = "intel-meta" if meta else ("intel-empty" if empty else "intel-line")
        self._body.mount(Static(text, classes=cls, markup=False))

    def set_tree(self, nodes: list[dict[str, Any]] | None = None) -> None:
        self._mode = "idle"
        self._clear_body()
        nodes = nodes or []
        if not nodes:
            self._add_line("No project index yet (run /refresh or start a session)", empty=True)
            return
        self._add_line("Project tree", meta=True)
        for node in nodes[:50]:
            name = node.get("name", "?")
            kind = node.get("kind", "")
            prefix = "📁 " if kind == "dir" else "  "
            self._add_line(f"{prefix}{name}")

    def set_results(self, query: str, hits: list[dict[str, Any]] | None = None) -> None:
        self._mode = "results"
        self._last_query = query
        self._clear_body()
        hits = hits or []
        self._add_line(f"Results for: {query}", meta=True)
        if not hits:
            self._add_line("No matches", empty=True)
            return
        for h in hits[:30]:
            file = h.get("file", "?")
            line = h.get("line", "?")
            name = h.get("name", "")
            tag = h.get("source", "")
            suffix = f"  [{tag}]" if tag else ""
            self._add_line(f"{file}:{line}  {name}{suffix}")

    def set_focus(self, hit: dict[str, Any] | None = None, excerpt_lines: list[str] | None = None) -> None:
        self._mode = "focused"
        self._clear_body()
        hit = hit or {}
        excerpt_lines = excerpt_lines or []
        file = hit.get("file", "?")
        line = hit.get("line", "?")
        self._add_line(f"Focus: {file}:{line}", meta=True)
        if not excerpt_lines:
            self._add_line("No excerpt available", empty=True)
            return
        for i, ln in enumerate(excerpt_lines[:15]):
            self._add_line(f"{i+1:4d}│ {ln[:80]}")
