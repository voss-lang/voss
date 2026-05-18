# Phase O1: Session-Tree Substrate + Budget Fan-out — Specification

**Created:** 2026-05-17
**Ambiguity score:** 0.157 (gate: ≤ 0.20)
**Requirements:** 5 locked

## Goal

The harness gains a parent→child agent session tree where a parent explicitly allocates a per-card budget envelope to each spawned child, the substrate enforces `sum(child envelopes) + reserve ≤ parent envelope`, caps cannot be raised, and a budget-drained child always finalizes a terminal record — implemented strictly harness-additively (no language-runtime or persisted-record schema change).

## Background

Today the harness is single-session-shaped:
- `voss/harness/subagents.py` `run_subagent` spawns a child turn that reuses the **parent's** permission gate, a fresh `EpisodicMemory(20)`, and has **no budget argument, no recorder, and no parent linkage**.
- `voss/harness/recorder.py` `RunRecorder` / `voss/harness/session.py` `RunRecord` are flat per-turn records. `RunRecord` has no parent field. `SessionRecord` has `parent_id`/`parent_turn_index`, but those are M9-06 **session-fork** lineage (resume/fork), not a live spawned-agent tree.
- `voss_runtime/budget.py` `BudgetScope` is a single flat `ContextVar` scope (token/latency/cost). No parent→child fan-out, no reserve, and it is re-enterable.
- `SessionRecord`/`RunRecord` are fixed-field dataclasses; `tests/harness/test_session_redaction.py` enforces the field allowlist — adding a field is a breaking change requiring a paired explicit redaction step.

O1 is the keystone: every other O-phase (O2–O6) renders off this substrate. It does not build the board, reviewers, or EM — only the recorded, budgeted, capped session tree they will use.

## Requirements

1. **Harness session tree**: Spawned child agent sessions are persisted nodes linked to their parent.
   - Current: `run_subagent` creates an unrecorded, unlinked child turn; `RunRecord` has no parent linkage; only session-fork lineage exists on `SessionRecord`.
   - Target: a new harness-side node type with minimum schema `{id, parent_run_id, envelope{limit, spent}, terminal_state}`; spawning a child creates a tree node linked to its parent. `voss_runtime.BudgetScope`, `SessionRecord`, and `RunRecord` field sets are unchanged.
   - Acceptance: spawning N children from a parent yields N persisted nodes each with `parent_run_id` = the parent's id; the full tree is reconstructable from persisted nodes; `tests/harness/test_session_redaction.py` passes unmodified.

2. **Explicit per-card budget allocation + fan-out invariant**: A parent allocates an explicit envelope per child; the substrate refuses oversell.
   - Current: `BudgetScope` is a single flat scope with no parent/child relationship; subagents receive no budget at all.
   - Target: the parent explicitly supplies a budget envelope per child card at spawn time; the substrate enforces `sum(child envelopes) + reserve ≤ parent envelope`. Allocation *policy* (equal split, WIP-driven) is explicitly O3's; O1 only enforces the invariant.
   - Acceptance: allocating children whose envelopes + reserve ≤ parent succeeds; an allocation that would exceed it raises a hard error and leaves no partial state (the rejected child is not created).

3. **Reserved drain budget → terminal-finalize guarantee**: A budget-exhausted child always finalizes; it is never stranded half-open.
   - Current: a budget-exhausted subagent has no finalize guarantee; `EXIT_REASONS` includes `"budget"` but `subagents.py` never emits a terminal record — a stranded half-open child is possible (Leak 4).
   - Target: a non-spendable reserve is carved from the parent envelope; a child that exhausts its spendable envelope always finalizes — emits exactly one terminal `RunRecord` with `exit_reason="budget"` and a closed recorder node. Verdict semantics (Blocked/Done) are explicitly deferred to O3.
   - Acceptance: a child driven to budget exhaustion produces exactly one `RunRecord` with `exit_reason="budget"` and a closed node (`terminal_state` set, `ended_at` populated); after parent teardown no node remains in an open state.

4. **Non-extendable cap with recorded escape attempts**: Budget caps cannot be raised; attempts are audited.
   - Current: `BudgetScope` is re-enterable via `ContextVar`; nothing prevents a child raising or replacing its own cap.
   - Target: any attempt by a child (or, later, the EM) to raise/extend its own budget cap raises a hard error AND records the rejected attempt on the node (audit trail consumed by O6).
   - Acceptance: invoking the cap-raise path on a child raises the documented error; the node carries a recorded entry of the rejected attempt; normal spend within the cap is unaffected by the recording.

5. **Strict harness-additive blast radius**: O1 introduces only new harness-side types.
   - Current: budget logic lives in `voss_runtime/budget.py`; record schemas are guarded by the redaction invariant.
   - Target: O1 adds only new harness-side types. `voss_runtime/budget.py` `BudgetScope`, `SessionRecord`, and `RunRecord` field sets are unchanged. Any budget-logic duplication-vs-reuse tradeoff is deferred to discuss-phase.
   - Acceptance: `git diff` shows no field added or removed on `SessionRecord`, `RunRecord`, or `BudgetScope`; `tests/harness/test_session_redaction.py` passes unmodified.

## Boundaries

**In scope:**
- New harness-side session-tree node type (`{id, parent_run_id, envelope{limit, spent}, terminal_state}`)
- Parent→child linkage created when a subagent is spawned
- Explicit per-card budget allocation + enforcement of `sum(children) + reserve ≤ parent`
- Reserved non-spendable drain budget + terminal-finalize guarantee for drained children
- Non-extendable cap + recording of rejected raise attempts
- Persistence of the tree sufficient to reconstruct it for audit

**Out of scope:**
- Board, columns, WIP, gated transitions — O3 (O1 is pure substrate)
- Budget allocation *policy* (equal split, WIP fan-out) — O3 owns policy; O1 enforces only the invariant
- Verdict semantics (Blocked/Done) — O3/O4 (O1 only guarantees terminal finalize)
- `.voss team{}` parsing, specialist roster, `SubagentSpec` enrichment — O2
- EM loop, specialist dispatch, routing rationale, kill/re-scope lineage — O5
- Audit surfacing, calibration telemetry, sign-off forcing function — O6
- Any change to `voss_runtime.BudgetScope`, `SessionRecord`, or `RunRecord` schema — deliberate, protects the fixed-field redaction invariant
- Role/routing stub fields on the node — excluded as untestable dead schema (nothing in O1 populates them)

## Constraints

- MUST NOT add or alter fields on `SessionRecord`, `RunRecord`, or `voss_runtime.BudgetScope` — the fixed-field redaction invariant is enforced by `tests/harness/test_session_redaction.py` and is a one-way door.
- Children may run concurrently (async). Fan-out invariant enforcement and reserve accounting MUST be correct under concurrent child spend — no oversell race (the `sum(children) + reserve ≤ parent` invariant must hold even when multiple children spend simultaneously).
- Tests follow existing `tests/harness/` conventions (pytest, class-based).
- No new third-party dependencies.

## Acceptance Criteria

- [ ] Spawning N children yields N persisted nodes, each with `parent_run_id` = parent id; tree is reconstructable from persisted nodes
- [ ] Allocation with `sum(children) + reserve ≤ parent` succeeds
- [ ] Allocation that would exceed `parent − reserve` raises a hard error and creates no partial/child state
- [ ] A budget-drained child emits exactly one `RunRecord` with `exit_reason="budget"` and a closed node
- [ ] No node remains open after parent teardown
- [ ] Cap-raise attempt raises the documented error AND is recorded on the node
- [ ] Concurrent children cannot oversell the parent envelope (invariant holds under concurrent spend)
- [ ] `git diff` shows zero field changes on `SessionRecord`, `RunRecord`, `BudgetScope`
- [ ] `tests/harness/test_session_redaction.py` passes unmodified

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Unit, blast radius, reserve, cap, fan-out all pinned          |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Explicit O1/O3 split; redaction invariant explicitly excluded |
| Constraint Clarity | 0.72  | 0.65 | ✓      | Redaction invariant + concurrency no-oversell race captured   |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 9 pass/fail criteria                                          |
| **Ambiguity**      | 0.157 | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective           | Question summary                          | Decision locked                                                                 |
|-------|-----------------------|-------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher            | What is the budget-fan-out unit at O1?    | Card is the unit; O1 models the card now                                         |
| 1     | Researcher            | O1 blast radius vs. language runtime?     | Harness-additive only; BudgetScope/SessionRecord/RunRecord untouched             |
| 1     | Researcher            | What does the reserve guarantee mean?     | Drained child always finalizes terminal `RunRecord exit_reason='budget'` + closed node; verdict → O3 |
| 2     | Researcher/Simplifier | Non-extendable cap behavior?              | Cap-raise attempt raises hard error AND records the attempt                       |
| 2     | Researcher/Simplifier | How is a child's envelope determined?     | Parent explicitly allocates per-card; substrate enforces sum+reserve ≤ parent     |
| 2     | Researcher/Simplifier | Irreducible card-node schema?             | `{id, parent_run_id, envelope{limit,spent}, terminal_state}`                     |

---

*Phase: O1-session-tree-substrate-budget-fan-out*
*Spec created: 2026-05-17*
*Next step: /gsd:discuss-phase O1 — implementation decisions (how to build what's specified above)*
