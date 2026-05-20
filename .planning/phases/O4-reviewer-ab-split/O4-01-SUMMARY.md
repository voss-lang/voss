---
phase: O4-reviewer-ab-split
plan: 01
status: complete
completed_at: 2026-05-20
commits:
  - b7eb88a — test: add xfail scaffold tests for ReviewerA, ReviewerB, and board integration
depends_on: []
requirements: [ORVW-01, ORVW-02, ORVW-03, ORVW-04, ORVW-05, ORVW-06, ORVW-07, ORVW-08, ORVW-09, ORVW-10]
---

# O4-01 Summary — Preflight gate + RED scaffolds

## Objective

Verify the O3 substrate is importable before writing any O4 production code. Stand up RED test scaffolds for all 10 ORVW requirements so O4-02 and O4-03 can drive implementations against failing tests.

## Files changed

- `tests/harness/board/test_reviewer_a.py` — **new** (5 xfail scaffolds): ORVW-01, 02, 03, 08, 09.
- `tests/harness/board/test_reviewer_b.py` — **new** (5 xfail scaffolds): ORVW-04, 05, 06, 07, 09.
- `tests/harness/board/test_reviewer_integration.py` — **new** (1 xfail scaffold): ORVW-10.

## Preflight findings

All 4 gates passed. No blockers.

### Gate 1 — O3 imports clean

`from voss.harness.board.verdict import ReviewerVerdict, Reviewer`, `from voss.harness.board.machine import Board, Card`, `from voss.harness.board.stub import DeterministicReviewerStub` all succeed.

### Gate 2 — Reviewer.review is SYNC

`Reviewer` Protocol declares `def review(self, card: object) -> ReviewerVerdict` (not `async def`). O4-02 and O4-03 must provide sync `review()` methods and bridge any internal async calls (provider.complete, run_turn) via thread-pool executor.

### Gate 3 — Card field inventory (MISSING fields)

Card fields from `dataclasses.fields(Card)`: `node_id`, `column`, `risk_tier`, `retry_count`, `deadline`, `scope`, `artifact`, `eval_threshold`.

**MISSING from Card:** `original_idea`, `domain`, `artifact_path`, `artifact_text`, `file_diff`, `a_verification_summary` (all 6 fields O4 reviewers need).

**Resolution:** O4 reviewers receive duck-typed objects (`card: object`), not raw `Card`. Tests use `SimpleNamespace` with the needed fields. Production will pass a review-context object wrapping Card + enrichment fields. This is structurally compatible because the Reviewer Protocol types card as `object`.

### Gate 4 — ReviewerVerdict is a frozen dataclass (not pydantic)

`dataclasses.is_dataclass(ReviewerVerdict)` is `True`. ReviewerVerdict cannot be used directly as `response_format` in `provider.complete()` (which requires a pydantic BaseModel). O4-02 must create a pydantic mirror class (`_ReviewerBOutput`) for structured output and translate back to the frozen dataclass.

## Deviations from plan

None. All 11 scaffolds collected and xfailed as specified.

## Verification

```
pytest tests/harness/board/ --collect-only -q  # 11 collected
pytest tests/harness/board/ -x -q              # 11 xfailed, 0 passed, 0 failed
```

## Next

O4-02 (ReviewerB) and O4-03 (ReviewerA) run in parallel against these RED scaffolds.
