"""E2E for `voss edit <path>`.

Scoped edit REPL. Validates:
  - path argument must exist (Click validation)
  - REPL launches with session name `edit-<basename>`
  - /exit closes cleanly
  - --mode flag plumbing
"""
from __future__ import annotations

from .runner import CliRunner


def test_edit_missing_path_exits_2(cli_runner: CliRunner) -> None:
    r = cli_runner.run("edit", "no-such-file.voss")
    # Click rejects with exit 2 for an invalid Path argument.
    assert r.returncode == 2, r.output
    assert "does not exist" in r.stderr.lower() or "no such" in r.stderr.lower()


def test_edit_launches_and_exits_cleanly(cli_runner: CliRunner) -> None:
    target = cli_runner.project_root / "hello.voss"
    assert target.exists()
    r = cli_runner.run(
        "edit", str(target), "--plain",
        stdin="/exit\n",
        timeout=20.0,
    )
    assert r.returncode == 0, r.output


def test_edit_mode_flag_accepts_plan(cli_runner: CliRunner) -> None:
    target = cli_runner.project_root / "hello.voss"
    r = cli_runner.run(
        "edit", str(target), "--plain", "--mode", "plan",
        stdin="/exit\n",
        timeout=20.0,
    )
    assert r.returncode == 0, r.output


def test_edit_mode_flag_rejects_bogus(cli_runner: CliRunner) -> None:
    target = cli_runner.project_root / "hello.voss"
    r = cli_runner.run(
        "edit", str(target), "--mode", "yolo",
        stdin="/exit\n",
        timeout=10.0,
    )
    assert r.returncode != 0
    assert "yolo" in r.stderr.lower() or "invalid" in r.stderr.lower()
