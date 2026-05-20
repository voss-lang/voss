---
phase: O4-reviewer-ab-split
plan: 04
status: complete
completed_at: 2026-05-20
commits:
  - 4a8f7b0 — feat: implement keymap profile management and workspace overrides in voss-app-core and complete reviewer integration tests
depends_on: [O4-02, O4-03]
requirements: [ORVW-10, ORVW-09]
---

# O4-04 Summary — Integration test + phase acceptance

## Objective

Prove the full board lifecycle works with real ReviewerA + ReviewerB implementations plugged into O3's Board via the frozen Reviewer Protocol. Verify all 10 ORVW requirements GREEN. Confirm phase invariants (verdict.py unmodified, no circular imports, isolation guarantees).

## Files changed

- `tests/harness/board/test_reviewer_integration.py` — **rewritten** (181 lines): 1 xfail scaffold replaced with 1 GREEN integration test.

## Unchanged

- `voss/harness/board/verdict.py` — zero diff from O3.
- `voss/harness/board/reviewer_a.py`, `voss/harness/board/reviewer_b.py` — no modifications from O4-02/O4-03.

## Integration architecture (ORVW-10)

The test proves Approach B from the plan: manual reviewer invocation + Board.move() composition.

1. **ReviewerB is the Board's gate reviewer** — passed to `Board.from_team_config(reviewer=reviewer_b)`. B is invoked by `conf_meets_p` at gate transitions (InProgress->InReview and InReview->Done).
2. **ReviewerA operates outside the Board** — called by the test driver (standing in for the EM loop) to author verification before the card enters the gate system.
3. **Board.move() drives column transitions** — Backlog->Planned->InProgress (no reviewer calls), InProgress->InReview (B invoked, `provider_b.call_count >= 1`), InReview->Done (B invoked again, `call_count` increments).
4. **Transition deltas verified** — `node.transitions` has 4 entries; artifact transitions (InReview, Done) have `verdict_snapshot` with `source="B"`.

## Key decisions

| Decision | Rationale |
|----------|-----------|
| Approach B (manual gate + Board.move) | Board does not have an auto-advance API; the EM orchestration loop calls reviewers and Board.move separately. |
| `_FakeProviderForA` raises `NotImplementedError` on `complete` | A uses `run_turn_fn` injection, not raw provider calls. Provider is only needed for construction signature. |
| `_FakeProviderForB` returns canned `_ReviewerBOutput(conf=0.99)` | 0.99 exceeds all risk-tier thresholds, ensuring gate transitions pass. |
| Artifact attached via `dataclasses.replace` + board._cards mutation | Card is a frozen dataclass; the test creates a passing artifact (tests_passed=True, scope_violations=()) and replaces it in the board's internal list. |
| `build_test_team()` imported from `conftest` | Reuses O3's shared team fixture for consistent Board construction. |

## Protocol interchangeability

All three reviewer implementations verified as Protocol-compatible in the same test:
```python
assert isinstance(reviewer_a, Reviewer)
assert isinstance(reviewer_b, Reviewer)
assert isinstance(DeterministicReviewerStub(conf=0.99), Reviewer)
```

## Test summary

| Test | ORVW | Assertion |
|------|------|-----------|
| `test_board_lifecycle_with_real_reviewers` | 10 | Card transitions Backlog->Planned->InProgress->InReview->Done; B invoked at InReview and Done gates; A produces source="A" verdict; verdict_snapshot has source="B"; 4 transition deltas recorded |

## Deviations from plan

- **Commit message not O4-prefixed.** Integration test was committed alongside unrelated voss-app keymap changes in `4a8f7b0`.
- **Plan said "11 tests must pass."** Final count is 12 tests (6 in test_reviewer_a.py, 5 in test_reviewer_b.py, 1 in test_reviewer_integration.py) because O4-03 split the test_file test into pass/fail variants.

## Phase O4 acceptance

| Gate | Status |
|------|--------|
| ORVW-01: A derives bar from original idea | GREEN |
| ORVW-02: A authors tests, exit code = verdict | GREEN |
| ORVW-03: A uses judge_run for AI cards | GREEN |
| ORVW-04: B message isolation (no EM narrative) | GREEN |
| ORVW-05: B uses fast model at intermediate gate | GREEN |
| ORVW-06: B uses strong model at Done gate | GREEN |
| ORVW-07: B returns verdict="block" (Residual-2) | GREEN |
| ORVW-08: EpisodicMemory fresh per review() | GREEN |
| ORVW-09: Both implement Reviewer Protocol | GREEN |
| ORVW-10: Board lifecycle with A+B | GREEN |
| verdict.py unmodified | VERIFIED |
| No circular imports | VERIFIED |
| B isolation (no agent/memory imports) | VERIFIED |
| A memory isolation (fresh per call) | VERIFIED |

## Verification

```
pytest tests/harness/board/test_reviewer_a.py tests/harness/board/test_reviewer_b.py tests/harness/board/test_reviewer_integration.py -q  # 12 passed
```
