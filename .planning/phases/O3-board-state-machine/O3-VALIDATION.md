---
phase: O3
slug: board-state-machine
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-19
completed: 2026-05-20
---

# Phase O3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/board/ -x -q --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/board/ -v --tb=long` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/harness/board/ -x -q --tb=short`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/harness/board/ -v --tb=long`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Requirement → Plan Coverage Matrix

| Requirement ID | Description | Plan(s) | Wave | Verify Command | Status |
|----------------|-------------|---------|------|----------------|--------|
| OBRD-01 | Card == session-tree node; column is a node attribute; transitions emit `RunRecord` deltas | O3-01, O3-02, O3-04 | 1, 2, 4 | `.venv/bin/python -m pytest tests/harness/board/test_card_node_wiring.py tests/harness/board/test_session_tree_additive.py tests/harness/board/test_transition_count_invariant.py -x -q` | ✅ green |
| OBRD-02 | Board lifecycle — one board per compiled `team{}`; `Board.from_team_config` factory; distinct root node ids | O3-02 | 2 | `.venv/bin/python -m pytest tests/harness/board/test_board_factory.py -x -q` | ✅ green |
| OBRD-03 | 6-column state machine + per-column WIP cap enforcement | O3-02 | 2 | `.venv/bin/python -m pytest tests/harness/board/test_columns_and_unknown.py tests/harness/board/test_wip_cap.py -x -q` | ✅ green |
| OBRD-04 | Gate predicates — typed predicates gate each non-terminal transition; `dry_run_gate` returns failing clauses | O3-03 | 3 | `.venv/bin/python -m pytest tests/harness/board/test_gate_predicates_basic.py tests/harness/board/test_dry_run_gate.py -x -q` | ✅ green |
| OBRD-05 | Artifact-only confidence gating — confidence checked only on `InProgress->InReview` and `InReview->Done`; non-artifact transitions never invoke reviewer | O3-03 | 3 | `.venv/bin/python -m pytest tests/harness/board/test_artifact_only_confidence.py -x -q` | ✅ green |
| OBRD-06 | Risk-tiered `p` — 3-bucket {low: 0.60, med: 0.80, high: 0.95} from single named constant; team-overridable | O3-02, O3-03 | 2, 3 | `.venv/bin/python -m pytest tests/harness/board/test_risk_thresholds.py -x -q` | ✅ green |
| OBRD-07 | `ReviewerVerdict` frozen dataclass + `Reviewer` Protocol — O4 consumer contract; `DeterministicReviewerStub` for tests | O3-01, O3-03 | 1, 3 | `.venv/bin/python -m pytest tests/harness/board/test_verdict.py tests/harness/board/test_verdict_imports.py tests/harness/board/test_stub.py tests/harness/board/test_stub_full_lifecycle.py -x -q` | ✅ green |
| OBRD-08 | Critic loop — failed review returns card to `InProgress` with retry notes; bounded by retry ceiling AND budget; first hit -> Blocked | O3-04 | 4 | `.venv/bin/python -m pytest tests/harness/board/test_critic_loop.py -x -q` | ✅ green |
| OBRD-09 | Timeout — budget-fraction primary + wall-clock safety net; every spawned card reaches Done or Blocked in finite time; 100-card stress test | O3-04 | 4 | `.venv/bin/python -m pytest tests/harness/board/test_timeout_tick.py tests/harness/board/test_budget_tick.py tests/harness/board/test_100_card_stress.py -x -q` | ✅ green |

Every OBRD-01..OBRD-09 requirement appears in >= 1 plan. Reverse check: every plan declares its OBRD coverage in `requirements:` frontmatter.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| O3-01-01 | O3-01 | 1 | OBRD-01, OBRD-07 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_session_tree_additive.py -x -q` | ✅ green |
| O3-01-02 | O3-01 | 1 | OBRD-07 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_verdict.py tests/harness/board/test_verdict_imports.py -x -q` | ✅ green |
| O3-02-01 | O3-02 | 2 | OBRD-01, OBRD-02 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_board_factory.py tests/harness/board/test_card_node_wiring.py -x -q` | ✅ green |
| O3-02-02 | O3-02 | 2 | OBRD-03, OBRD-06 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_columns_and_unknown.py tests/harness/board/test_wip_cap.py -x -q` | ✅ green |
| O3-02-03 | O3-02 | 2 | OBRD-01 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_transition_count_invariant.py -x -q` | ✅ green |
| O3-03-01 | O3-03 | 3 | OBRD-04 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_gate_predicates_basic.py tests/harness/board/test_dry_run_gate.py -x -q` | ✅ green |
| O3-03-02 | O3-03 | 3 | OBRD-05 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_artifact_only_confidence.py -x -q` | ✅ green |
| O3-03-03 | O3-03 | 3 | OBRD-06 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_risk_thresholds.py -x -q` | ✅ green |
| O3-03-04 | O3-03 | 3 | OBRD-07 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_stub.py tests/harness/board/test_stub_full_lifecycle.py -x -q` | ✅ green |
| O3-04-01 | O3-04 | 4 | OBRD-09 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_tick_clock.py tests/harness/board/test_timeout_tick.py tests/harness/board/test_budget_tick.py -x -q` | ✅ green |
| O3-04-02 | O3-04 | 4 | OBRD-08 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_critic_loop.py -x -q` | ✅ green |
| O3-04-03 | O3-04 | 4 | OBRD-08, OBRD-09 | tdd | `.venv/bin/python -m pytest tests/harness/board/test_board_lifecycle.py -x -q` | ✅ green |
| O3-04-04 | O3-04 | 4 | OBRD-09, OBRD-01 | stress | `.venv/bin/python -m pytest tests/harness/board/test_100_card_stress.py -x -q` | ✅ green |

---

## Wave Structure

| Wave | Plans | Autonomous | Files Modified |
|------|-------|------------|----------------|
| 1 | O3-01 | yes | voss/harness/session.py (additive), voss/harness/session_tree.py (additive), voss/harness/board/ (new package: __init__.py, verdict.py, errors.py); tests/harness/board/ |
| 2 | O3-02 | yes | voss/harness/board/machine.py (new), voss/harness/board/__init__.py; tests/harness/board/ |
| 3 | O3-03 | yes | voss/harness/board/gates.py (new), voss/harness/board/stub.py (new), voss/harness/board/machine.py; tests/harness/board/ |
| 4 | O3-04 | yes | voss/harness/board/tick.py (new), voss/harness/board/machine.py; tests/harness/board/ |

---

## Wave 0 Requirements

- [x] O1 session-tree substrate available (`SessionTreeManager`, `SessionTreeNode`, budget envelopes)
- [x] O2 compiled config available (`TeamConfig`, `BoardSpec`, `SubagentRegistry`)
- [x] `EXIT_REASONS` extended with `"timeout"` (additive)
- [x] `SessionTreeNode` gains `transitions` and `retry_notes` fields with backwards-compat hydration
- [x] `SessionTreeManager.get_node()` lookup added

---

## SPEC Acceptance Criteria Coverage

| Acceptance Criterion (SPEC line) | Proving Test File(s) | Status |
|----------------------------------|---------------------|--------|
| L110: Card.column reachable only via recorder.get_node | `test_card_node_wiring.py` | ✅ green |
| L111: Board.from_team_config creates board with observable root_node_id | `test_board_factory.py` | ✅ green |
| L112: Exactly 6 column names accepted; unknown -> BoardGateError | `test_columns_and_unknown.py` | ✅ green |
| L113: WIP cap of N refuses (N+1)th transition with BoardWIPError | `test_wip_cap.py` | ✅ green |
| L114: dry_run_gate returns failing predicate clauses by stable name | `test_gate_predicates_basic.py`, `test_dry_run_gate.py` | ✅ green |
| L115: Mocked Reviewer not invoked for Backlog->Planned or Planned->InProgress | `test_artifact_only_confidence.py` | ✅ green |
| L116: Risk thresholds {0.60, 0.80, 0.95} from single named constant | `test_risk_thresholds.py` | ✅ green |
| L117: ReviewerVerdict frozen dataclass with 6 fields; Reviewer is Protocol | `test_verdict.py` | ✅ green |
| L118: DeterministicReviewerStub runs full lifecycle without LLM | `test_stub_full_lifecycle.py` | ✅ green |
| L119: 4 sequential fails -> Blocked(retry_ceiling) with 3 RetryNotes | `test_critic_loop.py` | ✅ green |
| L120: Wall-clock deadline elapse -> Blocked(timeout) after tick | `test_timeout_tick.py` | ✅ green |
| L121: O1 envelope drain -> Blocked(budget) after tick | `test_budget_tick.py` | ✅ green |
| L122: 100-card stress: zero non-terminal cards | `test_100_card_stress.py` | ✅ green |
| L123: Transition-delta count == transition attempts | `test_transition_count_invariant.py`, `test_100_card_stress.py` | ✅ green |
| L124: verdict.py imports only from typing/dataclasses | `test_verdict_imports.py` | ✅ green |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | O3 is fully automatable | — |

---

## Test Summary

| Wave | Source | Test Count |
|------|--------|-----------|
| O3-01 | `test_session_tree_additive.py` | 9 |
| O3-01 | `test_verdict.py` | 11 |
| O3-01 | `test_verdict_imports.py` | 1 |
| O3-02 | `test_board_factory.py` | 7 |
| O3-02 | `test_card_node_wiring.py` | 2 |
| O3-02 | `test_columns_and_unknown.py` | 3 |
| O3-02 | `test_wip_cap.py` | 3 |
| O3-02 | `test_transition_count_invariant.py` | 1 |
| O3-03 | `test_gate_predicates_basic.py` | 6 |
| O3-03 | `test_risk_thresholds.py` | 6 |
| O3-03 | `test_dry_run_gate.py` | 5 |
| O3-03 | `test_artifact_only_confidence.py` | 3 |
| O3-03 | `test_stub.py` | 4 |
| O3-03 | `test_stub_full_lifecycle.py` | 3 |
| O3-04 | `test_tick_clock.py` | 4 |
| O3-04 | `test_timeout_tick.py` | 3 |
| O3-04 | `test_budget_tick.py` | 1 |
| O3-04 | `test_critic_loop.py` | 3 |
| O3-04 | `test_board_lifecycle.py` | 4 |
| O3-04 | `test_100_card_stress.py` | 1 |
| | **Total O3 tests** | **80** |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (substrate-gate scope)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Every OBRD-01..OBRD-09 appears in >= 1 plan
- [x] Every plan declares OBRD coverage in `requirements:` frontmatter
- [x] All 15 SPEC acceptance criteria have proving test files

**Approval:** green 2026-05-20 — 80 board tests pass across 4 waves. All OBRD-01..OBRD-09 green. All 15 SPEC acceptance criteria covered with automated tests. Phase complete.
