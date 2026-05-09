"""Helper-behavior tests for Phase 6 examples harness."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.examples.helpers import (
    assert_no_repo_cache_artifacts,
    assert_python_parses,
    copy_example,
    deterministic_subprocess_env,
    example_source,
    register_stub,
    run_cmd,
    run_voss,
)


def test_example_source_returns_existing_classify():
    path = example_source("classify")
    assert path.exists()
    assert path.suffix == ".voss"


def test_copy_example_writes_only_under_tmp(tmp_path: Path):
    dest = copy_example(tmp_path, "classify")
    assert dest.exists()
    assert dest.is_file()
    # Destination must live under tmp_path.
    assert tmp_path in dest.parents
    assert dest.read_text() == example_source("classify").read_text()


def test_run_cmd_captures_stdout_stderr_returncode(tmp_path: Path):
    script = tmp_path / "echo.py"
    script.write_text(
        "import sys\n"
        "sys.stdout.write('hello-stdout')\n"
        "sys.stderr.write('hello-stderr')\n"
        "sys.exit(3)\n"
    )
    result = run_cmd([sys.executable, str(script)], cwd=tmp_path)
    assert result.returncode == 3
    assert "hello-stdout" in result.stdout
    assert "hello-stderr" in result.stderr


def test_assert_no_repo_cache_artifacts_catches_idx(tmp_path: Path):
    cache = tmp_path / ".voss-cache"
    cache.mkdir()
    bogus = cache / "fake.idx"
    bogus.write_text("not-a-real-index")
    with pytest.raises(AssertionError, match="repo-local indexes left behind"):
        assert_no_repo_cache_artifacts(tmp_path)


def test_assert_python_parses_rejects_invalid_python(tmp_path: Path):
    bad = tmp_path / "bad.py"
    bad.write_text("def broken(:\n")
    with pytest.raises(AssertionError, match="did not parse"):
        assert_python_parses(bad)

    good = tmp_path / "ok.py"
    good.write_text("def ok():\n    return 1\n")
    assert_python_parses(good)


def test_register_stub_yields_provider_and_resets():
    with register_stub("foo") as stub:
        assert stub.default_response == "foo"
        from voss_runtime._config import get_config

        assert get_config().default_model == "__stub__"
    # After exit, config is reset to default.
    from voss_runtime._config import get_config

    assert get_config().default_model != "__stub__"


def test_deterministic_subprocess_env_configures_child(tmp_path: Path):
    env = deterministic_subprocess_env(tmp_path, "deterministic-response")
    assert "PYTHONPATH" in env
    stub_dir = tmp_path / "_voss_stub"
    assert (stub_dir / "sitecustomize.py").exists()
    assert str(stub_dir) in env["PYTHONPATH"]
    assert env["VOSS_TEST_STUB_RESPONSE"] == "deterministic-response"

    # Child process picks up the deterministic stub via sitecustomize.
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import voss_runtime\n"
        "from voss_runtime._config import get_config\n"
        "from voss_runtime.providers import get\n"
        "p = get()\n"
        "print(get_config().default_model)\n"
        "print(p.default_response)\n"
    )
    result = subprocess.run(
        [sys.executable, str(probe)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "__stub__"
    assert lines[1] == "deterministic-response"


def test_run_voss_invokes_cli_help(tmp_path: Path):
    result = run_voss(["--help"], cwd=tmp_path)
    assert result.returncode == 0
    assert "compile" in result.stdout
    assert "check" in result.stdout
    assert "run" in result.stdout
