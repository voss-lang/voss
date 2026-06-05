"""FallbackProvider cascade behaviour."""
from __future__ import annotations

import pytest

from voss_runtime.exceptions import ProviderError
from voss_runtime.providers.base import ProviderResponse
from voss_runtime.providers.fallback import FallbackProvider, is_retryable_error


def _resp(model: str) -> ProviderResponse:
    return ProviderResponse(
        text=f"ok:{model}", model=model, prompt_tokens=1, completion_tokens=1, cost_usd=0.0
    )


class _StubProvider:
    """Records calls; raises a preprogrammed error or returns a response."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    async def complete(self, *, messages, model, **kw) -> ProviderResponse:
        self.calls.append(model)
        if self.error is not None:
            raise self.error
        return _resp(model)

    async def stream(self, *, messages, model, **kw):
        self.calls.append(model)
        if self.error is not None:
            raise self.error
        yield ("delta", model)

    def count_tokens(self, *, text, model) -> int:
        return len(text)


async def _nosleep(_: float) -> None:
    return None


def test_is_retryable_matches_429_and_quota() -> None:
    assert is_retryable_error(ProviderError("claude: 429 Too Many Requests"))
    assert is_retryable_error(ProviderError("gpt: insufficient_quota"))
    assert is_retryable_error(ProviderError("x: Overloaded"))
    assert not is_retryable_error(ProviderError("claude: 400 bad request"))


@pytest.mark.asyncio
async def test_complete_cascades_on_retryable() -> None:
    p1 = _StubProvider(error=ProviderError("m1: 429 rate limit"))
    p2 = _StubProvider()
    fb = FallbackProvider([(p1, "m1"), (p2, "m2")], sleep=_nosleep)
    resp = await fb.complete(messages=[], model="ignored")
    assert resp.model == "m2"
    assert p1.calls == ["m1"] and p2.calls == ["m2"]


@pytest.mark.asyncio
async def test_complete_does_not_cascade_on_non_retryable() -> None:
    p1 = _StubProvider(error=ProviderError("m1: 400 bad request"))
    p2 = _StubProvider()
    fb = FallbackProvider([(p1, "m1"), (p2, "m2")], sleep=_nosleep)
    with pytest.raises(ProviderError):
        await fb.complete(messages=[], model="x")
    assert p2.calls == []  # never reached


@pytest.mark.asyncio
async def test_complete_raises_last_when_all_fail() -> None:
    p1 = _StubProvider(error=ProviderError("m1: 429"))
    p2 = _StubProvider(error=ProviderError("m2: 503 service unavailable"))
    fb = FallbackProvider([(p1, "m1"), (p2, "m2")], sleep=_nosleep)
    with pytest.raises(ProviderError, match="m2"):
        await fb.complete(messages=[], model="x")


@pytest.mark.asyncio
async def test_stream_cascades_before_first_event() -> None:
    p1 = _StubProvider(error=ProviderError("m1: 429"))
    p2 = _StubProvider()
    fb = FallbackProvider([(p1, "m1"), (p2, "m2")], sleep=_nosleep)
    events = [ev async for ev in fb.stream(messages=[], model="x")]
    assert events == [("delta", "m2")]


def test_primary_model_and_candidates() -> None:
    fb = FallbackProvider([(_StubProvider(), "m1"), (_StubProvider(), "m2")])
    assert fb.primary_model == "m1"
    assert fb.candidate_models == ["m1", "m2"]


def test_empty_candidates_rejected() -> None:
    with pytest.raises(ValueError):
        FallbackProvider([])
