---
phase: V3-team-spec-role-cage-supersedes-o2
plan: 02
subsystem: api
tags: [cli, click, team-compiler, validation]

# Dependency graph
requires:
  - phase: V3-01
    provides: compile_team validator + seven-role roster/tier defaults that team check surfaces
provides:
  - "`voss team check [path]` CLI: thin wrapper over compile_team with PASS/roster/ceiling summary + --json"
  - Deterministic exit codes (0 valid / 1 invalid / non-zero missing) for CI gating
affects: [team-cage authoring, CI validation, downstream team phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-validator rule: CLI parses -> first TeamDecl -> compile_team; no second validation path"
    - "Failure paths print to stderr + raise click.exceptions.Exit(1); --json emits {ok:false,error} and exits 1"

key-files:
  created:
    - tests/harness/test_team_check_cli.py
  modified:
    - voss/harness/cli.py

key-decisions:
  - "team click group mirrors principles_group/principles_show_cmd shape (D-03)"
  - "Positional [path] defaults to .voss/team.voss; --json flag for machine-readable output"
  - "No independent checks — compile_team IS the validator; team.py untouched by this plan"

patterns-established:
  - "team check exit-code contract: 0 PASS / 1 config-error / non-zero missing|no-team-block, asserted via CliRunner"

requirements-completed: [VTEAM-10]

# Metrics
duration: ~6min
completed: 2026-06-06
---

# Phase V3 Plan 02: `voss team check` CLI Summary

**Shipped `voss team check [path]` (default `.voss/team.voss`) as a thin CLI wrapper over the single `compile_team` validator — PASS + roster/ceiling summary on success (text or `--json`), first `VossTeamConfigError` on failure, deterministic 0/1/non-zero exit codes.**

## Performance

- **Duration:** ~6 min
- **Completed:** 2026-06-06
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `team` click group + `check` subcommand mirroring `principles_group`, registered in `AGENT_COMMANDS`.
- Body: parse file → first `TeamDecl` → `compile_team`; missing file → `team file not found`, no team block → `no team{} block`, config error → first error message; all failures Exit(1) to stderr.
- `--json` emits `{"ok":true,"team","roster","ceiling":{budget_tokens,scope,latency_seconds}}` on success / `{"ok":false,"error"}` on failure.
- CliRunner tests: valid/invalid/missing/json + registration.

## Task Commits
1. **Task 1: team check command body** — `7a9456f` (feat: command + AGENT_COMMANDS registration)
2. **Task 2: register team_group + CLI tests** — `7a9456f` (test file batched into same commit by the repo auto-committer)

_Note: a repo-side auto-commit watcher batched cli.py + the test file into a single `feat` commit rather than the two atomic commits authored._

## Files Created/Modified
- `voss/harness/cli.py` — `team_group` + `team_check_cmd` (positional `path` default `.voss/team.voss`, `--json`), appended `team_group` to `AGENT_COMMANDS`.
- `tests/harness/test_team_check_cli.py` — CliRunner exit-code + output assertions (valid/invalid/missing/json/registration).

## Decisions Made
None beyond the locked design pin (command shape, exit codes, single validator).

## Deviations from Plan
- Tests used `CliRunner()` reading `res.stderr` for failure-path text instead of `mix_stderr=True` — Click 8.2 removed the `mix_stderr` kwarg and captures stderr separately. Functionally equivalent; the exit-code + message contract is unchanged.

## Issues Encountered
`CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'` on first test run (Click ≥8.2). Fixed by dropping the kwarg and asserting on `res.stderr`.

## User Setup Required
None.

## Verification
- `pytest tests/harness/test_team_check_cli.py` — 5 passed; combined team suites — 28 passed.
- `git diff --stat voss/harness/team.py` empty (team.py untouched; this plan only imports it).

## Next Phase Readiness
Team cage is now shell-validatable. Ready for remaining V3 plans (V3-03) and any CI gate keying on `voss team check` exit codes.

---
*Phase: V3-team-spec-role-cage-supersedes-o2*
*Completed: 2026-06-06*
