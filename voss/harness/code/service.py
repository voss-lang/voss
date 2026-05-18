"""
CodeIntelService – high level orchestration for search (M10-03 Task 3).

This is the facade that later tools and slash commands will call.
For now it only implements the search path (ast-grep + regex fallback).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ast_grep, regex_fallback
from .index import build_index
from .models import SearchHit


class CodeIntelService:
    def __init__(self, cwd: Path, session_id: str | None = None):
        self.cwd = cwd
        self.session_id = session_id

    @classmethod
    def for_cwd(cls, cwd: Path, session_id: str | None = None, renderer: Any = None) -> "CodeIntelService":
        # Ensure index exists (cheap if already built)
        try:
            build_index(cwd)
        except Exception:
            pass
        return cls(cwd, session_id)

    async def search(
        self,
        pattern: str,
        path: str = ".",
        max_results: int = 50,
    ) -> dict[str, Any]:
        """
        Structural / text search.
        Tries ast-grep first, falls back to regex.
        Returns a source-tagged envelope.
        """
        search_root = (self.cwd / path).resolve()
        if not str(search_root).startswith(str(self.cwd.resolve())):
            return {"result": "error", "message": "path escapes cwd"}

        # Try ast-grep
        ast_result = await ast_grep.search(pattern, search_root, max_results=max_results)

        if isinstance(ast_result, list):
            return {
                "result": "ok",
                "source": "ast-grep",
                "hits": [self._hit_to_dict(h) for h in ast_result],
                "truncated": len(ast_result) >= max_results,
            }

        # Fallback to regex
        regex_result = await regex_fallback.search(pattern, search_root, max_results=max_results)

        if isinstance(regex_result, list):
            return {
                "result": "ok",
                "source": "regex",
                "fallback": "code_search.fallback=regex",
                "hits": [self._hit_to_dict(h) for h in regex_result],
                "truncated": len(regex_result) >= max_results,
            }

        return regex_result or {"result": "error", "message": "search failed"}

    def _hit_to_dict(self, hit: SearchHit) -> dict:
        return {
            "file": hit.location.file,
            "line": hit.location.line,
            "text": hit.matched_text,
            "language": hit.language,
            "source": hit.source,
        }
