"""Clock abstraction + async tick loop for Board (O3 OBRD-09).

Two clock forms supported:
  (a) Callable[[], float] — the auth.py:423 convention.
  (b) Clock Protocol — for tests that want clock.advance(dt) ergonomics.
FakeClock satisfies BOTH (callable + .now()/.advance()).
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float: ...


class MonotonicClock:
    """Default production clock — wraps time.monotonic()."""
    def __call__(self) -> float:
        return time.monotonic()

    def now(self) -> float:
        return time.monotonic()


@dataclass
class FakeClock:
    """Test clock — manually advanced via advance(dt). Satisfies both
    Callable[[], float] and Clock Protocol."""
    _t: float = 0.0

    def __call__(self) -> float:
        return self._t

    def now(self) -> float:
        return self._t

    def advance(self, dt: float) -> None:
        self._t += dt


async def _tick_loop(board: object, clock: object, interval_s: float) -> None:
    """Async tick loop. ONE production path. Cancellation via CancelledError.

    board is opaquely typed to avoid machine→tick→machine import cycle;
    it must expose `_tick_once(now: float) -> None`.
    """
    while True:
        now_val = clock.now() if hasattr(clock, "now") else clock()  # type: ignore[operator]
        board._tick_once(now_val)  # type: ignore[attr-defined]
        await asyncio.sleep(interval_s)
