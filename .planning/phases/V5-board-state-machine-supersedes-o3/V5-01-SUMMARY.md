---
phase: V5-board-state-machine-supersedes-o3
plan: 01
subsystem: testing
tags: [pytest, board, state-machine, click, cli, dataclass, red-scaffold, tdd]

# Dependency graph
requires:
  - phase: O3-board (shipped)
    provides: Board, Card, BoardGateError, DeterministicReviewerStub, conftest fixtures, audit/load column-derivation rule
provides:
  - "RED Wave-0 test scaffolds for VBOARD-03 (Card fields + card_status/card_budget helpers)"
  - "RED Wave-0 test scaffold for VBOARD-07 (self-Done no-reviewer guard) with GREEN positive-path + injection tripwire"
  - "RED Wave-0 test scaffold for VBOARD-10 (voss board CLI exit codes, latest-root, path-traversal)"
affects: [V5-02, V5-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave-0 RED scaffold drives the REAL planned surface (no fictional API); helper/command imports inside test methods so collection never crashes"

key-files:
  created:
    - tests/harness/board/test_card_fields_v5.py
    - tests/harness/board/test_self_done_guard.py
    - tests/harness/board/test_board_cli.py
  modified: []

key-decisions:
  - "reviewer=None self-Done test places the card into InReview via dataclasses.replace+rebind (the conf gate blocks the move when reviewer is None), isolating the Done independence guard under test"
  - "board_cmd imported inside each CLI test method so missing-symbol RED is an in-test ImportError, not a collection-aborting error"

patterns-established:
  - "RED-for-the-right-reason: failures are genuine ImportError/AttributeError/unexpected-keyword/AssertionError mapping 1:1 to V5-02/V5-03 targets; zero xfail/skip masking"

requirements-completed: [VBOARD-03, VBOARD-07, VBOARD-10]

# Metrics
duration: 12min
completed: 2026-06-06
---

# Phase V5-01: Board State Machine RED Scaffolds Summary

**Three RED Wave-0 pytest scaffolds (Card field completeness, self-Done independence guard, `voss board` CLI) that drive the exact V5-02/V5-03 planned symbols and fail today for genuine missing-surface reasons.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2 (Task 1 = two files, Task 2 = one file)
- **Files created:** 3

## Accomplishments
- `test_card_fields_v5.py` — VBOARD-03: 5 tests across `TestCardFieldsV5`, `TestCardStatus`, `TestCardBudget`. All 5 RED.
- `test_self_done_guard.py` — VBOARD-07: 3 tests in `TestSelfDoneGuard`. 1 RED (no-reviewer guard), 2 GREEN (positive path + no-verdict-injection structural tripwire).
- `test_board_cli.py` — VBOARD-10: 6 tests in `TestBoardCLI`. All 6 RED on missing `board_cmd`.
- Total: 14 new tests — **12 RED, 2 GREEN**. Full board suite: **12 failed, 109 passed** (all 12 failures are the new scaffolds).

## RED Reasons (mapped to downstream targets)

VBOARD-03 → V5-02 (`voss/harness/board/machine.py`):
- `test_new_fields_have_defaults` → `AttributeError: 'Card' object has no attribute 'idea'` (four new fields missing)
- `test_old_construction_paths_unchanged` → `TypeError: Card.__init__() got an unexpected keyword argument 'idea'`
- `test_card_is_still_frozen` → `TypeError` assigning a non-existent slot (`idea`) — turns into the asserted `FrozenInstanceError` once V5-02 adds the field
- `test_card_status_returns_column` → `ImportError: cannot import name 'card_status'`
- `test_card_budget_reads_envelope` → `ImportError: cannot import name 'card_budget'`

VBOARD-07 → V5-02 (`Board.move` guard):
- `test_reviewer_none_raises_board_gate_error` → `AssertionError: 'no-reviewer' in ['reviewer_a','reviewer_b']` — today's refusal carries the gate-predicate names, not the explicit `no-reviewer` clause the guard will add.

VBOARD-10 → V5-03 (`voss/harness/cli.py` + `cli_view.py`):
- All six CLI tests → `ImportError: cannot import name 'board_cmd' from 'voss.harness.cli'`.

## GREEN-now invariants (must stay green after V5-02)
- `test_valid_reviewer_allows_done` — full lifecycle to Done via `DeterministicReviewerStub` (positive path).
- `test_no_verdict_injection_path` — `inspect.signature(board.move)` has no `verdict` parameter (T-V5-02 Spoofing tripwire).

## Files Created/Modified
- `tests/harness/board/test_card_fields_v5.py` — VBOARD-03 RED suite (Card fields, card_status, card_budget)
- `tests/harness/board/test_self_done_guard.py` — VBOARD-07 RED suite + positive/structural tripwires
- `tests/harness/board/test_board_cli.py` — VBOARD-10 RED suite (CLI exit codes, mtime-latest root, path traversal)

## Decisions Made
- For the reviewer=None self-Done test, the card is forced into `InReview` via `dataclasses.replace` + rebind in `board._cards` because the `conf` gate refuses `InProgress→InReview` when `reviewer is None`; this isolates the Done independence guard rather than tripping on the upstream conf gate.
- CLI `board_cmd` is imported inside each test method (per V5-PATTERNS skeleton) so the missing symbol produces an in-method `ImportError` (RED) without aborting collection of the rest of the board suite.

## Deviations from Plan
None - plan executed exactly as written. The verify commands all passed: both scaffold groups collect cleanly and exit non-zero (RED), no `xfail`/`skip` markers, node fixtures use the real `transitions`/`envelope{spent,limit}`/`terminal_state` shape, path-traversal + mtime-latest cases encoded.

## Issues Encountered
None. Pre-existing baseline confirmed: `test_exit_reasons_is_sorted_superset_of_pre_o3` is already fixed and stays GREEN; no previously-green board test flipped red. `tests/harness/test_session_redaction.py` stays green (7 passed). No production file under `voss/` was modified.

## Next Phase Readiness
- V5-02 implements the four additive `Card` fields + `card_status`/`card_budget` helpers + the `no-reviewer` Done guard → flips 6 RED tests GREEN.
- V5-03 implements `board_cmd` + `cli_view.render_board` → flips the 6 CLI RED tests GREEN.
- The scaffold files were auto-committed by the repo watcher as `b2b3102`.

---
*Phase: V5-board-state-machine-supersedes-o3*
*Completed: 2026-06-06*
