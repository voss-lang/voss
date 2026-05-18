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
from .lsp_registry import LspRegistry
from .models import CodeLocation, ReferenceHit, SearchHit


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

    # --- Lazy registries for semantic operations (M10-04) ---
    def _get_registry(self) -> LspRegistry:
        if not hasattr(self, "_registry") or self._registry is None:
            self._registry = LspRegistry(self.cwd, self.session_id or "default")
        return self._registry

    async def find_definition(
        self, symbol: str, path: str | None = None
    ) -> list[CodeLocation] | dict[str, Any]:
        """Best-effort definition lookup. Uses index + LSP when possible."""
        # For M10-04 minimal, we delegate to LSP registry (which falls back gracefully)
        reg = self._get_registry()
        # Simple heuristic: use workspace symbol first if needed, then definition on first hit.
        # For simplicity, assume caller gives a file:line or we use index.
        # Here we do a basic pass-through to the registry for a placeholder file.
        # In real use, tools will resolve symbol to location first.
        # For now, return unavailable if we can't resolve easily.
        # Better: use index to find candidates, then LSP.
        # Simplified for wave 4:
        return await reg.find_definition("python", f"file://{self.cwd}/dummy.py", 0, 0)  # placeholder until symbol resolution

    async def find_references(
        self, symbol: str, path: str | None = None, max_results: int = 50
    ) -> list[ReferenceHit] | dict[str, Any]:
        reg = self._get_registry()
        return await reg.find_references("python", f"file://{self.cwd}/dummy.py", 0, 0)

    async def code_refresh(self, paths: list[str] | None = None) -> dict[str, Any]:
        """Rebuild the project index (cache only)."""
        try:
            from .index import build_index
            build_index(self.cwd)
            return {"result": "ok", "action": "refreshed", "path": str(self.cwd / ".voss-cache/code/index.db")}
        except Exception as e:
            return {"result": "error", "message": str(e)}
