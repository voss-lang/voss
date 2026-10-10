"""J3-11 D-14/D-15/Pitfall 1: in-process recall tasks, paired A/B runs, and `voss eval --ab`."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import yaml
from click.testing import CliRunner

from tests.code_recall.conftest import JevStub, make_candidates, score_body
from voss.eval import ab, runner
from voss.eval.suite import TaskSpec
from voss.harness import cli
from voss.harness.agent import TurnResult
from voss.harness.code.rerank import RUBRIC_VERSION
from voss.harness.config import get_judgments_config
from voss.harness.memory_store import Hit
from voss.harness.session import RunRecord
from voss_runtime import configure, get_config
from voss_runtime.providers import StubProvider

TASK = "where is retry backoff handled"
FAVOR_C07 = {f"c{i:02d}": 3 if i == 7 else 0 for i in range(1, 16)}


class FakeService:
    def __init__(self, pool, *, ready_after=0):
        self.pool = pool
        self.ready_checks = 0
        self.ready_after = ready_after
        self.legacy = [
            Hit(source="code", locator=f"code:legacy/l{i}.py:000", score=0.9 - i / 10, excerpt=f"def legacy_{i}():\n    return {i}", line_start=i + 3)
            for i in range(10)
        ]
        self.candidate_calls = 0
        self.queries: list[tuple[str, int]] = []

    def is_ready(self):
        self.ready_checks += 1
        return self.ready_checks > self.ready_after

    def candidates(self, query):
        self.candidate_calls += 1
        return self.pool

    def query(self, query, top_k=5):
        self.queries.append((query, top_k))
        return self.legacy[:top_k]


@pytest.fixture
def jev(monkeypatch):
    from voss.harness import judgments
    from voss_runtime.judgments import JevClient

    stub = JevStub()

    def factory(key, *, timeout_ms=None, ledger=None):
        return JevClient(
            key, model="jev-1.13.0", timeout_ms=5000 if timeout_ms is None else timeout_ms, max_request_bytes=24000,
            max_calls=4, max_cost_usd=0.01, client=httpx.AsyncClient(transport=httpx.MockTransport(stub.dispatch)), ledger=ledger,
        )

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setattr(judgments, "make_client", factory)
    return stub


@pytest.fixture
def turns(monkeypatch):
    calls: list[dict] = []

    async def run_turn(task, *, tools, code_recall_text=None, **kwargs):
        calls.append({
            "task": task,
            "tools": tools,
            "code_recall_text": code_recall_text,
            "embedding_model": get_config().default_embedding_model,
            **kwargs,
        })
        return TurnResult(plan=None, confidence=1.0, final="done", tool_results=[], cost_usd=0.0, run=RunRecord(id="run", started_at="", ended_at=""))

    monkeypatch.setattr(runner, "run_turn", run_turn)
    return calls


def _use(monkeypatch, svc):
    seen = []

    def get(cwd, session_id=None):
        seen.append((cwd, session_id))
        return svc

    monkeypatch.setattr(cli, "_get_code_recall_service", get)
    return seen


def _spec(**kw):
    return TaskSpec(prompt=TASK, mode="plan", rubric="Pass if it answers.", **kw)


def _config(cwd):
    return yaml.safe_load((cwd / ".voss" / "config.yml").read_text())


async def test_active_recall_task_injects_the_reranked_pool_after_the_index_is_ready(jev, turns, tmp_path, monkeypatch):
    (tmp_path / ".voss").mkdir()
    (tmp_path / ".voss" / "config.yml").write_text("project:\n  name: pinned\njudgments:\n  model: keep-me\n")
    pool = make_candidates(15)
    svc = FakeService(pool, ready_after=2)
    seen = _use(monkeypatch, svc)
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C07))

    record, final, crash, capped = await runner._drive_task(
        "05-background", _spec(recall="active"), cwd=tmp_path, provider=StubProvider(), model="m"
    )

    assert (crash, final, capped) == (None, "done", False)
    assert _config(tmp_path) == {
        "project": {"name": "pinned"},
        "judgments": {"model": "keep-me", "enabled": True, "code_recall": "active"},
    }
    assert set(seen) == {(tmp_path, record.id)}
    assert svc.ready_checks >= 3
    [call] = turns
    assert call["code_recall_text"] == cli._format_code_recall_section([pool[i].hit for i in (6, 0, 1, 2, 3)])
    assert call["session_id"] == record.id
    assert "code_recall" in call["tools"]
    await call["tools"]["code_recall"].descriptor(query="retry", top_k=2)
    assert svc.queries == [("retry", 2)]
    assert len(jev.requests) == 1
    assert len(record.runs[0]["judgment_receipts"]) == 1


async def test_off_recall_task_injects_the_legacy_section_and_never_calls_jev(jev, turns, tmp_path, monkeypatch):
    svc = FakeService(make_candidates(15))
    _use(monkeypatch, svc)

    record, _, crash, _ = await runner._drive_task(
        "01-off", _spec(recall="off"), cwd=tmp_path, provider=StubProvider(), model="m"
    )

    assert crash is None
    assert _config(tmp_path) == {"judgments": {"enabled": True, "code_recall": "off"}}
    assert turns[0]["code_recall_text"] == cli._render_code_recall_text(tmp_path, TASK)
    assert turns[0]["code_recall_text"] == cli._format_code_recall_section(svc.legacy[:5])
    assert jev.requests == [] and svc.candidate_calls == 0
    assert record.runs[0]["judgment_receipts"] == []


async def test_recall_task_whose_index_never_becomes_ready_is_a_crash_row(jev, turns, tmp_path, monkeypatch):
    _use(monkeypatch, FakeService([], ready_after=10**9))
    monkeypatch.setattr(runner, "RECALL_READY_TIMEOUT_S", 0.2)

    _, _, crash, _ = await runner._drive_task(
        "01-slow", _spec(recall="active"), cwd=tmp_path, provider=StubProvider(), model="m"
    )

    assert crash is not None and crash.startswith("TimeoutError")
    assert turns == []


async def test_pinned_task_runs_with_the_local_embedding_model_and_restores_it(jev, turns, tmp_path, monkeypatch):
    _use(monkeypatch, FakeService(make_candidates(15)))
    previous = get_config().default_embedding_model
    configure(default_embedding_model="remote-embedding-sentinel")
    try:
        await runner._drive_task(
            "01-pinned", _spec(recall="off", corpus="pinned"), cwd=tmp_path, provider=StubProvider(), model="m"
        )
        assert turns[0]["embedding_model"] == get_config().local_embedding_model
        assert get_config().default_embedding_model == "remote-embedding-sentinel"
    finally:
        configure(default_embedding_model=previous)


async def test_task_without_recall_keeps_the_plain_turn(turns, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda *a, **k: pytest.fail("no recall service"))

    record, _, crash, _ = await runner._drive_task(
        "01-plain", _spec(), cwd=tmp_path, provider=StubProvider(), model="m"
    )

    assert crash is None
    assert turns[0]["code_recall_text"] is None
    assert "code_recall" not in turns[0]["tools"]
    assert not (tmp_path / ".voss" / "config.yml").exists()
    assert record.runs[0]["judgment_receipts"] == []


def _write_task(root: Path, task_id: str) -> None:
    task_dir = root / "tests" / "eval" / "golden" / task_id
    (task_dir / "fixture").mkdir(parents=True)
    (task_dir / "fixture" / "README.md").write_text("# Fixture\n")
    (task_dir / "task.toml").write_text(f'prompt = "{TASK}"\nmode = "plan"\nrubric = "Pass."\n')


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_rows_carry_the_judgment_receipt_count(jev, turns, tmp_path, monkeypatch):
    _write_task(tmp_path, "01-task")
    monkeypatch.chdir(tmp_path)
    _use(monkeypatch, FakeService(make_candidates(15)))
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C07))

    runner.run_suite(stub=True, out=tmp_path / "active", overrides={"recall": "active"}, judge=False)
    runner.run_suite(stub=True, out=tmp_path / "plain")

    assert [r["judgment_receipt_count"] for r in _rows(tmp_path / "active" / "runs.jsonl")] == [1]
    assert [r["judgment_receipt_count"] for r in _rows(tmp_path / "plain" / "runs.jsonl")] == [0]


def _row(task_id, passed, receipts=0):
    return {"task_id": task_id, "run_idx": 0, "gate_pass": passed, "capped": False, "judgment_receipt_count": receipts}


FIRST = {
    "off": {"t1": True, "t2": True, "t3": False},
    "active": {"t1": True, "t2": False, "t3": True},
}


def test_run_ab_reruns_only_disagreements_and_writes_the_contract(tmp_path, monkeypatch):
    calls = []

    def fake_run_suite(*, suite, out, overrides, judge, task=None, **kwargs):
        calls.append({"suite": suite, "out": out, "overrides": overrides, "judge": judge, "task": task, **kwargs})
        value = overrides["recall"]
        receipts = 1 if value == "active" else 0
        rows = [_row(t, p, receipts) for t, p in FIRST[value].items() if task in (None, t)]
        out.mkdir(parents=True)
        (out / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        return out

    monkeypatch.setattr(runner, "run_suite", fake_run_suite)
    meta = {"jev_model": "jev-x", "rubric_version": "rv", "generation_model": "gen"}

    out = ab.run_ab(suite="code-recall-ab", setting="recall", a="off", b="active", out=tmp_path, metadata=meta, stub=True, max_turns=3)

    assert out == tmp_path
    assert [(c["out"], c["overrides"], c["task"]) for c in calls] == [
        (tmp_path / "a", {"recall": "off"}, None),
        (tmp_path / "b", {"recall": "active"}, None),
        (tmp_path / "rerun" / "a" / "t2", {"recall": "off"}, "t2"),
        (tmp_path / "rerun" / "b" / "t2", {"recall": "active"}, "t2"),
        (tmp_path / "rerun" / "a" / "t3", {"recall": "off"}, "t3"),
        (tmp_path / "rerun" / "b" / "t3", {"recall": "active"}, "t3"),
    ]
    assert all(c["judge"] is False and c["suite"] == "code-recall-ab" and c["stub"] is True and c["max_turns"] == 3 for c in calls)

    a_rows = [_row(t, p) for t, p in FIRST["off"].items()] + [_row("t2", True), _row("t3", False)]
    b_rows = [_row(t, p, 1) for t, p in FIRST["active"].items()] + [_row("t2", False, 1), _row("t3", True, 1)]
    expected = ab.compare(a_rows, b_rows)
    assert expected["regressions"] == ["t2"] and expected["passed"] is False
    payload = json.loads((tmp_path / "ab.json").read_text())
    assert payload == {
        "schema_version": 1,
        "setting": "recall",
        "a": "off",
        "b": "active",
        **meta,
        "a_judgment_receipts": 0,
        "b_judgment_receipts": 5,
        "compare": expected,
        "passed": False,
    }
    assert (tmp_path / "ab.md").read_text() == ab.render(expected, a_label="recall=off", b_label="recall=active")


def test_run_ab_without_disagreements_runs_each_side_once(tmp_path, monkeypatch):
    calls = []

    def fake_run_suite(*, out, overrides, task=None, **kwargs):
        calls.append(task)
        out.mkdir(parents=True)
        (out / "runs.jsonl").write_text(json.dumps(_row("t1", True)) + "\n")
        return out

    monkeypatch.setattr(runner, "run_suite", fake_run_suite)

    ab.run_ab(suite="s", setting="recall", a="off", b="active", out=tmp_path)

    assert calls == [None, None]
    payload = json.loads((tmp_path / "ab.json").read_text())
    assert payload["passed"] is True and "jev_model" not in payload


def _no_run_suite(**kwargs):
    pytest.fail("run_suite must not be called")


def test_eval_ab_passes_recall_metadata_to_run_ab(tmp_path, monkeypatch):
    seen = {}

    def fake_run_ab(**kwargs):
        seen.update(kwargs)
        return kwargs["out"]

    monkeypatch.setattr(ab, "run_ab", fake_run_ab)
    monkeypatch.setattr(runner, "run_suite", _no_run_suite)

    result = CliRunner().invoke(cli.eval_cmd, ["--suite", "code-recall-ab", "--ab", "recall=off,active", "--stub", "--max-turns", "4", "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert seen == {
        "suite": "code-recall-ab",
        "setting": "recall",
        "a": "off",
        "b": "active",
        "out": tmp_path,
        "metadata": {
            "jev_model": get_judgments_config()["model"],
            "rubric_version": RUBRIC_VERSION,
            "generation_model": get_config().default_model,
        },
        "stub": True,
        "live": False,
        "auth_pref": "auto",
        "max_turns": 4,
        "require_all_toolchains": False,
    }
    assert str(tmp_path / "ab.md") in result.output


@pytest.mark.parametrize("spec", ["recall", "recall=off", "nope=a,b", "recall=off,", "recall=a,b,c"])
def test_eval_ab_rejects_a_malformed_spec(spec, monkeypatch):
    monkeypatch.setattr(ab, "run_ab", lambda **kw: pytest.fail("run_ab must not be called"))
    monkeypatch.setattr(runner, "run_suite", _no_run_suite)

    result = CliRunner().invoke(cli.eval_cmd, ["--ab", spec])

    assert result.exit_code == 2
    assert "FIELD=A,B" in result.output


def test_eval_without_ab_calls_run_suite_as_before(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(ab, "run_ab", lambda **kw: pytest.fail("run_ab must not be called"))
    monkeypatch.setattr(runner, "run_suite", lambda **kw: seen.update(kw))

    result = CliRunner().invoke(cli.eval_cmd, ["--stub", "--task", "01-x", "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert seen == {
        "suite": "golden",
        "stub": True,
        "live": False,
        "k": 1,
        "out": tmp_path,
        "judge_model": None,
        "task": "01-x",
        "auth_pref": "auto",
        "max_turns": None,
        "require_all_toolchains": False,
    }


def test_eval_help_lists_ab():
    result = CliRunner().invoke(cli.eval_cmd, ["--help"])
    assert "--ab" in result.output and "FIELD=A,B" in result.output
