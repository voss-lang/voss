"""MemoryStore: orchestrator over voss_runtime.memory + .voss/memory/ filesystem mirror.

Composition (not subclassing) of voss_runtime types per Req 7 grep gate.
Owned by M8-02 (MEM-03 + MEM-07). Lazy chroma init per Pitfall 4.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from voss_runtime.memory import EpisodicMemory, SemanticMemory, Turn  # noqa: F401  (imported for downstream waves)


SOURCE_QUOTAS = {
    "turns": 0.60,
    "ledgers": 0.20,
    "decisions": 0.10,
    "conventions": 0.10,
}

DEFAULT_CAP_BYTES = 100 * 1024 * 1024


@dataclass
class Hit:
    source: str
    locator: str
    score: float
    excerpt: str
    session_id: str | None = None
    ts: str | None = None


def make_id(source: str, locator: str, seq: int | None = None) -> str:
    """D-04 composite ID format <source>:<locator>:<seq>."""
    raise NotImplementedError("M8-02")


class MemoryStore:
    def __init__(self, cwd: Path, *, cap_bytes: int = DEFAULT_CAP_BYTES) -> None:
        self.cwd = cwd
        self.cap_bytes = cap_bytes
        self.root = cwd / ".voss" / "memory"
        self._chroma: Optional[SemanticMemory] = None
        self._size_cache: dict[str, int] = {}
        self._session_id: Optional[str] = None

    def bind(self, *, session_id: str) -> "MemoryStore":
        """Attach a session id; lazy — does NOT instantiate chroma (Pitfall 4)."""
        raise NotImplementedError("M8-02")

    def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        source: str | None = None,
    ) -> list[Hit]:
        """Hybrid recall: chroma when available, keyword fallback otherwise."""
        raise NotImplementedError("M8-02")

    def forget(self, pattern: str, *, confirm: bool = False) -> int:
        """Tombstone entries matching pattern; returns count."""
        raise NotImplementedError("M8-02")

    def write_turn(
        self,
        *,
        role: str,
        content: str,
        session_id: str,
        turn_idx: int,
    ) -> None:
        raise NotImplementedError("M8-02")

    def write_ledger(self, run, *, session_id: str) -> None:
        raise NotImplementedError("M8-02")

    def write_note(self, text: str, *, session_id: str) -> Path:
        raise NotImplementedError("M8-02")

    def write_convention(self, candidate, *, session_id: str) -> Path:
        raise NotImplementedError("M8-02")

    def vacuum(self) -> int:
        """Compact chroma + delete tombstoned entries; returns bytes reclaimed."""
        raise NotImplementedError("M8-02")

    def summary(self, *, source: str | None = None) -> str:
        raise NotImplementedError("M8-02")
