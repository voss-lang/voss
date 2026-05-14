"""VOSS.md file-format owner: parse fenced blocks, inject into system context, migrate legacy architecture.md.

Owned by M8-01 (loader + migration) and M8-05 (cognition rewire). All behavior-bearing
functions raise NotImplementedError until their owning plan lands.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


FENCE_BEGIN = re.compile(r"<!-- voss:begin id=([\w-]+) -->")
FENCE_HASH = re.compile(r"<!-- voss:hash ([0-9a-f]{64}) -->")
FENCE_END = re.compile(r"<!-- voss:end id=([\w-]+) -->")


@dataclass(frozen=True)
class Block:
    kind: str
    id: str | None
    body: str
    recorded_hash: str | None


class HashMismatch(Exception):
    def __init__(self, fence_id: str, *, recorded: str, actual: str, on_disk: str) -> None:
        super().__init__(
            f"VOSS.md fence id={fence_id} hash mismatch: recorded={recorded[:12]}…, "
            f"actual={actual[:12]}…"
        )
        self.fence_id = fence_id
        self.recorded = recorded
        self.actual = actual
        self.on_disk = on_disk


def parse(text: str) -> list[Block]:
    raise NotImplementedError("M8-01")


def read_and_inject(cwd: Path) -> str | None:
    """Return verbatim VOSS.md bytes for D-08 system-context injection; None if file absent (Req 1 silent degradation)."""
    raise NotImplementedError("M8-01")


def ensure_migrated(cwd: Path) -> bool:
    """Idempotent migration of .voss/architecture.md into VOSS.md id=architecture fence; archive byte-identical per Req 2(a) sha256 gate."""
    raise NotImplementedError("M8-01")


def read_fence_body(path: Path, *, fence_id: str) -> str | None:
    """Return fence body text; raises HashMismatch if recorded != computed sha256."""
    raise NotImplementedError("M8-01")


def write_fence_body(path: Path, *, fence_id: str, body: str) -> None:
    """Write body into id=<fence_id>; recompute hash; raises HashMismatch on baseline drift."""
    raise NotImplementedError("M8-01")


def machine_fence_path_or_marker(cwd: Path, *, fence_id: str) -> Path:
    """Return the VOSS.md path used by fence writers (consumed by analyze.py via M8-05)."""
    raise NotImplementedError("M8-01")
