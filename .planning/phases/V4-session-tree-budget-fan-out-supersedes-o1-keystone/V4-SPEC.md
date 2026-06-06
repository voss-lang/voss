# Phase V4: Session Tree + Budget Fan-out (supersedes O1 — KEYSTONE) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.141 (gate: ≤ 0.20)
**Requirements:** 10 locked (VTREE-01..10; delta on shipped O1)

## Goal

Close the gap between the shipped O1 session-tree substrate and PRD TREE-01..10 so every agent is a durable, budgeted, terminally-finalized node — adding a **pre-emptive spend guard** (a node cannot execute the call that would breach its envelope), an all-reason finalize guarantee, scope+role node metadata, a `voss session tree` CLI, and a machine-readable consolidated export — without touching the frozen `SessionRecord`/`RunRecord`/`BudgetScope` schemas.

## Background

O1 already shipped a working substrate (`voss/harness/session_tree.py`, plans O1-01/O1-02 with SUMMARYs):
- `SessionTreeNode` (`id, root_id, parent_run_id, envelope{limit,spent}, terminal_state, created_at, ended_at, rejected_raises[]`; O3 already added `transitions[]`, `retry_notes[]`, `get_node`).
- `SessionTreeManager.allocate_child` — enforces `sum(child limits) + reserve ≤ parent` under an `asyncio.Lock` (no-oversell); per-node JSON at `.voss/sessions/<root_id>/<node_id>.json` (0o600).
- `finalize_node` — idempotent terminal seal, validates `exit_reason ∈ EXIT_REASONS`.
- `mutate_envelope` — rejects `delta>0` (non-extendable cap) and appends to `rejected_raises`.

So **TREE-01..06 are effectively shipped.** The gaps vs PRD TREE-01..10:
- **Pre-emptive enforcement missing** — `mutate_envelope` records spend *after the fact* (`spent += delta`); nothing blocks the call that breaches the envelope. "Budget = security boundary" is not yet real.
- **TREE-07** — only budget-drain finalize was guaranteed in O1; error/timeout paths unverified; finalize for all reasons unproven.
- **TREE-08** — O1 *deliberately excluded* scope/role node fields as "dead schema."
- **TREE-09** — no `voss session tree` CLI.
- **TREE-10** — only per-node files; no consolidated machine-readable export.

V4 supersedes O1 (ROADMAP); O1's phase artifacts remain as reference design. **Locked direction (interview):** delta-only on shipped O1; pre-emptive spend guard; scope/role schema+plumbing + JSON export + CLI in V4 with ADE *rendering* deferred to V11; depth-1 only (recursion → V8); carry O1's schema freeze; finalize *mechanism* for all `EXIT_REASONS` with error/timeout/budget wired in V4 (killed/blocked emitters → V5/V7).

## Requirements

1. **SessionTreeNode (verify + extend)**: the node type persists and round-trips, extended additively with scope/role.
   - Current: `SessionTreeNode` exists; no scope/role fields; `_hydrate_node` uses `setdefault` for back-compat.
   - Target: node verified intact; scope + role fields added additively (nullable), back-compat hydrate preserved.
   - Acceptance: node carries `scope` + `role` fields; missing in old files → null on hydrate; all prior fields unchanged.

2. **SessionTreeManager (verify + extend)**: the per-tree allocator works and gains spend-guard + export hooks.
   - Current: `allocate_child`/`get_node`/lock exist.
   - Target: manager verified; extended only as needed for the pre-emptive guard (VTREE-04) and export (VTREE-10).
   - Acceptance: existing manager behavior regresses green; new methods covered by tests.

3. **Persistence (verify)**: each node persists durably and the tree reconstructs from disk.
   - Current: `.voss/sessions/<root_id>/<node_id>.json` at 0o600.
   - Target: unchanged; verified that the full tree reconstructs from persisted nodes alone.
   - Acceptance: spawning N children yields N node files; tree reconstructable from files without the chat transcript.

4. **Fan-out invariant + pre-emptive spend guard**: allocation cannot oversell AND a node cannot spend past its envelope.
   - Current: `allocate_child` enforces `sum + reserve ≤ parent`; `mutate_envelope` records spend post-hoc with no ceiling check.
   - Target: keep the allocation invariant; ADD a pre-emptive guard — a node refuses to **begin** an iteration/call when its spendable envelope is exhausted (`spent ≥ limit`), halting **before** the breaching spend and finalizing `exit_reason="budget"`. (Exact per-call output cost is unknowable pre-call; enforcement is at the iteration boundary.)
   - Acceptance: a node at/over its envelope cannot start another call (guard halts before spend); a child driven to exhaustion stops at the boundary, not after overspending; concurrent children still cannot oversell the parent (lock holds).

5. **Non-extendable cap (verify)**: caps cannot be raised.
   - Current: `mutate_envelope` rejects `delta>0` via `BudgetCapRaiseError`.
   - Target: verified; unchanged.
   - Acceptance: a cap-raise attempt raises `BudgetCapRaiseError`; normal in-cap spend unaffected.

6. **Rejected-raise audit (verify)**: rejected raises are recorded.
   - Current: `rejected_raises[]` appended + persisted on rejection.
   - Target: verified; unchanged.
   - Acceptance: a rejected raise produces a `rejected_raises` entry persisted on the node.

7. **Always-finalize (mechanism + V4-era reasons)**: every terminating child finalizes exactly once.
   - Current: `finalize_node` idempotent + validates `EXIT_REASONS`; only budget-drain finalize wired in O1.
   - Target: guarantee `finalize_node` works for ALL `EXIT_REASONS`; wire the always-finalize boundary so **error, timeout, and budget** termination paths each emit exactly one terminal node. `killed`/`blocked` emitters deferred to V5/V7 (reuse this mechanism).
   - Acceptance: a child terminating via error, timeout, or budget each yields exactly one finalized node (`terminal_state` set, `ended_at` populated); no node open after teardown; `finalize_node` accepts every `EXIT_REASONS` value.

8. **Scope + role metadata**: nodes carry scope and role, populated where known.
   - Current: nodes have neither (O1 excluded as dead schema).
   - Target: populate `scope`/`role` at spawn when available (role from a V3 spec when present; scope from allocation context); null when unknown. Full population via V7 EM dispatch.
   - Acceptance: spawning a child with a known role/scope persists them; spawning without → null; both fields present in the export.

9. **`voss session tree <root_id>` CLI**: the tree is inspectable from the CLI.
   - Current: no such command.
   - Target: a CLI command that reads persisted nodes for a root and prints a tree (id, parent, envelope limit/spent, terminal_state, scope, role).
   - Acceptance: `voss session tree <root_id>` exits 0 and prints the node tree for a known root; an unknown root exits non-zero with a stderr message.

10. **Machine-readable consolidated export**: one JSON document represents a whole tree.
    - Current: only per-node files; no consolidated export.
    - Target: an export (API + reachable via the CLI) returning a single JSON object per `root_id` — all nodes, parent linkage, envelopes, terminal states, scope/role — for ADE consumption. ADE *rendering* is V11.
    - Acceptance: the export returns one valid JSON object per `root_id` containing every node with parent linkage + envelope + terminal_state + scope/role; it round-trips the persisted tree.

## Boundaries

**In scope:**
- Pre-emptive spend guard (the keystone correctness fix).
- All-reason finalize *mechanism* + wiring of error/timeout/budget termination paths.
- `scope` + `role` fields on `SessionTreeNode` + spawn-time population where available.
- `voss session tree <root_id>` CLI.
- Consolidated machine-readable JSON export per root.
- Verification/regression of the shipped TREE-01..06 surface.
- Mark O1 superseded/absorbed (bookkeeping; O1 artifacts retained as reference).

**Out of scope:**
- Recursive multi-level fan-out (child-of-child) — V8 (MAG-07).
- ADE rendering of the tree — V11 (V4 ships the export data only).
- Full scope/role population via EM dispatch — V7 (V4 populates only what's available at spawn).
- `killed`/`blocked` terminal emitters — V5/V7 (V4 proves the finalize mechanism; those reasons get emitted later).
- Board columns/WIP/gates/verdicts — V5; reviewers — V6.
- Any field change to `SessionRecord`, `RunRecord`, or `voss_runtime.BudgetScope` — frozen (redaction invariant).
- New third-party dependencies.

## Constraints

- **Schema freeze (carried from O1):** no field added/removed on `SessionRecord`, `RunRecord`, or `voss_runtime.BudgetScope`; `tests/harness/test_session_redaction.py` must pass unmodified.
- `SessionTreeNode` may be extended additively only; `_hydrate_node` back-compat (`setdefault`) must keep loading pre-V4 node files.
- **Concurrency:** the fan-out invariant AND the pre-emptive spend guard must be correct under concurrent child spend (no oversell race) — reuse the existing `asyncio.Lock`.
- **Pre-emptive semantics:** the guard refuses to *start* a call/iteration when the spendable envelope is exhausted; it does not predict exact per-call cost.
- Tests follow `tests/harness/` conventions (pytest, class-based). No new deps.

## Acceptance Criteria

- [ ] A node whose spendable envelope is exhausted cannot start another iteration/call — the guard halts before the breaching spend and finalizes `exit_reason="budget"`.
- [ ] A child driven to budget exhaustion yields exactly one finalized node (`terminal_state` set, `ended_at` populated) and stops at the boundary (no overspend beyond envelope).
- [ ] `finalize_node` accepts every value in `EXIT_REASONS`; error, timeout, and budget termination paths each emit exactly one terminal node.
- [ ] No node remains open after parent teardown.
- [ ] `SessionTreeNode` carries `scope` + `role`; populated when known at spawn, null otherwise; present in the export.
- [ ] `voss session tree <root_id>` exits 0 and prints the node tree (id/parent/envelope/terminal/scope/role) for a known root; unknown root exits non-zero with stderr.
- [ ] The consolidated export returns one valid JSON object per `root_id` with all nodes + parent linkage + envelope + terminal_state + scope/role; round-trips the persisted tree.
- [ ] Concurrent children cannot oversell the parent envelope (regression holds).
- [ ] `git diff` shows zero field changes on `SessionRecord`, `RunRecord`, `BudgetScope`.
- [ ] `tests/harness/test_session_redaction.py` passes unmodified.
- [ ] Shipped TREE-01..06 surface regresses green (existing `session_tree` tests pass).

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                 |
|--------------------|-------|------|--------|-----------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Delta scope + pre-emptive guard pinned                                 |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Recursion→V8, render→V11, role-pop→V7, killed/blocked→V5/V7 all out    |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Schema freeze carried; concurrency; pre-emptive boundary semantics      |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 11 pass/fail criteria, delta-focused                                   |
| **Ambiguity**      | 0.141 | ≤0.20| ✓      |                                                                       |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                   | Decision locked                                                              |
|-------|-------------------|---------------------------------------------------|-----------------------------------------------------------------------------|
| 0     | Researcher (scout)| What of TREE-01..10 already exists?               | O1 shipped session_tree.py → TREE-01..06 done; 07/08/09/10 + enforcement gap |
| 1     | Researcher        | V4 scope given O1 shipped?                         | Delta on shipped O1; verify 01..06, build the gaps; O1 superseded            |
| 1     | Researcher        | How to enforce budget (post-hoc gap)?             | Pre-emptive spend guard — block + finalize at envelope boundary              |
| 1     | Researcher        | Where do TREE-08 scope/role + TREE-10 export land?| Schema+plumbing+export+CLI in V4; ADE rendering deferred to V11              |
| 2     | Boundary Keeper   | Recursive depth>1 in V4?                           | Depth-1 only; recursion → V8 (MAG-07)                                        |
| 2     | Boundary Keeper   | Carry O1's SessionRecord/RunRecord/BudgetScope freeze? | Yes; extend SessionTreeNode only; redaction test green                  |
| 2     | Failure Analyst   | What does "always finalize" guarantee in V4?      | Mechanism for all EXIT_REASONS; wire error/timeout/budget; killed/blocked→V5/V7 |

---

*Phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V4 — implementation decisions (guard placement, CLI/export shape, scope/role wiring)*
