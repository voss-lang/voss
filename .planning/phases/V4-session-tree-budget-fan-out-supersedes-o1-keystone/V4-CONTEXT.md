# Phase V4: Session Tree + Budget Fan-out (supersedes O1 — KEYSTONE) - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct synthesis from V4-SPEC.md (ambiguity 0.141; discuss-phase skipped — SPEC interview already locked direction)

<domain>
## Phase Boundary

Close the delta between the **shipped O1 substrate** (`voss/harness/session_tree.py`, 192 lines) and PRD TREE-01..10 so every agent/subagent is a durable, budgeted, terminally-finalized node. This is the substrate every later V-phase (V5 board, V6 reviewers, V7 EM, V9 audit, V11 ADE) renders off.

**Already shipped in O1 (verify-only, do not rebuild):** TREE-01..06 — `SessionTreeNode`, `SessionTreeManager.allocate_child` (no-oversell under `asyncio.Lock`), per-node JSON at `.voss/sessions/<root_id>/<node_id>.json` (0o600), idempotent `finalize_node`, `mutate_envelope` rejecting `delta>0`, `rejected_raises[]` audit. O3 already added `transitions[]`, `retry_notes[]`, `get_node`.

**V4 builds the gaps:**
- **Pre-emptive spend guard** (the keystone correctness fix) — `mutate_envelope` records spend post-hoc; nothing blocks the breaching call. Budget-as-security-boundary not yet real.
- **TREE-07** — all-reason finalize *mechanism* + wire error/timeout/budget paths (O1 only wired budget-drain).
- **TREE-08** — scope/role node fields (O1 excluded as dead schema).
- **TREE-09** — `voss session tree <root_id>` CLI.
- **TREE-10** — consolidated machine-readable JSON export per root.

Pure substrate — no board, no reviewers, no EM here.

</domain>

<decisions>
## Implementation Decisions

### Scope: delta-only on shipped O1
- Verify/regress TREE-01..06; build only the gaps (enforcement, finalize wiring, scope/role, CLI, export).
- O1 marked superseded/absorbed (bookkeeping); O1 artifacts retained as reference design.

### Pre-emptive spend guard (VTREE-04 — keystone)
- A node refuses to **begin** an iteration/call when its spendable envelope is exhausted (`spent ≥ limit`) — halts **before** the breaching spend, finalizes `exit_reason="budget"`.
- Enforcement is at the **iteration/call boundary** — exact per-call output cost is unknowable pre-call, so the guard does not predict per-call cost; it blocks starting a call when already at/over envelope.
- Keep the existing `allocate_child` allocation invariant (`sum(child limits) + reserve ≤ parent`).
- Guard correctness must hold under concurrent child spend — reuse the existing `asyncio.Lock`, no oversell race.

### Always-finalize (VTREE-07): mechanism for all reasons, wire 3 now
- Guarantee `finalize_node` works for ALL `EXIT_REASONS`.
- Wire the always-finalize boundary so **error, timeout, and budget** termination paths each emit exactly one terminal node.
- `killed`/`blocked` emitters deferred to V5/V7 — V4 proves the mechanism; those reasons get emitted later (reuse this mechanism).

### Scope + role metadata (VTREE-08)
- Add `scope` + `role` fields to `SessionTreeNode` — **additive, nullable**.
- Populate at spawn when available (role from a V3 spec when present; scope from allocation context); null when unknown.
- Full population via V7 EM dispatch (later). Both fields present in the export.

### CLI (VTREE-09)
- `voss session tree <root_id>` reads persisted nodes for a root and prints a tree: id, parent, envelope limit/spent, terminal_state, scope, role.
- Exits 0 for a known root; unknown root exits non-zero with a stderr message.

### Export (VTREE-10)
- API + reachable via CLI: returns a single JSON object per `root_id` — all nodes, parent linkage, envelopes, terminal states, scope/role.
- Round-trips the persisted tree. ADE *rendering* deferred to V11 (V4 ships export data only).

### Depth-1 only
- No recursive multi-level fan-out (child-of-child) in V4 — recursion → V8 (MAG-07).

### Claude's Discretion
- Exact placement/shape of the pre-emptive guard call site within the iteration loop (subagent/harness boundary).
- Internal structure of the export function and CLI rendering format (tree-print style).
- Test organization within `tests/harness/` conventions.
- How `scope` is derived from allocation context.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Shipped substrate (the delta target)
- `voss/harness/session_tree.py` — `SessionTreeNode`, `SessionTreeManager`, `finalize_node`, `mutate_envelope`, `allocate_child` (192 lines — the file V4 extends).
- `tests/harness/test_session_tree.py` — existing tree tests (must regress green).
- `tests/harness/test_session_redaction.py` — **must pass UNMODIFIED** (redaction/schema-freeze invariant).
- `tests/harness/test_session_roundtrip.py`, `test_session.py`, `test_session_iterations.py` — adjacent session tests.

### Frozen schemas (do NOT modify any field)
- `SessionRecord`, `RunRecord` (session/recorder modules), `voss_runtime.BudgetScope` — frozen; `git diff` must show zero field changes.

### Reuse (per SPEC)
- `RunRecorder`, `BudgetScope`, `run_subagent`, M13 allocator, `subagents.py` (gains budget/scope/recorder plumbing it lacks today).

### Prior-phase reference design
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-RESEARCH.md`, `O1-PATTERNS.md`, `O1-CONTEXT.md`, `O1-SPEC.md` — O1 design rationale.
- `.planning/phases/V4-.../V4-SPEC.md` — locked requirements VTREE-01..10 + acceptance criteria.

</canonical_refs>

<specifics>
## Specific Ideas

- Pre-emptive guard halts at `spent >= limit` BEFORE starting the next call, then `finalize_node(exit_reason="budget")`.
- `finalize_node` must accept every value in `EXIT_REASONS`; error/timeout/budget each emit exactly one terminal node (`terminal_state` set, `ended_at` populated).
- No node remains open after parent teardown.
- `_hydrate_node` back-compat (`setdefault`) must keep loading pre-V4 node files (missing scope/role → null).
- Tests: pytest, class-based, `tests/harness/` conventions. **No new third-party deps.**

</specifics>

<deferred>
## Deferred Ideas

- Recursive multi-level fan-out (child-of-child) → V8 (MAG-07).
- ADE rendering of the tree → V11 (V4 ships export data only).
- Full scope/role population via EM dispatch → V7.
- `killed`/`blocked` terminal emitters → V5/V7 (mechanism proven here).
- Board columns/WIP/gates/verdicts → V5; reviewers → V6.

</deferred>

---

*Phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone*
*Context synthesized: 2026-06-06 direct from V4-SPEC.md (discuss-phase skipped per locked SPEC interview)*
