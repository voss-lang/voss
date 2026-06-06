---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 03
subsystem: api
tags: [board, reviewer, gates, state-machine, persistence, two-source-gate]

# Dependency graph
requires:
  - phase: V6-01
    provides: RED scaffolds (test_two_source_gate, test_review_sidecar) turned GREEN here
  - phase: V6-02
    provides: domain_inferred verdict field serialized into the sidecar via asdict
provides:
  - "Two-source Done gate: A verification PASS AND B verdict pass, independent predicates"
  - "B-block -> Blocked terminal routing at the Done gate (Residual-2)"
  - "Board reviewer_a/reviewer_b slots + legacy reviewer alias (back-compat)"
  - ".review.json sidecar (0o600) persisting A verification + B verdict + outcome"
affects: [V6-04 (review CLI reads the sidecar), V6-05 (final integration/regression)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two independent boolean gate predicates with separate lazy-cached verdict slots (verdict_a/verdict_b)"
    - "Terminal routing (block->Blocked) in Board.move after the predicate loop, NOT inside a predicate"
    - "0o600 JSON sidecar mirroring session_tree._write_node_file; stdlib-only, string type hints to avoid cycle"

key-files:
  created:
    - voss/harness/board/review_persistence.py
  modified:
    - voss/harness/board/gates.py
    - voss/harness/board/machine.py

key-decisions:
  - "Done gate replaces conf_meets_p with a_verification_passes + b_passes; conf_meets_p stays ONLY on InProgress->InReview (Open Question 2)"
  - "b_passes returns False for both 'block' and 'fail'; block->Blocked terminal seam lives in Board.move (Pitfall 2)"
  - "Sidecar written only when BOTH verdict_a and verdict_b present — pure A-fail writes no partial sidecar (Pitfall 5)"

patterns-established:
  - "verdict_snapshot capture falls back ctx.verdict or verdict_b or verdict_a so the Done transition still records a verdict"

requirements-completed: [VREV-03, VREV-04, VREV-07, VREV-09]

# Metrics
duration: ~14min
completed: 2026-06-06
---

# Phase V6 Plan 03: Two-source Done gate + sidecar Summary

**Wired Reviewer-A and Reviewer-B into the board Done gate as two genuinely independent gating sources (A verification PASS AND B verdict pass), routed a B `block` to a terminal Blocked column, gave Board `reviewer_a`/`reviewer_b` slots with a legacy `reviewer` alias, and persisted A+B review artifacts as a 0o600 `.review.json` sidecar on Done and Blocked.**

## Performance

- **Duration:** ~14 min
- **Completed:** 2026-06-06
- **Tasks:** 3 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- **GateContext** gains `reviewer_a`/`reviewer_b`/`verdict_a`/`verdict_b` (all defaulted); two new boolean predicates `a_verification_passes` and `b_passes` lazy-cache to separate slots (each reviewer ≤1 call/move).
- **Done tuples** (`_CODE_DONE_PREDICATES`, `_AI_DONE_PREDICATES` + the inline AI swaps in `move`/`dry_run_gate`) are now `scope_clean → a_verification_passes → b_passes → tests/eval` (cheap→expensive). `conf_meets_p` retained only on the intermediate gate.
- **Board** takes `reviewer_a`/`reviewer_b`; legacy `reviewer=` aliases both; `self._reviewer` falls back to A so the intermediate conf gate still functions in pure two-stub mode.
- **B-block seam** in `Board.move`'s `if failing:` branch → `_write_review_sidecar(outcome="Blocked")` + `_force_terminal(reason="retry_ceiling")` (exit_reason `max-iter`).
- **`review_persistence._write_review_sidecar`** mirrors `_write_node_file`: 0o600 `<node_id>.review.json` with `a_verification`/`b_verdict`/`final_outcome`.

## Task Commits
1. **Task 1: GateContext dual slots + A/B predicates** — committed in the gates.py change (batched).
2. **Task 2: Board slots + alias + GateContext wiring** — committed in the machine.py change (batched).
3. **Task 3: B-block seam + sidecar** — `b1b8516` + `5a90511` (feat: review sidecar persistence for Done + terminal block).

_Note: the repo auto-committer batched the gates.py/machine.py edits with the sidecar commits rather than per-task atomic commits._

## Files Created/Modified
- `voss/harness/board/gates.py` — 4 GateContext slots; `a_verification_passes`/`b_passes`; two-source Done tuples.
- `voss/harness/board/machine.py` — `reviewer_a`/`reviewer_b` on `__init__`/`from_team_config`; alias fallback; GateContext wiring (both constructions); inline AI Done tuples updated; B-block seam; Done sidecar; `verdict_snapshot` fallback.
- `voss/harness/board/review_persistence.py` — `_write_review_sidecar` (new).

## Decisions Made
None beyond the plan's locked pins.

## Deviations from Plan
- **`self._reviewer` fallback to `reviewer_a`** (beyond the literal PATTERNS, which set `self._reviewer = reviewer` only). Required: the two-stub construction (`reviewer_a=`/`reviewer_b=` with no legacy `reviewer=`) would otherwise leave `self._reviewer = None`, and `conf_meets_p` at InProgress→InReview returns False when the reviewer is None — blocking the card before Done. Fallback keeps the intermediate gate functional; the RED scaffold drives two-stub→Done and now passes.
- **`verdict_snapshot` capture widened** to `ctx.verdict or ctx.verdict_b or ctx.verdict_a`. Required: the Done gate now populates `verdict_a`/`verdict_b` (not `ctx.verdict`), so existing lifecycle tests asserting a non-None Done-transition snapshot regressed until the fallback was added.

## Issues Encountered
Two pre-existing lifecycle tests (`test_stub_full_lifecycle`, `test_reviewer_integration`) regressed after the Done-gate predicate swap because the snapshot read only `ctx.verdict`. Fixed by the verdict_snapshot fallback above; both green.

## User Setup Required
None.

## Verification
- `pytest test_two_source_gate.py test_review_sidecar.py` — green (back-compat, A-fail/B-fail refuse, both-pass→Done, B-block→Blocked terminal, sidecar 0o600 + 3 keys).
- Full board suite: **9 RED → 3 RED, 103 passed.** Remaining 3 = `test_review_cli` (V6-04 target, `review_cmd` ImportError).
- `tests/harness/em/` — green (board callers, no regression).
- Grep gates: gate slots 17; `self._reviewer_a/b` 6; `reviewer_a=self._reviewer_a` 2; `_write_review_sidecar` 3; force_terminal seam + review.json present.
- Schema freeze: `git diff --stat session.py budget.py` empty.

## Next Phase Readiness
The two-source gate, terminal block routing, and sidecar persistence are live. V6-04 implements `review_cmd` to read the `.review.json` sidecars (3 remaining RED). V6-05 is final integration/regression.

---
*Phase: V6-reviewer-a-b-split-supersedes-o4*
*Completed: 2026-06-06*
