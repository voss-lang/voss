from __future__ import annotations
import asyncio, time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional
from .exceptions import BudgetExceededError

_current_budget: ContextVar[Optional["BudgetScope"]] = ContextVar("_current_budget", default=None)


@dataclass
class BudgetScope:
    token_limit: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    name: str = ""
    tokens_so_far: int = 0
    cost_so_far: float = 0.0
    _start: Optional[float] = field(default=None, init=False, repr=False)
    _token: Optional[object] = field(default=None, init=False, repr=False)

    async def __aenter__(self):
        if self.token_limit is None and self.latency_ms is None and self.cost_usd is None:
            raise ValueError("BudgetScope requires at least one of token_limit, latency_ms, cost_usd")
        self._start = time.perf_counter()
        self._token = _current_budget.set(self)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        _current_budget.reset(self._token)
        self._token = None
        return False  # do not suppress

    @property
    def latency_so_far_ms(self) -> float:
        return (time.perf_counter() - (self._start or time.perf_counter())) * 1000.0

    def add_usage(self, *, tokens: int = 0, cost: float = 0.0) -> None:
        self.tokens_so_far += tokens
        self.cost_so_far += cost
        self.check()

    def check(self) -> None:
        if self.token_limit is not None and self.tokens_so_far > self.token_limit:
            raise BudgetExceededError(reason="tokens", limit=self.token_limit, observed=self.tokens_so_far, scope=self.name)
        if self.cost_usd is not None and self.cost_so_far > self.cost_usd:
            raise BudgetExceededError(reason="cost", limit=self.cost_usd, observed=self.cost_so_far, scope=self.name)
        if self.latency_ms is not None and self.latency_so_far_ms > self.latency_ms:
            raise BudgetExceededError(reason="latency", limit=self.latency_ms, observed=self.latency_so_far_ms, scope=self.name)


def current_budget() -> Optional[BudgetScope]:
    return _current_budget.get()


async def run_with_budget(coro, *, token_limit=None, latency_ms=None, cost_usd=None, name=""):
    """Convenience helper: run coro inside a BudgetScope with asyncio.wait_for for latency."""
    async with BudgetScope(token_limit=token_limit, latency_ms=latency_ms, cost_usd=cost_usd, name=name) as bs:
        try:
            if latency_ms is not None:
                return await asyncio.wait_for(coro, timeout=latency_ms / 1000.0)
            return await coro
        except asyncio.TimeoutError as e:
            raise BudgetExceededError(reason="latency", limit=latency_ms, observed=bs.latency_so_far_ms, scope=name) from e
