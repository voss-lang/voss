---
phase: F5-commit-with-critique-hook
plan: 02
type: execute
wave: 2
depends_on:
  - F5-01
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_consensus.py
autonomous: true
requirements:
  - D-05
  - D-06
  - D-07

must_haves:
  truths:
    - "voss hooks install writes a thin shell shim to .git/hooks/pre-commit"
    - "voss hooks install refuses when .git/hooks/pre-commit already exists"
    - "voss hooks install --force overwrites an existing hook"
    - "voss hooks uninstall removes the shim only if it was installed by voss"
    - "voss hooks appears in voss --help"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "hooks_group with install and uninstall subcommands"
      contains: "hooks_group"
    - path: "tests/harness/test_consensus.py"
      provides: "Hook lifecycle unit tests"
      contains: "test_hooks_install"
  key_links:
    - from: "voss/harness/cli.py hooks_group"
      to: ".git/hooks/pre-commit"
      via: "Path.write_text(HOOK_SHIM) + chmod 0o755"
      pattern: "HOOK_SHIM"
    - from: ".git/hooks/pre-commit"
      to: "voss consensus --staged"
      via: "exec voss consensus --staged"
      pattern: "exec voss consensus"
---

<objective>
Implement `voss hooks install` / `voss hooks uninstall` — the git hook lifecycle commands that write and remove the thin shell shim invoking `voss consensus --staged`. Depends on Plan 01 having registered `consensus_cmd`.

Purpose: Provides the opt-in mechanism for developers to wire Voss commit critique into their git workflow via a standard pre-commit hook.

Output: `hooks_group` with `install` and `uninstall` subcommands in `cli.py`, plus tests for hook lifecycle in `tests/harness/test_consensus.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/F5-commit-with-critique-hook/F5-CONTEXT.md
@.planning/phases/F5-commit-with-critique-hook/F5-RESEARCH.md
@.planning/phases/F5-commit-with-critique-hook/F5-PATTERNS.md
@.planning/phases/F5-commit-with-critique-hook/F5-01-SUMMARY.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From voss/harness/cli.py (lines 2596-2598, 2710-2712) — Click group patterns:
  @click.group("skill")
  def skill_group() -> None:
      """Run registered skills."""

  @click.group("agent")
  def agent_group() -> None:
      """Run registered subagents."""

From voss/harness/cli.py (lines 3163-3188) — AGENT_COMMANDS tuple (after Plan 01):
  AGENT_COMMANDS = (..., consensus_cmd,)  # hooks_group gets added here

From voss/harness/diagnostics.py (lines 115-124) — check_git_on_path:
  def check_git_on_path() -> Check:
      path = shutil.which("git")
      ...

From F5-CONTEXT.md D-06 — Hook shim content:
  HOOK_SHIM = "#!/bin/sh\n# Installed by: voss hooks install\nexec voss consensus --staged\n"
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add hooks_group with install/uninstall subcommands to cli.py</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py (lines 2596-2712 for skill_group/agent_group Click group patterns; lines 3163-3188 for AGENT_COMMANDS tuple; Plan 01 already added consensus_cmd)
    - voss/harness/diagnostics.py (lines 115-124 for check_git_on_path reuse opportunity)
  </read_first>
  <action>
    Add a hooks_group Click group to cli.py with install and uninstall subcommands. Place the definition near the other group commands (after skill_group/agent_group, before AGENT_COMMANDS).

    **Constants (module-level or near hooks_group):**
    - HOOK_SHIM = "#!/bin/sh\n# Installed by: voss hooks install\nexec voss consensus --staged\n"
    - HOOK_MARKER = "Installed by: voss hooks install" — used by uninstall to verify it is a voss-managed hook.

    **hooks_group:**
    - @click.group("hooks") decorator.
    - Docstring: "Manage git pre-commit hook for voss consensus."

    **install subcommand (per D-05, D-06, D-07):**
    - @hooks_group.command("install")
    - Options: --cwd (default=".", type=click.Path(file_okay=False)), --force (is_flag=True, default=False).
    - Body: Resolve cwd. Run subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(cwd), capture_output=True, text=True, timeout=5) to find the git root (Research OQ-2 recommendation: use git root, not cwd). If returncode != 0, print "Error: not a git repository." and sys.exit(2). Compute hook_path = Path(git_root.strip()) / ".git" / "hooks" / "pre-commit". Create hooks directory if it does not exist (hook_path.parent.mkdir(parents=True, exist_ok=True)). If hook_path.exists() and not force: print "Error: .git/hooks/pre-commit already exists. Use --force to overwrite." and sys.exit(1) (per D-07). Write hook_path.write_text(HOOK_SHIM). Set hook_path.chmod(0o755). Print "Installed pre-commit hook at {hook_path}".

    **uninstall subcommand (per D-05):**
    - @hooks_group.command("uninstall")
    - Options: --cwd (default=".", type=click.Path(file_okay=False)).
    - Body: Same git root resolution. Compute hook_path. If not hook_path.exists(): print "No pre-commit hook found." and sys.exit(0). Read hook content. If HOOK_MARKER not in content: print "Error: .git/hooks/pre-commit was not installed by voss. Remove manually." and sys.exit(1) (safety: never remove someone else's hook). Remove hook_path.unlink(). Print "Removed pre-commit hook."

    **Registration:**
    - Add hooks_group to the AGENT_COMMANDS tuple (after consensus_cmd).
  </action>
  <acceptance_criteria>
    - grep -c "hooks_group" voss/harness/cli.py returns >= 2 (definition + AGENT_COMMANDS entry)
    - grep -c '@click.group("hooks")' voss/harness/cli.py returns 1
    - grep -c "HOOK_SHIM" voss/harness/cli.py returns >= 1
    - grep -c "exec voss consensus --staged" voss/harness/cli.py returns >= 1
    - grep -c "chmod" voss/harness/cli.py returns >= 1 (hook made executable)
    - AGENT_COMMANDS tuple contains hooks_group
    - .venv/bin/python -c "from voss.harness.cli import hooks_group; print('OK')" exits 0
    - CliRunner().invoke(voss_main, ["--help"]) output contains "hooks"
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.cli import hooks_group; print('hooks_group imported')" && .venv/bin/python -m pytest tests/harness/test_cli.py -q</automated>
  </verify>
  <done>hooks_group with install and uninstall subcommands exists in cli.py. Registered in AGENT_COMMANDS. "hooks" appears in voss --help. No regression in test_cli.py.</done>
</task>

<task type="auto">
  <name>Task 2: Add hook lifecycle tests to test_consensus.py</name>
  <files>tests/harness/test_consensus.py</files>
  <read_first>
    - tests/harness/test_consensus.py (the test file from Plan 01 — to append hook tests without overwriting)
    - voss/harness/cli.py (the hooks_group just added in Task 1 — to know the exact Click command names and options)
  </read_first>
  <action>
    Append hook lifecycle tests to tests/harness/test_consensus.py (do NOT overwrite existing Plan 01 tests).

    **Test fixtures for hooks:**
    - A fake_git_repo fixture using tmp_path: creates tmp_path / ".git" / "hooks" directory, monkeypatches subprocess.run so that "git rev-parse --show-toplevel" returns tmp_path as stdout.
    - Reuse CliRunner from existing test imports.

    **Required tests:**
    - test_hooks_install_writes_shim (D-05, D-06): Invoke "hooks install --cwd {tmp_path}" via CliRunner with the fake_git_repo. Assert .git/hooks/pre-commit exists. Assert content matches HOOK_SHIM exactly ("#!/bin/sh\n# Installed by: voss hooks install\nexec voss consensus --staged\n"). Assert file is executable (stat.S_IXUSR bit set via os.stat).
    - test_hooks_install_refuses_existing (D-07): Write a dummy file to .git/hooks/pre-commit first. Invoke "hooks install --cwd {tmp_path}" without --force. Assert exit_code == 1. Assert "already exists" in output. Assert dummy content unchanged (not overwritten).
    - test_hooks_install_force_overwrites (D-07): Write a dummy file first. Invoke "hooks install --cwd {tmp_path} --force". Assert exit_code == 0. Assert .git/hooks/pre-commit content is now HOOK_SHIM (overwritten).
    - test_hooks_uninstall_removes_voss_hook: Install via "hooks install", then invoke "hooks uninstall --cwd {tmp_path}". Assert .git/hooks/pre-commit no longer exists. Assert exit_code == 0.
    - test_hooks_uninstall_refuses_foreign_hook: Write a foreign hook content (e.g., "#!/bin/sh\nnpx lint-staged\n"). Invoke "hooks uninstall --cwd {tmp_path}". Assert exit_code == 1. Assert "not installed by voss" in output. Assert file still exists (not deleted).
    - test_hooks_uninstall_no_hook_exists: Invoke "hooks uninstall --cwd {tmp_path}" with no hook file. Assert exit_code == 0. Assert "No pre-commit hook found" in output.
    - test_hooks_in_voss_help: CliRunner invoke voss --help, assert "hooks" in output.

    Run the full test file to confirm all existing + new tests pass together.
  </action>
  <acceptance_criteria>
    - grep -c "def test_hooks" tests/harness/test_consensus.py returns >= 6
    - .venv/bin/python -m pytest tests/harness/test_consensus.py -q exits 0 with ALL tests passing (Plan 01 + Plan 02 tests together)
    - test_hooks_install_writes_shim verifies exact shim content match
    - test_hooks_install_refuses_existing verifies exit_code == 1 and content preserved
    - test_hooks_install_force_overwrites verifies content replaced
    - test_hooks_uninstall_refuses_foreign_hook verifies exit_code == 1 and file preserved
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_consensus.py -q</automated>
  </verify>
  <done>7+ hook lifecycle tests all GREEN. Combined test file (Plan 01 consensus tests + Plan 02 hook tests) passes cleanly. D-05, D-06, D-07 fully covered by automated tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User filesystem -> hooks_group | .git/hooks/pre-commit written by voss; pre-existing hooks are untrusted |
| voss hooks uninstall -> .git/hooks/ | Only remove hooks with the HOOK_MARKER; never delete foreign hooks |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F5-03 | Tampering | hooks install overwriting existing hook | mitigate | D-07: refuse if .git/hooks/pre-commit exists; require --force flag to overwrite |
| T-F5-06 | Tampering | hooks uninstall deleting foreign hook | mitigate | Check HOOK_MARKER in file content before deletion; refuse if not a voss-installed hook |
| T-F5-07 | Elevation | Hook shim runs with user's shell privileges | accept | Hook is a standard git mechanism; runs as the invoking user; no privilege escalation beyond normal git hooks |
| T-F5-SC | Tampering | npm/pip installs | accept | Zero new packages installed in this phase |
</threat_model>

<verification>
After Plan 02 completes:
1. `voss hooks` appears in `voss --help`
2. `voss hooks install --help` shows --cwd and --force options
3. `.venv/bin/python -m pytest tests/harness/test_consensus.py -q` — all tests GREEN (Plan 01 + Plan 02 combined)
4. `.venv/bin/python -m pytest tests/harness/test_cli.py -q` — no regression
5. `.venv/bin/python -m pytest tests/harness/ -q` — full harness suite no regression
</verification>

<success_criteria>
- hooks_group with install and uninstall subcommands registered in AGENT_COMMANDS
- "voss hooks" appears in voss --help
- install writes exact 3-line HOOK_SHIM to .git/hooks/pre-commit with 0o755 permissions
- install refuses when hook exists (D-07), --force overwrites
- uninstall only removes voss-installed hooks (HOOK_MARKER check)
- 7+ hook tests all GREEN in test_consensus.py
- No regression in existing harness test suite
</success_criteria>

<output>
Create `.planning/phases/F5-commit-with-critique-hook/F5-02-SUMMARY.md` when done
</output>
