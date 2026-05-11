---
phase: M2
plan: 06
type: execute
wave: 5
depends_on: [M1, M2-00, M2-01, M2-02, M2-04, M2-05]
files_modified:
  - voss/harness/cli.py
  - voss/harness/permissions.py
  - tests/harness/test_cli.py
  - tests/harness/test_repl_cognition.py
autonomous: true
requirements:
  - COG-03
  - COG-05
tags:
  - harness
  - cli
  - doctor
  - permissions
  - drift

must_haves:
  truths:
    - "At REPL launch (chat_cmd, do_cmd, resume_cmd), when bundle.initialized and drift_check returns is_stale=True, the harness prints one dim line `cognition stale (<reason>) — /analyze to refresh` and continues. Never blocks."
    - "`voss sessions` lists cwd-scoped sessions only; `voss sessions --all` (alias --global) merges legacy XDG-dir sessions with `[legacy]` row prefix."
    - "`voss doctor` appends three rows: `.voss/ initialized`, `cognition staleness`, `legacy sessions detected` with M1's `f'{label:<20}: {value}'` layout."
    - "`PermissionGate.check` consults `project_policy: PermissionsConfig | None` first — project-level deny always wins over allow/auto; project-level allow is additive but cannot expand session-mode permissions."
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "drift hint at REPL banner; sessions_cmd --all flag; doctor cognition rows"
      contains: "cognition stale"
    - path: "voss/harness/permissions.py"
      provides: "PermissionGate.project_policy field + deny-wins check; module docstring updated for layering precedence"
      contains: "project_policy"
    - path: "tests/harness/test_cli.py"
      provides: "test_sessions_cwd_scoped, test_sessions_all_includes_legacy, test_doctor_cognition_rows unskipped + permissions layering test"
      contains: "def test_doctor_cognition_rows"
    - path: "tests/harness/test_repl_cognition.py"
      provides: "test_drift_hint_printed_non_blocking unskipped"
      contains: "def test_drift_hint_printed_non_blocking"
  key_links:
    - from: "voss/harness/cli.py::_run_repl"
      to: "voss/harness/cognition.py::drift_check"
      via: "after bundle = cognition.load(cwd), if bundle.architecture_frontmatter: drift = drift_check(cwd, bundle.architecture_frontmatter); if drift.is_stale: click.echo(...)"
      pattern: "drift_check"
    - from: "voss/harness/permissions.py::PermissionGate.check"
      to: "PermissionsConfig.tool_policy.deny"
      via: "first clause of check() — if project_policy and tool_name in deny → return (False, 'denied by .voss/permissions.yml')"
      pattern: "project_policy"
---

<objective>
Close M2's last three loose ends: (1) drift hint at REPL launch reads cognition frontmatter and prints a non-blocking notice when stale (D-04), (2) `voss sessions --all` / `--global` flag merges legacy sessions with a `[legacy]` tag and `voss doctor` reports three new cognition rows (D-11, D-12), (3) `PermissionGate.check` layers project-level `permissions.yml` deny rules with deny-wins-over-allow precedence (D-07 + Open Question 3).

Purpose: These three integrations make the cognition layer visible (drift + doctor) and enforceable (permissions.yml layering). They sit at the user-facing edge — the parts that turn the silent infrastructure of waves 1-3 into observable behavior. After this plan, M2's success criteria 3, 4, and the "diagnose, don't fix" stance carried over from M1 are all observably satisfied.

Output:
- `voss/harness/cli.py` — drift hint after the banner; sessions_cmd `--all`/`--global` flag; doctor_cmd three new rows.
- `voss/harness/permissions.py` — `project_policy: PermissionsConfig | None = None` field on PermissionGate; new first-clause check; module docstring updated to spell out deny-wins precedence.
- 4 tests flipped from skip to live + 1 new permissions-layering test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M2-project-cognition/M2-CONTEXT.md
@.planning/phases/M2-project-cognition/M2-RESEARCH.md
@.planning/phases/M2-project-cognition/M2-PATTERNS.md
@voss/harness/cli.py
@voss/harness/permissions.py
@voss/harness/cognition.py
@voss/harness/session.py

<interfaces>
From voss/harness/cli.py (M2-04 + M2-05 state):
    _run_repl loads cognition bundle near top (M2-05 wired this).
    sessions_cmd at lines 389-399 — currently no flags.
    doctor_cmd at lines 333-369 — current rows: default model, ANTHROPIC_API_KEY, OPENAI_API_KEY, Claude Code OAuth, Codex creds, --auth=auto picks, voss_runtime.
    Layout convention: f"{label:<20}: {value}"  (label left-padded to 20 chars).

From voss/harness/permissions.py (M1):
    @dataclass class PermissionGate(mode: Mode = "edit", store: PermissionStore | None = None, auto_yes: bool = False, prompt_fn = None)
    .check(tool_name, args) -> tuple[bool, str]:
        if not self.needs_prompt(tool_name): return True, "auto"
        if self.store is not None: ...
        return self._prompt(tool_name, args)

From voss/harness/cognition.py (M2-01):
    drift_check(cwd, fm) -> DriftStatus(is_stale, head_diverged_by, file_count_delta, days_elapsed, reason)
    CognitionBundle.architecture_frontmatter: ArchitectureFrontmatter | None

From voss/harness/session.py (M2-02):
    list_sessions(cwd: Path, *, include_legacy: bool = False) -> list[SessionRecord]
    Records may carry attribute `_legacy = True` when read from legacy dir.

Click flag pattern (M2-PATTERNS.md):
    @click.option("--all", "--global", "include_legacy", is_flag=True,
                  help="Include legacy sessions from ~/.local/state/voss/sessions/.")
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add drift hint at REPL launch + sessions --all + doctor cognition rows</name>
  <files>voss/harness/cli.py, tests/harness/test_cli.py, tests/harness/test_repl_cognition.py</files>
  <read_first>
    - voss/harness/cli.py (full file; especially 245-249 banner block, 389-399 sessions_cmd, 333-369 doctor_cmd)
    - voss/harness/cognition.py (load + drift_check signatures)
    - voss/harness/session.py (list_sessions signature; _legacy_state_dir for the doctor legacy-count row)
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (§D-04 drift hint wording; §D-11 sessions --all; §D-12 doctor legacy note)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§voss/harness/cli.py MODIFIED — verbatim doctor rows + sessions flag pattern)
    - tests/harness/test_cli.py (existing CliRunner patterns; Wave-2/4 stubs to unskip)
    - tests/harness/test_repl_cognition.py (test_drift_hint_printed_non_blocking stub from M2-00)
  </read_first>
  <behavior>
    - test_sessions_cwd_scoped (in test_cli.py — flip from skip if it's a stub, otherwise add): create 2 sessions under tmp_path/.voss/sessions and 1 under monkeypatched XDG legacy dir. Invoke `sessions_cmd` with cwd switched to tmp_path; output contains the 2 cwd-scoped ids and does NOT contain the legacy id.
    - test_sessions_all_includes_legacy: same setup; invoke with --all; output contains all 3, legacy row has prefix `[legacy]`.
    - test_doctor_cognition_rows: tmp_path with .voss/architecture.md present; invoke doctor; output contains the three label strings (`.voss/ initialized`, `cognition staleness`, `legacy sessions`).
    - test_drift_hint_printed_non_blocking (in test_repl_cognition.py): tmp_path with a `.voss/architecture.md` whose frontmatter is intentionally stale (e.g. analyzed_at = 30 days ago). Invoke _run_repl (or a minimal harness around the banner block) with stub provider that exits immediately on /exit. Output contains "cognition stale" and "/analyze to refresh"; exit code 0; turn loop ran (no block).
  </behavior>
  <action>
    1. Edit voss/harness/cli.py.
    2. In `_run_repl`, immediately after the banner block (after `renderer.banner(...)` and the optional auth-detail echo and the optional resumed-turns echo, line ~249), insert drift hint:
       ```
       if bundle.initialized and bundle.architecture_frontmatter:
           drift = cognition.drift_check(cwd, bundle.architecture_frontmatter)
           if drift.is_stale:
               click.echo(f"  [dim]cognition stale ({drift.reason}) — /analyze to refresh[/dim]")
       ```
       (Use plain text formatting via click.echo; renderer dim styling is internal to TtyRenderer only — for the banner-adjacent message, click.echo is fine and grep-friendly.)
       Note: M2-05 already inserted the `bundle = cognition.load(...)` near the top of _run_repl. This task uses it.
    3. Update sessions_cmd: add `@click.option("--all", "--global", "include_legacy", is_flag=True, help="...")` decorator. Body:
       ```
       cwd = Path.cwd()
       records = session_store.list_sessions(cwd=cwd, include_legacy=include_legacy)
       if not records:
           click.echo("(no sessions)")
           return
       for r in records:
           tag = "[legacy] " if getattr(r, "_legacy", False) else ""
           click.echo(f"  {tag}{r.id[:8]}  {r.updated_at}  {r.model:<28}  {r.first_task()}")
       ```
    4. Update doctor_cmd: append three rows after the existing rows (after voss_runtime line). Use cwd = Path.cwd() at the top.
       ```
       from . import cognition as cognition_mod
       bundle = cognition_mod.load(cwd)
       click.echo(f".voss/ initialized  : {'yes' if bundle.initialized else 'no'}")
       if bundle.initialized and bundle.architecture_frontmatter:
           drift = cognition_mod.drift_check(cwd, bundle.architecture_frontmatter)
           click.echo(f"cognition staleness : {'stale (' + drift.reason + ')' if drift.is_stale else 'fresh'}")
       else:
           click.echo(f"cognition staleness : n/a")
       legacy_dir = session_store._legacy_state_dir()
       legacy_count = len(list(legacy_dir.glob('*.json'))) if legacy_dir.exists() else 0
       if legacy_count:
           click.echo(f"legacy sessions     : {legacy_count} (read-only via voss sessions --all)")
       else:
           click.echo(f"legacy sessions     : 0")
       ```
    5. In tests/harness/test_cli.py:
       - Unskip / add test_sessions_cwd_scoped and test_sessions_all_includes_legacy. Use CliRunner; set up two `.voss/sessions/` dirs (per-cwd + legacy XDG) with synthetic SessionRecord JSON files; invoke `main` with `["sessions"]` and `["sessions", "--all"]`.
       - Unskip / add test_doctor_cognition_rows. Use CliRunner; invoke `main` with `["doctor"]`; assert each of the three label substrings present in output.
    6. In tests/harness/test_repl_cognition.py: unskip test_drift_hint_printed_non_blocking. Use a tmp_path .voss/architecture.md with stale frontmatter; instantiate the REPL entry (CliRunner against `main` with `["chat"]` + stdin "/exit\n", or factor out the banner+drift block into a helper for direct unit testing). Assert the stale message appears AND the program exited cleanly (exit_code == 0).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_cli.py tests/harness/test_repl_cognition.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "cognition stale" voss/harness/cli.py` returns at least 1.
    - `grep -c '\\.voss/ initialized\\|cognition staleness\\|legacy sessions' voss/harness/cli.py` returns at least 3.
    - `grep -c '"--all", "--global"' voss/harness/cli.py` returns 1.
    - `grep -c "include_legacy" voss/harness/cli.py` returns at least 2.
    - `pytest tests/harness/test_cli.py::test_sessions_cwd_scoped tests/harness/test_cli.py::test_sessions_all_includes_legacy tests/harness/test_cli.py::test_doctor_cognition_rows -v` exits 0.
    - `pytest tests/harness/test_repl_cognition.py::test_drift_hint_printed_non_blocking -v` exits 0.
    - Manual: in this repo (no .voss/ yet), `voss doctor` prints `.voss/ initialized  : no` and `cognition staleness : n/a` and `legacy sessions     : 0`.
  </acceptance_criteria>
  <done>Drift hint, sessions --all, and doctor cognition rows all observable; tests prove behavior.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Layer PermissionsConfig onto PermissionGate with deny-wins precedence</name>
  <files>voss/harness/permissions.py, voss/harness/cli.py, tests/harness/test_cli.py</files>
  <read_first>
    - voss/harness/permissions.py (entire file — PermissionGate dataclass + check())
    - voss/harness/cognition.py (M2-01 — CognitionBundle.permissions: PermissionsConfig | None)
    - voss/harness/cognition_schemas.py (M2-01 — PermissionsConfig.tool_policy.deny / .allow shapes)
    - voss/harness/cli.py (_run_repl bundle loading from M2-05 — pass bundle.permissions into PermissionGate)
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (Claude's-Discretion: "design so project rules layer additively (deny wins over allow)")
    - .planning/phases/M2-project-cognition/M2-RESEARCH.md (§Open Question 3 — deny-wins-over-allow recommendation)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§voss/harness/permissions.py MODIFIED — layering shape)
  </read_first>
  <behavior>
    - test_project_policy_deny_wins: build PermissionGate(mode="auto", project_policy=PermissionsConfig(tool_policy=ToolPolicy(deny=["shell_run"]))); check("shell_run", {"cmd":"ls"}) returns (False, reason containing "denied by .voss/permissions.yml").
    - test_project_policy_allow_does_not_expand: PermissionGate(mode="plan", project_policy=PermissionsConfig(tool_policy=ToolPolicy(allow=["shell_run"]))); check("shell_run", {"cmd":"ls"}) goes through the normal needs_prompt path (mode=plan requires prompt for non-READ_ONLY). Project allow is recorded but does NOT short-circuit to auto. (Tests confirm allow does not bypass mode rules.)
    - test_no_project_policy_unchanged: PermissionGate(mode="edit", project_policy=None); check("shell_run", ...) behaves exactly as M1 (prompt in edit mode).
  </behavior>
  <action>
    1. Edit voss/harness/permissions.py.
    2. Update module docstring: after the existing Mode descriptions, append:
       ```
       Project-level layering (.voss/permissions.yml, added in M2)
       -----------------------------------------------------------
       When .voss/permissions.yml is loaded into a PermissionsConfig and
       attached to the gate, its rules layer on top of the session mode:
         - deny (project) ALWAYS wins, even in mode=auto.
         - allow (project) is recorded but does NOT expand session-mode
           permissions (a project allow does not auto-approve a tool that
           the session mode would have prompted for).
       This mirrors M1's "least-privilege wins" stance.
       ```
    3. Add field to PermissionGate dataclass: `project_policy: "PermissionsConfig | None" = None`. Use a string annotation to avoid circular import (PermissionsConfig is in voss.harness.cognition_schemas which doesn't import permissions, so a real import is also fine — prefer the real import for type-checker support):
       `from .cognition_schemas import PermissionsConfig`.
    4. Modify PermissionGate.check(tool_name, args):
       - Insert new first clause:
         ```
         if self.project_policy is not None:
             if tool_name in self.project_policy.tool_policy.deny:
                 return False, "denied by .voss/permissions.yml"
         ```
       - Keep the rest of the body identical.
    5. Edit voss/harness/cli.py — _run_repl: after `bundle = cognition.load(...)` (added by M2-05), construct gate with the project_policy:
       ```
       gate = PermissionGate(mode=mode, store=PermissionStore.load(cwd),
                             project_policy=bundle.permissions if bundle.initialized else None)
       ```
       Same update inside do_cmd's gate construction (line ~156).
    6. Add test in tests/harness/test_cli.py (or a new tests/harness/test_permissions.py if the file fits the convention; M1 has test_permissions or it's part of test_tools — check and place accordingly; prefer adding to existing test file to minimize sprawl):
       - test_project_policy_deny_wins
       - test_project_policy_allow_does_not_expand
       - test_no_project_policy_unchanged
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/ -x -k "permission or project_policy"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "project_policy" voss/harness/permissions.py` returns at least 3 (field, type annotation, check clause).
    - `grep -c "denied by .voss/permissions.yml" voss/harness/permissions.py` returns 1.
    - `grep -c "Project-level layering" voss/harness/permissions.py` returns 1 (docstring extension).
    - `grep -c "project_policy" voss/harness/cli.py` returns at least 2 (chat_cmd path + do_cmd path).
    - `pytest tests/harness/ -x -k "permission or project_policy"` exits 0 with the 3 new tests passing.
    - `pytest tests/harness/ -x` exits 0 (no regression in M1 permissions tests).
    - Manual: write a .voss/permissions.yml with `tool_policy:\n  deny:\n    - shell_run\n`, invoke `voss do --mode auto "echo hi"`, observe the shell_run call denied with the new reason string.
  </acceptance_criteria>
  <done>Project permissions.yml deny rules are enforced first, before session mode; allow is recorded but does not auto-bypass mode prompts.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/ -x` exits 0; drift hint, sessions --all, doctor cognition rows, and permissions layering all green.
- Manual: in a `.voss/`-initialized repo with a stale architecture.md, `voss chat` prints the drift hint and continues to the prompt.
- Manual: `voss sessions --all` after legacy + new sessions show both lists; legacy rows have `[legacy]` prefix.
- Manual: `voss doctor` prints exactly three new rows with M1's label-padding layout.
</verification>

<success_criteria>
- COG-05 fully covered: `voss sessions` and `voss sessions --all` behave per D-11/D-12 with the proper marker for legacy entries.
- COG-03 fully covered: permissions.yml is not just parsed (M2-01) but actually enforced via the PermissionGate (deny-wins precedence).
- Drift hint is a non-blocking informational notice — mirrors M1 D-13 "diagnose, don't fix".
- voss doctor extension uses the M1 label-padding convention without breaking existing rows.
- All 36 named tests from M2-VALIDATION.md plus the 2 record_run integration tests are now live (no remaining @pytest.mark.skip on M2 tests).
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .voss/permissions.yml → PermissionGate | project-committed YAML controls runtime tool dispatch |
| disk → drift_check at REPL launch | git subprocess output drives a user-visible notice |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M2-21 | Tampering | malicious .voss/permissions.yml in a fetched repo grants broad permissions on first run | mitigate | Only deny rules short-circuit to auto-deny; allow rules require the session mode to already permit the tool (do NOT expand mode). The user explicitly chose `--mode auto` if they want broad access; project allow cannot override session intent upward. |
| T-M2-22 | Reliability | drift_check raises mid-banner due to a malformed frontmatter | mitigate | M2-01 wraps drift_check in never-raise discipline. Additional safety: wrap the drift hint block in cli.py in try/except (OSError, ValueError) — log via click.echo(err=True) but proceed to REPL prompt. |
| T-M2-23 | Information Disclosure | doctor row exposes legacy session count to anyone running `voss doctor` in this dir | accept | Count alone is not sensitive; the row already documents the read-only location (`~/.local/state/voss/sessions/`). |
</threat_model>

<output>
After completion, create `.planning/phases/M2-project-cognition/M2-06-SUMMARY.md` documenting: (1) drift hint exact wording + insertion point in _run_repl, (2) sessions --all output format incl. [legacy] marker, (3) doctor row layout + the three new labels, (4) permissions.yml layering precedence with the deny-wins rule, (5) confirmation that all 36 M2-VALIDATION.md tests are now live and the M2 phase is ready for /gsd-verify-work.
</output>
