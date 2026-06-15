"""Slash-command coverage matrix.

Drives `voss chat --plain` with each registered slash command via stdin and
asserts:
  - exit 0
  - no Python traceback leaked to stderr
  - command-specific marker present in output where applicable

Mutating commands run with permission `mode=auto` so they don't prompt.
Commands that require credentials beyond stub (login, model switch) are
exercised in their read-only form.

Parametrize source matches the SlashRegistry entries in
voss/harness/cli.py:_build_slash_registry. Adding a new slash here means
adding the row below; the registry-divergence test guards against drift.
"""
from __future__ import annotations

import pytest

from .runner import CliRunner


# (command_line, optional substring expected in output)
SLASH_CASES: list[tuple[str, str]] = [
    ("/help", "/exit"),
    ("/clear", ""),
    ("/cost", "cost"),
    ("/tools", "fs_read"),
    ("/login", ""),  # status output varies; tolerate empty
    ("/model", ""),
    ("/mode", "mode:"),
    ("/recall foo", ""),
    ("/memory", ""),
    ("/save reminder note", ""),
    ("/save-plan", ""),
    ("/plugins", ""),
    ("/skills", ""),
    ("/agents", "explorer"),
    ("/forget foo", ""),
    ("/budget", "budget:"),
    ("/probable", ""),  # "no session" status when none recorded; tolerate
    ("/btrace", ""),  # "no session" status when none recorded; tolerate
    ("/why", ""),  # "no plan yet" status before a turn; tolerate
    ("/diff", ""),  # working-tree diff (may be empty)
    ("/apply", "/apply"),  # v0.1 no-op stub status line
]


@pytest.mark.parametrize("line, expected_substring", SLASH_CASES)
def test_slash_command_runs_cleanly(
    cli_runner: CliRunner, line: str, expected_substring: str
) -> None:
    r = cli_runner.run(
        "chat", "--plain", "--mode", "auto",
        stdin=f"{line}\n/exit\n",
        timeout=20.0,
    )
    assert r.returncode == 0, f"slash {line!r} exited {r.returncode}: {r.output}"
    assert "Traceback" not in r.stderr, (
        f"slash {line!r} leaked traceback to stderr:\n{r.stderr}"
    )
    if expected_substring:
        assert expected_substring in r.output, (
            f"slash {line!r} output missing {expected_substring!r}:\n{r.output}"
        )


def test_slash_registry_matches_test_matrix() -> None:
    """Pin: every slash registered in cli.py is exercised by SLASH_CASES.

    Excludes /exit (drives the REPL terminator separately) and aliases.
    Excludes /analyze (does real filesystem work that's tested elsewhere).
    Excludes /save-session, /plugin, /skill, /agent (require sub-args that
    are exercised by dedicated e2e tests).
    """
    from voss.harness.cli import _build_slash_registry
    from types import SimpleNamespace

    ctx = SimpleNamespace(
        cwd=None, history=None, record=None, provider=None,
        memory_store=None, slash_registry=None,
    )
    registry = _build_slash_registry()
    registered = {cmd.name for cmd in registry._commands.values()}

    exercised = {line.split()[0] for line, _ in SLASH_CASES} | {"/exit"}
    skipped = {
        "/analyze", "/save-session", "/plugin", "/skill", "/agent",
        "/symbol", "/refs", "/refresh",  # M10-04 stubs; full E2E in later wave
        # Mutating/git-backed: need real run state + --confirm; dedicated tests.
        "/undo", "/redo", "/discard",
        "/resume",  # live-resume needs a saved session id/name
        "/vdiff",  # needs a <file.voss> arg
        "/models", "/auth",  # credential/catalog (network); auth tested in tests/harness/test_auth_default.py
        "/doctor",  # health checks exercised by tests/.../doctor suite
    }

    missing = registered - exercised - skipped
    assert not missing, f"slash commands not covered in SLASH_CASES: {missing}"


def test_slash_unknown_emits_error(cli_runner: CliRunner) -> None:
    r = cli_runner.run(
        "chat", "--plain",
        stdin="/totally-fake\n/exit\n",
        timeout=15.0,
    )
    assert r.returncode == 0, r.output
    assert "unknown" in (r.stdout + r.stderr).lower()
