# Phase O1: Session-Tree Substrate + Budget Fan-out - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** O1-session-tree-substrate-budget-fan-out
**Areas discussed:** Tree persistence shape, Budget accounting source, Drain/finalize trigger, Cap-raise attempt surface

---

## Tree Persistence Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Per-node files under root dir | `.voss/sessions/<root_id>/<node_id>.json`, incremental, crash-safe, best for O6 audit/replay + resume | ✓ |
| Single tree file at finalize | In-memory during run, flushed at root finalize; mid-run crash loses tree (weakens Leak-4 audit) | |
| Embed children in session JSON | Embedded tree alongside session file; bloat + SessionRecord-shape coupling risk | |

**User's choice:** Per-node files under root dir
**Notes:** Existing single-session files unchanged; tree is a new sibling structure. Crash-safety + O6 consumability drove it.

---

## Budget Accounting Source

| Option | Description | Selected |
|--------|-------------|----------|
| Compose BudgetScope per node | Child node owns a `BudgetScope` (reuse check/add_usage); harness tree layers fan-out enforcement. No duplicated arithmetic | ✓ |
| Independent harness ledger | New decoupled arithmetic; maximal isolation but two implementations to keep in sync (drift risk) | |
| You decide | Defer reuse-vs-duplicate to researcher/planner | |

**User's choice:** Compose BudgetScope per node
**Notes:** Resolves the reuse-vs-duplicate question SPEC.md explicitly deferred to discuss-phase. Stays inside "harness-additive only" since BudgetScope is consumed unchanged.

---

## Drain / Finalize Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Exception at single boundary | `BudgetExceededError` caught at the one subagent-run boundary that always finalizes terminal `RunRecord exit_reason='budget'` + closes node; reserve covers the write | ✓ |
| Cooperative self-check | Child loop self-finalizes on exhaustion; relies on every loop path being disciplined — a missed check strands a node | |
| Supervisory monitor | Out-of-band supervisor force-tears-down + finalizes; robust but adds concurrent monitor + teardown-race handling | |

**User's choice:** Exception at single boundary
**Notes:** One chokepoint that cannot be forgotten = the structural mechanism that closes Leak 4.

---

## Cap-Raise Attempt Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Single guarded envelope mutator | All envelope writes funnel through one method: upward delta → raise + record; spend/down allowed. Every write audited | ✓ |
| Explicit raise_cap() reject path | Dedicated reject+record method separate from spend path; two write surfaces to prove safe | |
| Frozen cap + separate spend ledger | Frozen limit + separate spend counter; rejected mutator still records attempt; extra bookkeeping | |

**User's choice:** Single guarded envelope mutator
**Notes:** SPEC ruled out "structurally impossible" (must be auditable). Single funnel → complete attempt log for O6, one constraint point for O5's EM.

## Claude's Discretion

- Concurrency primitive for the no-oversell invariant (lock vs. atomic accounting) — SPEC mandates only the outcome.
- Node-id scheme + exact per-node JSON serialization (within the locked logical schema).
- Resume semantics for a partially-written tree — substrate must not preclude it; behavior is a planning detail.

## Deferred Ideas

None — discussion stayed within phase scope. Allocation policy, verdict semantics, board, roster, EM, and audit surfacing were correctly deferred to O2–O6 by SPEC.md and not re-litigated.
