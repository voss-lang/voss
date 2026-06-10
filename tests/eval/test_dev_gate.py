from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_eval(
    args: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy() if env is None else env.copy()
    repo = str(_repo_root())
    run_env["PYTHONPATH"] = repo + os.pathsep + run_env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval", *args],
        cwd=cwd,
        env=run_env,
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
        "\n".join(
            [
                'prompt = "Say hello without editing files."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        )
    )
    return tmp_path


def test_eval_blocked_without_voss_dev(
    golden_repo_root: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "eval-out"
    env = os.environ.copy()
    env.pop("VOSS_DEV", None)
    repo = str(_repo_root())
    env["PYTHONPATH"] = repo + os.pathsep + env.get("PYTHONPATH", "")

    result = _run_eval(
        ["--stub", "--auth", "none", "--task", "02-plan-only", "--out", str(out)],
        cwd=golden_repo_root,
        env=env,
    )

    assert result.returncode != 0
    assert "internal tool" in result.stderr
    assert not (out / "runs.jsonl").exists()


def test_eval_proceeds_with_voss_dev(
    golden_repo_root: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "eval-out"
    env = os.environ.copy()
    env["VOSS_DEV"] = "1"
    repo = str(_repo_root())
    env["PYTHONPATH"] = repo + os.pathsep + env.get("PYTHONPATH", "")

    result = _run_eval(
        ["--stub", "--auth", "none", "--task", "02-plan-only", "--out", str(out)],
        cwd=golden_repo_root,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (out / "runs.jsonl").exists()
