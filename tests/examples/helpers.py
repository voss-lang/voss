"""Shared helpers for Phase 6 example end-to-end tests.

These helpers run the real Voss CLI from temp project roots and execute
generated Python in subprocesses with deterministic provider configuration.
They never fall back to live providers.
"""
from __future__ import annotations

import ast
import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import voss_runtime
from voss_runtime import StubProvider, configure, reset_config


REPO_ROOT = Path(__file__).resolve().parents[2]
PARSER_EXAMPLES = REPO_ROOT / "tests" / "parser" / "examples"


def example_source(name: str) -> Path:
    """Return path to a canonical parser example .voss source."""
    path = PARSER_EXAMPLES / f"{name}.voss"
    if not path.exists():
        raise FileNotFoundError(f"parser example missing: {path}")
    return path


def copy_example(tmp_path: Path, name: str) -> Path:
    """Copy a parser example into ``tmp_path`` and return the destination."""
    src = example_source(name)
    dest = tmp_path / src.name
    shutil.copyfile(src, dest)
    return dest


def run_cmd(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> subprocess.CompletedProcess[str]:
    """Run an external command capturing stdout/stderr/return code."""
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_voss(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> subprocess.CompletedProcess[str]:
    """Invoke the Voss CLI via ``python -m voss.cli`` from ``cwd``."""
    cmd = [sys.executable, "-m", "voss.cli", *args]
    return run_cmd(cmd, cwd=cwd, env=env, timeout=timeout)


def assert_no_repo_cache_artifacts(repo_root: Path = REPO_ROOT) -> None:
    """Fail if any repository-local ``.voss-cache`` index artifacts exist."""
    bad: list[str] = []
    for path in repo_root.glob("**/.voss-cache/*.idx"):
        if ".pytest_cache" in path.parts:
            continue
        # Allow temp dirs that happen to live under repo_root only when
        # explicitly inside system temp; otherwise flag.
        bad.append(str(path))
    if bad:
        raise AssertionError(f"repo-local indexes left behind: {bad}")


def assert_python_parses(path: Path) -> None:
    """Fail if the file at ``path`` is not parseable Python."""
    source = path.read_text()
    try:
        ast.parse(source)
    except SyntaxError as exc:
        raise AssertionError(f"generated python at {path} did not parse: {exc}") from exc


@contextlib.contextmanager
def register_stub(default_response: str) -> Iterator[StubProvider]:
    """In-process StubProvider registration mirroring integration tests."""
    stub = StubProvider(default_response=default_response)
    voss_runtime.providers.register("__stub__", stub)
    configure(default_model="__stub__")
    try:
        yield stub
    finally:
        reset_config()


def _sitecustomize_source(default_response: str) -> str:
    """Return Python source for a sitecustomize that registers StubProvider."""
    escaped = default_response.replace("\\", "\\\\").replace('"', '\\"')
    return (
        "import voss_runtime\n"
        "from voss_runtime import StubProvider, configure\n"
        f'_stub = StubProvider(default_response="{escaped}")\n'
        'voss_runtime.providers.register("__stub__", _stub)\n'
        'configure(default_model="__stub__")\n'
    )


def deterministic_subprocess_env(
    tmp_path: Path,
    default_response: str,
    *,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build an env dict that forces child processes onto a StubProvider.

    Writes a ``sitecustomize.py`` under ``tmp_path/_voss_stub`` and prepends
    that directory to ``PYTHONPATH``. Also includes ``REPO_ROOT`` so the
    in-tree ``voss``/``voss_runtime`` packages are importable. The contract
    is explicit: if a child process imports ``voss_runtime`` it will land on
    the deterministic stub configured here.
    """
    stub_dir = tmp_path / "_voss_stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "sitecustomize.py").write_text(_sitecustomize_source(default_response))

    env = dict(base_env if base_env is not None else os.environ)
    existing = env.get("PYTHONPATH", "")
    parts = [str(stub_dir), str(REPO_ROOT)]
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env["VOSS_TEST_STUB_RESPONSE"] = default_response
    return env
