"""Per-tool token-bucket rate limiting. Pure stdlib. T3-04 / NET-07.

Tests monkeypatch ``voss.harness.rate_limit.time.monotonic`` for
deterministic clocks (RESEARCH Pitfall 7). NetSession (T3-05) owns the
per-tool registry; this module owns the primitive only.

Acquire is fail-fast: on a missed token we return (False, retry_after_s)
and never sleep. The caller (NetSession in T3-05) surfaces a
``<error: rate limit: retry after Ns>`` envelope to the agent loop.
"""

from __future__ import annotations

import time
import warnings  # noqa: F401  (reserved for future warning paths)
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    rate_per_min: int
    burst: int
    _tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        if self.rate_per_min <= 0:
            raise ValueError("rate_per_min must be positive")
        if self.burst <= 0:
            raise ValueError("burst must be positive")
        self._tokens = float(self.burst)
        self._last = time.monotonic()

    def acquire(self) -> tuple[bool, float]:
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(float(self.burst), self._tokens + elapsed * (self.rate_per_min / 60.0))
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True, 0.0
        retry_after = (1.0 - self._tokens) / (self.rate_per_min / 60.0)
        return False, retry_after


DEFAULT_SPECS = {
    "web_fetch": (30, 30),  # NET-07 SPEC
    "web_search": (10, 10),  # NET-07 SPEC
}  # type: dict[str, tuple[int, int]]


def make_default_bucket(tool_name: str) -> TokenBucket:
    """Construct a fresh TokenBucket with SPEC defaults for ``tool_name``.

    Returns a NEW bucket on every call so each NetSession owns its own
    registry per RESEARCH Pitfall 7. Raises ``KeyError`` if the tool is
    not in ``DEFAULT_SPECS`` — callers enumerate the keys they care
    about (T3-05's NetSession constructor).
    """
    rate, burst = DEFAULT_SPECS[tool_name]
    return TokenBucket(rate_per_min=rate, burst=burst)
