from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REQUIRED_FIELDS = {
    "task_id",
    "run_idx",
    "success",
    "cost_usd",
    "confidence",
    "duration_s",
    "judge_verdict",
    "judge_confidence",
    "judge_rationale",
    "provider",
    "model",
    "judge_model",
    "seed",
    "voss_version",
    "started_at",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_eval(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    repo = str(_repo_root())
    env["PYTHONPATH"] = repo + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def golden_repo_root(tmp_path: Path) -> Path:
    task_dir = tmp_path / "tests" / "eval" / "golden" / "02-plan-only"
    fixture = task_dir / "fixture"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("# Fixture\n")
    (task_dir / "task.toml").write_text(
        '\n'.join(
            [
                'prompt = "Say hello without editing files."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        )
    )
    return tmp_path


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_voss_eval_stub_writes_single_jsonl_row(
    golden_repo_root: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "eval-out"

    result = _run_eval(
        ["--stub", "--auth", "none", "--task", "02-plan-only", "-k", "1", "--out", str(out)],
        cwd=golden_repo_root,
    )

    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == REQUIRED_FIELDS
    assert row["task_id"] == "02-plan-only"
    assert row["run_idx"] == 0
    assert row["cost_usd"] is None
    assert row["judge_verdict"] == "skipped"
    assert row["success"] is None


def test_cost_field_null_under_stub(
    golden_repo_root: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "eval-out"

    result = _run_eval(
        ["--stub", "--auth", "none", "--task", "02-plan-only", "-k", "1", "--out", str(out)],
        cwd=golden_repo_root,
    )

    assert result.returncode == 0, result.stderr
    row = _read_rows(out / "runs.jsonl")[0]
    assert row["cost_usd"] is None


def test_voss_eval_without_creds_points_to_stub(
    golden_repo_root: Path,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / "empty-home"
    env_path.mkdir()
    out = tmp_path / "eval-out"
    env = os.environ.copy()
    repo = str(_repo_root())
    env["PYTHONPATH"] = repo + os.pathsep + env.get("PYTHONPATH", "")
    env["HOME"] = str(env_path)
    env["XDG_CONFIG_HOME"] = str(env_path / ".config")
    env["XDG_STATE_HOME"] = str(env_path / ".local" / "state")
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "voss.cli",
            "eval",
            "--auth",
            "none",
            "--task",
            "02-plan-only",
            "--out",
            str(out),
        ],
        cwd=golden_repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stderr.strip() == "voss eval: no provider creds — pass --stub for hermetic smoke or run /login"


@pytest.mark.parametrize(
    "task_id",
    ["01-analyze", "02-plan-only", "03-approved-edit", "04-validation", "05-resume"],
    ids=["task_01", "task_02", "task_03", "task_04", "task_05"],
)
def test_existing_golden_tasks_stub(task_id: str, tmp_path: Path) -> None:
    repo = _repo_root()
    if not (repo / "tests" / "eval" / "golden" / task_id / "task.toml").exists():
        pytest.skip(f"golden task not present: {task_id}")

    out = tmp_path / task_id
    result = _run_eval(
        ["--stub", "--auth", "none", "--task", task_id, "-k", "1", "--out", str(out)],
        cwd=repo,
    )

    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 1
    assert set(rows[0]) == REQUIRED_FIELDS
