---
phase: V3-team-spec-role-cage-supersedes-o2
plan: 02
type: execute
wave: 2
depends_on: [V3-01]
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_team_check_cli.py
autonomous: true
requirements: [VTEAM-10]
must_haves:
  truths:
    - "voss team check on a valid .voss/team.voss exits 0 and prints the roster + ceiling summary."
    - "voss team check on an invalid team exits 1 and prints the first VossTeamConfigError."
    - "voss team check on a missing file exits non-zero with a clear message."
    - "voss team check defaults its path to .voss/team.voss."
    - "team check wraps compile_team — no second validator."
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "team click group with a check [path] command, registered in AGENT_COMMANDS"
      contains: "team"
    - path: "tests/harness/test_team_check_cli.py"
      provides: "CliRunner exit-code + output assertions for valid/invalid/missing"
  key_links:
    - from: "voss/harness/cli.py::team_check_cmd"
      to: "voss.harness.team.compile_team"
      via: "parse(.voss) -> TeamDecl -> compile_team"
      pattern: "compile_team"
    - from: "voss/harness/cli.py::AGENT_COMMANDS"
      to: "team_group"
      via: "tuple registration"
      pattern: "team_group"
---

<objective>
Ship `voss team check [path]` (default `.voss/team.voss`) as a thin CLI wrapper over the single `compile_team` validation path: parse the file, compile it, and print a PASS + roster/ceiling summary on success or the first config error on failure, with correct exit codes.

Purpose: Closes VTEAM-10. Makes the team cage validatable from the shell without writing code, reusing the one validator (no second path).
Output: A `team` click group with a `check` command, registered in `AGENT_COMMANDS`; CLI tests.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md
@.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md

<interfaces>
<!-- The CLI pattern to copy + the validator to wrap. -->

voss/harness/cli.py:
- principles_group / principles_show_cmd  (L3740-3774)  # COPY this click.group + command + --json + error->Exit(1) shape
- AGENT_COMMANDS = (...)                   (L3777-3807)  # ADD team_group here
- register(group)                          (L3810)       # iterates AGENT_COMMANDS

Validation path (single validator — wrap, do not fork):
- from voss import parse                       # parse(source_text, filename) -> program; program.body is a list of decls
- from voss.ast_nodes import TeamDecl          # filter program.body to TeamDecl instances
- from voss.harness.team import compile_team, VossTeamConfigError, TeamConfig
- compile_team(team_decl) -> (TeamConfig, SubagentRegistry)
- TeamConfig fields: name, ceiling (TeamCeiling: budget_tokens, scope (TeamRoleScope: globs), latency_seconds), roster_ids (frozenset[str]), em_agent_id
- SubagentRegistry.ids() -> list[str]; .get(id) -> SubagentSpec | None
</interfaces>

<read_first>
- voss/harness/cli.py (L3740-3814 — principles_group pattern + AGENT_COMMANDS + register)
- voss/harness/team.py (L33-46 VossTeamConfigError, L210-219 TeamConfig, L438-497 compile_team)
- tests/voss/test_team_compile.py (L9-26 — the parse() -> _only_team(decls) -> compile_team idiom; reuse it verbatim for the CLI body)
- .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md (requirement 3 + Acceptance Criteria)
- .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md (D-03)
</read_first>

<design_pin>
## Command shape (D-03 discretion -> LOCKED)
- A `team` click group (`@click.group("team")`) with a `check` command (`@team_group.command("check")`), mirroring `principles_group` / `principles_show_cmd`.
- Positional `[path]` argument, `default=".voss/team.voss"`, `required=False`.
- `--json` flag (JSON-first welcome): on success emit `{"ok": true, "team": <name>, "roster": [...ids...], "ceiling": {"budget_tokens":..,"scope":[..],"latency_seconds":..}}`; on failure emit `{"ok": false, "error": "<first error message>"}` and exit 1.
- Single validator: the command body parses the file (`from voss import parse`), filters `program.body` to the first `TeamDecl`, and calls `compile_team`. Do NOT add any independent checks — compile_team is the validator.

## Exit codes
- Valid team -> exit 0, print `PASS` + team name + sorted roster ids + ceiling (budget/scope/latency).
- Invalid team (VossTeamConfigError from compile_team) -> exit 1, print the first error (the message of the raised VossTeamConfigError).
- Missing file -> non-zero exit (use Exit(1)) + a clear `team file not found: <path>` message.
- No TeamDecl in the file -> non-zero exit + clear message (`no team{} block in <path>`).
- Use `raise click.exceptions.Exit(1)` (same as principles_show_cmd) for the failure paths; print errors to stderr.
</design_pin>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: team check command body</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py (L3740-3774 — principles_group/principles_show_cmd to mirror)
    - tests/voss/test_team_compile.py (L9-26 parse->TeamDecl->compile_team idiom)
    - voss/harness/team.py (TeamConfig + VossTeamConfigError + compile_team)
    - <design_pin> above
  </read_first>
  <action>Add a `team_group` (`@click.group("team")`) and a `team_check_cmd` (`@team_group.command("check")`) to voss/harness/cli.py just above the `AGENT_COMMANDS` tuple, mirroring principles_group/principles_show_cmd. Signature: positional `path` argument default `.voss/team.voss`, plus `--json json_mode` flag. Body: lazily import `parse` from `voss`, `TeamDecl` from `voss.ast_nodes`, and `compile_team`/`VossTeamConfigError`/`TeamConfig` from `voss.harness.team`. Read the file (missing -> stderr `team file not found: <path>` + Exit(1)); parse; pick the first TeamDecl in `program.body` (none -> stderr `no team{} block in <path>` + Exit(1)); call `compile_team` inside try/except VossTeamConfigError (-> stderr first error + Exit(1)). On success print PASS + team name + `sorted(config.roster_ids)` + ceiling (budget_tokens, scope.globs, latency_seconds), or the JSON object per <design_pin> when `--json`.</action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness import cli; assert any(getattr(c,'name',None)=='team' for c in cli.AGENT_COMMANDS), 'team_group not registered'"</automated>
  </verify>
  <acceptance_criteria>
    - `team_group` (name `team`) with a `check` subcommand exists in voss/harness/cli.py.
    - The command body calls `compile_team` and references no other validation function (single validator).
    - The `path` argument default is the string `.voss/team.voss`.
  </acceptance_criteria>
  <done>team check command authored, wrapping compile_team, with json + exit-code branches per design_pin.</done>
</task>

<task type="auto">
  <name>Task 2: Register team_group + CLI tests</name>
  <files>voss/harness/cli.py, tests/harness/test_team_check_cli.py</files>
  <read_first>
    - voss/harness/cli.py (L3777-3814 — AGENT_COMMANDS tuple + register)
    - tests/voss/test_team_compile.py (a valid team source to reuse as a fixture) + tests/parser/examples/team_strawman.voss
    - <design_pin> (exit codes)
  </read_first>
  <action>Append `team_group` to the `AGENT_COMMANDS` tuple (cli.py L3777) next to `capabilities_group`/`principles_group`. Author tests/harness/test_team_check_cli.py using click's `CliRunner`: (1) valid team file in a tmp `.voss/team.voss` -> exit_code 0 and output contains the roster ids + ceiling budget; (2) invalid team (e.g. a role budget over ceiling, reusing the over-ceiling source from test_team_compile.py) -> exit_code 1 and output contains the error text; (3) missing path -> non-zero exit + `not found`; (4) `--json` on the valid file -> parseable JSON with `ok: true` and the roster list. Invoke the command via the registered group (build a click group, call `cli.register(group)`, invoke `["team","check",path]`).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_team_check_cli.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `team check <valid>` exits 0 and prints the roster + ceiling.
    - `team check <invalid>` exits 1 and prints the first error.
    - `team check <missing>` exits non-zero with a `not found` message.
    - `team check --json <valid>` emits JSON with `ok: true` and a roster array.
    - `team_group` is present in `cli.AGENT_COMMANDS`.
  </acceptance_criteria>
  <done>team_group registered; CLI tests cover valid/invalid/missing/json paths and pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| shell user -> team check -> compiler | An operator points the CLI at an arbitrary `.voss` path; parse+compile must fail closed with a clear message and a non-zero exit, never crash with a traceback. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V3-04 | Denial of service | team_check_cmd file read/parse | mitigate | Missing file and no-team-block paths handled explicitly (Exit(1) + message); compile errors caught as VossTeamConfigError, not propagated as raw tracebacks. |
| T-V3-05 | Repudiation | exit-code contract | mitigate | Deterministic 0/1 exit codes asserted in tests so CI/automation can gate on validity. |
| T-V3-SC | Tampering | npm/pip installs | n/a | No new deps (click already present). |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_team_check_cli.py -q` green.
- `git diff --stat voss/harness/team.py` shows no change from this plan (team check only imports team.py; does not edit it — team.py edits belong to V3-01/V3-03).
</verification>

<success_criteria>
- `voss team check` validates a team file via compile_team with correct 0/1/non-zero exit codes and a roster/ceiling summary (text + --json).
- Single validation path preserved (no second validator).
- Command registered in AGENT_COMMANDS.
</success_criteria>

<output>
Create `.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-02-SUMMARY.md` when done.
</output>
