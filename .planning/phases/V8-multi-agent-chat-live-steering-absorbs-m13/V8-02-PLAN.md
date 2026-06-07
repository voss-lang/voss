---
phase: V8-multi-agent-chat-live-steering-absorbs-m13
plan: 02
type: execute
wave: 2
depends_on: ["V8-01"]
files_modified:
  - voss/harness/session_tree.py
  - voss/harness/multiagent.py
  - voss/harness/cli.py
autonomous: true
requirements: [VMAG-10, VMAG-UNIFY, VMAG-07, VMAG-ROOT]
must_haves:
  truths:
    - "A chat /agent spawn creates a persisted V4 session-tree node (child of the chat root); terminal state finalized on disk"
    - "Chat spawns allocate through the V4 SessionTreeManager; no separate in-memory allocator governs chat spawns"
    - "A child-of-child spawn persists as a nested node; the budget invariant holds at every level; recursion terminates via the viable-floor with no depth constant"
    - "The chat session has a persisted root node with a default envelope (60k, configurable) + reserve; exhausted envelope denies further spawns"
    - "Concurrent chat spawns cannot oversell the chat root"
  artifacts:
    - path: "voss/harness/session_tree.py"
      provides: "release_child(node_id) additive method on SessionTreeManager"
      contains: "def release_child"
    - path: "voss/harness/multiagent.py"
      provides: "V4-backed attach_multiagent_tools(node_manager=...), ChildHandle.node, per-node recursion, finalize_node on terminal"
      contains: "node_manager"
    - path: "voss/harness/cli.py"
      provides: "chat root node creation + session-exit finalize + node_manager wiring"
      contains: "create_root"
  key_links:
    - from: "voss/harness/cli.py"
      to: "voss.harness.multiagent.attach_multiagent_tools"
      via: "node_manager=_chat_tree keyword (replaces M13Allocator fallback)"
      pattern: "node_manager=_chat_tree"
    - from: "voss/harness/multiagent.py subagent_spawn"
      to: "voss.harness.session_tree.SessionTreeManager.allocate_child"
      via: "await node_manager.allocate_child(allotment, scope='chat', role=agent)"
      pattern: "allocate_child"
    - from: "voss/harness/multiagent.py subagent_gather/_teardown_orphans"
      to: "voss.harness.session_tree.finalize_node"
      via: "finalize_node(h.node, exit_reason=...) guarded by `if h.node is not None`"
      pattern: "finalize_node"
---

<objective>
Implement the V8 unification: swap the M13 in-memory allocation backend for the V4 persisted `SessionTreeManager`, make every chat spawn a persisted session-tree node, deliver recursive (depth>1) persisted fan-out via per-node managers, and give the chat session a V4 root envelope. This makes V8-01's RED tests GREEN.

Purpose: Close PRD §2.2 fragmentation — one substrate (V4) governs chat fan-out budget; child events persist and the tree reconstructs from disk; recursion is bounded by the viable-floor with no depth constant (M13's property, now persisted). Implements VMAG-10 (persist), VMAG-UNIFY (single allocator), VMAG-07 (recursion), VMAG-ROOT (chat root).

Output: An additive `release_child` on `SessionTreeManager`; a V4-backed `attach_multiagent_tools` (parameter `allocator`→`node_manager`) with `ChildHandle.node` and `finalize_node` on terminal; chat-root creation + session-exit finalize + the updated call site in `cli.py`.

CRITICAL COUPLING (V8-RESEARCH Pitfall 7): the `attach_multiagent_tools` parameter rename (`allocator`→`node_manager`) and the `cli.py` call-site update MUST land together in this single plan/wave — otherwise the chat session fails to boot (TypeError on unexpected keyword). Tasks 2 and 3 are file-coupled by design.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-SPEC.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-CONTEXT.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-RESEARCH.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-PATTERNS.md

<interfaces>
<!-- The exact disk surfaces V8-02 builds on (verified on disk 2026-06-06). -->

From voss/harness/session_tree.py (V4-01 + V4-02 on disk):
- `SessionTreeNode.create_root(*, cwd, limit) -> SessionTreeNode`; `to_dict()`; fields incl `scope`/`role` (V4-01), `terminal_state`, `envelope={"limit","spent"}`, `root_id`, `parent_run_id`.
- `SessionTreeManager(root_node, *, reserve, cwd)`; `_root`, `_reserve`, `_cwd`, `_children: list`, `_lock: asyncio.Lock`; `.allocate_child(limit, *, scope=None, role=None)` (async, lock-held, raises `BudgetAllocationError`, sets `root_id=self._root.id` + `parent_run_id=self._root.id`, persists, sets `_budget`); `.get_node(node_id)`.
- `finalize_node(node, *, exit_reason, final="", cwd)` (idempotent via `_finalized`; validates `exit_reason in EXIT_REASONS`).
- `export_tree(root_id, cwd)` exists.
- `BudgetAllocationError`.
- `EXIT_REASONS` (from voss.harness.session) already contains done/interrupt/error/budget/timeout/killed — do NOT add a new reason.

From voss/harness/multiagent.py (M13 surface to migrate):
- `M13Allocator` (remove), `DEFAULT_PARENT_RESERVE=30_000`, `DEFAULT_VIABLE_FLOOR=2_000` (keep).
- `ChildHandle` dataclass (fields: id, task, allotment, done, result, queue, panel_id, sub_allocator) — add `node: Any = None` as last field; set `sub_allocator=None`.
- `ChildRegistry`, `new_handle_id`, `PanelBridgeRenderer` (keep intact).
- `attach_multiagent_tools(tools, *, registry, cwd, renderer, provider, model, gate, cognition=None, allocator=None)` at line 279 — rename `allocator` → `node_manager`. `subagent_spawn` (346-417), `subagent_steer` (419-435), `subagent_status` (437-463), `subagent_gather` (465-496), `_teardown_orphans` (498-522).

From voss/harness/cli.py:
- `from .multiagent import attach_multiagent_tools` (line 41).
- `_run_repl(*, cwd, json_mode, mode, history, record, provider, ...)` (line 1927) — `cwd: Path` is in scope.
- `attach_multiagent_tools(...)` call at lines 2019-2028 (no `allocator=` passed today).
- Session-exit `finally` block at lines 2231-2247 (the bookend; runs reap_jobs).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add release_child to SessionTreeManager (session_tree.py)</name>
  <files>voss/harness/session_tree.py</files>
  <read_first>
    - `voss/harness/session_tree.py` lines 173-225 (the `SessionTreeManager` class — `__init__`, `get_node`, `allocate_child`). The `_children` list is never pruned today.
    - V8-RESEARCH.md "Research Focus Area 2" Pitfall 2 (finalized children must be pruned so freed budget is reusable) + Open Question 3 (RESOLVED: add `release_child`).
    - V8-PATTERNS.md "`release_child` — NEW method needed on `SessionTreeManager`" (lines 483-499).
  </read_first>
  <action>
    Add an additive `release_child(self, node_id: str) -> None` method to `SessionTreeManager` (after `get_node`, before `allocate_child`, or directly after `allocate_child`). It removes the node from `self._children` so its `envelope["limit"]` no longer counts against `available` in subsequent `allocate_child` calls: `self._children = [c for c in self._children if c.id != node_id]`. Idempotent (unknown id is a no-op). Do NOT acquire `self._lock` inside this method — the callers (`subagent_gather`, `_teardown_orphans`) invoke it outside any `allocate_child` transaction (per V8-PATTERNS note). Add a one-line docstring describing it mirrors `M13Allocator.release` semantics (frees budget for reallocation).

    Do NOT change any `SessionTreeNode` field, `_NODE_FIELDS`, `create_root`, `allocate_child`, `finalize_node`, `mutate_envelope`, or `export_tree`. This is the ONLY change to `session_tree.py`. Do NOT add `release_child` to `__all__` (it is a method, not a module export).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_session_tree.py -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'def release_child' voss/harness/session_tree.py` returns one match on `SessionTreeManager`.
    - `.venv/bin/python -m pytest tests/harness/test_session_tree.py -q` still passes all existing tests (18 tests; no regression).
    - `git diff voss/harness/session_tree.py` shows ONLY the added `release_child` method (no field changes, no `allocate_child`/`create_root` edits).
  </acceptance_criteria>
  <done>`SessionTreeManager.release_child(node_id)` exists, prunes `_children`, is idempotent, holds no lock; all existing session_tree tests stay green; no other change to the file.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: V4-backed multiagent.py — node_manager param, ChildHandle.node, per-node recursion, finalize on terminal</name>
  <files>voss/harness/multiagent.py</files>
  <read_first>
    - `voss/harness/multiagent.py` in full (the module read this plan was authored against) — especially `M13Allocator` (69-155, to remove), `ChildHandle` (158-188), `attach_multiagent_tools` signature (279-290), the `allocator is None` fallback (324-325), `subagent_spawn` allocation + recursive attach (346-417), `subagent_status` snapshot use (445-463), `subagent_gather` release+rebalance (473-496), `_teardown_orphans` (498-522).
    - V8-PATTERNS.md sections "`voss/harness/multiagent.py` (service/orchestrator — MODIFY)" (lines 24-330) — imports addition, signature change, ChildHandle extension, recursive-attach replacement, subagent_spawn even-split inline, ChildHandle construction with `node=`, gather finalize pattern, teardown finalize pattern, constants to keep.
    - V8-RESEARCH.md "Research Focus Area 1" (per-node manager mechanism), "Focus Area 2" (M13Allocator fold; even-split is calculation-only since V4 limits are immutable), "Focus Area 4" (persistence wiring), Pitfalls 1/2/3/5/6/7.
  </read_first>
  <action>
    Migrate the allocation backend from `M13Allocator` to V4 `SessionTreeManager`, keeping the entire tool surface (`subagent_spawn/steer/status/gather`, `ChildRegistry`, `ChildHandle`, `PanelBridgeRenderer`, `new_handle_id`, `_teardown_orphans`) intact.

    Imports: add `from .session_tree import BudgetAllocationError, SessionTreeManager, SessionTreeNode, finalize_node` (after the existing `.tools` import block; `from __future__ import annotations` is already present).

    Constants: KEEP `DEFAULT_PARENT_RESERVE = 30_000` and `DEFAULT_VIABLE_FLOOR = 2_000`. Add a module-level `VIABLE_FLOOR = DEFAULT_VIABLE_FLOOR` alias used by the inline even-split denial. (These are budget constants — NOT depth constants; they stay in this module, never in subagents.py, per V8-RESEARCH Pitfall 6.)

    Remove `M13Allocator` entirely (class 69-155). V8-01's `TestUnifiedAllocator::test_no_m13allocator_attribute` asserts `not hasattr(multiagent, "M13Allocator")`, so do not leave a shim.

    `ChildHandle`: add `node: Any = None` as the LAST field (after `sub_allocator`). Update the docstring to mark `sub_allocator` deprecated in V8 (kept for positional back-compat, set to None at construction).

    `attach_multiagent_tools` signature: rename keyword `allocator: M13Allocator | None = None` → `node_manager: SessionTreeManager | None = None`. Remove the `if allocator is None: allocator = M13Allocator(...)` fallback (324-325) — the chat root manager is now owned by `cli.py` and injected; there is no in-module construction. Update the docstring to describe the V4-backed `node_manager`.

    `subagent_spawn`: replace the `allotment = await allocator.allocate(handle)` path with an inline even-split + V4 allocation. Inside `async with node_manager._lock:` compute `active_children = [c for c in node_manager._children if c.terminal_state is None]`, `n = len(active_children) + 1`, `allocated = sum(c.envelope["limit"] for c in active_children)`, `available = node_manager._root.envelope["limit"] - node_manager._reserve - allocated`, `allotment = available // n`; if `allotment < VIABLE_FLOOR`, return the canonical denial string `f"<denied: budget below viable floor — cannot spawn {agent!r}>"`. Then, OUTSIDE the lock (Pitfall 1 — never hold the lock across allocate/create_task), call `child_node = await node_manager.allocate_child(allotment, scope="chat", role=agent)` wrapped in `try/except BudgetAllocationError as exc: return f"<denied: {exc}>"` (the authoritative guard against the TOCTOU window). Replace the `sub_alloc = M13Allocator(reserve=allotment)` recursive-attach block with: `child_manager = SessionTreeManager(child_node, reserve=VIABLE_FLOOR, cwd=cwd)` then the recursive `attach_multiagent_tools(child_tools, ..., node_manager=child_manager)` (renamed keyword). Keep the `run_turn(..., token_budget=allotment, steer_inbox=queue)` call unchanged. Construct the `ChildHandle` with `id=child_node.id` (use the persisted node id as the handle so registry lookups and node finalize align), `sub_allocator=None`, `node=child_node`. Note: `panel_id`/`bridge` keying and the `bridges` dict must key on the same id used as the handle — keep them consistent (use `child_node.id`).

    `subagent_status`: it currently reads `allocator.snapshot()`. Replace with a snapshot derived from `node_manager` — build `snap = {c.id: c.envelope["limit"] for c in node_manager._children}` so the per-child allotment display still works. Keep the rest of the status formatting.

    `subagent_gather`: remove `allocator.release(h.id)` + `await allocator.rebalance()`. After resolving each handle's result, finalize + release: if `isinstance(r, Exception)` set `h.result` to the error and, guarded `if h.node is not None:`, call `finalize_node(h.node, exit_reason="error", final=h.result, cwd=cwd)`; else set the done result and `finalize_node(h.node, exit_reason="done", final=h.result, cwd=cwd)`. In both branches call `node_manager.release_child(h.id)` (Pitfall 2). Keep `br.end_panel(1)`.

    `_teardown_orphans`: remove `allocator.release(h.id)` + `await allocator.rebalance()`. After cancelling the task and setting `h.result` to the orphan string, guarded `if h.node is not None:` call `finalize_node(h.node, exit_reason="interrupt", final=h.result, cwd=cwd)` then `node_manager.release_child(h.id)` (Pitfall 5). Keep `br.end_panel(1)`.

    Do NOT add `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` anywhere. Do NOT touch `subagents.py`. Do NOT change `SessionTreeNode` fields. Implements VMAG-10/UNIFY/07.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `attach_multiagent_tools` accepts `node_manager` and NOT `allocator`: `grep -nE 'allocator' voss/harness/multiagent.py | grep -v '^#'` returns nothing (no M13Allocator, no allocator param/usages remain).
    - `grep -n 'node: Any = None' voss/harness/multiagent.py` shows `ChildHandle.node` added.
    - `grep -nE 'finalize_node\(' voss/harness/multiagent.py` returns ≥ 3 (gather done, gather error, teardown interrupt).
    - `grep -cE 'MAX_DEPTH|DEPTH_LIMIT|RECURSION_LIMIT' voss/harness/multiagent.py` returns 0.
    - `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestPersistOnSpawn tests/harness/test_multiagent_session_tree.py::TestUnifiedAllocator tests/harness/test_multiagent_session_tree.py::TestPersistedRecursion tests/harness/test_multiagent_session_tree.py::TestViableFloorTermination -q` passes (these classes exercise multiagent.py without the cli wiring, since the tests build their own root manager). Note: `TestChatRootEnvelope`/`TestConcurrentNoOversellChatRoot` also pass here as they build their own manager.
  </acceptance_criteria>
  <done>multiagent.py routes allocation through the injected V4 `node_manager`, persists every spawn as a node, recurses via per-node managers with viable-floor denial (no depth constant), finalizes on done/error/interrupt and prunes via `release_child`; `ChildHandle.node` is the only new field; M13Allocator is gone; the V8-01 multiagent-driven test classes are GREEN.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Chat root + session-exit finalize + call-site rename (cli.py) — coupled with Task 2</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - `voss/harness/cli.py` lines 1927-2028 (the `_run_repl` signature with `cwd: Path`, the `attach_subagent_tool`/`attach_memory_tools` block, and the `attach_multiagent_tools` call at 2019-2028) and lines 2231-2247 (the session-exit `finally` block).
    - `voss/harness/cli.py` line 41 (`from .multiagent import attach_multiagent_tools`).
    - V8-PATTERNS.md sections "`voss/harness/cli.py` chat session" (lines 334-427) — chat root creation insert point, call-site parameter update (Pitfall 7), session-exit finalize.
    - V8-RESEARCH.md "Research Focus Area 3: Chat Root Lifecycle" (root created ONCE per `_run_repl`, finalized on exit; 60k configurable default; reserve=DEFAULT_PARENT_RESERVE) + Pitfall 4 (do NOT create root per-turn) + Pitfall 7 (rename breaks cli if not updated together).
  </read_first>
  <action>
    Wire the chat root node and update the call site. This task is coupled with Task 2's rename — both land in this plan/wave (Pitfall 7).

    Imports: extend the line-41 import to `from .multiagent import attach_multiagent_tools, DEFAULT_PARENT_RESERVE` and add `from .session_tree import SessionTreeManager, SessionTreeNode, finalize_node` (place near the other `voss.harness` imports at the top of the module; do not import inside the function unless that matches the file's existing convention for these symbols — prefer top-level).

    Chat root creation: immediately BEFORE the `attach_multiagent_tools` call (after line 2018, in `_run_repl`, session-scoped — NOT inside any per-turn loop, Pitfall 4), create: `_chat_root = SessionTreeNode.create_root(cwd=cwd, limit=60_000)` (the configurable default sourced to match `agent.py` `token_budget=60_000`; leave 60_000 as the literal V8 default), `_chat_tree = SessionTreeManager(_chat_root, reserve=DEFAULT_PARENT_RESERVE, cwd=cwd)`. Add a comment noting 60_000 is the configurable chat-root envelope default and DEFAULT_PARENT_RESERVE (30_000) is the carved reserve.

    Call-site update (lines 2019-2028): add `node_manager=_chat_tree` as the final keyword argument to the `attach_multiagent_tools(...)` call. (Without this the session fails to boot after Task 2's rename.)

    Session-exit finalize: in the `finally` block at 2231, BEFORE the existing `lifecycle.reap_jobs` try-block, add a guarded finalize: `try: finalize_node(_chat_root, exit_reason="done", final="", cwd=cwd) except Exception as exc: click.echo(f"chat root finalize skipped: {exc}", err=True)`. `finalize_node` is idempotent so this is safe on all exit paths (Ctrl+C, EOFError, normal, TUI close). Use `exit_reason="done"` (a valid existing EXIT_REASON — do NOT invent a new reason).

    Do NOT pass `node_manager` to `attach_subagent_tool` (the serial path is unchanged — V8-RESEARCH Open Question 2 RESOLVED). Do NOT create the root inside the per-turn dispatch. Implements VMAG-ROOT.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "import voss.harness.cli" && .venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `voss.harness.cli` imports without error (no TypeError / no leftover `allocator=`).
    - `grep -n 'create_root(cwd=cwd, limit=60_000)' voss/harness/cli.py` returns one match inside `_run_repl`.
    - `grep -n 'node_manager=_chat_tree' voss/harness/cli.py` returns one match (the call-site update — Pitfall 7 satisfied).
    - `grep -n 'finalize_node(_chat_root' voss/harness/cli.py` returns one match inside the `finally` block.
    - `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q` is fully GREEN (all six classes pass — the full V8-01 RED scaffold is now satisfied).
  </acceptance_criteria>
  <done>`_run_repl` creates a session-scoped chat root + V4 manager, injects `node_manager=_chat_tree`, and finalizes the root on session exit; cli.py imports cleanly; the full V8-01 test file is GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| chat-turn LLM → spawn tool | The model's `subagent_spawn` calls cross into budget allocation; untrusted call frequency/arguments |
| recursive child → sub-spawn | A spawned child can itself spawn; the budget cage must hold at every level |
| in-memory handle → persisted node | `ChildHandle.node` references a disk file written under `.voss/sessions/<root_id>/` |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V8-01 | Tampering | concurrent `subagent_spawn` over-allocating the chat root | mitigate | All check-and-allocate runs under `SessionTreeManager._lock` in `allocate_child`; `available` computed under the lock; `BudgetAllocationError` is the authoritative guard even if the inline even-split races (Pitfall 1). Verified by `TestConcurrentNoOversellChatRoot`. |
| T-V8-02 | Denial of Service | recursive spawn exhausting budget via unbounded depth | mitigate | Viable-floor denial: `allotment = available // n; if allotment < VIABLE_FLOOR → "<denied: ...>"`. NO depth/max_depth constant — termination is budget-structural. Verified by `TestViableFloorTermination` + the no-depth-constant pin across multiagent.py and subagents.py. |
| T-V8-03 | Elevation of Privilege | a child spending past its envelope | mitigate | V4-02 pre-emptive spend guard (subagents.py:232, on disk) + `mutate_envelope` track spent; child envelope `limit` is immutable once allocated. V8 does not weaken this path. |
| T-V8-04 | Denial of Service | orphaned child task leaks budget/panel on Ctrl+C / un-gathered turn | mitigate | `_teardown_orphans` cancels the task, calls `finalize_node(..., exit_reason="interrupt")` guarded by `if h.node is not None`, then `release_child`. Verified by `TestOrphanTeardown` (V8-03 regression). |
| T-V8-05 | Tampering | nested-node `parent_run_id` chain corruption | mitigate | `parent_run_id=self._root.id` set atomically inside `allocate_child`'s lock; per-node manager means each level's root is well-defined; tree reconstructs by following the chain. |
| T-V8-06 | Information Disclosure | path traversal via `root_id` in node file ops | accept | `root_id`/node ids are `uuid4().hex[:12]` (no user-controlled separators); `_write_node_file` scopes to `cwd/.voss/sessions/<root_id>/`. No mitigation code needed. |
| T-V8-07 | Tampering | `ChildHandle.node` None-deref at finalize | mitigate | Every `finalize_node` call guarded with `if h.node is not None:`. |
| T-V8-SC | Tampering | npm/pip/cargo installs | mitigate | V8 installs ZERO new dependencies (V8-RESEARCH "No Package Legitimacy Audit Required"); stdlib + existing voss modules only. No install task exists in this phase. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q` fully GREEN (all six V8-01 classes pass).
- `.venv/bin/python -m pytest tests/harness/test_session_tree.py -q` still passes (no V4 regression from `release_child`).
- `.venv/bin/python -c "import voss.harness.cli"` succeeds (the rename + call-site are coupled and consistent).
- No `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` introduced in multiagent.py or subagents.py; `subagents.py` untouched.
- `SessionTreeNode` fields unchanged; the only dataclass field change in the phase is `ChildHandle.node`.
- The pre-existing `test_multiagent_chat_e2e.py::test_multiagent_chat_e2e` (AUTH_STEERED) failure is out of scope — do not fix, do not regress further.
</verification>

<success_criteria>
- Chat spawns allocate through the V4 `SessionTreeManager`; `M13Allocator` is removed; no second in-memory allocator remains.
- Every spawn persists a node; terminal state finalized on disk (done/error/interrupt); tree reconstructs from disk.
- Recursive depth>1 fan-out persists nested nodes; invariant holds per level; viable-floor terminates with no depth constant.
- Chat root node created once per `_run_repl` with 60k envelope + 30k reserve; finalized on session exit; exhaustion denies.
- `release_child` is the only `session_tree.py` change; `ChildHandle.node` is the only new dataclass field.
</success_criteria>

<output>
Create `.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-02-SUMMARY.md` when done.
</output>
