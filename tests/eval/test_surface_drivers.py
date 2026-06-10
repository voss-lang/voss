"""E3 surface driver tests.

CLI drivers run under STUB mode here (D-10 — sitecustomize/StubProvider
injection is permitted in tests via the CliRunner env; the live drivers
themselves never inject it). The stub env reaches the driver subprocess by
monkeypatching voss.eval.runner._live_env for the cli:* tests only.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tests.e2e.runner import CliRunner
from voss.eval.runner import _drive_cli_chat, _drive_cli_do, _drive_cli_edit
from voss.eval.suite import TaskSpec


@pytest.fixture
def stub_runner(tmp_path: Path) -> CliRunner:
    runner = CliRunner(project_root=tmp_path / "proj", state_home=tmp_path / "state")
    runner.project_root.mkdir(parents=True, exist_ok=True)
    return runner


@pytest.fixture
def stub_live_env(stub_runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """Point the drivers' env at the CliRunner stub env (tests only)."""
    monkeypatch.setattr(
        "voss.eval.runner._live_env", lambda cwd: stub_runner.env(VOSS_DEV="1")
    )
    return stub_runner


def test_cli_do_stub(stub_live_env: CliRunner) -> None:
    cwd = stub_live_env.project_root
    (cwd / "README.md").write_text("# seed\n")
    spec = TaskSpec(prompt="Say hello.", mode="plan", rubric="...", surface="cli:do")

    final, crash_reason, capped = asyncio.run(_drive_cli_do(spec, cwd))

    assert crash_reason is None
    assert final
    assert capped is False


def test_cli_chat_stub(stub_live_env: CliRunner) -> None:
    cwd = stub_live_env.project_root
    (cwd / "README.md").write_text("# seed\n")
    spec = TaskSpec(prompt="Say hello.", mode="plan", rubric="...", surface="cli:chat")

    final, crash_reason, capped = asyncio.run(_drive_cli_chat(spec, cwd))

    assert crash_reason is None
    assert final
    assert capped is False


def test_cli_edit_requires_target_file(tmp_path: Path) -> None:
    spec = TaskSpec(prompt="x", mode="edit", rubric="...", surface="cli:edit")

    final, crash_reason, capped = asyncio.run(_drive_cli_edit(spec, tmp_path))

    assert crash_reason is not None
    assert "target_file" in crash_reason
    assert final == ""


def test_cli_edit_stub(stub_live_env: CliRunner) -> None:
    cwd = stub_live_env.project_root
    (cwd / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    spec = TaskSpec(
        prompt="Describe calc.py.",
        mode="edit",
        rubric="...",
        surface="cli:edit",
        target_file="calc.py",
    )

    final, crash_reason, capped = asyncio.run(_drive_cli_edit(spec, cwd))

    assert crash_reason is None
    assert capped is False
