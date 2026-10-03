import ast
import asyncio
from dataclasses import asdict
import json
from pathlib import Path

import httpx
import pytest

from voss_runtime import judgments as j


@pytest.fixture
def questions():
    return {
        "pick": j.ChoiceQuestion("Pick a team", {"billing": None, "technical": "Bugs"}),
        "rating": j.ScoreQuestion("Rate frustration", ["Calm", "Frustrated", "Angry"]),
        "urgent": j.NoulQuestion("Is it urgent?"),
    }


@pytest.fixture
def body():
    return {
        "model": "jev-1.13.0",
        "answers": {
            "pick": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.88, "technical": 0.12}, "confidence": 0.81},
            "rating": {"type": "score", "score": 1.05, "legend": {"0": "Calm", "1": "Frustrated", "2": "Angry"}, "probabilities": {"0": 0.0, "1": 0.95, "2": 0.05}, "confidence": 0.92},
            "urgent": {"type": "noul", "noul": 0.95},
        },
        "usage": {"input_tokens": 10, "output_tokens": 0},
    }


def test_parse_all_three_types(body, questions):
    answers, model, input_tokens, output_tokens = j.parse_response(body, questions)
    assert answers == {
        "pick": j.ChoiceResult("billing", {"billing": 0.88, "technical": 0.12}, 0.81),
        "rating": j.ScoreResult(1.05, {"0": 0.0, "1": 0.95, "2": 0.05}, 0.92),
        "urgent": j.NoulResult(0.95),
    }
    assert (model, input_tokens, output_tokens) == ("jev-1.13.0", 10, 0)
    assert list(answers) == list(questions)


def test_result_types_distinct(body, questions):
    answers, *_ = j.parse_response(body, questions)
    assert {type(a) for a in answers.values()} == {j.ChoiceResult, j.ScoreResult, j.NoulResult}
    assert [asdict(a)["type"] for a in answers.values()] == ["choice", "score", "noul"]
    assert not issubclass(j.ChoiceResult, j.ScoreResult)
    assert not issubclass(j.NoulResult, j.ChoiceResult)


@pytest.mark.parametrize("path,value", [
    ((), []), (("model",), None), (("model",), 1),
    (("usage",), None), (("usage", "input_tokens"), None),
    (("usage", "input_tokens"), True), (("usage", "input_tokens"), -1),
    (("usage", "output_tokens"), 1.5), (("usage", "output_tokens"), False),
    (("answers",), []), (("answers", "pick"), None),
    (("answers", "pick", "type"), "noul"),
    (("answers", "pick", "choice"), "other"), (("answers", "pick", "choice"), []),
    (("answers", "pick", "probabilities"), {"billing": 1}),
    (("answers", "pick", "probabilities"), {"billing": 0.8, "other": 0.2}),
    (("answers", "pick", "probabilities"), {"billing": 0.8, "technical": 0.1}),
    (("answers", "pick", "probabilities"), {"billing": 0.9, "technical": 0.2}),
    (("answers", "pick", "probabilities", "billing"), float("nan")),
    (("answers", "pick", "probabilities", "billing"), float("inf")),
    (("answers", "pick", "probabilities", "billing"), -0.1),
    (("answers", "pick", "probabilities", "billing"), 1.1),
    (("answers", "pick", "probabilities", "billing"), True),
    (("answers", "pick", "confidence"), -0.1),
    (("answers", "pick", "confidence"), float("nan")),
    (("answers", "rating", "probabilities"), {"0": 0, "1": 1, "3": 0}),
    (("answers", "rating", "score"), -0.1),
    (("answers", "rating", "score"), 2.1),
    (("answers", "rating", "score"), True),
    (("answers", "rating", "confidence"), 1.1),
    (("answers", "urgent", "noul"), float("inf")),
    (("answers", "urgent", "noul"), -0.1),
    (("answers", "urgent", "noul"), 1.1),
    (("answers", "urgent", "noul"), True),
])
def test_validation_rejects_bad_fields(body, questions, path, value):
    if not path:
        body = value
    else:
        target = body
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    with pytest.raises(j.JudgmentError) as caught:
        j.parse_response(body, questions)
    assert caught.value.outcome == "invalid_response"


@pytest.mark.parametrize("path", [("model",), ("usage", "input_tokens"), ("usage", "output_tokens"), ("answers", "pick"), ("answers", "urgent", "noul"), ("answers", "pick", "confidence")])
def test_validation_rejects_missing_fields(body, questions, path):
    target = body
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    with pytest.raises(j.JudgmentError):
        j.parse_response(body, questions)


def test_validation_rejects_extra_answer(body, questions):
    body["answers"]["extra"] = body["answers"]["urgent"]
    with pytest.raises(j.JudgmentError):
        j.parse_response(body, questions)


def test_accepts_rounding_without_renormalizing(body, questions):
    body["answers"]["pick"]["probabilities"] = {"billing": 0.88, "technical": 0.11}
    answers, *_ = j.parse_response(body, questions)
    assert answers["pick"].probabilities == {"billing": 0.88, "technical": 0.11}
    assert answers["pick"].probabilities is not body["answers"]["pick"]["probabilities"]


@pytest.mark.parametrize("factory,criteria", [
    (j.ChoiceQuestion, {"one": None}), (j.ChoiceQuestion, {str(n): None for n in range(256)}),
    (j.ChoiceQuestion, {"": None, "two": None}), (j.ChoiceQuestion, {"one": True, "two": None}),
    (j.ScoreQuestion, ["one"]), (j.ScoreQuestion, ["level"] * 11),
    (j.ScoreQuestion, "not levels"), (j.ScoreQuestion, ["one", 2]),
    (j.NoulQuestion, {"maybe": "yes"}), (j.NoulQuestion, {"true": False}),
])
def test_question_validation(factory, criteria):
    with pytest.raises(ValueError):
        factory("question", criteria)


@pytest.mark.parametrize("instructions", [None, True, 42])
@pytest.mark.parametrize("factory,criteria", [
    (j.ChoiceQuestion, {"one": None, "two": None}),
    (j.ScoreQuestion, ["low", "high"]),
    (j.NoulQuestion, None),
])
def test_question_rejects_invalid_instructions(factory, criteria, instructions):
    with pytest.raises(ValueError, match="instructions must be a string, object, or array"):
        factory(instructions, criteria)


def test_questions_to_wire_and_structured_descriptions(questions):
    assert questions["pick"].to_wire() == {"type": "choice", "instructions": "Pick a team", "criteria": {"billing": None, "technical": "Bugs"}}
    assert questions["rating"].to_wire()["criteria"] == ["Calm", "Frustrated", "Angry"]
    assert questions["urgent"].to_wire() == {"type": "noul", "instructions": "Is it urgent?"}
    assert j.ChoiceQuestion({}, {"a": {}, "b": []}).to_wire()["criteria"] == {"a": {}, "b": []}
    assert j.ScoreQuestion([], ({"level": "one"}, ["two"])).to_wire()["criteria"] == [{"level": "one"}, ["two"]]
    assert j.NoulQuestion("?", {"true": {"meaning": "yes"}}).to_wire()["criteria"] == {"true": {"meaning": "yes"}}


def test_no_harness_import():
    tree = ast.parse(Path(j.__file__).read_text())
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        assert not any(m == "voss" or m.startswith("voss.") for m in modules)


@pytest.fixture
async def client_factory():
    clients = []

    def make(handler, **overrides):
        transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        clients.append(transport)
        settings = dict(model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000, max_calls=4, max_cost_usd=0.01)
        settings.update(overrides)
        return j.JevClient("test-key", client=transport, **settings)

    yield make
    for client in clients:
        await client.aclose()


async def test_synthetic_all_three_and_request_shape(client_factory, questions, body):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=body)

    client = client_factory(handler)
    result = await client.evaluate({"synthetic": "state"}, questions)
    assert len(seen) == 1
    assert seen[0].method == "POST" and str(seen[0].url) == j.JEV_URL
    assert seen[0].headers["authorization"] == "Bearer test-key"
    assert seen[0].headers["content-type"] == "application/json"
    assert json.loads(seen[0].content) == {"model": "jev-1.13.0", "state": {"synthetic": "state"}, "questions": {k: q.to_wire() for k, q in questions.items()}}
    assert result.answers == j.parse_response(body, questions)[0]
    assert (result.model, result.input_tokens, result.output_tokens, result.attempts, result.outcome) == ("jev-1.13.0", 10, 0, 1, "answered")
    assert result.latency_ms >= 0
    assert result.cost_usd_estimate == 10 * j.USD_PER_INPUT_TOKEN
    assert client.spent_usd == pytest.approx(result.cost_usd_estimate)
    assert client.calls_used == 1


@pytest.mark.parametrize("status,header,delay", [(429, None, 0.25), (529, "1", 1.0), (429, "soon", 0.25), (429, "-1", 0.25), (429, "nan", 0.25), (429, "inf", 0.25)])
async def test_retry_policy_retry_after(client_factory, questions, body, status, header, delay):
    calls, sleeps, now = [], [], [0.0]

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status, headers={} if header is None else {"Retry-After": header})
        return httpx.Response(200, json=body)

    async def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    client = client_factory(handler, sleep=sleep, clock=lambda: now[0])
    result = await client.evaluate("state", questions)
    assert result.attempts == client.calls_used == len(calls) == 2
    assert sleeps == [delay]
    assert result.latency_ms == delay * 1000
    assert client.spent_usd == pytest.approx((j.MAX_REQUEST_TOKENS + 10) * j.USD_PER_INPUT_TOKEN)


@pytest.mark.parametrize("status,expected_calls", [(429, 2), (529, 2), (401, 1), (422, 1), (500, 1)])
async def test_retry_policy_max_one_retry_and_no_retry_statuses(client_factory, questions, status, expected_calls):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"Retry-After": "0"})

    client = client_factory(handler)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert (caught.value.outcome, caught.value.status, caught.value.attempts) == ("unavailable", status, expected_calls)
    assert len(calls) == client.calls_used == expected_calls


@pytest.mark.parametrize("elapsed,delay,timeout", [(0.8, "0.25", 1000), (0, "30", 5000)])
async def test_deadline_includes_backoff(client_factory, questions, elapsed, delay, timeout):
    now, sleeps = [0.0], []

    def handler(request):
        now[0] += elapsed
        return httpx.Response(429, headers={"Retry-After": delay})

    async def sleep(seconds):
        sleeps.append(seconds)

    client = client_factory(handler, clock=lambda: now[0], sleep=sleep, timeout_ms=timeout)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert caught.value.outcome == "unavailable"
    assert client.calls_used == 1 and sleeps == []


async def test_expired_deadline_blocks_dispatch(client_factory, questions):
    times = iter([0.0, 5.0])

    def handler(request):
        pytest.fail("expired request must not dispatch")

    client = client_factory(handler, clock=lambda: next(times))
    with pytest.raises(j.JudgmentError, match="deadline exceeded") as caught:
        await client.evaluate("state", questions)
    assert caught.value.outcome == "unavailable"
    assert caught.value.attempts == client.calls_used == client.spent_usd == 0


async def test_deadline_bounds_slow_backoff(client_factory, questions):
    async def sleep(seconds):
        await asyncio.sleep(1)

    client = client_factory(lambda r: httpx.Response(429, headers={"Retry-After": "0"}), timeout_ms=20, sleep=sleep)
    with pytest.raises(j.JudgmentError, match="timed out"):
        await client.evaluate("state", questions)
    assert client.calls_used == 1


async def test_ambiguous_timeout_not_retried(client_factory, questions):
    async def handler(request):
        await asyncio.sleep(1)

    client = client_factory(handler, timeout_ms=20)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert caught.value.outcome == "unavailable"
    assert caught.value.attempts == client.calls_used == 1
    assert client.spent_usd == j.MAX_REQUEST_TOKENS * j.USD_PER_INPUT_TOKEN


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
async def test_transport_error_not_retried(client_factory, questions, error, caplog):
    def handler(request):
        raise error("test-key ECHO-ME-BODY", request=request)

    client = client_factory(handler)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert caught.value.outcome == "unavailable"
    assert caught.value.attempts == client.calls_used == 1
    assert "test-key" not in str(caught.value) + repr(caught.value) + caplog.text
    assert caught.value.__suppress_context__


async def test_cancellation_propagates(client_factory, questions):
    started = asyncio.Event()

    async def handler(request):
        started.set()
        await asyncio.Event().wait()

    client = client_factory(handler)
    task = asyncio.create_task(client.evaluate("state", questions))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert client.calls_used == 1


async def test_allowance_blocks_retry(client_factory, questions):
    client = client_factory(lambda r: httpx.Response(429, headers={"Retry-After": "0"}), max_calls=1)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert caught.value.outcome == "budget_exhausted"
    assert caught.value.attempts == client.calls_used == 1


@pytest.mark.parametrize("limits,state", [({"max_cost_usd": 0.002}, "state"), ({"max_request_bytes": 100}, "x" * 1000)])
async def test_size_cap_and_cost_reservation_block_dispatch(client_factory, questions, limits, state):
    def handler(request):
        pytest.fail("must not dispatch")

    client = client_factory(handler, **limits)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate(state, questions)
    assert caught.value.outcome == "budget_exhausted"
    assert client.calls_used == client.spent_usd == 0


async def test_allowance_spans_calls(client_factory, questions, body):
    client = client_factory(lambda r: httpx.Response(200, json=body), max_calls=1)
    await client.evaluate("state", questions)
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert caught.value.outcome == "budget_exhausted"
    assert caught.value.attempts == 0 and client.calls_used == 1


@pytest.mark.parametrize("status,content", [(500, b"ECHO-ME-BODY test-key"), (200, b"ECHO-ME-BODY test-key"), (200, b'{"answers":"ECHO-ME-BODY test-key"}')])
async def test_error_body_not_echoed(client_factory, questions, status, content, caplog):
    client = client_factory(lambda r: httpx.Response(status, content=content))
    with pytest.raises(j.JudgmentError) as caught:
        await client.evaluate("state", questions)
    assert caught.value.outcome == ("invalid_response" if status == 200 else "unavailable")
    assert caught.value.attempts == 1
    output = str(caught.value) + repr(caught.value) + repr(client) + caplog.text
    assert "ECHO-ME-BODY" not in output and "test-key" not in output


async def test_owned_client_lifecycle(client_factory, questions, body, monkeypatch):
    supplied = client_factory(lambda r: httpx.Response(200, json=body))
    await supplied.aclose()
    assert not supplied._client.is_closed
    transport = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    monkeypatch.setattr(j.httpx, "AsyncClient", lambda: transport)
    async with j.JevClient("test-key", model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000, max_calls=4, max_cost_usd=0.01) as owned:
        assert owned._client is None
        await owned.evaluate("state", questions)
    assert transport.is_closed
