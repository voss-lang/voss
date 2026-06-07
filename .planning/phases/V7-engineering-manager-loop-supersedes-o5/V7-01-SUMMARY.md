---
phase: V7-engineering-manager-loop-supersedes-o5
plan: 01
subsystem: testing
tags: [cli, em-loop, red-scaffold, tdd, nyquist, run-final]

# Dependency graph
requires:
  - phase: V6
    provides: Board reviewer_a/reviewer_b slots + two-source Done gate the run CLI composes
  - phase: O5
    provides: em_loop, RunFinal (10-field record), EMBoardHandle
provides:
  - "RED acceptance scaffold for `voss team run` (10 tests) pinning VEM-CLI/PERSIST/SIGNOFF before implementation"
affects: [V7-02 (implements team run against these RED tests)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Glob-discovered sidecar (.voss/sessions/*/run-final.json) instead of hardcoded root_id — test cannot know root_id without running"
    - "autouse monkeypatch of voss.harness.config.get_model_tiers so default-roster construction resolves offline"

key-files:
  created:
    - tests/harness/test_team_run_cli.py

key-decisions:
  - "Drive the real planned surface only (team run <goal> --cwd + run-final.json with 10 RunFinal fields + sign_off); no fake team_run stub, no xfail (gsd-scaffold-fictional-api)"
  - "Assert RunFinal's 10 fields exactly (root_id/idea/total_cards/done_count/blocked_count/killed_count/rescope_count/em_iterations/ts/kind); NOT evidence_refs/diff_summary/residual (those are Ticket fields)"
  - "CliRunner tests are sync — command runs asyncio.run internally (Pitfall 4)"

patterns-established:
  - "reject is record-only: capture node-JSON set before/after, assert unchanged (no lineage revert)"

requirements-completed: [VEM-CLI, VEM-PERSIST, VEM-SIGNOFF]

# Metrics
duration: ~5min
completed: 2026-06-06
---

# Phase V7 Plan 01: `voss team run` RED scaffold Summary

**Created `tests/harness/test_team_run_cli.py` — 10 failing tests across TestTeamRunCLI / TestRunFinalPersist / TestSignOff that encode the V7 acceptance surface (compose V3 team + V4 tree + V5 board + V6 Reviewer-A/B + O5 em_loop → pre-spawn card → persist RunFinal → sign-off prompt) before any implementation. All RED for the right reason: the `team run` subcommand does not exist yet.**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-06-06
- **Tasks:** 1 completed
- **Files modified:** 1 (created, test-only)

## Accomplishments
- 10 tests collect cleanly, **10 RED** (no collection errors):
  - `TestTeamRunCLI` (5): stub-run-exits-zero, produces-card-and-run-final, run-final-persisted, default-roster-fallback, team-file-override.
  - `TestRunFinalPersist` (2): fields-serialized (exactly the 10 RunFinal keys, sign_off superset), rereadable (idea round-trips).
  - `TestSignOff` (3): prompt-appears, approve-recorded, reject-recorded-no-revert.
- Each test drives the real `["team","run",<goal>,"--cwd",tmp]` path and reads `.voss/sessions/<root_id>/run-final.json` via glob — no fictional API, no `xfail`.
- autouse `get_model_tiers` monkeypatch documented (target named in a comment for V7-02 consistency) so default-roster construction won't raise offline.

## Task Commits
1. **Task 1: RED scaffold** — `49a17f9` (test: RED scaffold for voss team run CLI).

## Files Created/Modified
- `tests/harness/test_team_run_cli.py` — root fixture (copied from test_team_check_cli), `_write_team`/`_sidecar`/`_node_json_set` helpers, autouse model-tier monkeypatch, 3 test classes.

## Decisions Made
None beyond the plan.

## Deviations from Plan
None — plan executed as written. (The live `get_model_tiers()` already resolves all DEFAULT_ROSTER tiers, so the monkeypatch is defensive per the plan's Pitfall-7 requirement rather than strictly necessary; kept as the documented V7-02 contract point.)

## Issues Encountered
None. (Collection-count grep tripped on pytest ANSI codes — confirmed 10 via `--co` raw output.)

## User Setup Required
None.

## Verification
- `pytest tests/harness/test_team_run_cli.py --co` — 10 tests collected.
- `pytest tests/harness/test_team_run_cli.py` — **10 failed (all RED)**; failures are missing `team run` command + absent sidecar, not collection errors.
- `pytest tests/harness/em/` — 79 passed (no production code added; no regression).
- `git diff --stat -- voss/` — empty (test-only, no production module touched).

## Next Phase Readiness
The acceptance contract is locked as runnable RED tests. V7-02 implements `@team_group.command("run")` composing the team/tree/board/reviewer/em_loop stack, `_persist_run_final` writing the 10-field sidecar + sign_off, and the click.prompt sign-off — flipping these 10 to GREEN. Monkeypatch target for default-roster tiers: `voss.harness.config.get_model_tiers`.

---
*Phase: V7-engineering-manager-loop-supersedes-o5*
*Completed: 2026-06-06*
