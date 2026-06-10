from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from voss.eval.suite import CmdCheck, FileExistsCheck, load_suite


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_eval(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_repo_root()) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_all_golden_tasks_have_checks() -> None:
    repo = _repo_root()
    tasks = load_suite(Path("tests/eval/golden"), suite="golden")
    assert len(tasks) == 6
    assert all(len(spec.checks) >= 1 for _, spec in tasks)

    by_id = dict(tasks)
    analyze_checks = by_id["01-analyze"].checks
    assert any(
        isinstance(c, FileExistsCheck) and c.path == ".voss/architecture.md"
        for c in analyze_checks
    )

    validation_checks = by_id["04-validation"].checks
    assert any(
        isinstance(c, CmdCheck)
        and "voss" in c.run
        and "check sample.voss" in c.run
        for c in validation_checks
    )


def test_stub_suite_runs_all_checks_without_error(tmp_path: Path) -> None:
    repo = _repo_root()
    out = tmp_path / "eval-out"

    result = _run_eval(
        ["--stub", "--auth", "none", "-k", "1", "--out", str(out)],
        cwd=repo,
    )

    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 6
    for row in rows:
        assert "checks" in row
        assert isinstance(row["checks"], list)
