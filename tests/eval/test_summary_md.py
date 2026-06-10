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
    assert "gate pass rate" in text
    assert "| task | runs | gate pass | pass rate | mean cost |" in text


def test_summary_renders_exact_markdown_bytes(tmp_path: Path) -> None:
    run_dir = tmp_path / "eval-run"
    run_dir.mkdir()
    jsonl = run_dir / "runs.jsonl"
    rows = [
        {
            "task_id": "01-alpha",
            "success": True,
            "cost_usd": 0.02,
            "confidence": 0.9,
            "provider": "StubProvider",
            "model": "__stub__",
        },
        {
            "task_id": "02-beta",
            "success": False,
            "cost_usd": 0.04,
            "confidence": 0.3,
            "provider": "StubProvider",
            "model": "__stub__",
        },
    ]
    _write_rows(jsonl, rows)

    text = write_summary(jsonl, run_dir / "summary.md").read_text()

    assert text == (
        "# voss eval — eval-run\n"
        "\n"
        "- runs: 2\n"
        "- provider: `StubProvider` · model: `__stub__`\n"
        "- overall success rate: 50% (1/2)\n"
        "- gate pass rate: n/a (0/0)\n"
        "- judge pass rate: n/a (0/0)\n"
        "- mean cost: $0.0300\n"
        "- conf_corr_r: 1.000 (n=2)\n"
        "\n"
        "## Per-task\n"
        "\n"
        "| task | runs | gate pass | pass rate | mean cost |\n"
        "|------|-----:|----------:|----------:|----------:|\n"
        "| `01-alpha` | 1 | n/a | 100% | $0.0200 |\n"
        "| `02-beta` | 1 | n/a | 0% | $0.0400 |\n"
    )


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
