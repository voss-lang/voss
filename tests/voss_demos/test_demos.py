"""Hermetic CLI coverage for the checked-in voss-demos programs."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from tests.examples.helpers import run_cmd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMOS_ROOT = REPO_ROOT / "voss-demos"
DEMO_SOURCES = tuple(sorted(DEMOS_ROOT.glob("*.voss")))
assert DEMO_SOURCES, "expected voss-demos/*.voss fixtures"


def _run_voss(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float = 120.0,
):
    return run_cmd(
        [sys.executable, "-m", "voss.cli", *args],
        cwd=cwd,
        env=env,
        timeout=timeout,
    )


@pytest.mark.parametrize(
    "source",
    [pytest.param(path, id=path.stem) for path in DEMO_SOURCES],
)
def test_voss_demo_check_and_run_are_hermetic(
    tmp_path: Path,
    demo_env: dict[str, str],
    source: Path,
):
    repo_cache_before = set((REPO_ROOT / ".voss-cache").glob("*.idx"))
    demo_source = tmp_path / source.name
    shutil.copyfile(source, demo_source)

    cache_dir = tmp_path / ".voss-cache"

    check_result = _run_voss(
        ["check", str(demo_source), "--cache-dir", str(cache_dir)],
        cwd=tmp_path,
        env=demo_env,
    )
    assert check_result.returncode == 0, check_result.stderr
    assert "Traceback" not in check_result.stderr

    run_result = _run_voss(
        ["run", str(demo_source), "--cache-dir", str(cache_dir)],
        cwd=tmp_path,
        env=demo_env,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert "Traceback" not in run_result.stderr
    assert run_result.stdout.strip() != ""
    assert set((REPO_ROOT / ".voss-cache").glob("*.idx")) == repo_cache_before
