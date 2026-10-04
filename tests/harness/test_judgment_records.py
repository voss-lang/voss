import asyncio
import json
from dataclasses import asdict
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from voss_runtime import EpisodicMemory
from voss_runtime import judgments as j

from voss.harness import session as session_store
from voss.harness.recorder import RunRecorder, write_decisions_md
from voss.harness.server import app as appmod

SENTINEL = "SENTINEL-c41e"
TOKEN = "test-token-abc123"


@pytest.fixture(autouse=True)
def state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


@pytest.fixture
async def receipt():
    body = {
        "model": "jev-1.13.1",
        "answers": {"pick": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.9, "technical": 0.1}, "confidence": 0.8}},
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))) as http:
        client = j.JevClient(
            "test-key", model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000,
            max_calls=4, max_cost_usd=0.01, client=http, sleep=lambda s: asyncio.sleep(0),
        )
        questions = {"pick": j.ChoiceQuestion(f"{SENTINEL} pick", {"billing": f"{SENTINEL} desc", "technical": None})}
        await client.evaluate({"secret": SENTINEL}, questions)
    return client.ledger.receipts[0]


def _finalized_run(tmp_path, receipt, *, decisions=()):
    rec = RunRecorder.start()
    rec.judgment_receipts.append(asdict(receipt))
    rec.judgments_cost_usd = 0.00042
    rec.decisions.extend(decisions)
    return rec.finalize(tmp_path, 0.01)


def test_finalized_run_carries_judgment_spend_and_receipts(tmp_path, receipt):
    run = _finalized_run(tmp_path, receipt)
    assert run.judgments_cost_usd == 0.00042
    assert run.judgment_receipts == [asdict(receipt)]
    assert run.cost_usd == 0.01
    restored = json.loads(json.dumps(asdict(run)))
    assert restored["judgment_receipts"] == [asdict(receipt)]
    assert restored["judgments_cost_usd"] == 0.00042


def test_pre_judgments_session_loads_with_empty_receipts(tmp_path):
    sessions = tmp_path / ".voss" / "sessions"
    sessions.mkdir(parents=True)
    old = {
        "id": "abc123def456", "name": "old", "cwd": str(tmp_path), "model": "m",
        "started_at": "t0", "updated_at": "t1", "total_cost_usd": 0.02,
        "turns": [], "runs": [{"id": "r1", "started_at": "t0", "ended_at": "t1", "cost_usd": 0.02}],
    }
    (sessions / "abc123def456.json").write_text(json.dumps(old))
    record, _ = session_store.load("abc123def456", cwd=tmp_path)
    assert record.judgments_cost_usd == 0.0
    assert record.total_cost_usd == 0.02
    assert all(r.get("judgment_receipts", []) == [] for r in record.runs)


def test_save_derives_session_judgments_from_runs_only(tmp_path, receipt):
    record = session_store.SessionRecord.new(cwd=tmp_path, model="m")
    record.total_cost_usd = 0.03
    record.runs.append(asdict(_finalized_run(tmp_path, receipt)))
    record.runs.append({"id": "old", "cost_usd": 0.02})
    path = session_store.save(record, EpisodicMemory(capacity=10))
    data = json.loads(path.read_text())
    assert data["judgments_cost_usd"] == pytest.approx(0.00042)
    assert data["total_cost_usd"] == 0.03


def test_saved_session_json_holds_no_request_content(tmp_path, receipt):
    record = session_store.SessionRecord.new(cwd=tmp_path, model="m")
    record.runs.append(asdict(_finalized_run(tmp_path, receipt)))
    text = session_store.save(record, EpisodicMemory(capacity=10)).read_text()
    assert receipt.call_id in text
    for forbidden in (SENTINEL, "test-key", "provider", "api_key", "Authorization"):
        assert forbidden not in text


def test_memory_notes_never_include_receipts(tmp_path, receipt):
    run = _finalized_run(tmp_path, receipt, decisions=[{"title": "pick a path", "body": "chose a", "confidence": 0.8}])
    paths = write_decisions_md(tmp_path, run, "sess1")
    assert paths
    for p in paths:
        text = p.read_text()
        assert receipt.call_id not in text
        assert "judgment" not in text


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (SimpleNamespace(source="test", detail="fake"), object()))
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)
    c = TestClient(appmod.create_app(TOKEN))
    r = c.post("/session", json={"cwd": str(tmp_path)}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 201, r.text
    c.sid = r.json()["id"]
    return c


def _server_cost(client, runs):
    client.app.state.sessions.get(client.sid).record.runs = runs
    r = client.get(f"/session/{client.sid}/cost", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    return r.json()


def test_server_cost_sums_chat_and_judgments_once(client):
    body = _server_cost(client, [{"cost_usd": 0.02, "judgments_cost_usd": 0.001}, {"cost_usd": 0.01}])
    assert body["v"] == 1 and body["turns"] == 2
    assert body["judgments_usd"] == pytest.approx(0.001)
    assert body["total_usd"] == pytest.approx(0.031)


def test_server_cost_unchanged_for_pre_judgments_sessions(client):
    body = _server_cost(client, [{"cost_usd": 0.02}, {"cost_usd": 0.01}])
    assert body["judgments_usd"] == 0.0
    assert body["total_usd"] == pytest.approx(0.03)


@pytest.fixture
def fake_ctx(tmp_path):
    record = SimpleNamespace(id="abc123", name="s", cwd=str(tmp_path), model="m", total_cost_usd=0.0, turns=[], runs=[])
    return SimpleNamespace(cwd=tmp_path, record=record, history=None, last_plan=None, total_cost=0.020, budget_usd=None, prior_context=None)


def _slash_cost(ctx, capsys):
    from voss.harness.cli import _build_slash_registry

    _build_slash_registry().lookup("/cost").handler(ctx, [], "/cost")
    return capsys.readouterr().out


def test_cli_cost_shows_judgments_line_and_total(fake_ctx, capsys):
    fake_ctx.record.runs = [{"cost_usd": 0.008, "judgments_cost_usd": 0.001}, {"cost_usd": 0.012}]
    out = _slash_cost(fake_ctx, capsys)
    assert out.splitlines()[0] == "session cost: $0.0200"
    assert "judgments: $0.0010" in out
    assert "total: $0.0210" in out
    assert fake_ctx.total_cost == 0.020


def test_cli_cost_without_judgments_matches_pre_judgments_output(fake_ctx, capsys):
    fake_ctx.record.runs = [{"cost_usd": 0.008}, {"cost_usd": 0.012}]
    assert _slash_cost(fake_ctx, capsys) == "session cost: $0.0200\n"
    assert fake_ctx.total_cost == 0.020
