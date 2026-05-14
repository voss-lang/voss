"""Convention extraction service: D-09 signal pre-filter + D-10 LLM call + D-11 review UX.

Owned by M8-03 (MEM-04). ConventionCandidate schema and regex constants are
concretely defined here; behavior-bearing functions raise NotImplementedError
until M8-03 lands.
"""
from __future__ import annotations

import asyncio
import re

from pydantic import BaseModel, Field, ValidationError  # noqa: F401  (used by M8-03 validation paths)


_SIGNAL_RE = re.compile(
    r"\b(?:no,?\s*use|always|never|prefer|let'?s|don'?t)\b",
    re.IGNORECASE,
)

DEFAULT_EXTRACTION_TIMEOUT_SECONDS = 8.0


class ConventionCandidate(BaseModel):
    statement: str = Field(..., min_length=1, max_length=500)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_quote: str = Field(..., min_length=1)
    evidence_turn_idx: int = Field(..., ge=0)


def has_signal(turns) -> bool:
    """D-09 pre-filter; True if any user turn matches _SIGNAL_RE OR repeat-edit detection fires on run.changed."""
    raise NotImplementedError("M8-03")


async def extract_conventions(
    history,
    provider,
    model: str,
    *,
    timeout: float = DEFAULT_EXTRACTION_TIMEOUT_SECONDS,
) -> list[ConventionCandidate]:
    """D-10 LLM call wrapped in asyncio.wait_for(timeout); on TimeoutError returns []."""
    raise NotImplementedError("M8-03")


def review_candidates(
    candidates,
    *,
    interactive: bool = True,
    selection: str | None = None,
) -> list[int]:
    """D-11 numbered list UX; returns selected 0-based indices."""
    raise NotImplementedError("M8-03")


def run_on_clean_exit(ctx, *, history, record, memory_store) -> int:
    """End-of-session hook; returns count of conventions persisted. Wraps in try/except; never raises out of REPL exit."""
    raise NotImplementedError("M8-03")


__all__ = [
    "ConventionCandidate",
    "DEFAULT_EXTRACTION_TIMEOUT_SECONDS",
    "_SIGNAL_RE",
    "extract_conventions",
    "has_signal",
    "review_candidates",
    "run_on_clean_exit",
]


# Hint to linters that asyncio is intentionally imported (used by M8-03)
_ = asyncio
