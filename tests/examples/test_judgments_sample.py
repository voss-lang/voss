from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest

from tests.codegen.helpers import load_module_from_path, write_generated_module
from voss.analyzer import analyze
from voss.codegen import generate_python
from voss.parser import parse
from voss_runtime import judgments as j

SAMPLES = Path(__file__).resolve().parents[2] / "examples" / "judgments"


def _compiled_source() -> str:
    program = parse((SAMPLES / "triage.voss").read_text())
    analysis = analyze(program, emit_indexes=False)
    return generate_python(program, analysis=analysis).source


def _load_voss(tmp_path):
    path = write_generated_module(tmp_path, "triage_voss", _compiled_source())
    return load_module_from_path(path, "triage_voss")


def _load_py(tmp_path):
    spec = importlib.util.spec_from_file_location("triage_py", SAMPLES / "triage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
async def transport(monkeypatch):
    state = {"requests": [], "probability": None, "clients": []}

    def handler(request):
        state["requests"].append(request)
        p = state["probability"]
        return httpx.Response(200, json={
            "model": "jev-1.13.0",
            "answers": {"route": {"type": "choice", "choice": "billing", "probabilities": {"billing": p, "other": round(1 - p, 2)}, "confidence": 0.5}},
            "usage": {"input_tokens": 10, "output_tokens": 0},
        })

    def factory(api_key, cfg, ledger):
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


def test_generated_source_awaits_judge_only():
    source = _compiled_source()
    assert "await judge(" in source
    assert ".to_probable()" in source
    assert "await to_probable" not in source
    assert "0.9" not in source


@pytest.mark.parametrize("p,expected", [(0.79, "unknown"), (0.81, "billing")])
@pytest.mark.parametrize("load", [_load_voss, _load_py], ids=["voss", "python"])
async def test_gate_at_0_80(transport, tmp_path, load, p, expected):
    transport["probability"] = p
    module = load(tmp_path)
    assert await module.triage("refund please") == expected
    assert len(transport["requests"]) == 1


@pytest.mark.parametrize("load", [_load_voss, _load_py], ids=["voss", "python"])
async def test_kill_switch_makes_zero_calls(transport, monkeypatch, tmp_path, load):
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    module = load(tmp_path)
    with pytest.raises(j.JudgmentError) as caught:
        await module.triage("refund please")
    assert caught.value.outcome == "disabled"
    assert transport["requests"] == [] and transport["clients"] == []
