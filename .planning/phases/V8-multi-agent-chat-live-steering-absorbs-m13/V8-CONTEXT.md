# Phase V8: Multi-agent Chat + Live Steering (absorbs M13) - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct synthesis from V8-SPEC.md (ambiguity 0.137; discuss-phase skipped — SPEC interview already locked direction)

> **⚠️ DEPENDENCY / SEQUENCING (operator decision 2026-06-06):** V8 is planned **against the post-V4 surface** — V4 is being executed now but is NOT yet on disk at planning time. **V8 hard-depends on V4 + M13 completion** and must execute only after both land. Verified on disk 2026-06-06: `session_tree.py` is currently the **O1 surface** (depth-1 `allocate_child(limit)` + `reserve` + `asyncio.Lock`; no pre-emptive guard / scope-role / export); M13 `multiagent.py` shipped (M13Allocator in-memory, explicitly NO `session_tree` import; M13-01..03 executed, 04..06 pending). The post-V4 API V8 targets is defined by V4-01..03 plans (see canonical refs) — plan the wiring against THAT, not the current O1 code.

<domain>
## Phase Boundary

Unify the shipped **M13 in-memory multi-agent chat** with the **V4 persisted session-tree cage**: route chat spawns through the V4 `SessionTreeManager` (single substrate), persist every chat child as a V4 node, deliver the **recursive (depth>1) persisted fan-out** V4 deferred to V8 (MAG-07), give the chat session a V4 root envelope, and verify the existing M13 spawn/steer/gather/panel surface. Closes PRD §2.2 fragmentation ("multi-agent chat not yet unified with the session-tree cage").

**Already shipped (M13, verify-only — do not rebuild):** MAG-01..09 — non-blocking spawn, immediate handle, status, gather, steer-between-iterations, child budget from parent, in-memory recursion, quiet-by-default TUI panel (`widgets/sub_agent_panel.py`), reveal. `attach_multiagent_tools` wired in `cli.py`; `/agent spawn`; `_teardown_orphans`.

**V8 builds the gap (MAG-10 + unify + recursion + root):**
- **VMAG-10** — chat children persist as V4 session-tree nodes (currently in-memory `ChildRegistry` only).
- **VMAG-UNIFY** — route chat spawn allocation through V4 `SessionTreeManager.allocate_child`; replace `M13Allocator`, folding its even-split + viable-floor logic onto V4; no second in-memory budget system remains.
- **VMAG-07** — recursive persisted fan-out (depth>1 nested nodes; invariant `sum(children)+reserve ≤ parent` at every level; viable-floor bound, **no depth/max_depth constant**). This is the V4-deferred piece.
- **VMAG-ROOT** — the chat session opens a V4 root node with a default envelope (60k, configurable) + carved reserve.

Pure unify + recursion + persistence. **No new spawn/gather/steer semantics** (V8 verifies, doesn't reinvent). TUI is the V8 surface; ADE child panels → V11.

</domain>

<decisions>
## Implementation Decisions

### Scope: unify M13 onto V4; build the deferred recursion; verify the rest
- Build VMAG-10 (persist), VMAG-UNIFY (single allocator), VMAG-07 (recursion), VMAG-ROOT (chat root); verify MAG-01..09 + back-compat.
- M13 marked absorbed into V8 (bookkeeping); M13 artifacts retained as reference.

### Persist chat children into the V4 session tree (VMAG-10)
- A chat `/agent spawn` creates a **persisted V4 session-tree node** (child of the chat root) via `SessionTreeManager.allocate_child`.
- Child lifecycle (spawn → terminal) is recorded; terminal state finalized on disk via `finalize_node`.
- The tree reconstructs from persisted nodes alone (without the chat transcript).

### Route chat spawns through V4 — one allocator (VMAG-UNIFY)
- Chat spawn allocation goes through the **post-V4 `SessionTreeManager.allocate_child(limit, *, scope=…, role=…)`**.
- **Replace `M13Allocator`** with V4-backed allocation: fold its **even-split-of-reserve** + **viable-floor** behavior onto the V4 manager (preserve the recursion bound + no-oversell `asyncio.Lock`). After V8, **no separate in-memory budget allocator** governs chat spawns.
- M13's spawn/gather/steer **tool surface keeps working** (the public `attach_multiagent_tools` + `ChildHandle`/`ChildRegistry` API stays; only the *allocation backend* swaps to V4). Migrate internals, preserve the surface.

### Recursive persisted fan-out (VMAG-07) — the new substrate work
- A child can allocate **sub-children from its own envelope**, persisted as **nested session-tree nodes** (V4 is depth-1; V8 makes it recursive).
- Budget invariant `sum(children limits) + reserve ≤ parent` holds **at every level**.
- Recursion is bounded **solely by the viable-floor** (an even slice below the floor → denial) — **no depth/max_depth constant** (preserves M13's property, now on the persisted substrate).
- No-oversell under concurrent spawn holds at each level (V4 `asyncio.Lock`).

### Chat root envelope (VMAG-ROOT)
- The chat session opens a **V4 root node** with a default envelope (the existing **60k, configurable**) + a **carved reserve** (M13's even-split reserve, now on V4).
- Spawns draw from the root envelope; an **exhausted envelope denies further spawns** (viable-floor).

### Verify MAG-01..09 + back-compat (verify)
- Regress: non-blocking spawn, immediate handle, status, gather, steer-between-iterations, child budget from parent, quiet-by-default TUI panel + reveal, Ctrl+C still interrupts.
- Back-compat: the spawn/gather/steer tool surface + **`tests/.../test_subagent_recursion.py`** stay green (migrate the recursion test to the V4-backed path as needed).

### Bookkeeping: M13 absorbed
- ROADMAP/STATE mark M13 absorbed into V8; the V8 surface is the TUI (now persisting state).
- **No ADE-side multiagent/child panel built in V8** (→ V11).
- `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope` (SessionTreeNode changes are owned by V4, not V8).

### Claude's Discretion
- Exact mechanism for recursive allocation on `SessionTreeManager` — e.g. a per-node child manager vs. a manager that allocates against an arbitrary parent node id; how nested nodes link (`parent_run_id` chaining).
- Where the even-split/viable-floor logic lives once folded onto V4 (helper on the manager vs. a thin allocation policy wrapper) — must keep `M13Allocator`'s test-visible properties (`VIABLE_FLOOR`, even slice) or migrate those tests.
- How the chat root node is created/torn down across a chat session lifecycle, and how the configurable 60k default is sourced (reuse the `token_budget=60_000` default + `DEFAULT_PARENT_RESERVE` carve).
- Test organization within `tests/harness/` conventions; how `test_subagent_recursion.py` migrates.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### M13 surface (the in-memory system being unified onto V4 — verify + migrate)
- `voss/harness/multiagent.py` — `M13Allocator` (even-split-of-reserve, `VIABLE_FLOOR`, `asyncio.Lock` no-oversell, `release`), `ChildHandle`, `ChildRegistry`, `DEFAULT_PARENT_RESERVE=30_000`, `DEFAULT_VIABLE_FLOOR=2_000`, `attach_multiagent_tools`, `_teardown_orphans`. **Explicitly NO `session_tree` import today — V8 changes that.**
- `voss/harness/widgets/sub_agent_panel.py` — the quiet-by-default TUI panel + reveal (verify, don't rebuild).
- `voss/harness/cli.py` — `attach_multiagent_tools` wiring + `/agent spawn` dispatch.
- `agent.py` (~:419, `token_budget=60_000`; ~:830 steer-drain branch) — chat-turn budget default + steer injection (per M13 SUMMARY notes in STATE).
- `tests/.../test_subagent_recursion.py` — back-compat recursion test (migrate to V4-backed path).
- `.planning/phases/M13-multi-agent-in-chat-caps-01d/` — M13 SPEC/RESEARCH/PATTERNS/plans (reference design).

### Post-V4 session-tree surface V8 BUILDS ON (planned, executing now — read the PLANS for the target API)
- `voss/harness/session_tree.py` — **current = O1** (depth-1 `allocate_child(limit)`, `reserve`, `asyncio.Lock`, `finalize_node`, `mutate_envelope`, `get_node`, per-node JSON `.voss/sessions/<root_id>/<node_id>.json` 0o600).
- `.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-01-PLAN.md` — adds `SessionTreeNode.scope`/`role` (nullable), `allocate_child(limit, *, scope=None, role=None)`, `_hydrate_node` back-compat, `"error"` exit reason.
- `.../V4-02-PLAN.md` — **pre-emptive spend guard** (refuse to begin a call when `spent ≥ limit` → `finalize exit_reason="budget"`) + always-finalize mechanism (error/timeout/budget).
- `.../V4-03-PLAN.md` — consolidated JSON **export** + **`voss session tree`** CLI.
- `.../V4-SPEC.md`, `V4-CONTEXT.md` — V4 locked direction; **V4 is depth-1; recursion is explicitly deferred to V8**.

### Frozen schemas (do NOT modify any field)
- `RunRecord`, `SessionRecord`, `voss_runtime.BudgetScope` — frozen; `git diff` must show zero field changes. `SessionTreeNode` extensions are owned by V4, not V8.

### Spec + PRD
- `.planning/phases/V8-.../V8-SPEC.md` — locked requirements VMAG-10/UNIFY/07/ROOT + verify + bookkeeping; 7 acceptance criteria.
- `docs/ORCHESTRATION_LAYERS.md` — PRD MAG-01..10 + §2.2 fragmentation source.

</canonical_refs>

<specifics>
## Specific Ideas

- `/agent spawn` path post-V8: allocate via `SessionTreeManager.allocate_child(limit, scope=…, role=…)` under the chat root → persisted node file → `ChildHandle` references the node id → on child terminal, `finalize_node`. The tree is reconstructable from `.voss/sessions/<root>/`.
- Recursion: a child node becomes a parent for its own `allocate_child` calls (sub-children persisted as nested nodes); even-split of the child's spendable envelope; deny when the even slice < viable-floor — terminating recursion with no depth constant.
- Unify: keep `ChildRegistry`/`ChildHandle`/the tool surface; swap the allocation backend from `M13Allocator` to V4; migrate `M13Allocator`'s `VIABLE_FLOOR`/even-split tests onto the V4-backed path.
- Chat root: open a V4 root node (envelope limit = configurable 60k default, reserve carved) at chat-session start; spawns draw from it; exhaustion → viable-floor denial.
- Tests: pytest, class-based, `tests/harness/` conventions; preserve M13's no-oversell + correction-vs-control + recursion signal bars; reuse the M13 `scripted_multiagent_provider` fixture. **No new third-party deps.**

</specifics>

<deferred>
## Deferred Ideas

- voss-app ADE multiagent/child panels → **V11** (V8 ships the TUI surface only).
- New spawn/gather/steer semantics — out (V8 verifies the shipped M13 surface).
- Cross-machine / distributed agents — far out of scope.
- Any field change to `RunRecord`/`SessionRecord`/`BudgetScope` — frozen; `SessionTreeNode` changes owned by V4.

</deferred>

---

*Phase: V8-multi-agent-chat-live-steering-absorbs-m13*
*Context synthesized: 2026-06-06 direct from V8-SPEC.md (discuss-phase skipped per locked SPEC interview; planned against post-V4 surface per operator decision — hard-depends V4 + M13)*
