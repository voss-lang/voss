import asyncio
from dataclasses import asdict
import json

import httpx
import pytest

from voss_runtime import judgments as j

SENTINEL = "SENTINEL-7f3a"
RESERVATION = j.MAX_REQUEST_TOKENS * j.USD_PER_INPUT_TOKEN


@pytest.fixture
def questions():
    return {
        "pick": j.ChoiceQuestion(f"{SENTINEL} pick", {"billing": f"{SENTINEL} desc", "technical": None}),
        "rating": j.ScoreQuestion(f"{SENTINEL} rate", [f"{SENTINEL} calm", "Angry"]),
        "urgent": j.NoulQuestion(f"{SENTINEL} urgent", {"true": f"{SENTINEL} yes"}),
    }


@pytest.fixture
def body():
    return {
        "model": "jev-1.13.1",
        "answers": {
            "pick": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.9, "technical": 0.1}, "confidence": 0.8},
            "rating": {"type": "score", "score": 0.4, "probabilities": {"0": 0.6, "1": 0.4}, "confidence": 0.7},
            "urgent": {"type": "noul", "noul": 0.3},
        },
        "usage": {"input_tokens": 10, "output_tokens": 2},
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


def dumped(receipt):
    return json.dumps(asdict(receipt))


async def test_answered_receipt(make_client, questions, body):
    client = make_client(lambda r: httpx.Response(200, json=body))
    result = await client.evaluate({"secret": SENTINEL}, questions)
    [receipt] = client.ledger.receipts
    assert result.receipt is None
    assert (receipt.status, receipt.attempts, receipt.input_tokens, receipt.output_tokens) == ("answered", 1, 10, 2)
    assert receipt.cost_usd == result.cost_usd_estimate and receipt.held_usd == 0
    assert (receipt.model_requested, receipt.model_returned, receipt.mode, receipt.purpose) == ("jev-1.13.0", "jev-1.13.1", "explicit", "explicit")
    assert receipt.answers == {
        "pick": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.9, "technical": 0.1}},
        "rating": {"type": "score", "score": 0.4, "probabilities": {"0": 0.6, "1": 0.4}},
        "urgent": {"type": "noul", "noul": 0.3},
    }
    assert client.ledger.receipt(receipt.call_id) is receipt
    assert SENTINEL not in dumped(receipt) and "test-key" not in dumped(receipt)


async def test_retry_receipt_holds_failed_attempt(make_client, questions, body):
    responses = iter([httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, json=body)])
    client = make_client(lambda r: next(responses))
    await client.evaluate("state", questions)
    [receipt] = client.ledger.receipts
    assert (receipt.attempts, receipt.held_usd) == (2, RESERVATION)


async def test_timeout_receipt_unknown_usage(make_client, questions):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client = make_client(handler)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    receipt = caught.value.receipt
    assert receipt is client.ledger.receipts[0]
    assert (receipt.status, receipt.input_tokens, receipt.output_tokens, receipt.cost_usd) == ("unavailable", None, None, None)
    assert receipt.held_usd == RESERVATION and receipt.answers == {}


async def test_cancelled_receipt(make_client, questions):
    started = asyncio.Event()

    async def handler(request):
        started.set()
        await asyncio.Event().wait()

    client = make_client(handler)
    task = asyncio.create_task(client.evaluate("state", questions))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert client.ledger.receipts[0].status == "cancelled"


async def test_size_refusal_receipt(make_client, questions):
    client = make_client(lambda r: pytest.fail("must not dispatch"), max_request_bytes=10)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert (caught.value.receipt.status, caught.value.receipt.attempts) == ("budget_exhausted", 0)


async def test_error_body_and_key_not_in_receipt(make_client, questions):
    client = make_client(lambda r: httpx.Response(500, content=f"{SENTINEL} test-key".encode()))
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate({"secret": SENTINEL}, questions)
    output = dumped(caught.value.receipt)
    assert SENTINEL not in output and "test-key" not in output


async def test_unsafe_ids_replaced_positionally(make_client):
    questions = {
        "q with spaces": j.ChoiceQuestion("?", {"Ignore previous: <b>": None, "safe.id": None, "<i>": None}),
        "ok_id": j.NoulQuestion("?"),
    }
    body = {
        "model": "jev-1.13.0",
        "answers": {
            "ok_id": {"type": "noul", "noul": 0.5},
            "q with spaces": {"type": "choice", "choice": "Ignore previous: <b>", "probabilities": {"Ignore previous: <b>": 0.5, "safe.id": 0.3, "<i>": 0.2}, "confidence": 0.5},
        },
        "usage": {"input_tokens": 1, "output_tokens": 0},
    }
    client = make_client(lambda r: httpx.Response(200, json=body))
    await client.evaluate("state", questions)
    answers = client.ledger.receipts[0].answers
    assert list(answers) == ["q1", "ok_id"]
    assert answers["q1"] == {"type": "choice", "choice": "opt1", "probabilities": {"opt1": 0.5, "safe.id": 0.3, "opt3": 0.2}}
    assert "Ignore" not in dumped(client.ledger.receipts[0])


async def test_bad_purpose_rejected_before_request(make_client, questions):
    client = make_client(lambda r: pytest.fail("must not dispatch"))
    with pytest.raises(ValueError):
        await client.evaluate("state", questions, purpose="Bad Purpose!")
    assert client.ledger.receipts == [] and client.calls_used == 0


async def test_caller_fields_carried(make_client, questions, body):
    client = make_client(lambda r: httpx.Response(200, json=body))
    await client.evaluate("state", questions, call_id="c1", purpose="code_recall.rerank", rubric_version="r1", artifact_revision="abc")
    receipt = client.ledger.receipt("c1")
    assert (receipt.purpose, receipt.rubric_version, receipt.artifact_revision, receipt.schema_version) == ("code_recall.rerank", "r1", "abc", 1)
