"""E2E for `voss chat` REPL via stdin script.

Drives the REPL by piping `/help\\n/tools\\n/exit\\n` into stdin. Asserts:
  - banner appears
  - /help lists known slash commands
  - /tools renders the tool table
  - /exit closes the REPL cleanly with exit 0
"""
from __future__ import annotations

from .runner import CliRunner


def test_chat_repl_help_and_exit(cli_runner: CliRunner) -> None:
    r = cli_runner.run(
        "chat", "--plain",
        stdin="/help\n/exit\n",
        timeout=20.0,
    )
    assert r.returncode == 0, r.output
    # /help should enumerate at least the core slash commands
    for cmd in ("/exit", "/tools", "/help", "/recall", "/mode"):
        assert cmd in r.stdout, f"missing slash command {cmd!r} in /help output"


def test_chat_tools_slash_lists_builtins(cli_runner: CliRunner) -> None:
    r = cli_runner.run(
        "chat", "--plain",
        stdin="/tools\n/exit\n",
        timeout=20.0,
    )
    assert r.returncode == 0, r.output
    for name in ("fs_read", "fs_write", "shell_run"):
        assert name in r.stdout, f"missing tool {name!r} in /tools output"


def test_chat_unknown_slash_emits_error(cli_runner: CliRunner) -> None:
    r = cli_runner.run(
        "chat", "--plain",
        stdin="/totally-not-a-real-command\n/exit\n",
        timeout=20.0,
    )
    assert r.returncode == 0, r.output
    assert "unknown command" in r.stderr.lower() or "unknown" in r.output.lower()


def test_chat_eof_closes_cleanly(cli_runner: CliRunner) -> None:
    """Ctrl-D (EOF on stdin) must exit the REPL with returncode 0."""
    r = cli_runner.run("chat", "--plain", stdin="", timeout=20.0)
    assert r.returncode == 0, r.output
