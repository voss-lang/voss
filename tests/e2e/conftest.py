"""Shared fixtures for tests/e2e/.

Layered on the StubProvider + sitecustomize pattern in tests/examples/helpers.
Adds:

  - `--update-transcripts` pytest CLI flag (read by recorded_transcript).
  - `cli_runner` fixture: per-test CliRunner pointing at an isolated project.
  - `tmp_project` fixture: copies tests/e2e/fixtures/projects/minimal into
    a tmp_path so tests can mutate it freely.
  - `recorded_transcript` fixture: closure-bound to current --update flag.
  - `stubbed_provider` fixture: in-process StubProvider registration for tests
    that exercise harness modules directly (no subprocess).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Iterator

import pytest

from .runner import CliRunner, record_or_assert_transcript

_FIXTURE_PROJECTS = Path(__file__).resolve().parent / "fixtures" / "projects"


# ---------------------------------------------------------------------------
# CLI flag
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-transcripts",
        action="store_true",
        default=False,
        help="Overwrite golden transcripts under tests/e2e/transcripts/.",
    )


# ---------------------------------------------------------------------------
# State isolation (autouse)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mirror tests/harness/conftest.py:isolated_state for the e2e suite.

    Sandboxes XDG_STATE_HOME per test so session JSON / permission state
    never leaks between tests.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "_xdg_state"))
    return tmp_path


# ---------------------------------------------------------------------------
# Project fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Copy the `minimal` fixture project tree into tmp_path/project.

    Returns the project root. Tests may mutate freely; the copy is owned by
    this test.
    """
    src = _FIXTURE_PROJECTS / "minimal"
    dest = tmp_path / "project"
    shutil.copytree(src, dest)
    return dest


@pytest.fixture
def cli_runner(tmp_project: Path, tmp_path: Path) -> CliRunner:
    """A CliRunner rooted at the minimal fixture project."""
    return CliRunner(
        project_root=tmp_project,
        state_home=tmp_path / "_state",
    )


# ---------------------------------------------------------------------------
# Transcripts
# ---------------------------------------------------------------------------


@pytest.fixture
def recorded_transcript(request: pytest.FixtureRequest) -> Callable[[str, object], None]:
    """Returns a closure(name, payload) -> None that records or asserts.

    The `--update-transcripts` flag is read once per test from the pytest
    config so callers do not need to plumb it through themselves.
    """
    update = bool(request.config.getoption("--update-transcripts"))

    def _check(name: str, payload: object) -> None:
        record_or_assert_transcript(name, payload, update=update)

    return _check


# ---------------------------------------------------------------------------
# In-process stub (for direct harness-module tests inside tests/e2e/)
# ---------------------------------------------------------------------------


@pytest.fixture
def stubbed_provider(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Register a StubProvider in-process and yield it.

    Mirrors `tests/examples/helpers.register_stub` but as a pytest fixture
    so tests don't need a `with` block. Resets configure() on teardown.
    """
    import voss_runtime
    from voss_runtime import StubProvider, configure, reset_config

    stub = StubProvider(default_response="stub-response")
    voss_runtime.providers.register("__stub__", stub)
    configure(default_model="__stub__")
    try:
        yield stub
    finally:
        reset_config()
