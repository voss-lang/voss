from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from tests.eval.test_retrieval_loader import write_dataset
from voss.eval.retrieval import load_dataset, main, render_report
from voss_runtime.judgments import JudgmentReceipt

HEADINGS = [
    "## Dataset", "## Ranking metrics", "## Adversarial subset", "## Ambiguous", "## Calibration",
    "## Errors and fallbacks", "## Cost", "## Latency", "## Model and rubric",
]
SCOPE = "metrics describe ranking of a fixed candidate pool, not complete user tasks"


def receipt(status: str, latency_ms: float, *, cost: float | None, fallback: str | None = None) -> dict:
    return dataclasses.asdict(
        JudgmentReceipt(
            call_id=f"call-{latency_ms}", purpose="rerank", rubric_version="rubric-1",
            model_requested="jev-1.13.0", model_returned="jev-1.13.0", mode="choice", status=status,
            fallback_reason=fallback, attempts=1, input_tokens=10, output_tokens=2, cost_usd=cost,
            held_usd=0.001, latency_ms=latency_ms, answers={}, artifact_revision=None,
        )
    )


def receipts() -> list[dict]:
    return [
        receipt("answered", 100, cost=0.002),
        receipt("answered", 200, cost=0.002),
        receipt("answered", 300, cost=0.002),
        receipt("unavailable", 400, cost=None, fallback="timeout"),
    ]


def test_baseline_report_has_every_section_and_no_judgments(tmp_path: Path) -> None:
    dataset = load_dataset(write_dataset(tmp_path))

    report = render_report(dataset, dataset.pools)

    for heading in HEADINGS:
        assert heading in report
    assert SCOPE in report
    assert "n/a: retrieval labels carry no probabilities" in report
    assert report.count("no judgments") == 4
    assert "baseline nDCG@5" in report
    assert "- gate:" not in report


def test_comparison_report_renders_gate_and_receipts(tmp_path: Path) -> None:
    dataset = load_dataset(write_dataset(tmp_path))
    candidate = {qid: list(reversed(pool)) for qid, pool in dataset.pools.items()}

    report = render_report(dataset, dataset.pools, candidate, receipts())

    assert "gate: **FAIL**" in report
    assert "0.03" in report
    assert "status answered: 3" in report
    assert "status unavailable: 1" in report
    assert "fallback timeout: 1" in report
    assert "observed: $0.0060" in report
    assert "held: $0.0040" in report
    assert "p50: 250 ms" in report
    assert "p95: " in report and "p95: n/a" not in report
    assert "model: `jev-1.13.0`" in report
    assert "rubric: `rubric-1`" in report
    assert "no judgments" not in report


def test_report_latency_and_model_degrade_with_few_or_mixed_receipts(tmp_path: Path) -> None:
    dataset = load_dataset(write_dataset(tmp_path))
    mixed = receipts()[:2]
    mixed[1]["model_returned"] = "jev-1.14.0"

    report = render_report(dataset, dataset.pools, receipts=receipts()[:1])
    assert "p50: n/a" in report and "p95: n/a" in report

    assert "model: `mixed`" in render_report(dataset, dataset.pools, receipts=mixed)


def test_report_test_split_requires_locked_final(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = write_dataset(tmp_path / "data")

    assert main(["report", "--root", str(root), "--split", "test"]) == 2
    assert "--locked-final" in capsys.readouterr().err

    assert main(["report", "--root", str(root), "--split", "test", "--locked-final"]) == 0
    assert "split: `test`" in capsys.readouterr().out


def test_report_writes_out_file_with_candidate_and_receipts(tmp_path: Path) -> None:
    root = write_dataset(tmp_path / "data")
    dataset = load_dataset(root)
    candidate_path = tmp_path / "candidate.jsonl"
    candidate_path.write_text(
        "".join(json.dumps({"query_id": qid, "ranking": pool}) + "\n" for qid, pool in dataset.pools.items())
    )
    receipts_path = tmp_path / "receipts.jsonl"
    receipts_path.write_text("".join(json.dumps(row) + "\n" for row in receipts()))
    out = tmp_path / "report.md"

    code = main([
        "report", "--root", str(root), "--candidate", str(candidate_path),
        "--receipts", str(receipts_path), "--out", str(out),
    ])

    assert code == 0
    text = out.read_text()
    assert "split: `dev`" in text
    assert "gate: **FAIL**" in text
    assert "status answered: 3" in text
