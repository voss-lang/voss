"""Shared fixtures for harness tests.

`isolated_state` is autouse — every harness test gets an XDG_STATE_HOME
sandbox pointed at its own tmp_path so session JSON / permission state never
leaks between tests.

`git_repo` is opt-in: tests request it by parameter when they need a real
git tree with one commit (drift tests, ls-files tests).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


@pytest.fixture(scope="session")
def precompiled_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    project = tmp_path_factory.mktemp("voss-m4-project")
    repo_root = Path(__file__).resolve().parents[2]
    source_dir = repo_root / "voss" / "harness" / "agent"
    target_dir = project / "voss" / "harness" / "agent"
    target_dir.mkdir(parents=True)

    for source in sorted(source_dir.glob("*.voss")):
        shutil.copy2(source, target_dir / source.name)

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(repo_root)
        if not env.get("PYTHONPATH")
        else f"{repo_root}{os.pathsep}{env['PYTHONPATH']}"
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "voss.cli",
            "compile",
            "voss/harness/agent/",
            "--project-root",
            str(project),
        ],
        cwd=str(project),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return project


@pytest.fixture
def parity_project(precompiled_harness: Path) -> Path:
    (precompiled_harness / "fixture.md").write_text("noop fixture body\n")
    return precompiled_harness
