# Phase V5: Board State Machine (supersedes O3) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.137 (gate: ≤ 0.20)
**Requirements:** 5 locked (delta on shipped O3)

## Goal

Close the gap between the shipped O3 board package and PRD BOARD-01..10: ship a read-only `voss board` CLI, complete the `Card` field set, and guarantee a card cannot reach Done without an independent reviewer verdict — while keeping the shipped state machine (columns/WIP/gates/Done-double-gate/timeout/persistence) intact and deferring reviewer A/B intelligence to V6.

## Background

O3 shipped a near-complete board package (`voss/harness/board/`, plans O3-01..04 with SUMMARYs):
- `machine.py` (21KB): `Board`, `Card` (1:1 `SessionTreeNode` via `allocate_child`), `Column` (6: Backlog/Planned/InProgress/InReview/Blocked/Done), `RiskTier`, per-column WIP (`BoardWIPError`), `Board.move` with gate enforcement + transition-delta emission.
- `gates.py`: 8 typed predicates / 7 stable names; artifact-only confidence (`InProgress→InReview`, `InReview→Done`); Done double-gate (code: `tests_pass`; ai: `eval_meets_threshold`).
- `errors.py` (WIP/Gate/Timeout); `tick.py` (timeout/critic→Blocked); `reviewer_a.py`/`reviewer_b.py`/`verdict.py` (`Reviewer`/`ReviewerVerdict` — stubs); `stub.py`.
- Transition persistence via `SessionTreeManager` + node `transitions[]`/`retry_notes[]` + `finalize_node`.

So **BOARD-01, 02, 04, 05, 06, 08, 09 are shipped.** Gaps vs PRD BOARD-01..10:
- **BOARD-03** — `Card` has `node_id`/`risk_tier`/`scope`/`artifact` but not `idea`/`role`/`acceptance_criteria`/`verification_requirement`.
- **BOARD-07** — a reviewer hook + verdict exist, but the *independent-review-required-for-Done* guarantee (and the real A/B split) is not closed; A/B intelligence is V6.
- **BOARD-10** — no `voss board` CLI.

V5 supersedes O3 (ROADMAP); O3 artifacts retained as reference. V5 builds on V4 (the session-tree keystone the board already uses). **Locked direction (interview):** delta on shipped O3; add the missing `Card` fields (status←column, budget←node); `voss board [root_id]` read-only from persisted node files (default latest); Done requires an independent reviewer verdict (self-Done guard); reviewer A/B intelligence → V6.

## Requirements

1. **`voss board` CLI** (VBOARD-10): the board is viewable from the CLI.
   - Current: no `board` command in `cli.py`.
   - Target: `voss board [root_id]` renders the 6 columns with their cards (id, role, risk, status, budget spent/limit), reading **read-only** from persisted session-tree node files; `root_id` defaults to the most-recent root.
   - Acceptance: `voss board` (no arg) renders the latest run's columns+cards and exits 0; `voss board <root_id>` renders that root; an unknown root exits non-zero with a stderr message.

2. **Card field completeness** (VBOARD-03): a card carries the full PRD field set.
   - Current: `Card` = `node_id`, `risk_tier`, `scope`, `artifact`.
   - Target: add `idea`, `role`, `acceptance_criteria`, `verification_requirement` to `Card` (additive, back-compat defaults); `status` derives from the current column; `budget` derives from the node envelope.
   - Acceptance: `Card` carries `idea`/`role`/`acceptance_criteria`/`verification_requirement`; `status` resolves from the column; `budget` resolves from the node envelope; existing O3 card construction still works.

3. **Self-Done guard** (VBOARD-07): a card cannot mark its own work Done.
   - Current: Done gate runs reviewer/verdict predicates but the independent-review requirement is not explicitly guaranteed.
   - Target: a card cannot transition to Done without an **independent reviewer verdict** (the Board's Reviewer, not the worker/EM); a worker/EM-authored verdict is rejected. Reviewer A/B intelligence stays in V6 — V5 enforces only the *independence requirement* via the existing Reviewer interface.
   - Acceptance: a `move(card, "Done")` without a reviewer verdict raises `BoardGateError`; a verdict not sourced from the reviewer role is rejected; a valid reviewer verdict allows Done (given other gate predicates pass).

4. **Shipped surface verification** (verify): BOARD-01/02/04/05/06/08/09 regress green.
   - Current: shipped in O3.
   - Target: verify after the V5 changes — 6 columns, per-column WIP, gate registry, Done double-gate (code/ai), timeout/critic→Blocked, transition persistence to the session-tree node, Card↔node 1:1 backing.
   - Acceptance: existing O3 board tests pass; WIP overflow raises `BoardWIPError`; an unmet gate raises `BoardGateError`; timeout/critic-exhaustion moves a card to Blocked; each move appends to the node's `transitions[]`.

5. **O3 supersession + V4 dependency** (bookkeeping): mark O3 superseded; board sits on the V4 keystone.
   - Current: board integrates `session_tree.py` as shipped (pre-V4-delta).
   - Target: mark O3 superseded by V5; confirm the board operates on the V4 session-tree substrate (the pre-emptive budget guard from V4 sits beneath it; V5 adds no budget enforcement of its own).
   - Acceptance: ROADMAP/STATE mark O3 superseded; V5 introduces no budget-enforcement logic (that's V4); the board uses `SessionTreeManager`/`SessionTreeNode` as the node source.

## Boundaries

**In scope:**
- `voss board [root_id]` read-only CLI.
- `Card` field completeness (`idea`/`role`/`acceptance_criteria`/`verification_requirement`; derived status/budget).
- Self-Done guard (Done requires an independent reviewer verdict).
- Verification/regression of the shipped board surface.
- Mark O3 superseded (artifacts retained as reference).

**Out of scope:**
- Reviewer-A/B intelligence (bar authoring, judge) — V6 (V5 keeps the existing Reviewer/verdict interface + the independence guard only).
- EM card creation / dispatch / routing — V7.
- ADE board panel rendering — V11 (V5 ships the CLI view only).
- Pre-emptive budget enforcement / session-tree changes — V4 (the keystone V5 sits on).
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen.
- New third-party dependencies.

## Constraints

- `voss board` is **read-only from persisted** `.voss/sessions/<root>/*.json` (column = latest `node.transitions[]` entry; budget = envelope); no live `Board`/`SessionTreeManager` instance required; latest = most-recent root dir.
- The Done gate **must require an independent reviewer verdict** — a worker/EM cannot self-transition to Done.
- Reuse the existing `Reviewer`/`ReviewerVerdict` interface; V5 adds no reviewer intelligence.
- `Card` field additions are additive with back-compat defaults; existing construction paths keep working.
- No change to frozen `RunRecord`/`SessionRecord`/`BudgetScope`; `SessionTreeNode` changes are owned by V4.
- No new deps.

## Acceptance Criteria

- [ ] `voss board` (no arg) renders the latest run's 6 columns + cards (id/role/risk/status/budget spent-limit) from persisted node files and exits 0; `voss board <root_id>` renders that root; unknown root exits non-zero with stderr.
- [ ] `Card` carries `idea`/`role`/`acceptance_criteria`/`verification_requirement`; `status` derives from the column; `budget` derives from the node envelope.
- [ ] `move(card, "Done")` without an independent reviewer verdict raises `BoardGateError`; a worker/EM-sourced verdict is rejected; a valid reviewer verdict (with other predicates passing) permits Done.
- [ ] Shipped regress: 6 columns; per-column WIP raises `BoardWIPError`; unmet gate raises `BoardGateError`; Done double-gate (code/ai) intact; timeout/critic-exhaustion → Blocked; each move appends to the node's `transitions[]`.
- [ ] Card↔`SessionTreeNode` 1:1 backing intact (`Card.node_id` = the `allocate_child` node).
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                            |
|--------------------|-------|------|--------|------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Delta = CLI + Card fields + self-Done guard, pinned               |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Reviewer A/B→V6, EM→V7, ADE→V11, budget→V4 explicit              |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Read-only CLI source, independence guard, additive Card fields    |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 6 pass/fail criteria, delta-focused                              |
| **Ambiguity**      | 0.137 | ≤0.20| ✓      |                                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                         |
|-------|-------------------|--------------------------------------------------|------------------------------------------------------------------------|
| 0     | Researcher (scout)| What of BOARD-01..10 already exists?             | O3 shipped 01,02,04,05,06,08,09; gaps = Card fields / self-Done / CLI   |
| 1     | Researcher        | V5 scope given O3 shipped?                        | Delta on shipped O3; verify the rest; reviewer A/B → V6; O3 superseded  |
| 1     | Researcher        | Card field completeness (BOARD-03)?              | Add idea/role/acceptance_criteria/verification_requirement; derive status/budget |
| 1     | Researcher        | `voss board` CLI target+output?                  | `board [root_id]` default latest; read-only 6-col render               |
| 2     | Failure Analyst   | Enforce 'agents can't self-Done'?               | Done requires an independent reviewer verdict                          |
| 2     | Boundary Keeper   | V5/V6 reviewer line?                              | V5 keeps gate hook; V6 builds real A/B                                 |
| 2     | Boundary Keeper   | `voss board` data source?                         | Read-only from persisted session-tree node files                      |

---

*Phase: V5-board-state-machine-supersedes-o3*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V5 — implementation decisions (board render layout, Card field wiring, self-Done guard placement)*
