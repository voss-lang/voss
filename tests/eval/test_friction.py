"""V20-02 friction reducer tests (VRES-02) — synthetic run dicts, no live model."""
from __future__ import annotations

from types import SimpleNamespace

from voss.eval.friction import friction


def _record(runs: list[dict]) -> SimpleNamespace:
    """SessionRecord-shaped object: friction() only reads .runs."""
    return SimpleNamespace(runs=runs)


ZERO = {
    "failed_tools": 0,
    "failed_validations": 0,
    "retries": 0,
    "help_probes": 0,
    "wasted_calls": 0,
}


def test_friction_counts_planted_failures():
    record = _record(
        [
            {
                "failures": [
                    {"tool": "fs_edit", "error": "no match"},
                    {"tool": "shell_run", "error": "timeout"},
                ],
                "validation": [],
            },
            {"failures": [{"tool": "fs_read", "error": "absent"}], "validation": []},
        ]
    )
    result = friction(record)
    assert result["failed_tools"] == 3
    assert result["wasted_calls"] == 3


def test_friction_counts_red_validations():
    record = _record(
        [
            {
                "failures": [],
                "validation": [
                    {"cmd": "pytest -q", "exit": 1, "summary": "1 failed"},
                    {"cmd": "ruff check .", "exit": 2, "summary": "errors"},
                    {"cmd": "pytest -q tests/x", "exit": 0, "summary": "ok"},
                    {"cmd": "mypy voss", "exit": None, "summary": ""},
                ],
            }
        ]
    )
    result = friction(record)
    assert result["failed_validations"] == 2
    assert result["wasted_calls"] == 2


def test_friction_zero_clean_run():
    record = _record([{"failures": [], "validation": []}])
    assert friction(record) == ZERO


def test_friction_repeat_command_retries():
    record = _record(
        [
            {
                "failures": [],
                "validation": [
                    {"cmd": "pytest -q", "exit": 0, "summary": "ok"},
                    {"cmd": "pytest -q", "exit": 0, "summary": "ok"},
                    {"cmd": "pytest -q", "exit": 0, "summary": "ok"},
                    {"cmd": "voss sync --help", "exit": 0, "summary": "usage"},
                ],
            }
        ]
    )
    result = friction(record)
    assert result["retries"] == 2  # k=3 -> k-1
    assert result["help_probes"] == 1
    assert result["wasted_calls"] == 3


def test_friction_missing_keys_tolerated():
    # Old transcripts: run dicts without failures/validation, junk entries.
    record = _record([{}, {"failures": None, "validation": None}, "not-a-dict"])
    assert friction(record) == ZERO


def test_summary_friction_column_additive(tmp_path):
    """Column renders only when rows carry friction; legacy rows unaffected."""
    import json

    from voss.eval.summary import write_summary

    base = {
        "task_id": "01-x",
        "success": True,
        "cost_usd": 0.02,
        "confidence": 0.9,
        "provider": "StubProvider",
        "model": "__stub__",
    }
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text(json.dumps(base) + "\n")
    text = write_summary(legacy, tmp_path / "legacy.md").read_text()
    assert "wasted" not in text  # byte-stable legacy summary

    jsonl = tmp_path / "runs.jsonl"
    jsonl.write_text(
        json.dumps({**base, "friction": dict(ZERO, wasted_calls=3)}) + "\n"
    )
    text = write_summary(jsonl, tmp_path / "summary.md").read_text()
    assert "- mean wasted calls: 3.0" in text
    assert "mean wasted |" in text
    assert "| 3.0 |" in text
