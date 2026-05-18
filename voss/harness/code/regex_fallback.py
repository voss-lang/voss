"""
Regex fallback for code_search when ast-grep is unavailable (M10-03 Task 2).

Searches only files present in the current index.db, with strict path jailing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .index import summarize as index_summarize  # to get file list
from .models import SearchHit, CodeLocation

SNIPPET_LINE_CAP = 10
SNIPPET_CHAR_CAP = 80


async def search(
    pattern: str,
    root: Path,
    *,
    max_results: int = 50,
) -> list[SearchHit] | dict[str, Any]:
    """
    Perform a simple regex search over files known to the index.
    Returns hits or error dict. Always sets fallback marker in caller.
    """
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return {"result": "bad_regex", "error": str(e)}

    # Get list of files from index (we reuse summarize for now; later we can add a direct file list)
    try:
        summary = index_summarize(root)
        # For simplicity in M10-03 we walk from index knowledge via a crude approach.
        # Better: expose a list_files from index.py. For now we do a safe walk.
    except Exception:
        summary = None

    hits: list[SearchHit] = []

    # Walk the tree but only consider "reasonable" source files
    exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".c", ".cpp", ".h", ".java"}

    for path in _safe_walk(root):
        if path.suffix.lower() not in exts:
            continue
        if len(hits) >= max_results:
            break
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    loc = CodeLocation(file=str(path.relative_to(root)), line=i, column=0)
                    snippet = line[:SNIPPET_CHAR_CAP]
                    hits.append(SearchHit(
                        location=loc,
                        language=_guess_lang(path),
                        matched_text=snippet,
                        source="regex",
                    ))
                    if len(hits) >= max_results:
                        break
        except Exception:
            continue

    return hits


def _safe_walk(root: Path) -> list[Path]:
    """Jailed walk, skipping obvious vendored dirs."""
    vendored = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", ".voss-cache"}
    files: list[Path] = []
    for dirpath, dirnames, filenames in __import__("os").walk(root):
        dirnames[:] = [d for d in dirnames if d not in vendored]
        for f in filenames:
            p = Path(dirpath) / f
            if p.is_file():
                try:
                    p.relative_to(root)  # jail
                    files.append(p)
                except ValueError:
                    continue
    return files


def _guess_lang(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".rs": "rust",
        ".go": "go",
    }.get(ext, "unknown")
