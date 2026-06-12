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


def test_surface_accepts_sdk_python_ts_go_rust() -> None:  # EVSDK-01
    import pydantic

    from voss.eval.suite import TaskSpec, load_suite

    for surface in ("sdk:python", "sdk:ts", "sdk:go", "sdk:rust"):
        spec = TaskSpec(prompt="x", mode="plan", rubric="r", surface=surface)
        assert spec.surface == surface

    with pytest.raises(pydantic.ValidationError):
        TaskSpec.model_validate(
            {"prompt": "x", "mode": "plan", "rubric": "r", "surface": "sdk:bogus"}
        )

    # Golden tasks (no surface key) still load 6 — additive extension only.
    assert len(load_suite(_repo_root() / "tests" / "eval" / "golden", suite="golden")) == 6


def test_drive_sdk_python_stub(tmp_path: Path) -> None:  # EVSDK-02
    """In-process driver via the public embedder surface returns a final."""
    import asyncio

    from voss_runtime.providers import StubProvider

    from voss.eval.runner import _drive_sdk_python
    from voss.eval.suite import TaskSpec

    cwd = tmp_path / "proj"
    cwd.mkdir()
    (cwd / "README.md").write_text("# seed\n")
    spec = TaskSpec(prompt="Say hello.", mode="plan", rubric="...", surface="sdk:python")

    final = asyncio.run(
        _drive_sdk_python(spec, cwd=cwd, provider=StubProvider(), model=None)
    )

    assert isinstance(final, str)
    assert final


def _drive_consumer_hermetic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consumer: str
) -> str:
    """Spawn FAKE_TURN serve + the W0 consumer through _drive_sdk_client.

    hermetic: FAKE_TURN emits no permission.updated; saw_permission_gate will
    be false — that is correct for stub mode (RESEARCH Pitfall 3).
    """
    import asyncio

    from voss.eval.runner import _drive_sdk_client
    from voss.eval.suite import TaskSpec

    monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")
    cwd = tmp_path / "proj"
    cwd.mkdir()
    (cwd / "README.md").write_text("# seed\n")
    spec = TaskSpec(
        prompt="hello", mode="plan", rubric="...", surface=f"sdk:{consumer}"
    )
    return asyncio.run(_drive_sdk_client(spec, cwd=cwd, consumer=consumer))


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_drive_sdk_client_ts_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # EVSDK-03
    final = _drive_consumer_hermetic(tmp_path, monkeypatch, "ts")
    assert "echo" in final, f"unexpected final: {final!r}"


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("go"), reason="go not installed")
def test_drive_sdk_client_go_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # EVSDK-04
    final = _drive_consumer_hermetic(tmp_path, monkeypatch, "go")
    assert "echo" in final, f"unexpected final: {final!r}"


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("cargo"), reason="cargo not installed")
def test_drive_sdk_client_rust_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # EVSDK-05
    final = _drive_consumer_hermetic(tmp_path, monkeypatch, "rust")
    assert "echo" in final, f"unexpected final: {final!r}"


def test_sdk_suite_loads() -> None:  # EVSDK-06
    from voss.eval.suite import load_suite

    tasks = load_suite(_repo_root() / "tests" / "eval" / "sdk", suite="sdk")

    assert len(tasks) == 4
    assert {spec.surface for _, spec in tasks} == {
        "sdk:python", "sdk:ts", "sdk:go", "sdk:rust",
    }


# E4 adds NO new JSONL row keys; the consumer result feeds the existing
# final/gate_pass/judge path (single E1 substrate). REQUIRED_FIELDS
# unchanged from E3-01.


def test_sdk_python_stub_row(tmp_path: Path) -> None:  # EVSDK-06
    from tests.eval.test_voss_eval_stub import REQUIRED_FIELDS, _read_rows, _run_eval

    out = tmp_path / "eval-out"
    result = _run_eval(
        ["--suite", "sdk", "--stub", "--auth", "none",
         "--task", "01-python-basic", "-k", "1", "--out", str(out)],
        cwd=_repo_root(),
    )

    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == REQUIRED_FIELDS
    assert row["surface"] == "sdk:python"


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_sdk_client_stub_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # EVSDK-06
    """Full --suite sdk -> _drive_sdk_client -> ts consumer -> E1 scoring row."""
    from tests.eval.test_voss_eval_stub import REQUIRED_FIELDS, _read_rows, _run_eval

    monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")
    out = tmp_path / "eval-out"
    result = _run_eval(
        ["--suite", "sdk", "--stub", "--auth", "none",
         "--task", "02-ts-permission-allow", "-k", "1", "--out", str(out)],
        cwd=_repo_root(),
    )

    assert result.returncode == 0, result.stderr
    rows = _read_rows(out / "runs.jsonl")
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == REQUIRED_FIELDS
    assert row["surface"] == "sdk:ts"


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
# Consumer end-to-end schema/decode tests (FAKE_TURN; EVSDK-03/04/05)
#
# Hermetic: FAKE_TURN -> server.connected/final/session.idle, NO
# permission.updated. saw_permission_gate=false is correct (RESEARCH
# Pitfall 3). The live Allow/Deny round-trip is EVSDK-07 (operator
# checkpoint, plan 07).
# ---------------------------------------------------------------------------

SIX_KEYS = {
    "surface",
    "session_id",
    "final",
    "saw_permission_gate",
    "cost_usd",
    "event_types_seen",
}


def _spawn_fake_serve(cwd: Path):
    """Test-local FAKE_TURN serve: returns (proc, base_url, token)."""
    import json
    import subprocess
    import sys
    import time

    env = dict(os.environ)
    env["VOSS_SERVE_FAKE_TURN"] = "1"
    env["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
    env["VOSS_DEV"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "voss.cli", "serve"],
        env=env,
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    deadline = time.monotonic() + 60.0
    for line in proc.stdout:
        try:
            h = json.loads(line.strip())
        except json.JSONDecodeError:
            h = None
        if isinstance(h, dict) and h.get("token"):
            return proc, f"http://127.0.0.1:{h['port']}", h["token"]
        if time.monotonic() > deadline:
            break
    _kill_serve(proc)
    raise TimeoutError("fake serve handshake timeout")


def _kill_serve(proc) -> None:
    import subprocess

    if proc.stdin:
        proc.stdin.close()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _run_consumer_schema(tmp_path: Path, cmd: list[str], run_cwd: Path | None):
    """Spawn FAKE_TURN serve, run the consumer, return its parsed JSON line."""
    import json

    fixture = tmp_path / "proj"
    fixture.mkdir()
    (fixture / "README.md").write_text("# seed\n")
    proc, base_url, token = _spawn_fake_serve(fixture)
    try:
        env = {
            **os.environ,
            "VOSS_BASE_URL": base_url,
            "VOSS_TOKEN": token,
            "VOSS_CWD": str(fixture),
            "VOSS_PROMPT": "hello",
            "VOSS_MODE": "plan",
        }
        cp = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
            cwd=str(run_cwd) if run_cwd else str(_repo_root()),
        )
        # Last JSON-decodable line (tolerates cargo/go build chatter).
        for line in reversed(cp.stdout.strip().splitlines()):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        raise AssertionError(f"no JSON line in consumer stdout: {cp.stdout!r} {cp.stderr!r}")
    finally:
        _kill_serve(proc)


def _assert_schema(result: dict, surface: str) -> None:
    assert set(result) == SIX_KEYS
    assert result["surface"] == surface
    assert isinstance(result["final"], str) and "echo" in result["final"]
    assert result["saw_permission_gate"] is False
    assert isinstance(result["event_types_seen"], list)
    assert "session.idle" in result["event_types_seen"]


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_ts_consumer_output_schema(tmp_path: Path) -> None:  # EVSDK-03
    consumer = _repo_root() / "tests" / "eval" / "sdk" / "consumers" / "ts" / "consumer.js"
    result = _run_consumer_schema(tmp_path, ["node", str(consumer)], None)
    _assert_schema(result, "sdk:ts")


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("go"), reason="go not installed")
def test_go_consumer_output_schema(tmp_path: Path) -> None:  # EVSDK-04
    result = _run_consumer_schema(
        tmp_path,
        ["go", "run", "."],
        _repo_root() / "tests" / "eval" / "sdk" / "consumers" / "go",
    )
    _assert_schema(result, "sdk:go")


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("cargo"), reason="cargo not installed")
def test_rust_consumer_output_schema(tmp_path: Path) -> None:  # EVSDK-05
    result = _run_consumer_schema(
        tmp_path,
        [
            "cargo", "run",
            "--manifest-path", str(_repo_root() / "crates" / "voss-sdk" / "Cargo.toml"),
            "--example", "sdk_proof_consumer", "--quiet",
        ],
        None,
    )
    _assert_schema(result, "sdk:rust")


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
