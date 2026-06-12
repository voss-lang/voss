"""CodeIndex: semantic code memory over the M10 lexical index (V19 VSEM-01/02).

Symbol-aware chunks from the M10 SQLite symbols table, a content-hash manifest
for incremental (never-full) reindex, a `voss_code` Chroma collection via the
reused SemanticMemory wrapper, and RRF(BM25+vector) query that degrades to
BM25-only when Chroma is absent.

Consume-not-modify boundary: the M10 db is opened read-only (SELECT only).
All artifacts live under `cwd/.voss-cache/code/` (derived cache — safe to rm).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

from voss.harness.code.index import LANGUAGE_EXTS, _discover_files, _get_db_path
from voss.harness.memory_store import Hit, MemoryStore, _bm25_tokenize
from voss_runtime.memory import SemanticMemory  # noqa: F401  (lazy use in _maybe_semantic)

# MiniLM max_seq_length=256 tokens (~512 chars); 800-char regions sub-split
# so no chunk silently truncates in the embedding window (Pitfall 5).
_MAX_CHUNK_CHARS = 800


def _chunk_id(rel_path: str, seq: int) -> str:
    """D-04 composite id: the `code:` prefix can never collide with turn:/note: ids."""
    return f"code:{rel_path}:{seq:03d}"


def _split_oversize(
    start: int, end: int, lines: list[str], max_chars: int = _MAX_CHUNK_CHARS
) -> list[tuple[int, int, str]]:
    text = "".join(lines[start - 1 : end])
    if len(text) <= max_chars:
        return [(start, end, text)]
    step = max(1, (end - start + 1) // 2)
    mid = start + step
    return _split_oversize(start, mid, lines, max_chars) + _split_oversize(
        mid + 1, end, lines, max_chars
    )


def extract_chunks(db_path: Path, file_path: str, content: str) -> list[tuple[int, int, str]]:
    """(start_line, end_line, chunk_text) regions for one file, split on M10
    symbol boundaries: chunk = [symbol_start, next_symbol_start), preamble
    before the first symbol is its own chunk, zero-symbol files are one
    whole-file chunk (Pitfall 6)."""
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)
    if total_lines == 0:
        return []

    starts: list[int] = []
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                """SELECT s.line FROM symbols s
                   JOIN files f ON s.file_id = f.id
                   WHERE f.path = ? ORDER BY s.line""",
                (file_path,),
            ).fetchall()
        finally:
            conn.close()
        starts = sorted({int(r[0]) for r in rows if r[0] and 1 <= int(r[0]) <= total_lines})
    except sqlite3.Error:
        starts = []  # missing/unreadable M10 db → whole-file chunk

    if not starts:
        return _split_oversize(1, total_lines, lines)

    boundaries = starts + [total_lines + 1]
    chunks: list[tuple[int, int, str]] = []
    for i, start in enumerate(boundaries[:-1]):
        end = boundaries[i + 1] - 1
        chunks.extend(_split_oversize(start, end, lines))
    if starts[0] > 1:
        chunks = _split_oversize(1, starts[0] - 1, lines) + chunks
    return chunks


def _file_hash(content: str) -> str:
    # Identical call to M10 build_index so manifests stay consistent with files.hash.
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()


def _effective_embedding_model() -> str:
    """The model name SemanticMemory._embedding_function would resolve to —
    tracked in the manifest so a model swap drops + rebuilds (Pitfall 1)."""
    from voss_runtime._config import get_config

    cfg = get_config()
    requested = cfg.default_embedding_model
    if requested.startswith("text-embedding-") and not os.environ.get("OPENAI_API_KEY"):
        requested = cfg.local_embedding_model
    return requested


def _manifest_path(cwd: Path) -> Path:
    return cwd / ".voss-cache" / "code" / "semantic-manifest.json"


def _load_manifest(cwd: Path) -> dict:
    path = _manifest_path(cwd)
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_manifest(cwd: Path, data: dict) -> None:
    path = _manifest_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0, sort_keys=True))
