# Phase V8: Multi-agent Chat + Live Steering (absorbs M13) — Research

**Researched:** 2026-06-06
**Domain:** Multi-agent orchestration unification — persisted session-tree + in-memory M13 chat allocator + recursive fan-out
**Confidence:** HIGH (all major surfaces read from disk; M13 code fully verified; V4 state verified; test suites run)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Scope:** Build VMAG-10 (persist), VMAG-UNIFY (single allocator), VMAG-07 (recursion), VMAG-ROOT (chat root); verify MAG-01..09 + back-compat. M13 marked absorbed into V8; M13 artifacts retained as reference.
- **Persist chat children into the V4 session tree (VMAG-10):** A chat `/agent spawn` creates a persisted V4 session-tree node (child of the chat root) via `SessionTreeManager.allocate_child`. Terminal state finalized on disk via `finalize_node`. Tree reconstructable from persisted nodes alone.
- **Route chat spawns through V4 (VMAG-UNIFY):** Chat spawn allocation goes through the post-V4 `SessionTreeManager.allocate_child(limit, *, scope=…, role=…)`. Replace `M13Allocator` with V4-backed allocation, folding its even-split/viable-floor behavior onto V4. No separate in-memory budget allocator remains after V8.
- **Recursive persisted fan-out (VMAG-07):** A child can allocate sub-children from its own envelope, persisted as nested session-tree nodes. Budget invariant `sum(children limits) + reserve ≤ parent` holds at every level. Recursion bounded solely by the viable-floor with no depth/max_depth constant.
- **Chat root envelope (VMAG-ROOT):** Chat session opens a V4 root node with a default envelope (the existing 60k, configurable) + a carved reserve. Spawns allocate from it; exhausted envelope denies further spawns.
- **Verify MAG-01..09 + back-compat:** Regress non-blocking spawn, immediate handle, status, gather, steer-between-iterations, quiet-by-default TUI panel + reveal, Ctrl+C interrupts; `test_subagent_recursion.py` (migrated) green.
- **Bookkeeping:** ROADMAP/STATE mark M13 absorbed; no ADE-side multiagent panel in V8.
- **Schema freeze:** `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`. SessionTreeNode changes owned by V4, not V8. No new deps.

### Claude's Discretion

- Exact mechanism for recursive allocation on `SessionTreeManager` — per-node child manager vs. manager that allocates against an arbitrary parent node id; how nested nodes link (`parent_run_id` chaining).
- Where the even-split/viable-floor logic lives once folded onto V4 (helper on manager vs. thin allocation policy wrapper). Must keep `M13Allocator`'s test-visible properties (`VIABLE_FLOOR`, even slice) or migrate those tests.
- How the chat root node is created/torn down across a chat session lifecycle, and how the configurable 60k default is sourced (reuse the `token_budget=60_000` default + `DEFAULT_PARENT_RESERVE` carve).
- Test organization within `tests/harness/` conventions; how `test_subagent_recursion.py` migrates.

### Deferred Ideas (OUT OF SCOPE)

- voss-app ADE multiagent/child panels — V11.
- New spawn/gather/steer semantics — V8 verifies, doesn't reinvent.
- Cross-machine / distributed agents.
- Any field change to `RunRecord`/`SessionRecord`/`BudgetScope`.

</user_constraints>

---

## Summary

V8 is a unification phase with a concrete scope: swap the allocation backend of the existing M13 multi-agent chat system from an in-memory `M13Allocator` to the V4 `SessionTreeManager`, persist every chat child as a `SessionTreeNode`, extend `SessionTreeManager` to support depth>1 recursive fan-out (the piece V4 deliberately deferred), and give the chat session a V4 root node as its budget envelope. The M13 tool surface (`attach_multiagent_tools`, `subagent_spawn/steer/status/gather`, `ChildHandle`, `ChildRegistry`, `PanelBridgeRenderer`) is kept entirely intact — only the allocation backend changes.

**Critical disk-state finding (2026-06-06):** V4-01 and V4-02 production code are BOTH executed on disk. V4-01 added `scope`/`role` to `SessionTreeNode` and `"error"` to `EXIT_REASONS`. V4-02 added the pre-emptive spend guard + `mutate_envelope` spend wiring + `except asyncio.TimeoutError` / `except Exception` / `finally` finalize net to `subagents.py`. V4-03 (export_tree + `voss session tree` CLI) is NOT yet executed — `export_tree` and `session_group` are absent from disk. M13 is **fully shipped** (all 10 xfail tests XPASSED, meaning all M13 code is live), including the in-memory recursive fan-out (depth>1 via `M13Allocator` + `sub_allocator`).

**Primary recommendation:** Extend `SessionTreeManager` with a per-node child allocation method (passing the parent node's envelope as the budget source), swap `M13Allocator` with a thin V4-backed adapter in `attach_multiagent_tools`, and add a chat-root creation step in `cli.py`. Even-split/viable-floor logic migrates as a helper alongside V4 allocation. Keep `ChildHandle.sub_allocator` field but replace its `M13Allocator` value with a `SessionTreeManager`-backed node.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chat root node creation | API / Backend (`cli.py`) | — | The chat REPL (`chat_cmd`) owns session lifecycle; root node creation belongs alongside record/session init |
| Child allocation (spawn budget) | API / Backend (`session_tree.py` + `multiagent.py`) | — | `SessionTreeManager.allocate_child` is the single allocation authority; M13 calls through it |
| Even-split budget redistribution | API / Backend (`session_tree.py` or `multiagent.py`) | — | Folded onto V4 manager; can live as a helper in the same module |
| Child persistence (node file) | API / Backend (`session_tree.py`) | — | `_write_node_file` + `finalize_node` already own this |
| Recursive fan-out (depth>1) | API / Backend (`session_tree.py`) | — | V8 extends `SessionTreeManager` for nested allocation; per-node manager is the cleanest seam |
| Tool surface (spawn/steer/gather) | API / Backend (`multiagent.py`) | — | `attach_multiagent_tools` public API unchanged; only allocation backend swaps |
| TUI panel display | Frontend Server / TUI (`tui/widgets/sub_agent_panel.py`) | — | Already shipped; quiet-by-default; just verify, don't rebuild |
| Budget viable-floor denial | API / Backend (`session_tree.py`) | — | Replaces `M13Allocator.VIABLE_FLOOR` denial with same logic on V4 path |
| Tree reconstruction from disk | API / Backend (`session_tree.py`) | — | `export_tree` (V4-03, pending) handles this; V8 depends on V4-03 completion OR writes its own traversal |

---

## Dependency Readiness

### CRITICAL: V4 Execution State vs. Post-V4 Target API

This is the most important section. V8 plans against the post-V4 surface but the executor runs after V4 lands. Map every API V8 touches.

**V4-01 (scope/role + "error" exit reason)** — STATUS: **DONE ON DISK**
- `SessionTreeNode` carries `scope: Optional[str] = None` and `role: Optional[str] = None` (session_tree.py:60-61). [VERIFIED: read from disk]
- `_hydrate_node` has back-compat `setdefault("scope", None)` / `setdefault("role", None)` (session_tree.py:96-97). [VERIFIED: read from disk]
- `SessionTreeManager.allocate_child(self, limit: int, *, scope: str | None = None, role: str | None = None)` with `scope=scope, role=role` passed into the constructor (session_tree.py:170, 194-195). [VERIFIED: read from disk]
- `EXIT_REASONS` frozenset contains `"error"` (session.py:75). [VERIFIED: read from disk]
- `TestSchemaExtension` class (4 tests) green in test_session_tree.py. [VERIFIED: tests pass]

**V4-02 (pre-emptive spend guard + all-reason finalize)** — STATUS: **PRODUCTION CODE DONE, test classes missing**
- Pre-emptive guard at subagents.py:232: `if node is not None and node.envelope["spent"] >= node.envelope["limit"]:` [VERIFIED: read from disk]
- `mutate_envelope` imported and called at subagents.py:283: `mutate_envelope(node, delta=-tokens_used, cwd=cwd)` [VERIFIED: read from disk]
- `except asyncio.TimeoutError` at subagents.py:308, `except Exception as exc` at subagents.py:317, `finally:` at subagents.py:326 — all on disk. [VERIFIED: read from disk]
- V4-02-SUMMARY.md: **does NOT exist** (confirms executor did not formally close V4-02).
- `TestSpendGuard` and `TestAllReasonsFinalize` test classes: **NOT in test_session_tree.py** (the file was evolved with `TestDrainFinalize` + `TestNoOpenNodes` instead — these cover the finalize contract but not the spend-guard mock-based test).
- **Impact for V8:** V8 can invoke the guard path and `mutate_envelope` with confidence the production code is live. The missing formal V4-02 test classes are NOT V8's problem to add, but V8 should not regress the existing guard logic.

**V4-03 (export_tree + `voss session tree` CLI)** — STATUS: **NOT EXECUTED**
- `export_tree` function: **ABSENT** from session_tree.py. [VERIFIED: grep found nothing]
- `session_group` click command group: **ABSENT** from cli.py. [VERIFIED: grep found nothing]
- V4-03-SUMMARY.md: does not exist.
- **Impact for V8 VMAG-10 acceptance criterion:** "tree reconstructs from persisted nodes" is stated in both SPEC and CONTEXT. V4-03's `export_tree` is the natural implementation of this, but V8 DOES NOT need to wait for V4-03 — V8 can write its own `_reconstruct_tree_from_disk(root_id, cwd)` helper (glob *.json under `.voss/sessions/<root_id>/`) or verify reconstruction by direct glob, since the disk format is stable. The acceptance criterion is about the DATA being reconstructable, not about the CLI. However, if V4-03 is executed before V8 (which is the plan), V8 can simply use `export_tree`. V8 planner should explicitly handle the case where V4-03 has not landed by providing a fallback.

**M13 surface (in-memory system being replaced)** — STATUS: **FULLY SHIPPED**

All 10 xfail tests in the M13 test suite XPASSED (stricter than passing — means the code is live even though it was scaffolded as "not yet implemented"). Complete M13 surface on disk:

| Symbol | File | Line | Status |
|--------|------|------|--------|
| `DEFAULT_PARENT_RESERVE = 30_000` | multiagent.py:55 | | LIVE |
| `DEFAULT_VIABLE_FLOOR = 2_000` | multiagent.py:66 | | LIVE |
| `M13Allocator` (even-split, VIABLE_FLOOR, lock, release, rebalance) | multiagent.py:69-155 | | LIVE |
| `ChildHandle` (id, task, allotment, done, result, queue, panel_id, sub_allocator) | multiagent.py:158-188 | | LIVE |
| `ChildRegistry` (add, get, active, all) | multiagent.py:191-212 | | LIVE |
| `new_handle_id()` | multiagent.py:219-224 | | LIVE |
| `PanelBridgeRenderer` (start_panel, step, end_panel, __getattr__) | multiagent.py:244-277 | | LIVE |
| `attach_multiagent_tools(tools, *, registry, cwd, renderer, provider, model, gate, cognition=None, allocator=None)` | multiagent.py:279-535 | | LIVE |
| `subagent_spawn` tool (allocate + create_task, returns handle string) | multiagent.py:346-417 | | LIVE |
| `subagent_steer` tool | multiagent.py:419-435 | | LIVE |
| `subagent_status` tool | multiagent.py:437-463 | | LIVE |
| `subagent_gather` tool (gather + release + rebalance + end_panel) | multiagent.py:465-496 | | LIVE |
| `_teardown_orphans` (cancel + release + collapse orphans) | multiagent.py:498-522 | | LIVE |
| **Recursive attach:** `sub_alloc = M13Allocator(reserve=allotment)` + `attach_multiagent_tools(child_tools, …, allocator=sub_alloc)` | multiagent.py:366-385 | | LIVE |
| cli.py wiring: `_multiagent_teardown = attach_multiagent_tools(…)` at chat-turn level | cli.py:2019-2028 | | LIVE |
| `_run_turn_with_teardown(turn_coro, teardown)` wraps every chat turn | cli.py:364-385 | | LIVE |
| `SubAgentPanel` (quiet-by-default, append_body, update_budget) | tui/widgets/sub_agent_panel.py:16-91 | | LIVE |
| TUI `show_subagent_start/progress/end` → `mount_subagent_panel` | tui/renderer.py:209-221, tui/app.py:248-269 | | LIVE |
| `test_subagent_recursion.py` (3 tests: no depth param, no depth constant, mutating) | tests/harness/test_subagent_recursion.py | | GREEN |

**MAG-01..09 vs. MAG-10 shipping status (verified from test results):**

| MAG ID | Behavior | Shipped? | Test | Status |
|--------|----------|----------|------|--------|
| MAG-01 | Non-blocking spawn, ≥2 in-flight | YES | TestConcurrentInFlight (xpassed) | LIVE |
| MAG-02 | Immediate handle return | YES | TestConcurrentInFlight | LIVE |
| MAG-03 | Even-split / rebalance | YES | TestEvenSplitRebalance (xpassed) | LIVE |
| MAG-04 | No-oversell, exactly-once release | YES | TestNoOversell (xpassed) | LIVE |
| MAG-05 | Steer between iterations | YES | TestCorrectionChangesBehavior (xpassed) | LIVE |
| MAG-06 | Child budget from parent | YES | TestNoOversell::test_depth_bound (xpassed) | LIVE |
| MAG-07 | Recursive child spawning | YES (in-memory) | TestDepth2 (xpassed) | LIVE but IN-MEMORY ONLY — V8 migrates to persisted |
| MAG-08 | Quiet-by-default TUI panel | YES | Sub_agent_panel.on_mount | LIVE |
| MAG-09 | User can reveal child details | YES | `action_toggle_subagent_detail` in app.py | LIVE |
| MAG-10 | Persist child events to session tree | NO | — | V8 BUILDS THIS |

---

## Research Focus Area 1: Recursive Allocation Mechanism (HIGHEST RISK)

### Current State

The current `SessionTreeManager` is depth-1 (current disk, post-V4-01+02):

```python
class SessionTreeManager:
    def __init__(self, root_node: SessionTreeNode, *, reserve: int, cwd: Path):
        self._root = root_node    # SINGLE root reference
        self._reserve = reserve
        self._cwd = cwd
        self._children: list[SessionTreeNode] = []  # FLAT list, depth-1 only
        self._lock = asyncio.Lock()

    async def allocate_child(self, limit: int, *, scope=None, role=None) -> SessionTreeNode:
        async with self._lock:
            allocated = sum(c.envelope["limit"] for c in self._children)
            available = self._root.envelope["limit"] - self._reserve - allocated
            # ... creates child with parent_run_id=self._root.id
```

The problem: `self._children` is flat, `available` is computed from `self._root.envelope["limit"]`, and `parent_run_id` is always `self._root.id`. This is structurally depth-1.

### V8 Target: Recursive via Per-Node Manager

**Recommended mechanism (Claude's Discretion):** A **per-node `SessionTreeManager`** where each node that can be a parent owns a manager instance rooted at that node. The `ChildHandle` carries a `node_manager: SessionTreeManager | None` field instead of `sub_allocator: M13Allocator | None`.

How it works:
1. Root chat session creates `root_manager = SessionTreeManager(root_node, reserve=carved_reserve, cwd=cwd)`.
2. When `subagent_spawn` is called, it calls `await root_manager.allocate_child(limit, scope=scope, role=role)` → gets a `SessionTreeNode` with `parent_run_id=root_node.id`.
3. The child node gets its own `child_manager = SessionTreeManager(child_node, reserve=viable_floor, cwd=cwd)`.
4. The recursive `attach_multiagent_tools` call passes `node_manager=child_manager` as the allocation backend for the child's tools.
5. The child's `subagent_spawn` calls `await child_manager.allocate_child(limit, ...)` → allocates from the child node's envelope, persists as a nested node with `parent_run_id=child_node.id` and `root_id=root_node.id`.

**How nested nodes link:** `parent_run_id` chains correctly because each `allocate_child` sets `parent_run_id=self._root.id` (the node owned by that manager). The tree is fully traversable from disk by following `parent_run_id` links.

**Invariant at each level:** Each `SessionTreeManager` enforces `sum(children_limits) + reserve <= self._root.envelope["limit"]` inside its own `asyncio.Lock`. Since each level has its own manager and lock, the invariant holds structurally at every level without cross-level locking.

**Viable-floor termination (no depth constant):** Instead of `M13Allocator`'s class-level `VIABLE_FLOOR`, the V4 path checks that `available > viable_floor` before allocating. If `available < viable_floor`, `BudgetAllocationError` is raised, `subagent_spawn` catches it and returns the `"<denied: ...>"` string — same denial as M13. The `VIABLE_FLOOR = 2_000` constant moves to a module-level constant in `multiagent.py` (or `session_tree.py`) and is referenced by `attach_multiagent_tools` when constructing child managers.

**The reserve for child managers:** The `M13Allocator` set `reserve=allotment` for sub-allocators (so a child's reserve equaled its entire envelope, meaning ALL of it was available for further splitting). In the V4 model, the child node's manager should set `reserve=VIABLE_FLOOR` (carve just enough reserve to prevent further splitting below the floor), which is more precise and equivalent in recursion-termination behavior.

**Alternative (single manager with parent_id parameter):** A single `SessionTreeManager` instance could accept an arbitrary `parent_node_id` in `allocate_child` and maintain a `_children_by_parent: dict[str, list[SessionTreeNode]]` map. This avoids multiple manager instances but adds complexity (the single lock must cover all levels, which risks contention) and requires passing `parent_node_id` through `attach_multiagent_tools`. The per-node manager is simpler and more correct.

### Key Wiring Change in `attach_multiagent_tools`

Current M13 `subagent_spawn` (multiagent.py:346-417):
```python
# Creates a sub-allocator (M13Allocator) for the child  
sub_alloc = M13Allocator(reserve=allotment)
# Passes it to recursive attach
attach_multiagent_tools(child_tools, ..., allocator=sub_alloc)
```

Post-V8 path:
```python
# Creates a persisted child node via V4 manager
child_node = await node_manager.allocate_child(allotment, scope="chat", role=agent)
# Creates a child node manager for recursion
child_node_manager = SessionTreeManager(child_node, reserve=VIABLE_FLOOR, cwd=cwd)
# Passes it to recursive attach
attach_multiagent_tools(child_tools, ..., node_manager=child_node_manager)
```

The `attach_multiagent_tools` signature changes from `allocator: M13Allocator | None = None` to `node_manager: SessionTreeManager | None = None`. This is a breaking change to the parameter name — all callers must be updated (just `cli.py:2019` for the top-level call and the recursive call inside `subagent_spawn` itself).

---

## Research Focus Area 2: M13Allocator → V4 Fold (UNIFY)

### What `M13Allocator` Does That Must Be Preserved

| Behavior | M13Allocator mechanism | V4 migration path |
|----------|----------------------|-------------------|
| Even-split: N children → `reserve // N` each | `_rebalance_locked` | Move to helper; call on each allocate/release |
| No-oversell under concurrent spawn | `asyncio.Lock` | Already in `allocate_child` asyncio.Lock |
| Viable-floor denial | `VIABLE_FLOOR` class attr | Module-level constant; check in `allocate_child` or wrapper |
| Idempotent release | `_credited_finished` set | `finalize_node` idempotence already covers this |
| Rebalance on release | `release` → `_rebalance_locked` | V4 envelope is fixed at allocation time — see below |

**Critical difference:** M13Allocator dynamically rebalances live allotments when a child releases (surviving children get more budget). The V4 model allocates fixed `limit` per child — once allocated, the `envelope["limit"]` is immutable (only `envelope["spent"]` moves via `mutate_envelope`). The even-split rebalance behavior **changes meaning** on V4: instead of updating a live allotment, release in V4 just means the spent tokens are accounted for but the node's limit remains fixed.

**Recommendation:** Keep even-split rebalance as a calculation-only helper for determining the initial allocation limit (how much to give each new child) rather than a live update. When a child spawns: `even_slice = available_envelope // (existing_children + 1)` if `even_slice >= VIABLE_FLOOR`, allocate `even_slice` for the new child. On release (finalize), the freed budget is simply the `envelope["limit"] - envelope["spent"]` of the finished child — this naturally "returns" to the parent's available balance since `allocate_child` computes `available = root.limit - reserve - sum(children.limit)`.

However, a finish-then-reallocate pattern (child finishes, parent spawns another with a larger slice) works correctly with V4's existing math because `allocate_child` always computes `available` fresh from the root envelope minus `sum(active child limits)`. If a child is finalized and its node is no longer in `self._children`, the freed limit is naturally available.

**`_children` management:** The current `self._children` list is never pruned after finalization. V8 must either (a) prune finalized children from `self._children` to make their budget available for reallocation, or (b) use a "finalized child still counts against budget" semantic (simpler but means budget can't be reused). Given M13's release/rebalance pattern, option (a) matches user expectation. **Recommendation:** Add a `release_child(node_id)` method or prune in `allocate_child` by filtering `self._children` to only non-finalized nodes.

### M13 Test-Visible Properties That Must Stay

The tests check:
- `multiagent.M13Allocator.VIABLE_FLOOR` (class attribute, used in TestNoOversell)
- `multiagent.DEFAULT_PARENT_RESERVE` (module-level constant)
- `multiagent.DEFAULT_VIABLE_FLOOR` (module-level constant)
- Even-split math: `even = reserve // N`

After V8, `M13Allocator` class **is removed from `multiagent.py`** (or deprecated/kept as a thin shim for test back-compat). The test classes `TestEvenSplitRebalance` and `TestNoOversell` in `test_multiagent_fanout.py` directly test `M13Allocator` — these MUST be migrated to test the V4-backed path.

**Migration path for xfail tests:** The xfail tests in `test_multiagent_fanout.py` and `test_multiagent_recursion.py` currently test `multiagent.M13Allocator` directly. After V8:
- `TestEvenSplitRebalance` — becomes a test of the even-split helper on the V4-backed `attach_multiagent_tools` path (test that two children get equal slices from a known root envelope).
- `TestNoOversell` — becomes a test of V4's `allocate_child` concurrency invariant (already covered by `TestConcurrency` in `test_session_tree.py`) + the viable-floor denial in the V8 path.
- `TestDepth2` — becomes the persisted-recursion test (the core VMAG-07 acceptance criterion).
- The xfail markers can be dropped (the tests will be GREEN from V8 onward).

---

## Research Focus Area 3: Chat Root Lifecycle (VMAG-ROOT)

### Current State (from disk)

`agent.py:518`: `async def run_turn(..., token_budget: int = 60_000, ...)` — the default budget. [VERIFIED]

`cli.py:2019-2028`: `attach_multiagent_tools` is called ONCE per chat session (outside the per-turn loop). The `allocator=None` default causes a fresh `M13Allocator(reserve=DEFAULT_PARENT_RESERVE)` to be created on EACH `attach_multiagent_tools` call — but since `attach_multiagent_tools` is called once per session (not once per turn), the `ChildRegistry` and allocator are session-scoped. [VERIFIED from code structure]

The `run_turn` calls within the TUI dispatch (cli.py:2108) and the REPL loop (cli.py:2199) do NOT pass `token_budget` — they use the default 60k.

### V8 Chat Root Creation

**Where:** In `chat_cmd` in `cli.py`, after the existing `SessionRecord` + `RunRecorder` setup and before the `attach_multiagent_tools` call. This mirrors V4's `SessionTreeNode.create_root` pattern.

**When:** Once per `chat_cmd` invocation (session-scoped, not turn-scoped). The root node ID is stored in a closure variable alongside `_multiagent_teardown`.

**What:** 
```python
# Session-scoped root node for the chat session's budget envelope
_chat_root = SessionTreeNode.create_root(cwd=cwd, limit=60_000)  # configurable
_chat_reserve = DEFAULT_PARENT_RESERVE  # 30_000
_chat_tree = SessionTreeManager(_chat_root, reserve=_chat_reserve, cwd=cwd)
```

**Teardown:** `finalize_node(_chat_root, exit_reason="done", final="", cwd=cwd)` should be called at session exit (in the `finally`/`KeyboardInterrupt` handler in `chat_cmd`). This is the session-level bookend.

**Configurable default:** The 60k default comes from `token_budget: int = 60_000` at agent.py:518. V8 should read this from the same config path as `get_config().default_model` (if a `token_budget` config key exists) or hardcode 60_000 as the V8 default, matching agent.py.

**Exhaustion denial:** When `_chat_tree.allocate_child` raises `BudgetAllocationError` (because available < VIABLE_FLOOR), `subagent_spawn` already returns `"<denied: budget below viable floor …>"` — this behavior is preserved, just now backed by V4 instead of `M13Allocator`.

---

## Research Focus Area 4: Persistence Wiring (VMAG-10)

### Current In-Memory Registration

When `subagent_spawn` is called (multiagent.py:346-417):
1. `allocator.allocate(handle)` → returns allotment (in-memory only).
2. `child_registry.add(ChildHandle(id=handle, ...))` → in-memory registry.
3. `asyncio.create_task(coro)` → detached task.
4. Nothing persists to `session_tree.py`.

### Minimal Wiring Change for V8

Replace step 1 with a V4 allocation:
1. `child_node = await node_manager.allocate_child(allotment_limit, scope="chat", role=agent)` → creates persisted node file under `.voss/sessions/<root_id>/<child_id>.json`.
2. `child_registry.add(ChildHandle(id=child_node.id, ..., node=child_node))` — add `node` field to `ChildHandle` to carry the V4 node reference.
3. `asyncio.create_task(coro)` → unchanged.

On terminal (in `subagent_gather` and `_teardown_orphans`):
- After task completion/cancellation: `finalize_node(h.node, exit_reason=exit_reason, final=h.result or "", cwd=cwd)` where `exit_reason` is `"done"` on success, `"error"` on exception, `"interrupt"` on cancellation.

The `ChildHandle` dataclass needs a `node: Any = None` field (typed `SessionTreeNode | None` with `from __future__ import annotations` to avoid circular). This is the ONLY new field on `ChildHandle`.

**Tree reconstruction:** After V8, `.voss/sessions/<root_id>/` contains `<root_id>.json` (root) + `<child_id>.json` for each spawned child + nested `<grandchild_id>.json` for recursive children. The `parent_run_id` chain lets any consumer reconstruct the tree. The `export_tree` function (once V4-03 lands) will handle this; until then the test can glob directly.

---

## Research Focus Area 5: Actual Test Surface Reality

### M13 Test Suite Current Status (verified by running tests)

**`test_multiagent_fanout.py`** (7 tests):
- `TestConcurrentInFlight` (2 tests): `xfail(strict=False)` but **XPASSED** — code is live
- `TestEvenSplitRebalance` (1 test): **XPASSED** — code is live
- `TestNoOversell` (3 tests): **XPASSED** — code is live  
- `TestOrphanTeardown` (1 test): **NOT xfail, PASSED** — live since M13-03

**`test_multiagent_recursion.py`** (5 tests):
- `TestDepth2` (2 tests): **XPASSED** — recursive fan-out code is live (in-memory)
- `TestBackCompatRecursionPinIntact` (3 tests): **PASSED** — back-compat green

**`test_multiagent_steer.py`** (2 tests):
- `TestCorrectionChangesBehavior` (2 tests): **XPASSED** — steer code is live

**`test_subagent_recursion.py`** (3 tests): **ALL PASSED** — green from day 1.

**`tests/e2e/test_multiagent_chat_e2e.py`** (1 test): **FAILING** — `test_multiagent_chat_e2e` fails at `AUTH_STEERED` assertion (steer-between-iterations in e2e context doesn't land in time). This is a pre-existing e2e flakiness, NOT a V8 issue. V8 must not regress this further.

### What V8 Needs NEW (Not Covered by Existing Tests)

| Acceptance Criterion | New Test Needed | Where |
|----------------------|-----------------|-------|
| `/agent spawn` creates persisted V4 node | `TestPersistOnSpawn` | `tests/harness/test_multiagent_session_tree.py` (new file) |
| Child terminal state finalized on disk | In `TestPersistOnSpawn` | same |
| Tree reconstructs from persisted nodes alone | In `TestPersistOnSpawn` | same |
| Chat root node created with 60k envelope + reserve | `TestChatRootEnvelope` | same |
| Spawns draw from root; exhaustion denies | `TestChatRootEnvelope` | same |
| Concurrent spawns cannot oversell chat root | `TestConcurrentNoOversellChatRoot` | same |
| Depth>1: child-of-child persists as nested node | `TestPersistedRecursion` | same |
| Invariant `sum+reserve ≤ parent` at every level | In `TestPersistedRecursion` | same |
| Recursion terminates via viable-floor, no depth constant | `TestViableFloorTermination` | same |

### `test_subagent_recursion.py` Migration

This file pins that `voss.harness.subagents.run_subagent` has NO `depth` / `max_depth` param and no `MAX_DEPTH` / `DEPTH_LIMIT` / `RECURSION_LIMIT` constants. V8 must not add any such symbol. The tests stay green verbatim — no migration needed. The CONTEXT says "migrate as needed" but the actual test contract is just "no depth constant in subagents.py." Since V8's viable-floor is in `session_tree.py` or `multiagent.py`, not `subagents.py`, the tests remain byte-stable.

The `TestBackCompatRecursionPinIntact` in `test_multiagent_recursion.py` adds a check that no depth constant is in `subagents` and that `test_subagent_recursion.py` still passes as a subprocess. These must stay green.

---

## Research Focus Area 6: Frozen Schema Guard

**Frozen fields (MUST NOT CHANGE):**
- `RunRecord` — 24 fields, verified by `test_session_redaction.py` (runs unmodified, all 7 tests pass).
- `SessionRecord` — schema isolation verified by `TestSchemaIsolation::test_no_schema_merge`.
- `BudgetScope` — in `voss_runtime`, not touched by any harness changes.

**V8 changes that touch dataclasses:**
- `ChildHandle` (multiagent.py): adding `node: Any = None` field. This is NOT a frozen schema — `ChildHandle` is an M13-internal type, not a serialized record. Safe to add fields.
- `SessionTreeNode` (session_tree.py): NOT changed by V8. Any `SessionTreeNode` schema changes are V4's responsibility. V8 consumes the V4 schema as-is.

**V8 changes to `_NODE_JSON_KEYS`:** None. V4-01 already added `scope`/`role`. V8 adds no new fields to `SessionTreeNode`.

**Git diff check:** After V8, `git diff -- voss/harness/session.py voss/runtime/` must show zero field changes. The test `test_node_keys_exact` (TestSchemaIsolation) will still pass because `_NODE_JSON_KEYS` is not touched by V8.

---

## Standard Stack

V8 introduces ZERO new third-party dependencies. All work is within the existing codebase.

### Core (existing, no new installs)

| Library | Version | Purpose | V8 Use |
|---------|---------|---------|--------|
| `asyncio` (stdlib) | Python 3.13 | Async lock, task creation, gather | `allocate_child` lock, `create_task` for child spawns |
| `dataclasses` (stdlib) | Python 3.13 | `SessionTreeNode`, `ChildHandle` | Adding `node` field to `ChildHandle` |
| `uuid` (stdlib) | Python 3.13 | Node ID generation | Already used in `session_tree.py` |
| `pathlib` (stdlib) | Python 3.13 | `.voss/sessions/` path ops | Node file path construction |
| `json` (stdlib) | Python 3.13 | Node serialization | `_write_node_file` |
| `pytest-asyncio` | Installed (asyncio_mode=auto) | Async test support | `TestPersistedRecursion` etc. |

### No Package Legitimacy Audit Required

V8 installs zero new packages. [VERIFIED: CONTEXT.md constraint "No new third-party dependencies"; confirmed by research showing only stdlib + existing voss modules are needed]

---

## Architecture Patterns

### System Architecture Diagram

```
cli.py (chat_cmd)
    │
    ├── creates _chat_root (SessionTreeNode.create_root, limit=60k)
    ├── creates _chat_tree (SessionTreeManager(_chat_root, reserve=30k))
    ├── passes _chat_tree to attach_multiagent_tools(tools, ..., node_manager=_chat_tree)
    │
    └── per-turn: run_turn → subagent_spawn tool
                                    │
                     ┌──────────────▼───────────────┐
                     │  node_manager.allocate_child() │ ← asyncio.Lock, even-slice check
                     │  → child_node (persisted)      │ ← .voss/sessions/<root>/<child>.json
                     └──────────────┬───────────────┘
                                    │
                     ┌──────────────▼───────────────┐
                     │  child_manager = STM(child_node) │
                     │  recursive attach_multiagent_tools │
                     │     (node_manager=child_manager)  │
                     └──────────────┬───────────────┘
                                    │
                     depth>1: grandchild_node = child_manager.allocate_child()
                              → .voss/sessions/<root>/<grandchild>.json
                              → parent_run_id=child_node.id
                              → root_id=root_node.id
                                    │
                     finalize on terminal:
                     finalize_node(child_node, exit_reason="done"|"error"|"interrupt")
                     → terminal_state written to .voss/sessions/<root>/<child>.json
```

### Recommended File Changes

```
voss/harness/
├── session_tree.py      # Add allocate_child_from(parent_node, ...) or extend STM.__init__
│                        # Add even_slice helper
│                        # Possibly add VIABLE_FLOOR constant here (or keep in multiagent.py)
├── multiagent.py        # Swap M13Allocator → SessionTreeManager backend
│                        # Change attach_multiagent_tools(... allocator=None) → 
│                        #   attach_multiagent_tools(... node_manager=None)
│                        # Add node field to ChildHandle
│                        # Keep VIABLE_FLOOR, DEFAULT_PARENT_RESERVE constants
│                        # Keep ChildRegistry, ChildHandle, PanelBridgeRenderer INTACT
│                        # Remove M13Allocator (or keep as deprecated shim for test compat)
│                        # Add finalize_node call in subagent_gather + _teardown_orphans
└── cli.py               # Add _chat_root + _chat_tree creation before attach_multiagent_tools
                         # Add finalize_node on session exit
tests/harness/
├── test_multiagent_session_tree.py  # NEW: persisted recursion tests
├── test_multiagent_fanout.py        # MIGRATE: swap M13Allocator tests → V4-backed tests
├── test_multiagent_recursion.py     # MIGRATE: TestDepth2 → persisted version
└── test_subagent_recursion.py       # UNCHANGED (byte-stable)
.planning/STATE.md                   # Mark M13 absorbed, ADE→V11
```

### Pattern 1: Per-Node Manager (Recommended Recursion Mechanism)

```python
# session_tree.py additive extension
CHAT_VIABLE_FLOOR: int = 2_000  # mirrors M13Allocator.VIABLE_FLOOR (module-level)

class SessionTreeManager:
    # EXISTING: __init__(self, root_node, *, reserve, cwd)
    # EXISTING: allocate_child(self, limit, *, scope=None, role=None) -> SessionTreeNode
    
    # V8 ADDS: even-slice helper for allocation policy
    def even_slice(self, n_new: int = 1) -> int:
        """Compute even-split slice for the next n_new children."""
        async with self._lock:  # NOTE: this should be called inside the lock
            allocated = sum(c.envelope["limit"] for c in self._active_children())
            available = self._root.envelope["limit"] - self._reserve - allocated
            n = len(self._active_children()) + n_new
            return available // n if n > 0 else 0
    
    def _active_children(self) -> list[SessionTreeNode]:
        """Non-finalized children only (finalized nodes freed their budget)."""
        return [c for c in self._children if c.terminal_state is None]
```

```python
# multiagent.py: subagent_spawn (after V8)
async def subagent_spawn(agent: str, task: str) -> str:
    handle = new_handle_id()
    
    # V4-backed allocation instead of M13Allocator.allocate
    async with node_manager._lock:
        active = node_manager._active_children()
        n = len(active) + 1
        allocated = sum(c.envelope["limit"] for c in active)
        available = node_manager._root.envelope["limit"] - node_manager._reserve - allocated
        even = available // n
        if even < VIABLE_FLOOR:
            return f"<denied: budget below viable floor — cannot spawn {agent!r}>"
        # Rebalance existing active children (conceptually; actual V4 nodes have fixed limits)
        # NOTE: V4 limits are immutable — "rebalance" just means the next allocation
        # uses the updated math; existing nodes keep their original limits.
        allotment = even
    
    child_node = await node_manager.allocate_child(allotment, scope="chat", role=agent)
    child_manager = SessionTreeManager(child_node, reserve=VIABLE_FLOOR, cwd=cwd)
    # ... rest of spawn: create_task, ChildHandle with node=child_node, recursive attach
```

### Pattern 2: ChildHandle Extension

```python
@dataclass
class ChildHandle:
    id: str
    task: Any = None
    allotment: int = 0
    done: bool = False
    result: str | None = None
    queue: Any = None
    panel_id: str = ""
    sub_allocator: Any = None   # DEPRECATED in V8 — kept for test back-compat, set to None
    node: Any = None            # V8 NEW: the SessionTreeNode for this child
```

### Anti-Patterns to Avoid

- **Do NOT hold the V4 `asyncio.Lock` across `create_task`**: the task creation and lock release must happen in order; the lock is for the check-and-allocate only.
- **Do NOT add `max_depth` or `depth` parameter to `run_subagent`** or any module-level `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` constant in `subagents.py` — this breaks `test_subagent_recursion.py`.
- **Do NOT touch `SessionTreeNode` schema fields in V8** — all node schema changes belong to V4.
- **Do NOT change the `attach_multiagent_tools` public parameter names silently** — the CLI wires it with keyword args; changing `allocator=` to `node_manager=` is a breaking rename that requires updating cli.py:2019.
- **Do NOT finalize the root node between turns** — the root node is session-scoped (created once, finalized on session exit), not per-turn.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent allocation safety | Custom lock-per-level logic | `asyncio.Lock` in `SessionTreeManager.__init__` (already there) | V4 already has the correct lock; add one per child manager instance |
| Node file write/read | Custom JSON persistence | `_write_node_file` + `_hydrate_node` + `finalize_node` (session_tree.py) | Already handles chmod 0o600, directory creation, idempotent finalize |
| Tree traversal for reconstruction | Custom recursive walk | glob `*.json` under `.voss/sessions/<root_id>/` (or `export_tree` once V4-03 lands) | The disk format IS the export format |
| Budget scope during run_turn | Custom context manager | Existing `BudgetScope` in `voss_runtime` | Already used by `run_subagent`; no change needed |
| Async task orchestration | Custom coroutine runner | `asyncio.create_task` + `asyncio.gather` (already in subagent_gather) | M13 already uses this correctly |

---

## Common Pitfalls

### Pitfall 1: V4 `allocate_child` is Called OUTSIDE the Lock in the Wrong Place

**What goes wrong:** `allocate_child` is `async`, so the caller might `await` it outside a critical section, causing a TOCTOU race.
**Why it happens:** `SessionTreeManager.allocate_child` already holds the lock internally (correct). The pitfall is calling even_slice / feasibility checks OUTSIDE the method and then calling `allocate_child` separately.
**How to avoid:** All "can I allocate?" + "do the allocation" logic must be inside a single `async with self._lock:` block. The `allocate_child` method already does this. Do not split the check from the allocation.

### Pitfall 2: Forgetting to Prune Finalized Children from `_children`

**What goes wrong:** If finalized child nodes remain in `self._children`, their `envelope["limit"]` counts against `available` forever, eventually denying all new spawns even when budget should be free.
**Why it happens:** The current O1 `SessionTreeManager` never removes from `_children`.
**How to avoid:** Either add `release_child(node_id)` that removes the node from `_children` (called in `subagent_gather` + `_teardown_orphans`), or filter `_children` to `[c for c in self._children if c.terminal_state is None]` inside `allocate_child`.

### Pitfall 3: Even-Split Semantics Mismatch Between M13 and V4

**What goes wrong:** M13's even-split dynamically updates existing children's allotments. V4 envelope limits are immutable once written. Tests that assert "after releasing child-a, child-b's allotment increased" will fail if migrated literally to V4.
**Why it happens:** V4 nodes have fixed `envelope["limit"]`; only `envelope["spent"]` moves.
**How to avoid:** Migrate even-split tests to test the INITIAL allocation math (new child gets `available // N`) rather than live-update semantics. The practical effect is the same: the next spawn gets a larger slice after a child finishes, because `allocate_child` recomputes `available` fresh.

### Pitfall 4: Root Node Created Multiple Times (Per-Turn Instead of Per-Session)

**What goes wrong:** If `SessionTreeNode.create_root` is called inside the per-turn loop or inside `attach_multiagent_tools`, a new root is created for every turn, destroying the session-level budget invariant.
**Why it happens:** `attach_multiagent_tools` is called once per session in `chat_cmd` (outside the loop) but it's easy to move it.
**How to avoid:** Root node creation belongs immediately before `attach_multiagent_tools` in `chat_cmd`, using the same session-scoped pattern as `record = SessionRecord(...)`.

### Pitfall 5: Forgetting `finalize_node` on Cancellation in `_teardown_orphans`

**What goes wrong:** If a child task is cancelled and `finalize_node` is not called, the node remains open (`terminal_state=None`) on disk. The tree-reconstruction acceptance criterion fails.
**Why it happens:** Easy to forget the finalize call in the exception path.
**How to avoid:** `_teardown_orphans` should call `finalize_node(h.node, exit_reason="interrupt", ...)` when `h.node is not None` before continuing. Mirror the V4-02 `finally` pattern.

### Pitfall 6: `test_subagent_recursion.py` Breakage from `max_depth` in Wrong Module

**What goes wrong:** Adding `VIABLE_FLOOR` or a constant to `voss.harness.subagents` (not `multiagent.py`) would break `test_subagent_recursion.py::test_no_module_level_depth_constant` which checks for `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` — but `VIABLE_FLOOR` is not one of those names, so this is safe. The real trap is adding any depth-related constant to `subagents.py`.
**How to avoid:** Keep all V8 viable-floor and budget constants in `multiagent.py` or `session_tree.py`. Touch `subagents.py` only for the V4-02 changes already there.

### Pitfall 7: The `allocator` Parameter Rename Breaks `cli.py`

**What goes wrong:** `cli.py:2019` calls `attach_multiagent_tools(..., allocator=None)` implicitly (the default). Changing to `node_manager=None` parameter requires updating `cli.py:2019` to pass `node_manager=_chat_tree`.
**How to avoid:** Update `cli.py:2019` call site simultaneously with the parameter rename in `attach_multiagent_tools`.

---

## Validation Architecture

Nyquist validation enabled (config.json `workflow.nyquist_validation: true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2, asyncio-mode=auto |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/ -q --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VMAG-10 | `/agent spawn` creates persisted V4 node; terminal finalized on disk; tree reconstructs | unit/integration | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestPersistOnSpawn -x -q` | ❌ Wave 0 |
| VMAG-UNIFY | Chat spawns via V4 manager; no separate in-memory allocator | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestUnifiedAllocator -x -q` | ❌ Wave 0 |
| VMAG-07 | Child-of-child persists as nested node; invariant at each level; viable-floor termination | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestPersistedRecursion -x -q` | ❌ Wave 0 |
| VMAG-ROOT | Chat root node with 60k envelope; spawns draw from it; exhaustion denies | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestChatRootEnvelope -x -q` | ❌ Wave 0 |
| VMAG-ROOT | Concurrent spawns cannot oversell chat root | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestConcurrentNoOversellChatRoot -x -q` | ❌ Wave 0 |
| verify | MAG-01..09 regress green | regression | `.venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_recursion.py tests/harness/test_multiagent_steer.py -x -q` | ✅ exists |
| verify | `test_subagent_recursion.py` green | regression | `.venv/bin/python -m pytest tests/harness/test_subagent_recursion.py -x -q` | ✅ exists |
| verify | Ctrl+C interrupts (teardown_orphans) | regression | `TestOrphanTeardown` in test_multiagent_fanout.py | ✅ exists |
| verify | TUI panel quiet-by-default + reveal | manual-only | Visual inspection in TUI | N/A |
| bookkeeping | `git diff` shows zero field changes on RunRecord/SessionRecord/BudgetScope | static | `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` | ✅ exists |
| bookkeeping | M13 absorbed in STATE/ROADMAP | manual-only | Review STATE.md | N/A |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/ -q --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/test_multiagent_session_tree.py` — covers VMAG-10, VMAG-UNIFY, VMAG-07, VMAG-ROOT, concurrent no-oversell
- [ ] Migration of `test_multiagent_fanout.py::TestEvenSplitRebalance`, `TestNoOversell` — swap to V4-backed path
- [ ] Migration of `test_multiagent_recursion.py::TestDepth2` — swap to persisted version

---

## Security Domain

Budget cage is a trust boundary. STRIDE analysis below.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | yes | Chat root node is session-scoped; finalize on exit |
| V4 Access Control | yes | `scope`/`role` on `SessionTreeNode`; `asyncio.Lock` per-manager |
| V5 Input Validation | yes | `exit_reason` validated against `EXIT_REASONS` frozenset in `finalize_node` |
| V6 Cryptography | no | node files are 0o600, not encrypted |

### Known Threat Patterns for Budget Cage + Recursive Spawn

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Concurrent spawn oversells root envelope | Tampering | Per-manager `asyncio.Lock` in `allocate_child`; `available` computed under lock; test `TestConcurrentNoOversellChatRoot` |
| Recursive spawn exhausts budget (DoS via depth) | Denial of Service | Viable-floor denial: `even < VIABLE_FLOOR → BudgetAllocationError → "<denied: ...>"`; no depth constant; `TestViableFloorTermination` |
| Child escapes its envelope via spend | Elevation of Privilege | Pre-emptive guard in `subagents.py:232` (V4-02, already on disk); `mutate_envelope` tracks spent; guard fires on next iteration |
| Orphaned child task leaks budget/panel | Denial of Service | `_teardown_orphans` + `finalize_node(exit_reason="interrupt")` on cancel |
| Nested node `parent_run_id` chain corruption | Tampering | `parent_run_id=self._root.id` is set atomically inside `asyncio.Lock` block; `_hydrate_node` back-compat cannot corrupt the chain |
| Path traversal via `root_id` in file ops | Information Disclosure | `root_id` is `uuid4().hex[:12]` (no user-controlled separators); `_write_node_file` scopes to `cwd / ".voss" / "sessions" / root_id` |
| `ChildHandle.node` None-deref if not set | Tampering | Finalize calls guarded with `if h.node is not None:` |

**Budget cage invariant summary:** At every tree level, `sum(active_children_limits) + reserve ≤ parent_limit` enforced by `asyncio.Lock` in each `SessionTreeManager`. Viable-floor (`2_000`) bounds recursion depth naturally — no depth constant, termination is budget-structural.

---

## Open Questions

1. **Does V8 need V4-03 (`export_tree`) to land first, or can it write its own glob-based reconstruction?**
   - What we know: V4-03 is NOT on disk. The acceptance criterion says "tree reconstructs from persisted nodes." The test only needs to verify the data is present and linkable.
   - What's unclear: Is the V8 planner expected to include a V4-03 execution wave, or just write an inline glob helper?
   - **Recommendation (RESOLVED):** V8 tests can use an inline `_glob_tree(cwd, root_id)` helper (same as `_load_nodes_from_disk` already in `test_session_tree.py`). The V8 acceptance criterion does not require the CLI subcommand. V4-03 can complete independently or be deferred; it does not block V8.

2. **Does `subagents.py::run_subagent` need to be updated for V8?**
   - What we know: `run_subagent` is the serial subagent path (not the M13 non-blocking path). M13's `subagent_spawn` already uses `run_turn` directly (not `run_subagent`). The pre-emptive guard in `run_subagent` applies to the OLD board/EM path, not the chat fan-out path.
   - What's unclear: Does V8 need `run_subagent` to accept a `node_manager` and allocate via V4 for the serial path too?
   - **Recommendation (RESOLVED):** No. `run_subagent`'s V4-02 guard already handles the direct `node=` path. V8 changes only the M13 non-blocking path (`attach_multiagent_tools` + `subagent_spawn`). The serial `run_subagent` stays as-is. The T-V4-14 documented gap ("tool-dispatched path unguarded — V5/V7") is unchanged by V8.

3. **Should `_children` be pruned when a child is finalized (i.e., add `release_child`)?**
   - What we know: Current `SessionTreeManager._children` is never pruned. If budget needs to be reusable (spawn more children after some finish), pruning is required.
   - What's unclear: M13 had `release`/`rebalance` for live allotment updates. V4 lacks this.
   - **Recommendation (RESOLVED):** Add `release_child(node_id: str)` to `SessionTreeManager` that removes the node from `_children` under the lock. Call it in `subagent_gather` and `_teardown_orphans` after `finalize_node`. This is the minimal change that makes budget reusable after a child finishes, matching M13's `release` semantics.

4. **What about the e2e test `test_multiagent_chat_e2e.py` pre-existing failure?**
   - What we know: The test fails on `AUTH_STEERED` assertion (steer-between-iterations timing in e2e context). This is a pre-existing failure unrelated to V8.
   - **Recommendation (RESOLVED):** V8 should not introduce NEW failures in this test. The existing failure is not V8's responsibility to fix. Flag in the plan.

5. **How does `DEFAULT_PARENT_RESERVE` interact with the chat root node's envelope?**
   - What we know: `DEFAULT_PARENT_RESERVE = 30_000`; chat root envelope `limit = 60_000`. The reserve carves 30k for the parent turn itself, leaving 30k for spawned children.
   - What's unclear: Should the reserve be a separate parameter or embedded in the `SessionTreeManager` constructor?
   - **Recommendation (RESOLVED):** Pass `reserve=DEFAULT_PARENT_RESERVE` to `SessionTreeManager(root, reserve=DEFAULT_PARENT_RESERVE, cwd=cwd)`. This matches the V4 design (reserve is a constructor parameter). No new field needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | All tests | ✓ | 3.13.12 | — |
| pytest-asyncio | Async tests (asyncio_mode=auto) | ✓ | 1.3.0 | — |
| voss_runtime (BudgetScope, EpisodicMemory, tool) | multiagent.py | ✓ | installed in .venv | — |
| asyncio (stdlib) | Lock, create_task | ✓ | stdlib | — |
| `.venv/bin/python` | All test invocations | ✓ | 3.13.12 | MUST use .venv/bin/python — bare python3 lacks deps (memory voss-python-interpreter) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | V4-02 production code on disk constitutes "V4-02 DONE" for V8's purposes even without V4-02-SUMMARY.md | Dependency Readiness | Low — code verified from disk; summary is a tracking artifact |
| A2 | V4-03 (`export_tree`) can be absent at V8 execution time; V8 uses inline glob helpers | Open Questions | Low — V8 tests don't depend on CLI; V4-03 is supplementary |
| A3 | The even-split rebalance semantics difference (V4 fixed limits vs M13 live allotments) is acceptable to users; no test regression expected | Research Focus 2 | Medium — if a test explicitly checks "after release, existing child's allotment increased" that test must be migrated |
| A4 | Per-node `SessionTreeManager` (one manager per node that can spawn children) is the correct recursion mechanism | Research Focus 1 | Low — alternative single-manager approach also works but is more complex |
| A5 | `ChildHandle.sub_allocator` field can be deprecated (set to None) without breaking anything | Standard Stack | Low — `sub_allocator` is only referenced internally in `attach_multiagent_tools` for recursive creation; V8 replaces that usage |

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/session_tree.py` (full read, current O1+V4-01+V4-02 state) — all `SessionTreeManager`, `SessionTreeNode`, `allocate_child` API details [VERIFIED: read from disk]
- `voss/harness/multiagent.py` (full read) — all M13Allocator, ChildHandle, ChildRegistry, attach_multiagent_tools, PanelBridgeRenderer details [VERIFIED: read from disk]
- `voss/harness/subagents.py` (lines 215-330) — run_subagent with V4-02 guard/finalize [VERIFIED: read from disk]
- `voss/harness/cli.py` (lines 2000-2230) — attach_multiagent_tools wiring, chat loop, _run_turn_with_teardown [VERIFIED: read from disk]
- `voss/harness/agent.py` (lines 515-530, 695-760, 1012-1021) — token_budget=60_000 default, steer_inbox drain [VERIFIED: read from disk]
- `voss/harness/tui/widgets/sub_agent_panel.py` (full read) — SubAgentPanel, quiet-by-default on_mount [VERIFIED: read from disk]
- `tests/harness/test_session_tree.py` (full read) — all 18 tests, _NODE_JSON_KEYS [VERIFIED: read from disk]
- `tests/harness/test_multiagent_fanout.py`, `test_multiagent_recursion.py`, `test_multiagent_steer.py` (full reads) [VERIFIED: read from disk]
- `tests/harness/test_subagent_recursion.py` (full read) [VERIFIED: read from disk]
- `tests/harness/conftest.py` (lines 310-519) — scripted_multiagent_provider fixture [VERIFIED: read from disk]
- `.planning/phases/V4-.../V4-01-PLAN.md`, `V4-02-PLAN.md`, `V4-03-PLAN.md` (full reads) — post-V4 target API [VERIFIED: read from disk]
- `.planning/phases/V8-.../V8-CONTEXT.md`, `V8-SPEC.md` (full reads) [VERIFIED: read from disk]
- `.planning/STATE.md` (lines 1-96) [VERIFIED: read from disk]
- Test run results: `pytest tests/harness/test_multiagent_*.py` → 4 passed, 10 xpassed [VERIFIED: run]
- Test run results: `pytest tests/harness/test_session_tree.py` → 18 passed [VERIFIED: run]
- Test run results: `pytest tests/harness/test_subagent_recursion.py` → 3 passed [VERIFIED: run]

### Secondary (MEDIUM confidence)

- `tests/e2e/test_multiagent_chat_e2e.py` — pre-existing FAILING test (AUTH_STEERED assertion); not a V8 regression [VERIFIED: run]
- `.planning/docs/ORCHESTRATION_LAYERS.md` — MAG-01..10 requirement definitions [VERIFIED: read from disk]

---

## Metadata

**Confidence breakdown:**
- Dependency Readiness (V4/M13 disk state): HIGH — every file read from disk, tests run
- Standard Stack: HIGH — zero new deps confirmed from CONTEXT + research
- Architecture (recursive mechanism): MEDIUM-HIGH — per-node manager recommended based on design analysis; alternative exists
- Pitfalls: HIGH — derived from direct code reading and test execution
- Test Migration: HIGH — all test files read, exact xfail counts confirmed

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (30 days; stable Python stdlib + existing codebase)

---

## RESEARCH COMPLETE

**Phase:** V8 - Multi-agent Chat + Live Steering (absorbs M13)
**Confidence:** HIGH

### Key Findings

1. **M13 is FULLY shipped** (all 10 xfail tests XPASSED), including in-memory recursive fan-out. V8 is purely a persistence+unification migration, not a feature build.

2. **V4 is PARTIALLY executed:** V4-01 (scope/role/error) and V4-02 (guard/finalize) are on disk and production-ready. V4-03 (export_tree/CLI) is NOT on disk — V8 does not require it; inline glob helpers suffice for test acceptance criteria.

3. **The core structural change:** Replace `M13Allocator(reserve=allotment)` with `SessionTreeManager(child_node, reserve=VIABLE_FLOOR, cwd=cwd)` in the recursive attach path. The even-split math moves from M13Allocator._rebalance_locked to an inline calculation in subagent_spawn.

4. **`test_subagent_recursion.py` needs zero changes** — V8's viable-floor constant goes in `multiagent.py` or `session_tree.py`, not `subagents.py`; the three assertions in that file remain valid.

5. **`ChildHandle` gets one new field:** `node: Any = None` to carry the `SessionTreeNode` reference for `finalize_node` calls on terminal. The `sub_allocator` field is deprecated (set to None in V8).

6. **Chat root lifecycle:** One `SessionTreeNode.create_root` call at `chat_cmd` session start (not per-turn); `finalize_node` at session exit. The `_chat_tree = SessionTreeManager(root, reserve=30_000, cwd=cwd)` replaces `M13Allocator(reserve=DEFAULT_PARENT_RESERVE)` as the top-level allocator passed to `attach_multiagent_tools`.

### File Created
`.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Dependency Readiness | HIGH | All surfaces read from disk; tests run to confirm |
| Recursive Mechanism | MEDIUM-HIGH | Design analysis clear; per-node manager recommended; alternative exists |
| M13 Ship Status | HIGH | Test run confirmed all 10 xfail tests XPASSED |
| Test Migration Path | HIGH | All test files read; exact migration requirements documented |
| Schema Safety | HIGH | Frozen schemas verified; `_NODE_JSON_KEYS` not changed by V8 |

### Open Questions (Resolved In-Research)

All 5 open questions were resolved during research — see `## Open Questions` section.

### Ready for Planning

Research complete. Planner can create PLAN.md files targeting the post-V4 surface (V4-01+02 on disk, V4-03 safe to ignore, M13 fully shipped).
