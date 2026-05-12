from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _has_live_creds() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.live
def test_cost(tmp_path: Path) -> None:
    row = _run_live_eval(tmp_path)
    assert row["cost_usd"] is None or row["cost_usd"] >= 0


@pytest.mark.live
def test_confidence(tmp_path: Path) -> None:
    row = _run_live_eval(tmp_path)
    assert row["confidence"] is None or 0.0 <= row["confidence"] <= 1.0


def _run_live_eval(tmp_path: Path) -> dict:
    repo = _repo_root()
    task_id = "02-plan-only"
    if not _has_live_creds():
        pytest.skip("live provider credentials not configured")
    if not (repo / "tests" / "eval" / "golden" / task_id / "task.toml").exists():
        pytest.skip(f"golden task not present: {task_id}")

    out = tmp_path / "live-out"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "voss.cli",
            "eval",
            "--live",
            "--task",
            task_id,
            "-k",
            "1",
            "--out",
            str(out),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    return json.loads((out / "runs.jsonl").read_text().splitlines()[0])
