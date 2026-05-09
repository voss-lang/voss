"""End-to-end validation for ``classify.voss`` (PRD §7.1, EX-01)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from examples.raw_python.classify import classify_intent

from tests.examples.helpers import (
    assert_no_repo_cache_artifacts,
    assert_python_parses,
    copy_example,
    deterministic_subprocess_env,
    register_stub,
    run_cmd,
    run_voss,
)


CONFIDENT_INPUT = "I want to cancel my subscription"


def _raw_python_output(default_response: str, user_input: str) -> str:
    """Run the raw-python oracle under a deterministic stub and return stdout."""
    with register_stub(default_response):
        return asyncio.run(classify_intent(user_input))


def test_classify_check_has_no_errors(tmp_path: Path):
    copy_example(tmp_path, "classify")
    result = run_voss(["check", "classify.voss"], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "error" not in result.stderr.lower()
    # check must not emit a generated python file.
    assert not (tmp_path / "classify.py").exists()
    # check must not write a repo-local cache.
    assert not (tmp_path / ".voss-cache").exists()
    assert_no_repo_cache_artifacts()


def test_classify_compile_python_and_run_match_raw_confident(tmp_path: Path):
    copy_example(tmp_path, "classify")

    expected = _raw_python_output("cancel_subscription", CONFIDENT_INPUT)
    assert expected == "cancel_subscription"

    out_path = tmp_path / "out" / "classify.py"
    compile_result = run_voss(
        ["compile", "classify.voss", "-o", str(out_path)],
        cwd=tmp_path,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    assert out_path.exists()
    assert_python_parses(out_path)

    env = deterministic_subprocess_env(tmp_path, "cancel_subscription")
    run_result = run_cmd(
        [sys.executable, str(out_path)],
        cwd=tmp_path,
        env=env,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert "Traceback" not in run_result.stderr
    assert run_result.stdout.strip() == expected
    assert_no_repo_cache_artifacts()


def test_classify_low_confidence_matches_raw_python(tmp_path: Path):
    copy_example(tmp_path, "classify")

    expected = _raw_python_output("", CONFIDENT_INPUT)
    assert expected == "unknown"

    out_path = tmp_path / "out" / "classify.py"
    compile_result = run_voss(
        ["compile", "classify.voss", "-o", str(out_path)],
        cwd=tmp_path,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    assert_python_parses(out_path)

    env = deterministic_subprocess_env(tmp_path, "")
    run_result = run_cmd(
        [sys.executable, str(out_path)],
        cwd=tmp_path,
        env=env,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert "Traceback" not in run_result.stderr
    assert run_result.stdout.strip() == expected
    assert_no_repo_cache_artifacts()


@pytest.mark.parametrize(
    "default_response,expected",
    [
        ("cancel_subscription", "cancel_subscription"),
        ("", "unknown"),
    ],
)
def test_classify_voss_run_matches_compile_python(
    tmp_path: Path, default_response: str, expected: str
):
    copy_example(tmp_path, "classify")

    raw_expected = _raw_python_output(default_response, CONFIDENT_INPUT)
    assert raw_expected == expected

    env = deterministic_subprocess_env(tmp_path, default_response)
    run_result = run_voss(["run", "classify.voss"], cwd=tmp_path, env=env)

    assert run_result.returncode == 0, run_result.stderr
    assert "Traceback" not in run_result.stderr
    assert run_result.stdout.strip().splitlines()[-1] == expected
    assert_no_repo_cache_artifacts()
