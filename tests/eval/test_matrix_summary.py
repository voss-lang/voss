"""Matrix summary skipped-column scaffold (EVGLD-06)."""
from __future__ import annotations

import json
from pathlib import Path

from voss.eval.summary import write_summary


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_summary_renders_skipped_header(tmp_path: Path) -> None:
    """EVGLD-06: summary mentions skipped toolchain-absent rows."""
    jsonl = tmp_path / "runs.jsonl"
    rows = [
        {
            "task_id": "py-01-analyze",
            "success": True,
            "cost_usd": 0.02,
            "confidence": 0.9,
            "provider": "StubProvider",
            "model": "__stub__",
            "gate_pass": True,
            "skipped": False,
        },
        {
            "task_id": "rust-03-approved-edit",
            "success": None,
            "cost_usd": None,
            "confidence": None,
            "provider": "StubProvider",
            "model": "__stub__",
            "gate_pass": None,
            "skipped": True,
            "skip_reason": "toolchain-absent",
        },
    ]
    _write_rows(jsonl, rows)

    text = write_summary(jsonl, tmp_path / "summary.md").read_text()

    assert "- skipped rate:" in text
    assert "toolchain-absent" in text


def test_summary_renders_skipped_column(tmp_path: Path) -> None:
    """EVGLD-06: per-task table includes a skipped column (never silent-green)."""
    jsonl = tmp_path / "runs.jsonl"
    rows = [
        {
            "task_id": "py-02-plan-only",
            "success": True,
            "cost_usd": 0.01,
            "confidence": 0.8,
            "provider": "StubProvider",
            "model": "__stub__",
            "gate_pass": True,
            "skipped": False,
        },
        {
            "task_id": "rust-04-validation",
            "success": None,
            "cost_usd": None,
            "confidence": None,
            "provider": "StubProvider",
            "model": "__stub__",
            "gate_pass": None,
            "skipped": True,
            "skip_reason": "toolchain-absent",
        },
    ]
    _write_rows(jsonl, rows)

    text = write_summary(jsonl, tmp_path / "summary.md").read_text()

    assert (
        "| task | runs | gate pass | skipped | pass rate | mean cost |" in text
    )
