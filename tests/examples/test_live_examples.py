"""Optional live-provider smoke tests for the three PRD examples.

Every test is marked ``live`` and skips unless explicit provider configuration
is present in the environment. These tests assert only stable signals
(command success, non-empty stdout, no traceback, no repo-local artifacts);
they do not assert specific natural-language output.

Enable with ``VOSS_LIVE_MODEL=<provider/model>`` and the matching credentials
for that provider (e.g. ``OPENAI_API_KEY``, ``ANTHROPIC_API_KEY``).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tests.examples.helpers import (
    assert_no_repo_cache_artifacts,
    copy_example,
    run_cmd,
    run_voss,
)


def _live_env_or_skip() -> dict[str, str]:
    """Return an env dict for live runs or skip if no live config present."""
    model = os.environ.get("VOSS_LIVE_MODEL")
    if not model:
        pytest.skip("VOSS_LIVE_MODEL not set; skipping live-provider tests")

    base = dict(os.environ)
    base["VOSS_LIVE_MODEL"] = model

    provider = model.split("/", 1)[0].lower()
    cred_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "ollama": None,
    }
    cred = cred_map.get(provider, None)
    if cred is not None and not os.environ.get(cred):
        pytest.skip(f"{cred} not set; skipping live-provider tests for {provider}")
    return base


@pytest.mark.live
@pytest.mark.parametrize("example", ["classify", "support", "research"])
def test_live_voss_run_smoke(tmp_path: Path, example: str):
    env = _live_env_or_skip()
    copy_example(tmp_path, example)

    result = run_voss(
        ["run", f"{example}.voss"],
        cwd=tmp_path,
        env=env,
        timeout=180.0,
    )

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() != "" or example == "support", (
        "live run produced empty stdout"
    )
    assert_no_repo_cache_artifacts()


@pytest.mark.live
@pytest.mark.parametrize("example", ["classify", "support", "research"])
def test_live_voss_compile_then_python_smoke(tmp_path: Path, example: str):
    env = _live_env_or_skip()
    copy_example(tmp_path, example)
    out_path = tmp_path / "out" / f"{example}.py"

    compile_result = run_voss(
        ["compile", f"{example}.voss", "-o", str(out_path)],
        cwd=tmp_path,
        env=env,
        timeout=120.0,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    assert out_path.exists()

    py_result = run_cmd(
        [sys.executable, str(out_path)],
        cwd=tmp_path,
        env=env,
        timeout=180.0,
    )
    assert py_result.returncode == 0, py_result.stderr
    assert "Traceback" not in py_result.stderr
    assert_no_repo_cache_artifacts()
