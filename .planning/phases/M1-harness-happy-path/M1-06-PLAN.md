---
phase: M1-harness-happy-path
plan: 06
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_tools_config_cmds.py
autonomous: true
requirements:
  - CLIH-07
  - CLIH-09
tags:
  - harness
  - cli

must_haves:
  truths:
    - "`voss tools` prints a table of registered tools with columns: name, mutating, description."
    - "`voss config` opens ~/.config/voss/config.toml in $EDITOR (creates with defaults if missing); `--show` prints contents to stdout instead."
    - "Both commands exit 0 on success; `voss config --show` exits 0 even if file empty."
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "tools_cmd, config_cmd click commands wired into AGENT_COMMANDS"
      contains: "@click.command(\"tools\")"
    - path: "tests/harness/test_tools_config_cmds.py"
      provides: "CLI tests for both commands"
  key_links:
    - from: "voss/harness/cli.py::tools_cmd"
      to: "voss/harness/tools.py::make_toolset"
      via: "make_toolset(cwd)"
      pattern: "make_toolset\\("
    - from: "voss/harness/cli.py::config_cmd"
      to: "voss/harness/config.py::config_path"
      via: "config_path()"
      pattern: "config_path\\("
---

<objective>
Add `voss tools` (lists registered tools) and `voss config` (opens or prints config.toml) commands.

Purpose: Covers CLIH-07 and CLIH-09 — the last two outstanding command gaps. Both commands are small but unblock the M1 happy path. Plan 05 introduced `voss/harness/config.py` for the file location, this plan reuses it.

Output:
- `tools_cmd` and `config_cmd` click commands.
- Added to `AGENT_COMMANDS` tuple so `register(group)` picks them up automatically.
- Tests for help text, output format, and `--show` flag behavior.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M1-harness-happy-path/M1-CONTEXT.md
@.planning/phases/M1-harness-happy-path/M1-01-PLAN.md
@voss/harness/cli.py
@voss/harness/tools.py

<interfaces>
After Plan 01: make_toolset(cwd) -> dict[str, ToolEntry], where ToolEntry has .name,
.description, .is_mutating.

After Plan 05: voss.harness.config.config_path() returns the config.toml Path.
This plan can either depend on Plan 05 or duplicate the path function. To keep
dependency arrow simple, this plan inlines its own config_path() lookup (or
imports lazily — if Plan 05 lands first, the import works; if it doesn't, the
executor adds the import + fallback). Both plans are wave 2 and parallel
because they touch disjoint command names and don't read each other's commits.

To eliminate the conflict, this plan owns ONLY: tools_cmd, config_cmd. Plan 05
owns: _handle_login, slash command edits, _run_repl preferred_model load.
The shared file is voss/harness/cli.py but the additions don't overlap.

For config_path, this plan duplicates the trivial helper inline:

    def _config_toml_path() -> Path:
        return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "voss" / "config.toml"

Plan 05 will use voss/harness/config.py:config_path() in its own code paths.
No actual collision.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: voss tools and voss config commands + tests</name>
  <files>voss/harness/cli.py, tests/harness/test_tools_config_cmds.py</files>
  <read_first>
    - voss/harness/cli.py (entire — focus on AGENT_COMMANDS tuple at line ~445)
    - voss/harness/tools.py (after Plan 01: ToolEntry shape)
    - voss/harness/render.py (table style for consistency)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions, Claude's Discretion bullet on table layout)
  </read_first>
  <behavior>
    - Test 1 (`voss tools` help): `--help` mentions "tools".
    - Test 2 (`voss tools` output): output contains every registered tool name (fs_read, fs_glob, fs_grep, fs_write, fs_edit, shell_run, git_status, git_diff, voss_check) — 9 names total.
    - Test 3 (`voss tools` mutating column): output marks fs_write, fs_edit, shell_run as mutating (e.g. column value "yes" or marker `✎`). The other 6 are not marked mutating.
    - Test 4 (`voss config --show` on missing file): `voss config --show --config-path=<tmp/voss.toml>` (where the file doesn't exist) prints either nothing or a one-line "(empty)" notice, and exits 0.
    - Test 5 (`voss config --show` on existing file): when config.toml contains `[harness]\npreferred_model = "x"`, `voss config --show` prints that content.
    - Test 6 (`voss config` without --show): opens the file in $EDITOR. To make this testable, monkeypatch the subprocess call. Verify it invokes the editor on the right path. If the file doesn't exist, it gets created with a default `[harness]\n` header before the editor opens.
  </behavior>
  <action>
1. Add to `voss/harness/cli.py` (near the other agent commands, before AGENT_COMMANDS tuple):
```python
# ---------------------------------------------------------------------------
# tools — registry table
# ---------------------------------------------------------------------------


@click.command("tools")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
def tools_cmd(cwd_str: str) -> None:
    """List registered harness tools."""
    cwd = Path(cwd_str).resolve()
    tools = make_toolset(cwd)
    name_w = max(len(n) for n in tools)
    click.echo(f"  {'name':<{name_w}}  {'mut':<5}  description")
    click.echo(f"  {'-' * name_w}  {'-' * 5}  {'-' * 40}")
    for name in sorted(tools):
        entry = tools[name]
        mut = "yes" if entry.is_mutating else "no"
        desc = entry.description
        if len(desc) > 60:
            desc = desc[:59] + "…"
        click.echo(f"  {name:<{name_w}}  {mut:<5}  {desc}")


# ---------------------------------------------------------------------------
# config — open/show ~/.config/voss/config.toml
# ---------------------------------------------------------------------------


def _config_toml_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "voss" / "config.toml"


@click.command("config")
@click.option("--show", is_flag=True, help="Print config to stdout instead of opening editor.")
@click.option("--config-path", "config_path_override", default=None,
              type=click.Path(path_type=Path), help="Override config.toml location (testing).")
def config_cmd(show: bool, config_path_override: Path | None) -> None:
    """Open or show ~/.config/voss/config.toml."""
    path = config_path_override if config_path_override else _config_toml_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[harness]\n")
        path.chmod(0o600)

    if show:
        text = path.read_text()
        if text.strip():
            click.echo(text, nl=False)
        else:
            click.echo("(empty)")
        return

    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.run([editor, str(path)], check=False)
    except OSError as e:
        click.echo(f"failed to launch editor {editor!r}: {e}", err=True)
        sys.exit(1)
```

2. Add both to `AGENT_COMMANDS` at the bottom of cli.py:
```python
AGENT_COMMANDS = (do_cmd, chat_cmd, doctor_cmd, sessions_cmd, resume_cmd, edit_cmd, tools_cmd, config_cmd)
```
   (`edit_cmd` comes from Plan 04.)

3. Create `tests/harness/test_tools_config_cmds.py`:
```python
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.cli import tools_cmd, config_cmd


class TestToolsCmd:
    def test_help_mentions_tools(self):
        result = CliRunner().invoke(tools_cmd, ["--help"])
        assert result.exit_code == 0
        assert "tool" in result.output.lower()

    def test_lists_all_nine_tools(self, tmp_path):
        result = CliRunner().invoke(tools_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0
        for name in ("fs_read", "fs_glob", "fs_grep", "fs_write", "fs_edit",
                     "shell_run", "git_status", "git_diff", "voss_check"):
            assert name in result.output

    def test_marks_mutating_tools(self, tmp_path):
        result = CliRunner().invoke(tools_cmd, ["--cwd", str(tmp_path)])
        # Find the line for each mutating tool, assert it has "yes" in the mut col.
        for line in result.output.splitlines():
            for mut_name in ("fs_write", "fs_edit", "shell_run"):
                if line.lstrip().startswith(mut_name + " ") or line.lstrip().startswith(mut_name + "\t"):
                    assert " yes" in line, f"{mut_name} should be marked mutating: {line!r}"
        # And non-mutating tools should have "no".
        for line in result.output.splitlines():
            for ro_name in ("fs_read", "fs_glob", "fs_grep", "git_status", "git_diff", "voss_check"):
                if line.lstrip().startswith(ro_name + " "):
                    assert " no" in line, f"{ro_name} should NOT be marked mutating: {line!r}"


class TestConfigCmd:
    def test_show_on_missing_file_creates_and_prints(self, tmp_path):
        cfg = tmp_path / "config.toml"
        result = CliRunner().invoke(config_cmd, ["--show", "--config-path", str(cfg)])
        assert result.exit_code == 0
        assert cfg.exists()  # was created

    def test_show_existing_content(self, tmp_path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('[harness]\npreferred_model = "claude-sonnet-4"\n')
        result = CliRunner().invoke(config_cmd, ["--show", "--config-path", str(cfg)])
        assert result.exit_code == 0
        assert 'preferred_model = "claude-sonnet-4"' in result.output

    def test_open_invokes_editor(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.toml"
        called = []

        def fake_run(argv, **kwargs):
            called.append(argv)
            class R:
                returncode = 0
            return R()

        import subprocess as _sp
        monkeypatch.setattr(_sp, "run", fake_run)
        monkeypatch.setenv("EDITOR", "my-editor")
        result = CliRunner().invoke(config_cmd, ["--config-path", str(cfg)])
        assert result.exit_code == 0
        assert called and called[0][0] == "my-editor"
        assert called[0][1] == str(cfg)
        assert cfg.exists()
        assert "[harness]" in cfg.read_text()
```

4. Run `pytest tests/harness/test_tools_config_cmds.py tests/harness/test_cli.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_tools_config_cmds.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "@click.command(\"tools\")" voss/harness/cli.py` returns 1.
    - `grep -c "@click.command(\"config\")" voss/harness/cli.py` returns 1.
    - `grep -c "tools_cmd" voss/harness/cli.py` returns at least 2 (def + AGENT_COMMANDS).
    - `grep -c "config_cmd" voss/harness/cli.py` returns at least 2.
    - `pytest tests/harness/test_tools_config_cmds.py -x` exits 0.
    - `python -m voss --help` lists `tools` and `config`.
    - `python -m voss tools` prints 9 tool names.
  </acceptance_criteria>
  <done>Both commands registered, output formatted, tests pass.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_tools_config_cmds.py tests/harness/test_cli.py -x` exits 0.
- Manual: `python -m voss tools` shows the 9-row table.
- Manual: `python -m voss config --show` prints contents (or `(empty)` after creation).
- Manual: `EDITOR=true python -m voss config` exits 0 (true is a no-op binary; verifies editor launch path works).
</verification>

<success_criteria>
- CLIH-07: `voss tools` lists all 9 registered tools with their mutating flag (data sourced from Plan 01's ToolEntry).
- CLIH-09: `voss config` opens or shows `~/.config/voss/config.toml`; creates with `[harness]` header if missing.
- Neither command changes harness behavior — they are inspection/configuration surfaces only.
</success_criteria>

<output>
After completion, create `.planning/phases/M1-harness-happy-path/M1-06-SUMMARY.md` documenting the table format chosen, the `--config-path` test override, and the choice not to add interactive provider-table UI (deferred until usage signals demand).
</output>
