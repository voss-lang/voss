"""External-source recall index skeleton.

Mirrors code/semantic_index.py with heading-boundary markdown chunking and
per-source isolation under .voss-cache/recall/<name>/.
"""
from __future__ import annotations

import re
from pathlib import Path

from voss.harness.code.semantic_index import _split_oversize, _file_hash, _effective_embedding_model
from voss.harness.memory_store import Hit, MemoryStore, _bm25_tokenize

_MD_SUFFIXES = {".md", ".markdown"}
_ATX_HEADING = re.compile(r"^(#{1,6})\s")
_FENCE_START = re.compile(r"^\s*(?:```|~~~)")


def extract_md_chunks(content: str) -> list[tuple[int, int, str]]:
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)
    if total_lines == 0:
        return []

    headings: list[tuple[int, int]] = []
    in_fence = False
    for idx, line in enumerate(lines, start=1):
        if _FENCE_START.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _ATX_HEADING.match(line)
        if match:
            headings.append((idx, len(match.group(1))))

    if not headings:
        return _split_oversize(1, total_lines, lines)

    chunks: list[tuple[int, int, str]] = []
    first_heading_line = headings[0][0]
    if first_heading_line > 1:
        chunks.extend(_split_oversize(1, first_heading_line - 1, lines))

    for pos, (start, level) in enumerate(headings):
        end = total_lines
        for next_start, next_level in headings[pos + 1 :]:
            if next_level <= level:
                end = next_start - 1
                break
        chunks.extend(_split_oversize(start, end, lines))
    return chunks


class ExternalSourceIndex:
    def __init__(self, cwd: Path, source: dict) -> None:
        raise NotImplementedError("V22-02/03")

    def build(self) -> None:
        raise NotImplementedError("V22-02/03")

    def query(self, query: str, top_k: int = 5) -> list[Hit]:
        raise NotImplementedError("V22-02/03")

    def _bm25_query(self, query: str, top_k: int) -> list[Hit]:
        raise NotImplementedError("V22-02/03")


class ExternalRecallService:
    def __init__(self, cwd: Path, session_id: str | None = None) -> None:
        raise NotImplementedError("V22-02/03")

    def ensure_background_build(self) -> None:
        raise NotImplementedError("V22-02/03")

    def is_ready(self) -> bool:
        raise NotImplementedError("V22-02/03")

    def build_all(self) -> None:
        raise NotImplementedError("V22-02/03")

    def query_all(self, query: str, top_k: int = 5) -> list[list[Hit]]:
        raise NotImplementedError("V22-02/03")
