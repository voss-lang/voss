from __future__ import annotations

import pytest
from pydantic import BaseModel

from voss_runtime import (
    BudgetScope,
    ContextScope,
    ProbableValue,
    StubProvider,
)


@pytest.mark.asyncio
async def test_add_accumulates_tokens():
    stub = StubProvider()
    cs = ContextScope(token_budget=1000, provider=stub, model="stub-model")
    await cs.add("hello world")
    await cs.add("another piece of content")
    assert cs.tokens_used > 0
    assert len(cs.slots) == 2


@pytest.mark.asyncio
async def test_compression_triggers_when_over_budget():
    stub = StubProvider()

    async def short_compressor(text, target, provider):
        return "x"

    cs = ContextScope(
        token_budget=50,
        provider=stub,
        model="stub-model",
        compressor=short_compressor,
    )
    await cs.add("x" * 4000)
    assert cs.tokens_used <= cs.token_budget


@pytest.mark.asyncio
async def test_ask_returns_str_by_default():
    stub = StubProvider(default_response="hello")
    cs = ContextScope(token_budget=10000, provider=stub, model="stub-model")
    result = await cs.ask("say hi")
    assert isinstance(result, str)
    assert result == "hello"
    assert stub.calls[-1]["max_tokens"] == 4096


@pytest.mark.asyncio
async def test_ask_probable_value():
    stub = StubProvider(default_response="hello")
    cs = ContextScope(token_budget=10000, provider=stub, model="stub-model")
    result = await cs.ask("say hi", return_type=ProbableValue)
    assert isinstance(result, ProbableValue)
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_ask_pydantic_model():
    class Out(BaseModel):
        value: str

    stub = StubProvider(default_response="hello")
    cs = ContextScope(token_budget=10000, provider=stub, model="stub-model")
    result = await cs.ask("say hi", return_type=Out)
    assert isinstance(result, Out)
    assert result.value == "hello"
    # response_format was forwarded
    assert stub.calls[-1]["response_format"] is Out


@pytest.mark.asyncio
async def test_budget_scope_composition():
    stub = StubProvider(default_response="hello")
    async with BudgetScope(token_limit=10000) as bs:
        cs = ContextScope(token_budget=10000, provider=stub, model="stub-model")
        await cs.ask("say hi")
        assert bs.tokens_so_far > 0
