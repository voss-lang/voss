"""Core data models for the code intelligence layer.

These are pure data containers returned by the index, LSP adapter,
ast-grep wrapper, and the public service facade. They do not carry
any runtime or third-party library types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class CodeLocation:
    """A precise location inside a source file."""
    file: str          # relative to cwd, normalized, jailed
    line: int          # 1-based
    column: int        # 0-based or 1-based (consistent within a hit)
    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True)
class SymbolHit:
    """A symbol definition or declaration found by index / LSP / ast-grep."""
    name: str
    kind: str                      # function, class, variable, etc.
    location: CodeLocation
    language: str
    source: Literal["index", "lsp", "ast-grep", "regex"] = "index"
    score: float = 1.0


@dataclass(frozen=True)
class ReferenceHit:
    """A reference / usage site for a symbol."""
    location: CodeLocation
    language: str
    source: Literal["index", "lsp", "ast-grep", "regex"] = "lsp"
    context: str | None = None     # optional one-line surrounding context (bounded)


@dataclass(frozen=True)
class SearchHit:
    """Generic structural or text search result."""
    location: CodeLocation
    language: str
    matched_text: str
    source: Literal["ast-grep", "regex"] = "ast-grep"


@dataclass(frozen=True)
class IndexSummary:
    """Compact project overview for system-context injection and TUI."""
    file_count: int
    symbol_count: int
    languages: dict[str, int] = field(default_factory=dict)   # lang -> file count
    top_modules: list[tuple[str, int]] = field(default_factory=list)  # (module, symbol_count)
    entry_points: list[str] = field(default_factory=list)     # detected main / __main__ etc.
    scanned_at: str | None = None
    partial: bool = False   # true if scan is still running / truncated


@dataclass(frozen=True)
class CodeResult:
    """Envelope returned by high-level code-intel operations."""
    kind: Literal["definition", "references", "search", "refresh", "summary"]
    items: list[SymbolHit | ReferenceHit | SearchHit] = field(default_factory=list)
    summary: IndexSummary | None = None
    meta: dict[str, str] = field(default_factory=dict)  # source tags, fallback info, etc.
