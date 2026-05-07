import asyncio

import pytest

from voss_runtime import (
    BudgetExceededError,
    BudgetScope,
    current_budget,
    run_with_budget,
)


@pytest.mark.asyncio
async def test_no_limits_raises_value_error():
    scope = BudgetScope()
    with pytest.raises(ValueError):
        await scope.__aenter__()


@pytest.mark.asyncio
async def test_token_overflow():
    async with BudgetScope(token_limit=100) as bs:
        bs.add_usage(tokens=50)
        with pytest.raises(BudgetExceededError) as exc_info:
            bs.add_usage(tokens=51)
        assert exc_info.value.reason == "tokens"


@pytest.mark.asyncio
async def test_cost_overflow():
    async with BudgetScope(cost_usd=1.0) as bs:
        bs.add_usage(cost=0.5)
        with pytest.raises(BudgetExceededError) as exc_info:
            bs.add_usage(cost=0.6)
        assert exc_info.value.reason == "cost"


@pytest.mark.asyncio
async def test_latency_overflow():
    with pytest.raises(BudgetExceededError) as exc_info:
        await run_with_budget(asyncio.sleep(0.5), latency_ms=10)
    assert exc_info.value.reason == "latency"


@pytest.mark.asyncio
async def test_current_budget_inside_and_outside():
    assert current_budget() is None
    async with BudgetScope(token_limit=100) as bs:
        assert current_budget() is bs
    assert current_budget() is None


@pytest.mark.asyncio
async def test_nested_scopes_restore_outer():
    async with BudgetScope(token_limit=100, name="outer") as outer:
        assert current_budget() is outer
        async with BudgetScope(token_limit=50, name="inner") as inner:
            assert current_budget() is inner
        assert current_budget() is outer
