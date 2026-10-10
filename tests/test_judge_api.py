import asyncio
import json

import httpx
import pytest

import voss_runtime
from voss.harness.config import JUDGMENTS_DEFAULTS
from voss_runtime import judgments as j
from voss_runtime._config import RuntimeConfig, configure, get_config, reset_config
from voss_runtime.probable import ProbableValue

QUESTION = j.ChoiceQuestion("Which queue?", {"billing": "Payment issue.", "other": "Anything else."})
WIRE = {"type": "choice", "instructions": "Which queue?", "criteria": {"billing": "Payment issue.", "other": "Anything else."}}
BODY = {
    "model": "jev-1.13.0",
    "answers": {"route": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.81, "other": 0.19}, "confidence": 0.62}},
    "usage": {"input_tokens": 10, "output_tokens": 0},
}


@pytest.fixture(autouse=True)
def _config_reset():
    yield
    reset_config()


@pytest.fixture
async def fake(monkeypatch):
    state = {"requests": [], "factory_calls": [], "clients": [], "handler": None}

    def handler(request):
        state["requests"].append(request)
        if state["handler"] is not None:
            return state["handler"](request)
        return httpx.Response(200, json=BODY)

    def factory(api_key, cfg, ledger):
        state["factory_calls"].append((api_key, cfg, ledger))
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        state["clients"].append(http)
        return j.JevClient(
            api_key, model=cfg.judgments_model, timeout_ms=cfg.judgments_timeout_ms,
            max_request_bytes=cfg.judgments_max_request_bytes, max_calls=cfg.judgments_max_calls_per_turn,
            max_cost_usd=cfg.judgments_max_cost_usd, client=http, ledger=ledger,
        )

    monkeypatch.setattr(j, "_new_client", factory)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    yield state
    for http in state["clients"]:
        await http.aclose()


async def test_object_and_wire_dict_send_identical_requests(fake):
    first = await j.judge("refund please", {"route": QUESTION})
    second = await j.judge("refund please", {"route": WIRE})
    assert [json.loads(r.content) for r in fake["requests"]] == [
        {"model": "jev-1.13.0", "state": "refund please", "questions": {"route": WIRE}},
    ] * 2
    assert isinstance(first.answers["route"], j.ChoiceResult)
    assert first.answers == second.answers


async def test_receipt_matches_ledger_entry(fake):
    async with j.JudgmentLedger(4, 1.0) as ledger:
        result = await j.judge("refund please", {"route": QUESTION})
    assert len(ledger.receipts) == 1
    assert result.receipt == ledger.receipt(result.receipt.call_id) == ledger.receipts[0]
    assert (result.receipt.status, result.receipt.purpose) == ("answered", "explicit")


async def test_concurrent_calls_get_distinct_call_ids(fake):
    async with j.JudgmentLedger(4, 1.0) as ledger:
        a, b = await asyncio.gather(j.judge("x", {"route": QUESTION}), j.judge("y", {"route": QUESTION}))
    assert a.receipt.call_id != b.receipt.call_id
    assert len(ledger.receipts) == 2


@pytest.mark.parametrize("value", ["off", " OFF ", "0", "false"])
async def test_kill_switch_makes_zero_calls(fake, monkeypatch, value):
    monkeypatch.setenv("VOSS_JUDGMENTS", value)
    with pytest.raises(j.JudgmentError) as caught:
        await j.judge("x", {"route": QUESTION})
    assert caught.value.outcome == "disabled"
    assert str(caught.value) == j.KILLED_MESSAGE
    assert fake["factory_calls"] == [] and fake["requests"] == []


async def test_missing_key_makes_zero_calls(fake, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    with pytest.raises(j.JudgmentError) as caught:
        await j.judge("x", {"route": QUESTION})
    assert caught.value.outcome == "unavailable"
    assert str(caught.value) == j.MISSING_KEY_MESSAGE
    assert fake["factory_calls"] == [] and fake["requests"] == []


@pytest.mark.parametrize("raw,message", [
    ({"type": "bogus", "instructions": "?", "criteria": {"a": None, "b": None}}, "question type must be choice, score, or noul"),
    ({"type": "choice", "criteria": {"a": None, "b": None}}, "each question needs an ID and instructions"),
])
async def test_malformed_wire_dict_raises_before_call(fake, raw, message):
    with pytest.raises(ValueError, match=message):
        await j.judge("x", {"route": raw})
    assert fake["factory_calls"] == [] and fake["requests"] == []


async def test_non_question_value_raises_type_error(fake):
    with pytest.raises(TypeError):
        await j.judge("x", {"route": "which queue?"})
    assert fake["requests"] == []


async def test_ambient_ledger_is_reused(fake):
    async with j.JudgmentLedger(1, 1.0) as ledger:
        await j.judge("x", {"route": QUESTION})
        with pytest.raises(j.JudgmentError) as caught:
            await j.judge("x", {"route": QUESTION})
    assert caught.value.outcome == "budget_exhausted"
    assert len(fake["requests"]) == 1
    assert all(call[2] is ledger for call in fake["factory_calls"])


async def test_explicit_ledger_wins_over_ambient(fake):
    explicit = j.JudgmentLedger(4, 1.0)
    async with j.JudgmentLedger(4, 1.0) as ambient:
        await j.judge("x", {"route": QUESTION}, ledger=explicit)
    assert len(explicit.receipts) == 1 and ambient.receipts == []


async def test_one_call_ledger_from_runtime_config(fake):
    configure(judgments_max_calls_per_turn=2, judgments_max_cost_usd=0.5, judgments_model="jev-test")
    await j.judge("x", {"route": QUESTION})
    _, cfg, ledger = fake["factory_calls"][0]
    assert cfg is get_config()
    assert (ledger.max_calls, ledger.max_cost_usd) == (2, 0.5)
    assert json.loads(fake["requests"][0].content)["model"] == "jev-test"


def test_new_client_uses_runtime_config_limits():
    configure(judgments_model="jev-x", judgments_timeout_ms=1234, judgments_max_request_bytes=999,
              judgments_max_calls_per_turn=3, judgments_max_cost_usd=0.2)
    ledger = j.JudgmentLedger(3, 0.2)
    client = j._new_client("k", get_config(), ledger)
    assert (client.model, client.timeout_ms, client.max_request_bytes, client.max_calls, client.max_cost_usd) == ("jev-x", 1234, 999, 3, 0.2)
    assert client.ledger is ledger


async def test_transport_failure_raises_with_receipt(fake):
    def fail(request):
        raise httpx.ConnectError("boom")

    fake["handler"] = fail
    with pytest.raises(j.JudgmentError) as caught:
        await j.judge("x", {"route": QUESTION})
    assert caught.value.outcome == "unavailable"
    assert caught.value.receipt is not None and caught.value.receipt.status == "unavailable"


def test_to_probable_uses_choice_probability():
    result = j.ChoiceResult("a", {"a": 0.81, "b": 0.19}, 0.62)
    assert j.to_probable(result) == ProbableValue("a", 0.81)
    assert result.to_probable() == ProbableValue("a", 0.81)
    assert result.confidence == 0.62 and result.probabilities == {"a": 0.81, "b": 0.19}


@pytest.mark.parametrize("result", [j.ScoreResult(1.0, {"0": 0.2, "1": 0.8}, 0.7), j.NoulResult(0.9)])
def test_to_probable_rejects_score_and_noul(result):
    with pytest.raises(TypeError):
        j.to_probable(result)


def test_runtime_config_defaults_match_harness_defaults():
    cfg = RuntimeConfig()
    assert {
        "model": cfg.judgments_model,
        "timeout_ms": cfg.judgments_timeout_ms,
        "max_calls_per_turn": cfg.judgments_max_calls_per_turn,
        "max_request_bytes": cfg.judgments_max_request_bytes,
        "max_cost_usd": cfg.judgments_max_cost_usd,
    } == JUDGMENTS_DEFAULTS


def test_runtime_config_repr_never_holds_key(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "sentinel-key-6f3a")
    assert "sentinel-key-6f3a" not in repr(get_config())


def test_public_exports():
    names = {"judge", "to_probable", "ChoiceQuestion", "ScoreQuestion", "NoulQuestion", "ChoiceResult",
             "ScoreResult", "NoulResult", "JudgmentResult", "JudgmentError", "JevClient"}
    assert names <= set(voss_runtime.__all__)
    assert all(getattr(voss_runtime, n) is getattr(j, n) for n in names)
