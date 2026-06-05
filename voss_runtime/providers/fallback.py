"""FallbackProvider — a ModelProvider decorator with per-role cascade.

Wraps an ordered list of `(provider, model)` candidates. On a *retryable*
failure (HTTP 429 / quota / overloaded / rate limit) it advances to the next
candidate with exponential backoff; non-retryable errors and the final
candidate's error propagate unchanged. It implements the same
complete/stream/count_tokens surface as any provider, so call sites are
untouched: the caller's `model=` argument is ignored — each candidate carries
its own model string.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from ..exceptions import ProviderError
from .base import ModelProvider, ProviderResponse

# Substrings (matched case-insensitively against the error message) that mark a
# failure as worth cascading to the next credential/model rather than aborting.
_RETRYABLE_MARKERS = (
    "429",
    "rate limit",
    "ratelimit",
    "rate_limit",
    "too many requests",
    "quota",
    "insufficient_quota",
    "overloaded",
    "503",
    "service unavailable",
)


def is_retryable_error(exc: BaseException) -> bool:
    """True when `exc` looks like a transient capacity/quota error. ProviderError
    wraps the underlying litellm exception as `"{model}: {e}"`, so message
    substring matching is the available signal."""
    msg = str(exc).lower()
    return any(m in msg for m in _RETRYABLE_MARKERS)


class FallbackProvider:
    def __init__(
        self,
        candidates: list[tuple[ModelProvider, str]],
        *,
        base_backoff_s: float = 0.5,
        max_backoff_s: float = 8.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not candidates:
            raise ValueError("FallbackProvider needs at least one candidate")
        self._candidates = list(candidates)
        self._base = base_backoff_s
        self._max = max_backoff_s
        self._sleep = sleep

    @property
    def primary_model(self) -> str:
        return self._candidates[0][1]

    @property
    def candidate_models(self) -> list[str]:
        return [m for _, m in self._candidates]

    def _backoff(self, attempt: int) -> float:
        return min(self._max, self._base * (2**attempt))

    async def complete(self, *, messages, model=None, **kw) -> ProviderResponse:
        last: ProviderError | None = None
        n = len(self._candidates)
        for i, (prov, m) in enumerate(self._candidates):
            try:
                return await prov.complete(messages=messages, model=m, **kw)
            except ProviderError as e:
                last = e
                if i + 1 >= n or not is_retryable_error(e):
                    raise
                await self._sleep(self._backoff(i))
        assert last is not None  # loop body either returns or sets last
        raise last

    async def stream(self, *, messages, model=None, **kw):
        # Retry is only safe before the first event is yielded. The live
        # LiteLLMProvider.stream completes the request fully before yielding, so
        # a 429 surfaces at the first __anext__ — exactly where we can still
        # fall through to the next candidate without emitting partial output.
        last: ProviderError | None = None
        n = len(self._candidates)
        for i, (prov, m) in enumerate(self._candidates):
            agen = prov.stream(messages=messages, model=m, **kw)
            try:
                first = await agen.__anext__()
            except StopAsyncIteration:
                return
            except ProviderError as e:
                last = e
                if i + 1 >= n or not is_retryable_error(e):
                    raise
                await self._sleep(self._backoff(i))
                continue
            yield first
            async for ev in agen:
                yield ev
            return
        if last is not None:
            raise last

    def count_tokens(self, *, text, model=None) -> int:
        prov, m = self._candidates[0]
        return prov.count_tokens(text=text, model=m)
