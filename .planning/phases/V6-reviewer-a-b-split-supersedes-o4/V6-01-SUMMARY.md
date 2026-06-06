---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 01
subsystem: testing
tags: [board, reviewer, tdd, red-scaffold, nyquist]

# Dependency graph
requires:
  - phase: O3/O4 (board state machine + reviewer A/B)
    provides: Board, ReviewerVerdict, DeterministicReviewerStub, board test fixtures
provides:
  - "Green board baseline (pre-existing exit-reasons regression fixed)"
  - "RED test scaffolds pinning every V6 target contract (two-source gate, domain_inferred, sidecar, review CLI)"
  - "7-field verdict invariant pinned in test_verdict.py + test_domain_inferred.py"
affects: [V6-02, V6-03, V6-04, V6-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave-0 RED scaffolds: assert target contract, fail at runtime (Attr/Type/Import/Assert), never at collection"
    - "Lazy function-level import of unbuilt symbols (review_cmd) keeps suite collectable"

key-files:
  created:
    - tests/harness/board/test_two_source_gate.py
    - tests/harness/board/test_domain_inferred.py
    - tests/harness/board/test_review_sidecar.py
    - tests/harness/board/test_review_cli.py
  modified:
    - tests/harness/board/test_session_tree_additive.py
    - tests/harness/board/test_verdict.py

key-decisions:
  - "Fixed pre-existing red by adding 'killed' to the exit-reasons expected set (test-only; no production touch)"
  - "Renamed test_exactly_6_fields -> test_exactly_7_fields and pinned domain_inferred (D-08)"
  - "review_cmd imported at test-function level so ImportError is a per-test RED, not a collection abort (T-V6-01-02)"

patterns-established:
  - "RED-before-GREEN Nyquist target exists and fails for each V6 requirement before implementation"

requirements-completed: [VREV-03, VREV-04, VREV-06, VREV-07, VREV-09, VREV-10, VREV-05]

# Metrics
duration: ~10min
completed: 2026-06-06
---

# Phase V6 Plan 01: RED baseline + scaffolds Summary

**Established a green board baseline (fixed the pre-existing exit-reasons regression) and laid down RED test scaffolds pinning every V6 target contract — two-source A/B Done gate, B-block terminal routing, slot back-compat, the 7th `domain_inferred` verdict field, `.review.json` sidecar persistence, and the `voss review` CLI — all failing against current code without breaking suite collection.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-06-06
- **Tasks:** 3 completed
- **Files modified:** 6 (4 created, 2 modified) — all test-only

## Accomplishments
- **Baseline:** `EXIT_REASONS` superset test now expects `"killed"` (O5 EM kill-flow) → green.
- **7-field invariant:** `test_verdict.py` + `test_domain_inferred.py` pin `domain_inferred` as the 7th field (default `"unknown"`, clamp to {code,ai,docs,unknown}).
- **Two-source gate (VREV-03/04/07):** `test_two_source_gate.py` — slot back-compat (legacy `reviewer=` fans to both slots), A-fail/B-fail refuse Done, both-pass reaches Done, B-block → `Blocked` terminal with `exit_reason == "max-iter"`.
- **Sidecar (VREV-09):** `test_review_sidecar.py` asserts `.review.json` path, `0o600` mode, and `a_verification`/`b_verdict`/`final_outcome` keys.
- **CLI (VREV-10):** `test_review_cli.py` — unknown run_id → non-zero + `unknown run_id`; no sessions → non-zero; existing sidecar → exit 0.

## Task Commits
1. **Task 1 + Task 2 + Task 3** — `fabd0cf` (feat: board harness test files + exit reasons killed) and `3748f32` (test doc/code-alias touch) — batched by the repo auto-committer.

_Note: the auto-committer batched all six files into shared commits rather than per-task atomic commits._

## Files Created/Modified
- `tests/harness/board/test_session_tree_additive.py` — added `"killed"` to the exit-reasons expected set (one-line, test-only).
- `tests/harness/board/test_verdict.py` — `test_exactly_6_fields` → `test_exactly_7_fields` with `domain_inferred`.
- `tests/harness/board/test_domain_inferred.py` — default/field-set/B-clamp assertions.
- `tests/harness/board/test_two_source_gate.py` — `TestBoardSlotBackCompat`, `TestTwoSourceGate`, `TestBBlockAtGate`.
- `tests/harness/board/test_review_sidecar.py` — sidecar path/mode/payload.
- `tests/harness/board/test_review_cli.py` — CliRunner exit-code/stderr.

## Decisions Made
None beyond the plan (test-only Wave-0 RED).

## Deviations from Plan
None — plan executed as written. Scaffold contents follow V6-PATTERNS.md; node terminal assertion verified against the live `node.terminal_state["exit_reason"]` shape.

## Issues Encountered
- An out-of-band edit expanded `voss/harness/team.py` DEFAULT_ROSTER to 14 roles (V6-adjacent product-eng roster) during this plan. Verified it does NOT regress the V3-03 empty-roster test (all 14 default scopes fit the `src/tests/docs` ceiling). Not part of this plan's scope (test-only).

## User Setup Required
None.

## Verification
- `pytest tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3` — green.
- `pytest tests/harness/board/` — **13 failed (the V6 RED scaffolds), 91 passed, 0 collection errors.** The 13 fail for the right reasons: missing `domain_inferred` field, missing `reviewer_a`/`reviewer_b` slots/kwargs, missing `review_cmd` import.
- `grep -c "class Test" test_two_source_gate.py` = 3; `grep -c domain_inferred test_domain_inferred.py` = 6.
- No `voss/` production module modified by this plan.

## Next Phase Readiness
Every V6 requirement now has a failing automated target. V6-02+ can implement against RED→GREEN: add `domain_inferred` to ReviewerVerdict, the A/B board slots + gate predicates, the sidecar writer, and the review CLI.

---
*Phase: V6-reviewer-a-b-split-supersedes-o4*
*Completed: 2026-06-06*
