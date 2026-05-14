"""E2E for extension surfaces: tools, skills, plugins, agents.

Listings are read-only and don't need stub plumbing. `agent spawn` and
`skill run` do call the provider — both should succeed under the stubbed
auth resolver. We only assert exit codes + visible registry markers, not
specific provider output (subagent output shape is its own contract).
"""
from __future__ import annotations

from .runner import CliRunner


def test_tools_lists_builtin_tools(cli_runner: CliRunner) -> None:
    r = cli_runner.run("tools")
    assert r.returncode == 0, r.output
    for name in ("fs_read", "fs_write", "shell_run", "git_status", "fs_glob"):
        assert name in r.stdout, f"missing built-in tool {name!r}"


def test_skills_lists_skills(cli_runner: CliRunner) -> None:
    r = cli_runner.run("skills")
    assert r.returncode == 0, r.output


def test_plugins_lists_plugins(cli_runner: CliRunner) -> None:
    r = cli_runner.run("plugins")
    assert r.returncode == 0, r.output


def test_agents_lists_subagents(cli_runner: CliRunner) -> None:
    r = cli_runner.run("agents")
    assert r.returncode == 0, r.output
    # Built-in subagents per voss/harness/subagents.py
    for name in ("explorer", "worker", "reviewer"):
        assert name in r.stdout, f"missing built-in subagent {name!r}"


def test_plugin_enable_disable_roundtrip(cli_runner: CliRunner) -> None:
    """`plugin enable <id>` then `plugin disable <id>` both report success."""
    r_en = cli_runner.run("plugin", "enable", "fake-plugin")
    assert r_en.returncode == 0, r_en.output
    assert "enabled" in r_en.stdout, r_en.stdout

    r_dis = cli_runner.run("plugin", "disable", "fake-plugin")
    assert r_dis.returncode == 0, r_dis.output
    assert "disabled" in r_dis.stdout, r_dis.stdout


def test_skill_run_unknown_fails_with_clean_message(cli_runner: CliRunner) -> None:
    r = cli_runner.run("skill", "run", "nonexistent-skill-id")
    assert r.returncode != 0, r.output
    assert "unknown skill" in r.stderr.lower(), r.stderr
