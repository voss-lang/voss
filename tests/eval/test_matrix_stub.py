"""Matrix stub-run scaffolds (EVGLD-05, EVGLD-06, EVGLD-07)."""
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
    "live",
    "seed",
    "voss_version",
    "started_at",
    "gate_pass",
    "capped",
    "checks",
    "input_tokens",
}

MATRIX_CELLS = [
    "py-01-analyze",
    "py-02-plan-only",
    "py-03-approved-edit",
    "py-04-validation",
    "py-05-resume",
    "py-06-fetch-summarize",
    "rust-01-analyze",
    "rust-03-approved-edit",
    "rust-04-validation",
    "ts-01-analyze",
    "ts-03-approved-edit",
    "ts-04-validation",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _matrix_present() -> bool:
    return (_repo_root() / "tests" / "eval" / "matrix").is_dir()


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


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


@pytest.mark.parametrize("cell", MATRIX_CELLS, ids=MATRIX_CELLS)
def test_matrix_cell_stub(cell: str, tmp_path: Path) -> None:
    """EVGLD-05/06: each matrix cell completes under --stub with required row shape."""
    repo = _repo_root()
    task_toml = repo / "tests" / "eval" / "matrix" / cell / "task.toml"
    if not task_toml.exists():
        pytest.skip(f"matrix cell not present: {cell}")

    out = tmp_path / cell
    result = _run_eval(
        [
            "--stub",
            "--auth",
            "none",
            "--suite",
            "matrix",
            "--task",
            cell,
            "-k",
            "1",
            "--out",
            str(out),
        ],
        cwd=repo,
    )

    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 1
    assert set(rows[0]) >= REQUIRED_FIELDS


def test_full_matrix_stub_run(tmp_path: Path) -> None:
    """EVGLD-07: full matrix stub run produces 12 rows."""
    if not _matrix_present():
        pytest.skip("matrix suite not built yet")

    repo = _repo_root()
    out = tmp_path / "matrix-stub"
    result = _run_eval(
        [
            "--stub",
            "--auth",
            "none",
            "--suite",
            "matrix",
            "-k",
            "1",
            "--out",
            str(out),
        ],
        cwd=repo,
    )

    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 12
