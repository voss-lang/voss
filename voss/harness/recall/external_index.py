"""External-source recall index skeleton.

Mirrors code/semantic_index.py with heading-boundary markdown chunking and
per-source isolation under .voss-cache/recall/<name>/.
"""
from __future__ import annotations

from pathlib import Path

from voss.harness.code.semantic_index import _split_oversize, _file_hash, _effective_embedding_model
from voss.harness.memory_store import Hit, MemoryStore, _bm25_tokenize


def extract_md_chunks(content: str) -> list[tuple[int, int, str]]:
    raise NotImplementedError("V22-02/03")


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
