---
phase: V5-board-state-machine-supersedes-o3
plan: 02
subsystem: testing
tags: [board, state-machine, dataclass, reviewer, gate, python]

requires:
  - phase: V5-01
    provides: RED scaffolds test_card_fields_v5.py and test_self_done_guard.py
provides:
  - Four additive Card fields (idea/role/acceptance_criteria/verification_requirement, "" defaults)
  - Module-level helpers card_status(card) and card_budget(node_envelope)
  - Self-Done independence guard in Board.move (no-injected-reviewer fails closed)
affects: [V5-03, V6, V7]

tech-stack:
  added: []
  patterns:
    - "Derived view as module-level function (not @property) to dodge slots=True interaction"
    - "Explicit injection-tracking flag at __init__ for fail-closed access control"

key-files:
  created: []
  modified:
    - voss/harness/board/machine.py

key-decisions:
  - "Injected-reviewer detection uses an explicit self._reviewer_injected flag set from (reviewer is not None or reviewer_a is not None or reviewer_b is not None) — NOT a bare self._reviewer is None check"
  - "status/budget remain derived (module helpers), not stored Card fields"

patterns-established:
  - "Pattern 1: card_status/card_budget as module-level helpers, never @property on a slots=True frozen dataclass"
  - "Pattern 2: refused-delta-then-raise mirror — exactly one _append_delta(outcome='refused') before raising BoardGateError"

requirements-completed: [VBOARD-03, VBOARD-07]

duration: 12min
completed: 2026-06-06
---

# Phase V5-02: Card field completeness + self-Done independence guard Summary

**Four additive Card fields + card_status/card_budget helpers, plus a fail-closed Done guard in Board.move gated on an explicit reviewer-injection flag.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2
- **Files modified:** 1 (`voss/harness/board/machine.py`)

## Accomplishments
- VBOARD-03: appended `idea`/`role`/`acceptance_criteria`/`verification_requirement` (all `= ""`) to the frozen `Card` dataclass after `eval_threshold`; added module-level `card_status(card)` (returns `card.column`) and `card_budget(node_envelope)` (returns `(spent, limit)` with `(0,0)` default). No stored `status`/`budget` fields.
- VBOARD-07: inserted the self-Done independence guard in `Board.move` between the WIP block and `transition = (card.column, to)`. Fires when `to == "Done"` and no reviewer was injected; emits exactly one refused delta then raises `BoardGateError("Done requires an independent reviewer", failing_clauses=["no-reviewer"])`.

## Injected-Reviewer Detection (the subtle part)

`Board.__init__` does `self._reviewer = reviewer if reviewer is not None else reviewer_b`. A bare `self._reviewer is None` check is unsafe for the two-source gate: those boards inject only `reviewer_a`/`reviewer_b` (no legacy `reviewer`), so `self._reviewer` resolves to `reviewer_b` (non-None) and the check would pass — but if someone gated only on the *legacy* slot it would misfire the other way. To be unambiguous and fail-closed, I added an explicit flag in `__init__`:

```python
self._reviewer_injected = (
    reviewer is not None or reviewer_a is not None or reviewer_b is not None
)
```

The guard gates on `not self._reviewer_injected`. This is logically equivalent to `self._reviewer is not None` (since `self._reviewer` is non-None iff any of the three was supplied) but states the intent explicitly. Verified against:
- `test_reviewer_none_raises_board_gate_error`: `from_team_config(reviewer=None)` → all three None → `_reviewer_injected=False` → guard fires with `no-reviewer`. GREEN.
- `test_valid_reviewer_allows_done`: `reviewer=stub` → injected → Done permitted. GREEN.
- `TestTwoSourceGate` (`reviewer_a`+`reviewer_b` only, no legacy `reviewer`): `_reviewer_injected=True` → Done permitted. `test_both_pass_reaches_done` GREEN.

## Files Created/Modified
- `voss/harness/board/machine.py` — Card: 4 new fields; 2 new module-level helpers; `__init__`: `_reviewer_injected` flag; `Board.move`: VBOARD-07 guard.

## Decisions Made
- Used an explicit `self._reviewer_injected` flag rather than relying on the implicit `self._reviewer is None` so the no-self-Done access control is obviously fail-closed and immune to the `reviewer_b` default at line 260.
- Kept `status`/`budget` derived (module helpers) per VBOARD-03 — no sync hazard from stored fields.

## Deviations from Plan
None - plan executed exactly as written. Only `voss/harness/board/machine.py` changed.

## Issues Encountered
None.

## Verification

- `test_card_fields_v5.py` + `test_self_done_guard.py`: **GREEN** (8 passed).
- Named regressions GREEN: `test_card_node_wiring.py`, `test_stub_full_lifecycle.py`, `test_two_source_gate.py`, `test_transition_count_invariant.py`, `tests/harness/test_session_redaction.py`.
- Full board suite: the ONLY 6 failures are all `test_board_cli.py` (ImportError on `board_cmd`) — left RED for V5-03. No previously-green test flipped red. `test_exit_reasons_is_sorted_superset_of_pre_o3` stays GREEN.
- Scope: auto-committed as `f7c378f`, touching ONLY `voss/harness/board/machine.py`. verdict.py / gates.py / session.py / session_tree.py / voss_runtime / test files untouched.

## User Setup Required
None.

## Next Phase Readiness
- V5-03 can now add `board_cmd` / `cli_view.py` to green `test_board_cli.py`. Card now carries `role` for the CLI renderer (empty for pre-V5 nodes, per RESEARCH A2).

---
*Phase: V5-board-state-machine-supersedes-o3*
*Completed: 2026-06-06*
