# Phase O1: Session-Tree Substrate + Budget Fan-out - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

O1 is the keystone of the O-track (Caged Autonomous Eng Team). It turns the single-session harness into a recorded parent→child agent **session tree** with per-card budget fan-out, a reserved drain budget that guarantees terminal finalization, and non-extendable caps. Pure substrate — it builds none of the board (O3), reviewers (O4), EM (O5), or audit surfacing (O6) that render off it.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 requirements are locked.** See `O1-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `O1-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- New harness-side session-tree node type (`{id, parent_run_id, envelope{limit, spent}, terminal_state}`)
- Parent→child linkage created when a subagent is spawned
- Explicit per-card budget allocation + enforcement of `sum(children) + reserve ≤ parent`
- Reserved non-spendable drain budget + terminal-finalize guarantee for drained children
- Non-extendable cap + recording of rejected raise attempts
- Persistence of the tree sufficient to reconstruct it for audit

**Out of scope (from SPEC.md):**
- Board, columns, WIP, gated transitions — O3
- Budget allocation *policy* (equal split, WIP fan-out) — O3 owns policy; O1 enforces only the invariant
- Verdict semantics (Blocked/Done) — O3/O4
- `.voss team{}` parsing, specialist roster, `SubagentSpec` enrichment — O2
- EM loop, specialist dispatch, routing rationale, kill/re-scope lineage — O5
- Audit surfacing, calibration telemetry, sign-off forcing function — O6
- Any change to `voss_runtime.BudgetScope`, `SessionRecord`, or `RunRecord` schema — protects the fixed-field redaction invariant
- Role/routing stub fields on the node — untestable dead schema

</spec_lock>

<decisions>
## Implementation Decisions

### Tree Persistence Shape
- **D-01:** Per-node files at `.voss/sessions/<root_id>/<node_id>.json`, one file per node, written incrementally as the tree grows. Chosen over a single tree-file-at-finalize (loses tree on mid-run crash — weakens the Leak-4 stranded-child audit) and over embedding children in the existing session JSON (bloat + SessionRecord-shape coupling risk). Existing single-session files at `.voss/sessions/<id>.json` are unchanged; the tree is a new sibling structure under a per-root directory. Crash-safe + append-friendly + directly consumable by O6 audit/replay and resume.

### Budget Accounting Source
- **D-02:** Compose `voss_runtime.BudgetScope` per node. Each child node owns a `BudgetScope` instance for spend tracking (reuse its battle-tested `check()` / `add_usage()`); the new harness session-tree layers the parent→child fan-out invariant (`sum(children) + reserve ≤ parent`) on top. No duplicated budget arithmetic, no drift. This is the resolution of the reuse-vs-duplicate question SPEC.md explicitly deferred to discuss-phase — and it stays within the locked "harness-additive only" boundary because `BudgetScope` is consumed unchanged (no new fields, no schema edit).

### Drain / Finalize Trigger
- **D-03:** Exception-at-single-boundary. `BudgetExceededError` raised by `BudgetScope.check()` is caught at the one subagent-run harness boundary, which ALWAYS finalizes: emits exactly one terminal `RunRecord` with `exit_reason="budget"` and closes the node. The reserved drain budget covers the cost of writing that final record. Chosen over cooperative self-check (relies on every child loop path being disciplined — a missed check strands a node) and supervisory monitor (adds a concurrent monitor + teardown-race handling). One chokepoint that cannot be forgotten = the structural mechanism that closes Leak 4.

### Cap-Raise Attempt Surface
- **D-04:** Single guarded envelope mutator. All envelope writes funnel through one method: an upward delta (cap raise/extend) raises a hard error AND records the rejected attempt on the node; spend / downward writes are allowed. No separate raise-cap API that could be left unguarded. SPEC.md ruled out "structurally impossible" (must be auditable), so the attempt surface exists by construction here, and every write is audited — O6 gets a complete attempt log; O5's EM has exactly one funnel to constrain.

### Claude's Discretion
- Concurrency primitive used to make the `sum(children) + reserve ≤ parent` invariant hold under concurrent child spend (lock vs. atomic accounting) — left to researcher/planner; SPEC only mandates the no-oversell outcome.
- Node-id scheme and the exact per-node JSON field serialization (within the locked logical schema `{id, parent_run_id, envelope{limit, spent}, terminal_state}`).
- Resume semantics for a partially-written tree (how `voss resume` rehydrates an interrupted root) — substrate must not preclude it; exact behavior is a planning detail.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements (read first)
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md` — Locked requirements, boundaries, acceptance criteria — MUST read before planning
- `.planning/ORCHESTRATION-PLAN.md` — O-track design + 21-row decision log + cross-O cage invariants; the authoritative O-track decision source (O1 is §9 keystone)
- `.planning/ROADMAP.md` — O1 phase entry + "O-prefixed phases" section (cage invariants, dependency chain)

### Code the phase extends (harness-additive)
- `voss/harness/recorder.py` — `RunRecorder` / `finalize()` producing `RunRecord`; the terminal-finalize path D-03 hooks
- `voss/harness/session.py` — `RunRecord` / `SessionRecord` (fixed-field, redaction invariant); `EXIT_REASONS` already includes `"budget"`; `parent_id`/`parent_turn_index` are session-fork lineage, NOT the live tree
- `voss/harness/subagents.py` — `run_subagent` / `attach_subagent_tool`; the single boundary D-03 finalizes at; currently no budget/recorder/parent plumbing
- `voss_runtime/budget.py` — `BudgetScope` (`check`/`add_usage`/`BudgetExceededError`); composed per-node by D-02, consumed unchanged
- `tests/harness/test_session_redaction.py` — enforces the fixed-field allowlist; must pass unmodified (acceptance criterion)

### Project conventions (carried forward, not re-asked)
- `.planning/PROJECT.md` §Constraints — `.voss/` durable vs `.voss-cache/` rebuildable; no provider secrets in sessions; Python runtime; generated code imports `voss_runtime`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `voss_runtime.BudgetScope`: per-node spend tracking via composition (D-02). `check()` raises `BudgetExceededError` — the exact signal D-03's boundary catches.
- `RunRecorder.finalize(cwd, cost_usd, *, exit_reason=...)` → `RunRecord`: the terminal-record producer; `EXIT_REASONS` already contains `"budget"`, so the terminal `exit_reason="budget"` record needs no schema change.
- `.voss/sessions/` storage convention + `session.save()` (0600, json.dumps): the per-root tree directory (D-01) sits beside it using the same durable-state location and permission posture.

### Established Patterns
- Fixed-field dataclass + `_hydrate` unknown-key drop (session.py): the redaction invariant. O1 must add NO field to `SessionRecord`/`RunRecord`/`BudgetScope` — new tree types are separate harness-side structures.
- `subagents.run_subagent` is already the single spawn chokepoint (`SPAWN_TOOL_NAME = "subagent_run"`): natural home for D-03's always-finalize boundary and D-01 node creation.

### Integration Points
- `subagents.run_subagent` → create tree node (D-01) + compose child `BudgetScope` (D-02) + wrap in the always-finalize boundary (D-03).
- Envelope writes → the single guarded mutator (D-04), through which composed-`BudgetScope` spend flows.
- Per-node files under `.voss/sessions/<root_id>/` → consumed later by O6 audit/replay.

</code_context>

<specifics>
## Specific Ideas

- The four decisions interlock by design: the exception-at-boundary finalize (D-03) writes a per-node file (D-01); the guarded mutator (D-04) is the one funnel composed-`BudgetScope` spend (D-02) flows through; O6 audit reads the per-node tree directory. Planner should treat them as one coherent substrate, not four independent features.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Allocation policy, verdict semantics, board, roster, EM, and audit surfacing were all correctly deferred to O2–O6 by SPEC.md and not re-litigated.)

</deferred>

---

*Phase: O1-session-tree-substrate-budget-fan-out*
*Context gathered: 2026-05-17*
