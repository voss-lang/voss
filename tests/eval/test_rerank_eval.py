"""J3-08 S3.5/D-17/D-19: rerank eval artifacts, latency gate, gate file, one-shot test split."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tests.code_recall import conftest as code_recall
from tests.eval.test_retrieval_loader import POOL, default_queries, query, write_dataset
from voss.eval import retrieval
from voss.eval.retrieval import LATENCY_MIN_SAMPLES, latency_gate, main
from voss.harness import judgments
from voss.harness.code.rerank import RUBRIC_VERSION

jev = code_recall.jev

LOCATION = "test-loc"
FAILING = "b01-g001-q1"
LEVELS = {"c01": 0, "c02": 0, "c03": 0, "c04": 1, "c05": 2, "c06": 3}
REORDERED = [POOL[5], POOL[4], POOL[3], POOL[0], POOL[1], POOL[2]]
SAMPLE_KEYS = {"query_id", "request_bytes", "location", "model", "latency_ms", "status", "fallback_reason"}
GATE_KEYS = {
    "schema_version", "status", "split", "commit", "model", "rubric_version", "location", "run_date",
    "ranking", "latency", "fallbacks", "passed",
}


def chunk_map() -> dict[str, tuple[str, int, int, str]]:
    return {cid: (cid.split(":")[1], 1, 9, f"def {cid.split(':')[1][0]}():\n    return 1\n") for cid in POOL}


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(retrieval, "_pinned_chunks", chunk_map)
    return write_dataset(tmp_path / "data", queries=default_queries() + [query("b03-g001-q1", "dev")])


def answer(request: httpx.Request) -> httpx.Response:
    state = json.loads(request.content)["state"]
    if state["task"] == f"where is {FAILING}":
        return httpx.Response(500)
    return httpx.Response(200, json=code_recall.score_body(LEVELS))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def rerank(root: Path, *extra: str) -> int:
    return main(["rerank", "--root", str(root), "--location", LOCATION, *extra])


def test_dev_run_writes_candidate_receipts_and_samples(root: Path, jev) -> None:
    jev.handler = answer

    assert rerank(root) == 0

    out = root / "reports" / "rerank-dev"
    candidate = {row["query_id"]: row["ranking"] for row in read_jsonl(out / "candidate.jsonl")}
    receipts = read_jsonl(out / "receipts.jsonl")
    samples = read_jsonl(out / "samples.jsonl")
    dev = {"b01-g001-q1", "b01-g001-q2", "b02-g001-q1", "b03-g001-q1"}
    assert set(candidate) == dev
    assert len(receipts) == 4 and {r["mode"] for r in receipts} == {"active"}
    assert [s["query_id"] for s in samples] == list(candidate)
    assert all(set(s) == SAMPLE_KEYS and s["location"] == LOCATION and s["request_bytes"] > 0 for s in samples)
    assert {s["query_id"]: s["status"] for s in samples}[FAILING] == "unavailable"
    assert len(jev.requests) == 4
    tasks = set()
    for request in jev.requests:
        state = json.loads(request.content)["state"]
        assert "query" not in state
        tasks.add(state["task"])
    assert tasks == {f"where is {qid}" for qid in dev}
    assert candidate["b01-g001-q2"] == REORDERED


def test_fallback_query_keeps_the_baseline_ranking(root: Path, jev) -> None:
    jev.handler = answer

    assert rerank(root) == 0

    rows = read_jsonl(root / "reports" / "rerank-dev" / "candidate.jsonl")
    ranking = next(row["ranking"] for row in rows if row["query_id"] == FAILING)
    assert ranking == POOL
    sample = next(s for s in read_jsonl(root / "reports" / "rerank-dev" / "samples.jsonl") if s["query_id"] == FAILING)
    assert sample["fallback_reason"] == "unavailable"


def test_markdown_has_gate_shadow_and_latency_sections(root: Path, jev) -> None:
    jev.handler = answer

    assert rerank(root) == 0

    text = (root / "reports" / "rerank-dev.md").read_text()
    assert "# Code recall rerank (dev)" in text
    assert "- gate: **" in text
    assert "## Shadow" in text and "gain 0.0 by definition" in text
    assert "## Latency gate" in text and f"`{LOCATION}`" in text


@pytest.mark.parametrize("env", ["killed", "no-key"])
def test_refuses_without_jev_before_any_request(root: Path, jev, monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    if env == "killed":
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    else:
        monkeypatch.setattr(judgments, "resolve_api_key", lambda: None)

    assert rerank(root) == 2

    assert jev.requests == []
    assert not (root / "reports").exists()


def test_missing_pool_chunk_refuses_before_any_request(root: Path, jev, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(retrieval, "_pinned_chunks", lambda: {k: v for k, v in chunk_map().items() if k != POOL[2]})

    assert rerank(root) == 2

    assert POOL[2] in capsys.readouterr().err
    assert jev.requests == []
    assert not (root / "reports").exists()


def receipt(status: str, latency_ms: float, attempts: int = 1) -> dict:
    return {"status": status, "latency_ms": latency_ms, "attempts": attempts}


def test_latency_gate_passes_at_100_answered_under_the_p95_cap() -> None:
    result = latency_gate([receipt("answered", 200)] * LATENCY_MIN_SAMPLES)

    assert result == {"n": 100, "p50_ms": 200, "p95_ms": 200, "passed": True}


def test_latency_gate_fails_below_100_answered() -> None:
    result = latency_gate([receipt("answered", 200)] * (LATENCY_MIN_SAMPLES - 1))

    assert result["n"] == 99 and result["passed"] is False


def test_latency_gate_counts_timeouts_in_p95() -> None:
    receipts = [receipt("answered", 200)] * 100 + [receipt("unavailable", 1500)] * 20

    result = latency_gate(receipts)

    assert result["n"] == 100
    assert result["p95_ms"] > 1000 and result["passed"] is False


def test_latency_gate_ignores_zero_attempt_receipts() -> None:
    receipts = [receipt("answered", 200)] * 100 + [receipt("unavailable", 5000, attempts=0)] * 20

    result = latency_gate(receipts)

    assert result["p95_ms"] == 200 and result["passed"] is True
    assert latency_gate([receipt("answered", 200)])["p95_ms"] is None


def test_dev_gate_file_has_the_activate_contract(root: Path, jev) -> None:
    jev.handler = answer

    assert rerank(root) == 0

    gate_file = json.loads((root / "reports" / "rerank-dev.json").read_text())
    assert set(gate_file) == GATE_KEYS
    assert gate_file["status"] == "complete" and gate_file["split"] == "dev"
    assert gate_file["schema_version"] == 1
    assert gate_file["commit"] == "a" * 40
    assert gate_file["model"] == "jev-1.13.0"
    assert gate_file["rubric_version"] == RUBRIC_VERSION
    assert gate_file["location"] == LOCATION
    assert set(gate_file["ranking"]) == {"mean_gain", "ci_low", "ci_high", "recall_diff", "passed"}
    assert set(gate_file["latency"]) == {"n", "p50_ms", "p95_ms", "passed"}
    assert gate_file["latency"]["n"] == 3
    assert gate_file["fallbacks"] == {"unavailable": 1}
    assert gate_file["passed"] == (gate_file["ranking"]["passed"] and gate_file["latency"]["passed"])


def test_dev_runs_can_repeat(root: Path, jev) -> None:
    jev.handler = answer

    assert rerank(root) == 0
    assert rerank(root) == 0

    assert len(jev.requests) == 8
    assert json.loads((root / "reports" / "rerank-dev.json").read_text())["status"] == "complete"


def test_test_split_without_locked_final_refuses(root: Path, jev, capsys) -> None:
    assert rerank(root, "--split", "test") == 2

    assert "--locked-final" in capsys.readouterr().err
    assert jev.requests == []
    assert not (root / "reports" / "rerank-test.json").exists()


def test_test_split_runs_once_with_a_started_marker(root: Path, jev, capsys) -> None:
    marker = root / "reports" / "rerank-test.json"

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(marker.read_text())["status"] == "started"
        return httpx.Response(200, json=code_recall.score_body(LEVELS))

    jev.handler = handler

    assert rerank(root, "--split", "test", "--locked-final") == 0

    assert len(jev.requests) == 2
    gate_file = json.loads(marker.read_text())
    assert gate_file["status"] == "complete" and gate_file["split"] == "test"
    assert set(gate_file) == GATE_KEYS
    capsys.readouterr()

    assert rerank(root, "--split", "test", "--locked-final") == 2

    err = capsys.readouterr().err
    assert "reports/rerank-test.json" in err and "D-19" in err
    assert len(jev.requests) == 2
