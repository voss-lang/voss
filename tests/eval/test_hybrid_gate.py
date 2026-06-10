"""Hybrid gate + judge integration tests (E1-03)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from voss.eval import runner
from voss.eval.judge import Verdict
from voss_runtime.providers import StubProvider

NEVER_DONE_PLAN = {
    "rationale": "loop",
    "steps": [{"name": "read_file", "args": {"path": "README.md"}, "why": "read"}],
    "confidence": 0.95,
    "final_when_done": "",
}


def _write_task(root: Path, task_id: str, task_toml: str) -> None:
    task_dir = root / "tests" / "eval" / "golden" / task_id
    fixture = task_dir / "fixture"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("# Fixture\n")
    (task_dir / "task.toml").write_text(task_toml)


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


@pytest.fixture
def golden_repo_root(tmp_path: Path) -> Path:
    _write_task(
        tmp_path,
        "gate-task",
        "\n".join(
            [
                'prompt = "Say hello without editing files."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
                "[[checks]]",
                'type = "file_exists"',
                'path = "missing.txt"',
                "",
            ]
        ),
    )
    return tmp_path


def test_gate_overrides_judge(golden_repo_root: Path, tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "out"
    monkeypatch.chdir(golden_repo_root)
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: StubProvider())
    monkeypatch.setattr(
        runner,
        "judge_run",
        AsyncMock(return_value=(Verdict(verdict="pass", confidence=0.9, rationale="ok"), "pass")),
    )

    runner.run_suite(stub=True, auth_pref="none", task="gate-task", out=out)

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["gate_pass"] is False
    assert row["success"] is False
    assert row["checks"][0]["pass"] is False


def test_no_checks_judge_only_fallback(tmp_path: Path, monkeypatch) -> None:
    _write_task(
        tmp_path,
        "no-checks",
        "\n".join(
            [
                'prompt = "Say hello without editing files."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)

    runner.run_suite(stub=True, auth_pref="none", task="no-checks", out=out)

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["gate_pass"] is True
    assert row["checks"] == []
    assert row["success"] is None


def test_capped_records_fail_and_skips_judge(tmp_path: Path, monkeypatch) -> None:
    _write_task(
        tmp_path,
        "loop-task",
        "\n".join(
            [
                'prompt = "Read the readme."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        runner,
        "_provider_for_eval",
        lambda *, stub, auth_pref: (StubProvider(default_response=NEVER_DONE_PLAN), None),
    )
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: StubProvider())

    start = time.monotonic()
    runner.run_suite(
        stub=True,
        auth_pref="none",
        task="loop-task",
        out=out,
        max_turns=1,
    )
    elapsed = time.monotonic() - start

    assert elapsed < 10.0
    row = _read_rows(out / "runs.jsonl")[0]
    assert row["capped"] is True
    assert row["success"] is False
    assert row["judge_verdict"] == "skipped"


def test_run_header_prints(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_task(
        tmp_path,
        "header-task",
        "\n".join(
            [
                'prompt = "Say hello."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)

    runner.run_suite(stub=True, auth_pref="none", task="header-task", out=out, max_turns=3)

    captured = capsys.readouterr()
    assert "tasks · max" in captured.out
    assert "turns/task" in captured.out


def test_judge_model_default(monkeypatch, tmp_path: Path) -> None:
    _write_task(
        tmp_path,
        "judge-model",
        "\n".join(
            [
                'prompt = "Say hello."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "get_eval_judge_model", lambda: "custom-judge-model")
    monkeypatch.setattr(
        runner,
        "_provider_for_eval",
        lambda *, stub, auth_pref: (StubProvider(), None),
    )
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: None)

    runner.run_suite(stub=False, task="judge-model", out=out)

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["judge_model"] == "custom-judge-model"
