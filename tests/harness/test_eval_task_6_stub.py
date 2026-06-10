from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_task_6_stub_runs(tmp_path: Path) -> None:
    repo = _repo_root()
    out = tmp_path / "eval-out"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
    # eval verb is dev-gated (tests/eval/conftest.py sets this for tests
    # under tests/eval/; this file lives in tests/harness/).
    env["VOSS_DEV"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "voss.cli",
            "eval",
            "--stub",
            "--auth",
            "none",
            "--task",
            "06-fetch-summarize",
            "-k",
            "1",
            "--out",
            str(out),
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )

    assert result.returncode == 0, result.stderr
    rows = [
        json.loads(line)
        for line in (out / "runs.jsonl").read_text().splitlines()
        if line
    ]
    assert len(rows) == 1
    assert rows[0]["task_id"] == "06-fetch-summarize"
