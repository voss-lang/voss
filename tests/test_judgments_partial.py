import httpx
import pytest

from voss_runtime import judgments as j

OPTIONS = {"supported": None, "contradicted": None, "insufficient_evidence": None}


def good(choice="supported"):
    probabilities = {o: 0.0 for o in OPTIONS}
    probabilities[choice] = 1.0
    return {"type": "choice", "choice": choice, "probabilities": probabilities, "confidence": 0.9}


@pytest.fixture
def questions():
    return {qid: j.ChoiceQuestion(f"Is {qid} met?", OPTIONS) for qid in ("q1", "q2", "q3")}


def body_with(answers):
    return {"model": "jev-1.13.0", "answers": answers, "usage": {"input_tokens": 10, "output_tokens": 2}}


@pytest.fixture
async def make_client():
    clients = []

    def make(body):
        transport = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
        clients.append(transport)
        return j.JevClient(
            "test-key", model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000,
            max_calls=4, max_cost_usd=0.01, client=transport, clock=lambda: 1.0,
        )

    yield make
    for client in clients:
        await client.aclose()


@pytest.mark.parametrize("bad", [
    {"q2": {**good(), "probabilities": {"supported": 0.5, "contradicted": 0.0, "insufficient_evidence": 0.0}}},
    {"q2": {**good(), "type": "score"}},
    {"q2": "supported"},
    {"q2": {**good(), "choice": "maybe"}},
])
async def test_partial_keeps_valid_answers_beside_a_malformed_one(make_client, questions, bad):
    client = make_client(body_with({"q1": good(), "q3": good("contradicted"), **bad}))
    result = await client.evaluate({"s": 1}, questions, partial=True)
    [receipt] = client.ledger.receipts
    assert set(result.answers) == {"q1", "q3"}
    assert result.answers["q3"].choice == "contradicted"
    assert set(receipt.answers) == {"q1", "q3"}
    assert receipt.status == "answered"
    assert result.cost_usd_estimate == 10 * j.USD_PER_INPUT_TOKEN
    assert receipt.cost_usd == 10 * j.USD_PER_INPUT_TOKEN


async def test_partial_tolerates_a_missing_answer_and_ignores_extra_keys(make_client, questions):
    client = make_client(body_with({"q1": good(), "q3": good(), "extra": good()}))
    result = await client.evaluate({"s": 1}, questions, partial=True)
    assert set(result.answers) == {"q1", "q3"}
    assert set(client.ledger.receipts[0].answers) == {"q1", "q3"}


async def test_partial_with_no_valid_answers_is_invalid(make_client, questions):
    client = make_client(body_with({qid: {**good(), "type": "noul"} for qid in questions}))
    with pytest.raises(j.JudgmentError) as err:
        await client.evaluate({"s": 1}, questions, partial=True)
    assert err.value.outcome == "invalid_response"
    assert err.value.receipt.status == "invalid_response"
    assert err.value.receipt.answers == {}


@pytest.mark.parametrize("overrides", [
    {"model": None},
    {"usage": {"input_tokens": -1, "output_tokens": 2}},
    {"usage": {"input_tokens": 10}},
    {"answers": ["q1"]},
    {"answers": None},
])
async def test_partial_still_rejects_an_invalid_envelope(make_client, questions, overrides):
    client = make_client({**body_with({qid: good() for qid in questions}), **overrides})
    with pytest.raises(j.JudgmentError) as err:
        await client.evaluate({"s": 1}, questions, partial=True)
    assert err.value.outcome == "invalid_response"


async def test_default_still_rejects_one_malformed_answer(make_client, questions):
    client = make_client(body_with({"q1": good(), "q2": {**good(), "type": "score"}, "q3": good()}))
    with pytest.raises(j.JudgmentError) as err:
        await client.evaluate({"s": 1}, questions)
    assert err.value.outcome == "invalid_response"
    assert err.value.receipt.status == "invalid_response"


async def test_default_still_rejects_a_missing_answer(make_client, questions):
    client = make_client(body_with({"q1": good(), "q3": good()}))
    with pytest.raises(j.JudgmentError, match="missing or extra"):
        await client.evaluate({"s": 1}, questions)
