"""RED scaffold for E4 SDK proof.

xfail stubs map 1:1 to EVSDK-01..08; W1 adds drivers, W2 adds consumers,
W3 adds scenarios. Permission-gate behavior is live-only (FAKE_TURN emits
no permission.updated -- app.py:166-178), so EVSDK-07 stays xfail/skip in
automated runs. The three build-verification tests are real (non-xfail):
they de-risk the TS file:-dep, Go replace-directive, and Rust examples/
open questions and must pass once the consumer subprograms exist.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# EVSDK xfail stubs (flipped to real assertions by W1/W2/W3 plans)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="EVSDK-01: surface Literal lacks sdk:* values until W1 plan 02",
    strict=False,
)
def test_surface_accepts_sdk_python_ts_go_rust() -> None:
    from voss.eval.suite import TaskSpec

    for surface in ("sdk:python", "sdk:ts", "sdk:go", "sdk:rust"):
        spec = TaskSpec(prompt="x", mode="plan", rubric="r", surface=surface)
        assert spec.surface == surface


@pytest.mark.xfail(
    reason="EVSDK-02: _drive_sdk_python not yet defined (W1 plan 02)",
    strict=False,
)
def test_drive_sdk_python_stub() -> None:
    from voss.eval.runner import _drive_sdk_python  # noqa: F401


@pytest.mark.xfail(
    reason="EVSDK-03: _drive_sdk_client (ts) not yet defined (W1 plan 03)",
    strict=False,
)
def test_drive_sdk_client_ts_stub() -> None:
    from voss.eval.runner import _drive_sdk_client  # noqa: F401


@pytest.mark.xfail(
    reason="EVSDK-04: _drive_sdk_client (go) not yet defined (W1 plan 03)",
    strict=False,
)
def test_drive_sdk_client_go_stub() -> None:
    from voss.eval.runner import _drive_sdk_client  # noqa: F401


@pytest.mark.xfail(
    reason="EVSDK-05: _drive_sdk_client (rust) not yet defined (W1 plan 03)",
    strict=False,
)
def test_drive_sdk_client_rust_stub() -> None:
    from voss.eval.runner import _drive_sdk_client  # noqa: F401


@pytest.mark.xfail(
    reason="EVSDK-06: tests/eval/sdk/<NN>/task.toml scenarios not yet created (W3 plan 06)",
    strict=False,
)
def test_sdk_suite_loads() -> None:
    sdk_dir = _repo_root() / "tests" / "eval" / "sdk"
    tasks = sorted(
        p for p in sdk_dir.iterdir() if p.is_dir() and (p / "task.toml").exists()
    )
    assert tasks, "no sdk task.toml scenarios on disk"


@pytest.mark.skip(
    reason="live-only: FAKE_TURN emits no permission.updated; run via --suite sdk --auth codex"
)
def test_permission_gate_live() -> None:  # EVSDK-07
    raise AssertionError("operator checkpoint covers this; never runs automated")


@pytest.mark.skip(
    reason="live-only: EVSDK-08 documented codex proof run is an operator checkpoint (W3)"
)
def test_live_proof_run_documented() -> None:  # EVSDK-08
    raise AssertionError("operator checkpoint covers this; never runs automated")


# ---------------------------------------------------------------------------
# Build-verification gates (real tests — the W0 de-risk for the open questions)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_ts_consumer_resolves() -> None:
    """`node consumer.js` with no VOSS_BASE_URL must fail on the env guard,
    proving the @vosslang/sdk import resolved + parsed (not ERR_MODULE_NOT_FOUND)."""
    consumer = _repo_root() / "tests" / "eval" / "sdk" / "consumers" / "ts" / "consumer.js"
    env = {k: v for k, v in os.environ.items() if k != "VOSS_BASE_URL"}
    result = subprocess.run(
        ["node", str(consumer)],
        capture_output=True,
        text=True,
        env=env,
        cwd=_repo_root(),
    )
    assert result.returncode != 0
    assert "VOSS_BASE_URL" in result.stderr, result.stderr
    assert "ERR_MODULE_NOT_FOUND" not in result.stderr, result.stderr
    assert "ERR_PACKAGE_PATH_NOT_EXPORTED" not in result.stderr, result.stderr
    assert "Cannot find" not in result.stderr, result.stderr


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("go"), reason="go not installed")
def test_go_consumer_builds() -> None:
    result = subprocess.run(
        ["go", "build", "./..."],
        cwd=_repo_root() / "tests" / "eval" / "sdk" / "consumers" / "go",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("cargo"), reason="cargo not installed")
def test_rust_consumer_builds() -> None:
    result = subprocess.run(
        [
            "cargo",
            "build",
            "--example",
            "sdk_proof_consumer",
            "--manifest-path",
            str(_repo_root() / "crates" / "voss-sdk" / "Cargo.toml"),
            "--quiet",
        ],
        capture_output=True,
        text=True,
        cwd=_repo_root(),
    )
    assert result.returncode == 0, result.stderr
