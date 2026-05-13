from __future__ import annotations

import json
from pathlib import Path

from voss.eval.summary import write_summary


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_summary_has_required_sections(tmp_path: Path) -> None:
    jsonl = tmp_path / "runs.jsonl"
    rows = [
        {
            "task_id": "01-analyze",
            "success": True,
            "cost_usd": 0.02,
            "confidence": 0.9,
            "provider": "LiteLLMProvider",
            "model": "gpt-test",
        },
        {
            "task_id": "02-plan-only",
            "success": False,
            "cost_usd": 0.04,
            "confidence": 0.3,
            "provider": "LiteLLMProvider",
            "model": "gpt-test",
        },
    ]
    _write_rows(jsonl, rows)

    summary_path = write_summary(jsonl, tmp_path / "summary.md")
    text = summary_path.read_text()

    assert "overall success rate" in text
    assert "mean cost" in text
    assert "conf_corr_r" in text
    assert "01-analyze" in text
    assert "02-plan-only" in text
    assert "| task | runs | pass rate | mean cost |" in text


def test_summary_handles_all_null_cost(tmp_path: Path) -> None:
    jsonl = tmp_path / "runs.jsonl"
    rows = [
        {
            "task_id": "01-analyze",
            "success": True,
            "cost_usd": None,
            "confidence": 0.9,
            "provider": "StubProvider",
            "model": "__stub__",
        },
        {
            "task_id": "02-plan-only",
            "success": False,
            "cost_usd": None,
            "confidence": 0.3,
            "provider": "StubProvider",
            "model": "__stub__",
        },
    ]
    _write_rows(jsonl, rows)

    text = write_summary(jsonl, tmp_path / "summary.md").read_text()

    assert "mean cost: n/a" in text


def test_summary_marks_mixed_provider_and_model(tmp_path: Path) -> None:
    jsonl = tmp_path / "runs.jsonl"
    rows = [
        {
            "task_id": "01-analyze",
            "success": True,
            "cost_usd": None,
            "confidence": 0.9,
            "provider": "ProviderA",
            "model": "model-a",
        },
        {
            "task_id": "02-plan-only",
            "success": True,
            "cost_usd": None,
            "confidence": 0.8,
            "provider": "ProviderB",
            "model": "model-b",
        },
    ]
    _write_rows(jsonl, rows)

    text = write_summary(jsonl, tmp_path / "summary.md").read_text()

    assert "provider: `mixed` · model: `mixed`" in text
