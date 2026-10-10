import asyncio

import httpx
import pytest

from voss_runtime import judgments as j
from voss_runtime.budget import BudgetScope

RESERVATION = j.MAX_REQUEST_TOKENS * j.USD_PER_INPUT_TOKEN
QUESTIONS = {"pick": j.ChoiceQuestion("Pick a team", {"billing": None, "technical": "Bugs"})}
BODY = {
    "model": "jev-1.13.0",
    "answers": {"pick": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.9, "technical": 0.1}, "confidence": 0.8}},
    "usage": {"input_tokens": 10, "output_tokens": 0},
}


@pytest.fixture
async def make_client():
    clients = []

    def make(handler, **overrides):
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        clients.append(transport)
        settings = dict(model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000, max_calls=4, max_cost_usd=0.01, sleep=lambda s: asyncio.sleep(0))
        settings.update(overrides)
        return j.JevClient("test-key", client=transport, **settings)

    yield make
    for client in clients:
        await client.aclose()


def ok(request):
    return httpx.Response(200, json=BODY)


def refuse(request):
    pytest.fail("must not dispatch")


async def test_retry_then_success_settles_once_and_holds_failed_attempt(make_client):
    responses = iter([httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, json=BODY)])
    ledger = j.JudgmentLedger(4, 0.01)
    await make_client(lambda r: next(responses), ledger=ledger).evaluate("state", QUESTIONS)
    assert ledger.calls_used == 2
    assert ledger.observed_usd == pytest.approx(10 * j.USD_PER_INPUT_TOKEN)
    assert ledger.held_usd == RESERVATION
    assert [e.state for e in ledger.entries] == ["unknown", "settled"]


async def test_settle_twice_is_noop(make_client):
    ledger = j.JudgmentLedger(4, 0.01)
    await make_client(ok, ledger=ledger).evaluate("state", QUESTIONS)
    observed = ledger.observed_usd
    ledger.settle(ledger.entries[0], 1.0)
    assert ledger.observed_usd == observed
    assert ledger.entries[0].cost_usd == pytest.approx(10 * j.USD_PER_INPUT_TOKEN)


async def test_ambiguous_timeout_holds_reservation(make_client):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    ledger = j.JudgmentLedger(4, 0.01)
    with pytest.raises(j.JudgmentError):
        await make_client(handler, ledger=ledger).evaluate("state", QUESTIONS)
    assert [e.state for e in ledger.entries] == ["unknown"]
    assert ledger.held_usd == RESERVATION
    assert ledger.observed_usd == 0


async def test_cancel_marks_entry_unknown(make_client):
    started = asyncio.Event()

    async def handler(request):
        started.set()
        await asyncio.Event().wait()

    ledger = j.JudgmentLedger(4, 0.01)
    task = asyncio.create_task(make_client(handler, ledger=ledger).evaluate("state", QUESTIONS))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert [e.state for e in ledger.entries] == ["unknown"]
    assert ledger.held_usd == RESERVATION


async def test_concurrent_calls_share_one_ledger_limit(make_client):
    seen = []

    async def handler(request):
        seen.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json=BODY)

    ledger = j.JudgmentLedger(2, 0.01)
    clients = [make_client(handler, ledger=ledger) for _ in range(3)]
    results = await asyncio.gather(*(c.evaluate("state", QUESTIONS) for c in clients), return_exceptions=True)
    errors = [r for r in results if isinstance(r, j.JudgmentError)]
    assert len(seen) == 2 and ledger.calls_used == 2
    assert [(e.outcome, e.attempts) for e in errors] == [("budget_exhausted", 0)]


async def test_cost_limit_below_one_reservation_refuses_without_mutation(make_client):
    ledger = j.JudgmentLedger(4, RESERVATION / 2)
    with pytest.raises(j.JudgmentError) as caught:
        await make_client(refuse, ledger=ledger).evaluate("state", QUESTIONS)
    assert caught.value.outcome == "budget_exhausted"
    assert ledger.calls_used == 0 and ledger.entries == []


async def test_budget_scope_charged_dollars_only(make_client):
    async with BudgetScope(cost_usd=1.0, token_limit=10) as scope:
        result = await make_client(ok).evaluate("state", QUESTIONS)
    assert scope.cost_so_far == pytest.approx(result.cost_usd_estimate)
    assert scope.tokens_so_far == 0


async def test_budget_scope_too_small_refuses_before_dispatch(make_client):
    ledger = j.JudgmentLedger(4, 0.01)
    async with BudgetScope(cost_usd=0.001) as scope:
        with pytest.raises(j.JudgmentError) as caught:
            await make_client(refuse, ledger=ledger).evaluate("state", QUESTIONS)
    assert caught.value.outcome == "budget_exhausted"
    assert scope.cost_so_far == 0 and ledger.calls_used == 0 and ledger.entries == []


async def test_budget_scope_keeps_unknown_reservation(make_client):
    async with BudgetScope(cost_usd=1.0) as scope:
        with pytest.raises(j.JudgmentError):
            await make_client(lambda r: httpx.Response(500)).evaluate("state", QUESTIONS)
    assert scope.cost_so_far == RESERVATION


async def test_ambient_ledger_context():
    ledger = j.JudgmentLedger(4, 0.01)
    assert j.current_ledger() is None
    async with ledger:
        assert j.current_ledger() is ledger
    assert j.current_ledger() is None


async def test_default_ledger_backs_client_counters(make_client):
    client = make_client(lambda r: httpx.Response(500))
    with pytest.raises(j.JudgmentError):
        await client.evaluate("state", QUESTIONS)
    assert client.calls_used == client.ledger.calls_used == 1
    assert client.spent_usd == client.ledger.observed_usd + client.ledger.held_usd == RESERVATION
