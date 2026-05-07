"""Integration test for examples/raw_python/research.py (PRD §7.3)."""
from __future__ import annotations

import asyncio

import pytest

import voss_runtime
from voss_runtime import configure, reset_config
from voss_runtime.budget import run_with_budget as orig_run_with_budget
from voss_runtime.providers.stub import StubProvider

from examples.raw_python import research
from examples.raw_python.research import Synthesizer, run_research


@pytest.fixture
def stub():
    s = StubProvider(default_response="STUB SUMMARY")
    voss_runtime.providers.register("__stub__", s)
    configure(default_model="__stub__")
    yield s
    reset_config()


@pytest.mark.asyncio
async def test_run_research_happy_path(stub):
    result = await run_research("Anthropic")
    assert isinstance(result, str)
    assert result
    # 4 researchers each call provider.complete once via ctx.ask, plus the
    # synthesizer's ask = 5 calls total.
    assert len(stub.calls) >= 4


@pytest.mark.asyncio
async def test_run_research_falls_back_on_synth_timeout(stub, monkeypatch):
    async def slow_run(self, reports):
        await asyncio.sleep(1)
        return "should not appear"

    monkeypatch.setattr(Synthesizer, "run", slow_run)

    def short_budget(coro, **kwargs):
        return orig_run_with_budget(
            coro, token_limit=kwargs.get("token_limit"), latency_ms=50
        )

    monkeypatch.setattr(research, "run_with_budget", short_budget)

    result = await run_research("Anthropic")
    expected = "\n---\n".join(["STUB SUMMARY"] * 4)
    assert result == expected
