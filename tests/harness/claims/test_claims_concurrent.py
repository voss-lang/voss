"""VBUS-01 concurrent-stake exactly-one-winner — Wave 0 RED (integration).

Races N real CLI subprocesses (`python -m voss.cli claims stake`) against the
same file-backed claims DB under tmp_path. SQLite BEGIN IMMEDIATE must grant
exactly one winner (V17-RESEARCH Pattern 1); distinct agent ids so D-04
self-overlap idempotency cannot mask a double grant.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.xfail(
        reason="claims module not yet implemented (V17-02/03)", strict=False
    ),
    pytest.mark.integration,
    pytest.mark.slow,
]

REPO_ROOT = Path(__file__).resolve().parents[3]
N_RACERS = 5


def test_concurrent_stake_exactly_one_winner(tmp_path: Path) -> None:
    procs: list[subprocess.Popen] = []
    for i in range(N_RACERS):
        env = os.environ.copy()
        env["VOSS_AGENT_ID"] = f"racer-{i}"
        env["PYTHONPATH"] = (
            str(REPO_ROOT)
            if not env.get("PYTHONPATH")
            else f"{REPO_ROOT}{os.pathsep}{env['PYTHONPATH']}"
        )
        procs.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "voss.cli",
                    "claims",
                    "stake",
                    "src/api/**",
                    "--cwd",
                    str(tmp_path),
                ],
                cwd=str(REPO_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        )
    codes = [p.wait(timeout=60) for p in procs]
    assert codes.count(0) == 1, f"expected exactly one winner, got {codes}"
    # Losers must lose with the conflict exit code, never usage error / crash.
    assert all(c in (0, 1) for c in codes), codes
