---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 04
subsystem: api
tags: [cli, click, review, board, read-only]

# Dependency graph
requires:
  - phase: V6-01
    provides: test_review_cli RED scaffold turned GREEN here
  - phase: V6-03
    provides: .review.json sidecars this command reads
provides:
  - "`voss review [run_id]` read-only CLI surfacing per-card A verification + B verdict + final outcome"
  - "_latest_root_id mtime-based latest-run discovery"
affects: [V6-05 (final integration/regression)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-only CLI from persisted sidecars (mirrors sessions_cmd); no live Board/manager/provider"
    - "Per-file json.loads wrapped so one corrupt sidecar warns and the loop continues (T-V6-04-02)"

key-files:
  modified:
    - voss/harness/cli.py

key-decisions:
  - "Mirrors sessions_cmd, NOT a nonexistent board_cmd (Pitfall 1 — V5 unshipped)"
  - "Unknown run_id / no-sessions -> stderr + SystemExit(1); empty-but-valid run -> benign message + exit 0"
  - "Path-traversal run_id resolves to sessions_dir/run_id gated by is_dir() + confined *.review.json glob (T-V6-04-01)"

patterns-established:
  - "voss review exit-code contract: 0 success / non-zero+stderr unknown-run, asserted via CliRunner"

requirements-completed: [VREV-10]

# Metrics
duration: ~5min
completed: 2026-06-06
---

# Phase V6 Plan 04: `voss review` CLI Summary

**Shipped the read-only `voss review [run_id]` CLI (VREV-10): defaults to the latest run by mtime, reads the `.review.json` sidecars written by V6-03, renders per-card A verification + B verdict + final outcome, exits 0 on success and non-zero + stderr on an unknown run — mirroring `sessions_cmd`, with no live Board/manager/provider.**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-06-06
- **Tasks:** 1 completed
- **Files modified:** 1

## Accomplishments
- `review_cmd` (`@click.command("review")`, optional `run_id`) + `_latest_root_id` + `_render_review_card` in cli.py; registered in `AGENT_COMMANDS` next to `sessions_cmd`.
- Latest-run default (max-by-mtime root); unknown run_id → `unknown run_id: …` stderr + `SystemExit(1)`; no sessions → `(no review runs found)` + exit 1; valid-but-empty run → benign message + exit 0.
- Per-card render: A result/rubric/notes, B verdict/conf/tier/domain_inferred/notes/evidence, final outcome.
- Corrupt-sidecar guard: per-file `json.loads` wrapped → warning line, loop continues.
- V6-01 `test_review_cli` RED scaffold (3 tests) now GREEN.

## Task Commits
1. **Task 1: review_cmd + _latest_root_id + registration** — `a57cd71` (feat: review subcommand to CLI).

## Files Created/Modified
- `voss/harness/cli.py` — `_latest_root_id`, `_render_review_card`, `review_cmd`; `review_cmd` added to `AGENT_COMMANDS`.

## Decisions Made
None beyond the plan (mirror sessions_cmd, latest-root default, read-only).

## Deviations from Plan
None — plan executed as written.

## Issues Encountered
None.

## User Setup Required
None.

## Verification
- `pytest tests/harness/board/test_review_cli.py` — 3 green (unknown-run non-zero+stderr, no-sessions non-zero, existing-run exit 0).
- `from voss.harness.cli import review_cmd` importable; `review` present in `AGENT_COMMANDS`.
- `grep -c board_cmd cli.py` = 0 (no nonexistent command referenced).
- **Full board suite: 106 passed, 0 failed** — every V6-01 RED scaffold is now GREEN.
- `test_team_check_cli` green (no AGENT_COMMANDS regression).

## Next Phase Readiness
All four V6 deliverables (verdict field, two-source gate, sidecar, review CLI) are live and green. V6-05 is final cross-cutting integration/regression + schema-freeze gate.

---
*Phase: V6-reviewer-a-b-split-supersedes-o4*
*Completed: 2026-06-06*
