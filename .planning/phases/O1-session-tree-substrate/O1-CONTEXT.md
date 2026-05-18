# Phase O1: Session-Tree Substrate + Budget Fan-out - Context

**Gathered:** 2026-05-17
**Status:** Seeded from `.planning/ORCHESTRATION-PLAN.md` — needs `/gsd-spec-phase` then `/gsd-plan-phase`
**Source of truth:** `.planning/ORCHESTRATION-PLAN.md` (design + decision log §8, phase table §9)

<domain>
## Phase Boundary

O1 is the **keystone**. Every other O-phase renders off it. It makes every spawned agent a first-class recorded node with its own budget, scope, and audit — turning the single-session harness into a session *tree*.

**In scope:**
- Parent→child session tree in `voss/harness/recorder.py` / `voss/harness/session.py` (extend `RunRecorder`, `SessionRecord`).
- Per-card budget envelope; budget fan-out `(envelope − reserve) / total WIP` = guaranteed per-card floor.
- Reserved, non-spendable **drain budget** so every in-flight card can always reach a verdict (Done or Blocked) even when the main envelope is exhausted (liveness primitive, Leaks 4/5).
- Hard, **non-extendable** caps — no "ask for more tokens" path for any child (cage invariant #1).
- Budget/scope/recorder plumbing added to `voss/harness/subagents.py` (today it passes the parent gate, fresh memory, no budget arg).

**Out of scope (hard boundaries):** No board / WIP / transitions (O3). No reviewers (O4). No EM loop (O2/O5). No `.voss team{}` parser (O2). Pure substrate — the data model + budget arithmetic + recorder schema only.
</domain>

<decisions>
## Locked Decisions (from ORCHESTRATION-PLAN.md §8)

- **Budget is a security boundary, not a cost knob** (invariant #1). Fan-out is parent→card; caps are pre-committed and non-extendable by any agent including the EM.
- **Liveness is guaranteed by construction** (decision #18): a reserved non-spendable drain budget is a substrate primitive, not an O6 add-on. O6 only *surfaces* it.
- **The session-tree recorder IS the human review product** (invariant #7), not telemetry. Schema must be designed for replay/audit consumption, not just metrics.
- Reuse-honesty: `subagents.py`/`recorder.py`/`session.py` are extended, not reused as-is. Plan against real build cost (ORCHESTRATION-PLAN.md §6).

### Claude's discretion (resolve at SPEC/plan)
- Exact recorder schema shape for the tree (nested vs. flat parent-id rows).
- Reserve sizing policy (fixed tokens vs. % of envelope).
- Whether budget arithmetic lives in `voss_runtime/budget.py` or harness-side.
</decisions>

## Dependencies
- Depends on: none (keystone, first O-phase).
- Blocks: O2, O3, O4, O5, O6.
