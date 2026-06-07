# Phase V8: Multi-agent Chat + Live Steering (absorbs M13) - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 5 (2 modify, 1 create, 2 migrate)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/multiagent.py` | service/orchestrator | event-driven (async spawn/gather) | `voss/harness/multiagent.py` itself (self-modification) | exact |
| `voss/harness/cli.py` (chat_cmd / `_run_repl`) | controller | request-response (session lifecycle) | `voss/harness/cli.py` itself (self-modification) | exact |
| `voss/harness/session_tree.py` (composition reference) | service/substrate | CRUD + event-driven | `voss/harness/session_tree.py` itself (read-only API reference) | exact |
| `tests/harness/test_multiagent_session_tree.py` | test | CRUD + event-driven | `tests/harness/test_multiagent_fanout.py` + `tests/harness/test_session_tree.py` | role-match |
| `tests/harness/test_multiagent_fanout.py` (migrate) | test | event-driven | self (assertion migration) | exact |
| `tests/harness/test_multiagent_recursion.py` (migrate) | test | event-driven | self (assertion migration) | exact |

---

## Pattern Assignments

### `voss/harness/multiagent.py` (service/orchestrator — MODIFY)

**Analog:** `voss/harness/multiagent.py` (existing code, self-modification)

#### Imports pattern — current (lines 40–46, 233–241)

```python
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from pathlib import Path
from typing import Callable

from voss_runtime import EpisodicMemory, tool

from .agent import run_turn
from .permissions import PermissionGate
from .subagents import SubagentRegistry, agent_task
from .tools import ToolEntry, make_toolset
```

**V8 adds** (after the existing imports):
```python
from .session_tree import (
    BudgetAllocationError,
    SessionTreeManager,
    SessionTreeNode,
    finalize_node,
)
```

NOTE: `from __future__ import annotations` already present (line 40) — `node: Any = None` on `ChildHandle` uses `Any` to avoid a forward-reference issue; `SessionTreeNode` import means you can type it properly if desired, but `Any` is safe and matches the existing `sub_allocator: Any = None` convention.

---

#### `M13Allocator` usage sites to REPLACE (lines 69–155, 289, 324–325, 366, 384)

**Current M13Allocator construction (top-level, line 324–325):**
```python
if allocator is None:
    allocator = M13Allocator(reserve=DEFAULT_PARENT_RESERVE)
```

**V8 target** — parameter rename + V4-backed fallback:
```python
# attach_multiagent_tools signature change: allocator → node_manager
def attach_multiagent_tools(
    tools: dict[str, ToolEntry],
    *,
    registry: SubagentRegistry,
    cwd: Path,
    renderer: Any,
    provider: Any,
    model: str | Callable[[], str],
    gate: PermissionGate,
    cognition: Any = None,
    node_manager: SessionTreeManager | None = None,   # RENAMED from allocator
) -> Callable[[], Any]:
    ...
    # node_manager is injected by cli.py (top-level) or recursively (child level)
    # No fallback construction here — the chat root is owned by cli.py
```

---

#### `ChildHandle` dataclass — current (lines 158–188) with V8 extension

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
    sub_allocator: Any = None   # DEPRECATED in V8: kept for back-compat, set to None
    node: Any = None            # V8 NEW: holds the SessionTreeNode for finalize_node calls
```

Pattern: add `node: Any = None` as the LAST field (dataclass field ordering matters for back-compat; `sub_allocator` stays to avoid positional breakage in any test that constructs ChildHandle by position).

---

#### Recursive attach block — current (lines 363–385)

Current pattern to REPLACE:
```python
# multiagent.py:366 — M13 sub_alloc creation (REPLACE this whole block)
sub_alloc = M13Allocator(reserve=allotment)
attach_multiagent_tools(
    child_tools,
    registry=registry,
    cwd=cwd,
    renderer=bridge,
    provider=provider,
    model=model,
    gate=gate,
    cognition=cognition,
    allocator=sub_alloc,          # ← rename to node_manager in V8
)
```

V8 target pattern:
```python
# 1. Persisted allocation via V4 manager
child_node = await node_manager.allocate_child(allotment, scope="chat", role=agent)
# 2. Per-node manager for this child's own recursive fan-out
child_manager = SessionTreeManager(child_node, reserve=VIABLE_FLOOR, cwd=cwd)
# 3. Recursive attach using per-node manager
attach_multiagent_tools(
    child_tools,
    registry=registry,
    cwd=cwd,
    renderer=bridge,
    provider=provider,
    model=model,
    gate=gate,
    cognition=cognition,
    node_manager=child_manager,   # V8: renamed parameter, V4-backed
)
```

CRITICAL: `allocate_child` is `async` — it must be awaited. The even-split check + allocation MUST happen atomically. Pattern from `SessionTreeManager.allocate_child` (session_tree.py:194–225): the lock is already held internally.

---

#### `subagent_spawn` allocation region — current (lines 346–417)

Current allocation path (lines 346–350):
```python
async def subagent_spawn(agent: str, task: str) -> str:
    handle = new_handle_id()
    allotment = await allocator.allocate(handle)
    if allotment is None:
        return (f"<denied: budget below viable floor — cannot spawn {agent!r}>")
```

V8 replacement — even-split inline + V4-backed allocation:
```python
async def subagent_spawn(agent: str, task: str) -> str:
    handle = new_handle_id()

    # Even-split check (inline, atomic under node_manager._lock via allocate_child)
    # The denial path mirrors M13Allocator.allocate's return-None → denied string.
    async with node_manager._lock:
        # Prune finalized children so freed budget is reusable (Pitfall 2)
        active_children = [c for c in node_manager._children if c.terminal_state is None]
        n = len(active_children) + 1
        allocated = sum(c.envelope["limit"] for c in active_children)
        available = node_manager._root.envelope["limit"] - node_manager._reserve - allocated
        allotment = available // n
        if allotment < VIABLE_FLOOR:
            return f"<denied: budget below viable floor — cannot spawn {agent!r}>"
    # allocate_child re-acquires the lock internally — do NOT hold lock here
    try:
        child_node = await node_manager.allocate_child(allotment, scope="chat", role=agent)
    except BudgetAllocationError as exc:
        return f"<denied: {exc}>"
```

NOTE: There is a TOCTOU window between the even-split check and `allocate_child` (Pitfall 1 in RESEARCH). The correct fix is to inline the even-split logic INSIDE `allocate_child` (add an `even_slice` policy to `SessionTreeManager`) OR accept the TOCTOU and rely on `allocate_child`'s own `BudgetAllocationError` as the authoritative guard. The `BudgetAllocationError` catch is mandatory either way.

---

#### `ChildHandle` construction in `subagent_spawn` (lines 403–411) — add `node` field

Current:
```python
child_registry.add(
    ChildHandle(
        id=handle,
        task=t,
        allotment=allotment,
        queue=queue,
        panel_id=panel_id,
        sub_allocator=sub_alloc,
    )
)
```

V8 target:
```python
child_registry.add(
    ChildHandle(
        id=handle,
        task=t,
        allotment=allotment,
        queue=queue,
        panel_id=panel_id,
        sub_allocator=None,        # deprecated — was M13Allocator; now None
        node=child_node,           # V8 NEW: carry SessionTreeNode for finalize
    )
)
```

---

#### `subagent_gather` finalize pattern (lines 473–496)

Current release path (lines 482–494):
```python
for h, r in zip(pending, results):
    allocator.release(h.id)
    await allocator.rebalance()
    if isinstance(r, Exception):
        h.done = True
        h.result = h.result or f"<error: {r}>"
    else:
        h.done = True
        h.result = h.result or (r.final if hasattr(r, "final") else str(r))
    br = bridges.get(h.id)
    if br is not None:
        br.end_panel(1)
```

V8 addition — `finalize_node` + `release_child` after each handle resolution:
```python
for h, r in zip(pending, results):
    if isinstance(r, Exception):
        h.done = True
        h.result = h.result or f"<error: {r}>"
        if h.node is not None:
            finalize_node(h.node, exit_reason="error",
                          final=h.result, cwd=cwd)
        node_manager.release_child(h.id)   # prune from _children (Pitfall 2)
    else:
        h.done = True
        h.result = h.result or (r.final if hasattr(r, "final") else str(r))
        if h.node is not None:
            finalize_node(h.node, exit_reason="done",
                          final=h.result, cwd=cwd)
        node_manager.release_child(h.id)
    br = bridges.get(h.id)
    if br is not None:
        br.end_panel(1)
```

The `release_child(node_id)` method is new on `SessionTreeManager` — see session_tree.py pattern section below.

---

#### `_teardown_orphans` finalize pattern (lines 498–521)

Current cancel path (lines 509–521):
```python
for h in child_registry.all():
    if h.done:
        continue
    t = h.task
    finished = t is not None and t.done()
    if t is not None and not finished:
        t.cancel()
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass
    allocator.release(h.id)
    await allocator.rebalance()
    h.done = True
    h.result = h.result or "<orphan: cancelled at parent turn exit>"
    br = bridges.get(h.id)
    if br is not None:
        br.end_panel(1)
```

V8 addition — `finalize_node` on cancel (Pitfall 5 in RESEARCH):
```python
for h in child_registry.all():
    if h.done:
        continue
    t = h.task
    finished = t is not None and t.done()
    if t is not None and not finished:
        t.cancel()
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass
    h.done = True
    h.result = h.result or "<orphan: cancelled at parent turn exit>"
    if h.node is not None:
        finalize_node(h.node, exit_reason="interrupt",
                      final=h.result, cwd=cwd)
    node_manager.release_child(h.id)   # prune finalized child (Pitfall 2)
    br = bridges.get(h.id)
    if br is not None:
        br.end_panel(1)
```

---

#### Constants to KEEP (lines 55–66) — migrate M13Allocator.VIABLE_FLOOR

```python
# Keep these module-level constants (tests reference them)
DEFAULT_PARENT_RESERVE: int = 30_000
DEFAULT_VIABLE_FLOOR: int = 2_000
VIABLE_FLOOR = DEFAULT_VIABLE_FLOOR   # V8: alias used in even-split inline logic
```

`M13Allocator.VIABLE_FLOOR` (class attribute at line 93) is referenced by `TestNoOversell` as `multiagent.M13Allocator.VIABLE_FLOOR`. After V8 removes `M13Allocator`, this test class migrates (see migration section).

---

### `voss/harness/cli.py` chat session (controller — MODIFY)

**Analog:** `voss/harness/cli.py` `_run_repl` function (self-modification)

#### Chat root creation pattern — insert BEFORE `attach_multiagent_tools` (after line 2012)

Pattern source: `tests/harness/test_session_tree.py::TestTreePersistence::test_root_and_children_persist_and_reconstruct` (lines 79–81) — `create_root` / `SessionTreeManager` construction pattern:

```python
# Insert before attach_multiagent_tools at cli.py:2019
# Session-scoped root node: created ONCE per _run_repl call (not per turn).
# Mirrors the SessionRecord + RunRecorder pattern: top-level, session-owned.
from .session_tree import SessionTreeManager, SessionTreeNode, finalize_node

_chat_root = SessionTreeNode.create_root(cwd=cwd, limit=60_000)
_chat_reserve = DEFAULT_PARENT_RESERVE   # 30_000 — from multiagent module
_chat_tree = SessionTreeManager(_chat_root, reserve=_chat_reserve, cwd=cwd)
```

Note: `DEFAULT_PARENT_RESERVE` and `DEFAULT_VIABLE_FLOOR` are imported from `voss.harness.multiagent` (where they are already defined). No new constant needed.

---

#### `attach_multiagent_tools` call site — update parameter (cli.py:2019–2028)

Current (line 2019–2028):
```python
_multiagent_teardown = attach_multiagent_tools(
    tools,
    registry=subagent_registry,
    cwd=cwd,
    renderer=renderer,
    provider=provider,
    model=lambda: get_config().default_model,
    gate=gate,
    cognition=bundle,
    # No allocator= passed → falls back to M13Allocator inside attach_multiagent_tools
)
```

V8 target — pass `node_manager=_chat_tree` (Pitfall 7 in RESEARCH: this rename is a breaking change):
```python
_multiagent_teardown = attach_multiagent_tools(
    tools,
    registry=subagent_registry,
    cwd=cwd,
    renderer=renderer,
    provider=provider,
    model=lambda: get_config().default_model,
    gate=gate,
    cognition=bundle,
    node_manager=_chat_tree,   # V8: replaces M13Allocator fallback
)
```

---

#### Session-exit finalize pattern — add to `finally` block (lines 2231–2246)

Analog: `voss/harness/session_tree.py::finalize_node` (lines 115–133) + the `finally` pattern in `_run_repl` (lines 2231–2246).

Existing `finally` (lines 2231–2246):
```python
finally:
    try:
        from . import lifecycle
        try:
            asyncio.run(lifecycle.reap_jobs())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(lifecycle.reap_jobs())
            finally:
                loop.close()
        if not keep_logs:
            shutil.rmtree(jobs_root / record.id, ignore_errors=True)
        active_session.unlink(missing_ok=True)
    except Exception as exc:
        click.echo(f"job reap skipped: {exc}", err=True)
```

V8 addition — `finalize_node` before `reap_jobs` (chat root must be finalized on ALL exit paths: Ctrl+C, EOFError, normal exit, TUI close):
```python
finally:
    try:
        finalize_node(_chat_root, exit_reason="done", final="", cwd=cwd)
    except Exception as exc:
        click.echo(f"chat root finalize skipped: {exc}", err=True)
    try:
        # existing lifecycle.reap_jobs() block unchanged
        ...
```

`finalize_node` is idempotent (`_finalized` guard at session_tree.py:123) — safe to call unconditionally.

---

### `voss/harness/session_tree.py` — `release_child` addition (composition reference)

**Read-only API used by V8. One additive method needed.**

#### `SessionTreeManager.__init__` — current (lines 177–183)

```python
class SessionTreeManager:
    def __init__(
        self, root_node: SessionTreeNode, *, reserve: int, cwd: Path
    ) -> None:
        self._root = root_node
        self._reserve = reserve
        self._cwd = cwd
        self._children: list[SessionTreeNode] = []
        self._lock = asyncio.Lock()
```

Pattern for V8's per-node child manager: pass the *child* node as `root_node` to create a new manager rooted at the child. The manager's `self._root.id` becomes the `parent_run_id` for its own children (session_tree.py:211: `parent_run_id=self._root.id`).

#### `SessionTreeManager.allocate_child` — current (lines 194–225)

```python
async def allocate_child(
    self, limit: int, *, scope: str | None = None, role: str | None = None
) -> SessionTreeNode:
    async with self._lock:
        allocated = sum(c.envelope["limit"] for c in self._children)
        available = (
            self._root.envelope["limit"] - self._reserve - allocated
        )
        if limit > available:
            raise BudgetAllocationError(
                f"child limit {limit} exceeds available {available} "
                f"(reserve={self._reserve})"
            )
        child_id = uuid.uuid4().hex[:12]
        child = SessionTreeNode(
            id=child_id,
            root_id=self._root.id,         # NOTE: always root of this manager
            parent_run_id=self._root.id,   # NOTE: this manager's root = child's parent
            envelope={"limit": limit, "spent": 0},
            ...
        )
        self._children.append(child)
        _write_node_file(child, self._cwd)
        child._budget = BudgetScope(token_limit=limit, name=child.id)
        return child
```

IMPORTANT: `root_id=self._root.id` means the root_id on nested nodes equals the sub-manager's root (the child node), NOT the original chat root. If the test acceptance criterion requires all nodes under the chat root to share the chat root's `root_id`, the per-node manager approach needs `root_id` to be passed through. Check against the test: `data["root_id"] == root.id` — this only passes if `root_id` is threaded. The planner must decide: either (a) add a `root_id` parameter to `SessionTreeManager.__init__` to thread the original root id, or (b) accept that nested nodes have `root_id=child_node.id`. Option (b) means `export_tree(chat_root_id)` will only find depth-1 nodes; depth-2+ nodes are under their parent's `root_id`. Thread `root_id` to get a flat directory.

#### `release_child` — NEW method needed on `SessionTreeManager`

Pattern: mirrors `M13Allocator.release` (lines 120–129). Removes the node from `self._children` so freed budget is available for reallocation (Pitfall 2 in RESEARCH):

```python
def release_child(self, node_id: str) -> None:
    """Remove a finalized child from the active list (frees its budget).

    Idempotent: if node_id not in _children, no-op.
    Called by subagent_gather and _teardown_orphans after finalize_node.
    Lock not held here — caller (subagent_gather) is not inside an
    allocate_child transaction.
    """
    self._children = [c for c in self._children if c.id != node_id]
```

This must be added to `session_tree.py` (V8 owns this change since V4 deferred it).

---

### `tests/harness/test_multiagent_session_tree.py` (test — CREATE)

**Analogs:**
1. `tests/harness/test_multiagent_fanout.py` — M13 fixture usage, `_NullRenderer`, `attach_multiagent_tools` call pattern, tool invocation via `.invoke()`
2. `tests/harness/test_session_tree.py` — persisted-node assertions, `_load_nodes_from_disk`, `_node_path`, `_sessions_tree_dir` helpers, `finalize_node` assertions

---

#### File header + imports pattern (from both analogs)

```python
"""V8 VMAG-10/UNIFY/07/ROOT — persisted multi-agent session-tree tests.

New test classes (all GREEN from V8 wave-0 onward — NOT xfail):
  TestPersistOnSpawn            VMAG-10: spawn creates persisted node; terminal finalized
  TestUnifiedAllocator          VMAG-UNIFY: no M13Allocator; V4 manager governs spawns
  TestPersistedRecursion        VMAG-07: depth>1 persisted fan-out; invariant at each level
  TestViableFloorTermination    VMAG-07: viable-floor bounds recursion; no depth constant
  TestChatRootEnvelope          VMAG-ROOT: root node 60k + reserve; exhaustion denies
  TestConcurrentNoOversellChatRoot  VMAG-ROOT: concurrent spawns cannot oversell
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

# Inline disk helpers (mirrors test_session_tree.py:59-73)
def _sessions_tree_dir(cwd: Path, root_id: str) -> Path:
    return cwd / ".voss" / "sessions" / root_id

def _node_path(cwd: Path, root_id: str, node_id: str) -> Path:
    return _sessions_tree_dir(cwd, root_id) / f"{node_id}.json"

def _load_nodes_from_disk(cwd: Path, root_id: str) -> dict[str, dict]:
    tree_dir = _sessions_tree_dir(cwd, root_id)
    nodes: dict[str, dict] = {}
    for path in tree_dir.glob("*.json"):
        data = json.loads(path.read_text())
        nodes[data["id"]] = data
    return nodes
```

---

#### `scripted_multiagent_provider` fixture usage pattern (from test_multiagent_fanout.py:57–60)

```python
# Every test class uses this fixture via parameter injection:
async def test_something(self, tmp_path, scripted_multiagent_provider) -> None:
    from voss.harness import multiagent
    from voss.harness.session_tree import (
        SessionTreeManager, SessionTreeNode, finalize_node
    )
    f = scripted_multiagent_provider
    f.scripts["child-a"] = [f.done_plan("A-DONE", rationale="child a")]
```

The `scripted_multiagent_provider` fixture is in `tests/harness/conftest.py:313` — auto-available in `tests/harness/`.

---

#### `_NullRenderer` pattern (from test_multiagent_fanout.py:24–33)

```python
class _NullRenderer:
    """No-op renderer — swallows all Renderer-protocol calls.
    No show_subagent_* methods so PanelBridgeRenderer hasattr-guards exercise
    the no-base-method path."""

    def __getattr__(self, _attr):
        def _noop(*a, **k):
            return None
        return _noop
```

Copy verbatim — same pattern needed for all test classes in the new file.

---

#### `attach_multiagent_tools` call pattern with `node_manager` (V8 API)

```python
# Pattern: create root → manager → attach (mirrors cli.py V8 target)
root = SessionTreeNode.create_root(cwd=tmp_path, limit=60_000)
chat_tree = SessionTreeManager(root, reserve=30_000, cwd=tmp_path)
tools: dict = {}
teardown = multiagent.attach_multiagent_tools(
    tools,
    registry=multiagent.SubagentRegistry(),
    cwd=tmp_path,
    renderer=_NullRenderer(),
    provider=scripted_provider,
    model="stub",
    gate=None,
    cognition=None,
    node_manager=chat_tree,   # V8: was `allocator=`
)
```

---

#### Persisted-node assertion pattern (from test_session_tree.py:79–112)

```python
# After spawn + gather: assert child node file on disk
nodes = _load_nodes_from_disk(tmp_path, root.id)
assert len(nodes) == 2  # root + 1 child
child_id = next(nid for nid in nodes if nid != root.id)
child_data = nodes[child_id]
assert child_data["parent_run_id"] == root.id
assert child_data["root_id"] == root.id  # or child node's id if per-node manager
# After gather: terminal_state finalized on disk
assert child_data["terminal_state"] is not None
assert child_data["terminal_state"]["exit_reason"] in ("done", "error", "interrupt")
```

---

#### `TestPersistOnSpawn` structure

```python
class TestPersistOnSpawn:
    """VMAG-10: /agent spawn creates persisted V4 node; terminal finalized."""

    async def test_spawn_creates_node_file(self, tmp_path, scripted_multiagent_provider):
        # Setup root + manager + attach
        # Invoke spawn tool
        # Assert: node file exists under .voss/sessions/<root_id>/
        # Assert: parent_run_id == root.id
        # Assert: envelope["limit"] == allotment

    async def test_gather_finalizes_node(self, tmp_path, scripted_multiagent_provider):
        # Spawn + gather
        # Assert: terminal_state is not None on disk
        # Assert: exit_reason == "done"

    async def test_tree_reconstructs_from_disk(self, tmp_path, scripted_multiagent_provider):
        # Spawn 2 children + gather
        # Discard in-memory references
        # Reload from disk via _load_nodes_from_disk
        # Assert: root + 2 children reconstructable from parent_run_id chain
```

---

#### `TestChatRootEnvelope` structure

```python
class TestChatRootEnvelope:
    """VMAG-ROOT: root node 60k envelope + carved reserve; exhaustion denies."""

    def test_root_node_created_with_envelope(self, tmp_path):
        # SessionTreeNode.create_root(cwd=tmp_path, limit=60_000)
        # Assert: node file at .voss/sessions/<root_id>/<root_id>.json
        # Assert: envelope["limit"] == 60_000

    async def test_exhaustion_denies_spawn(self, tmp_path, scripted_multiagent_provider):
        # root limit=6_000, reserve=3_000, VIABLE_FLOOR=2_000
        # Spawn until denied
        # Assert: denial string returned (not a crash)
        # Assert: denied string starts with "<denied:"
```

---

#### `TestPersistedRecursion` structure

```python
class TestPersistedRecursion:
    """VMAG-07: depth>1 persisted fan-out; invariant sum+reserve<=parent."""

    async def test_grandchild_node_persisted(self, tmp_path, scripted_multiagent_provider):
        # 3-level: chat root → child → grandchild
        # Assert: grandchild node on disk with parent_run_id == child.id
        # Assert: sum(children limits) + reserve <= parent limit at each level

    async def test_viable_floor_terminates_recursion(self, tmp_path, scripted_multiagent_provider):
        # Root with small envelope; spawn until viable-floor denial
        # Assert: no depth constant used (no MAX_DEPTH / DEPTH_LIMIT in multiagent)
        # Assert: denial is budget-structural (even_slice < VIABLE_FLOOR)
```

Use the `_PanelRecordingRenderer` from `test_multiagent_recursion.py:178–204` for panel tracking in recursion tests — copy verbatim as an inner class.

---

#### `TestConcurrentNoOversellChatRoot` structure

```python
class TestConcurrentNoOversellChatRoot:
    """VMAG-ROOT: concurrent spawns cannot oversell the chat root."""

    async def test_concurrent_no_oversell(self, tmp_path, scripted_multiagent_provider):
        # root limit=30_000, reserve=10_000
        # Concurrent asyncio.gather of many spawns
        # Assert: sum of granted allotments + reserve <= root.limit
        # Mirrors TestConcurrency in test_session_tree.py:167-176
```

---

### Migration: `tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance` + `TestNoOversell`

**File to modify:** `tests/harness/test_multiagent_fanout.py`

#### Current assertions to MIGRATE (lines 176–264)

**`TestEvenSplitRebalance::test_even_split_then_rebalance` (lines 183–202)**

Current (M13Allocator direct):
```python
allocator = multiagent.M13Allocator(reserve=reserve)
for h in handles:
    await allocator.allocate(h)
snap = allocator.snapshot()
for h in handles:
    assert snap[h] == pytest.approx(reserve // len(handles), rel=0.05)
```

V8 migration target — test V4-backed even-split via `attach_multiagent_tools`:
```python
# Test via the tool surface: spawn N children, assert allotments are even-split
# Root with known limit; reserve carved; spawn 3 children; check allotments
root = SessionTreeNode.create_root(cwd=tmp_path, limit=60_000)
chat_tree = SessionTreeManager(root, reserve=0, cwd=tmp_path)
tools: dict = {}
multiagent.attach_multiagent_tools(
    tools, ..., node_manager=chat_tree
)
h1 = await tools["subagent_spawn"].invoke(agent="child-a", task="t1")
h2 = await tools["subagent_spawn"].invoke(agent="child-b", task="t2")
h3 = await tools["subagent_spawn"].invoke(agent="child-c", task="t3")
# Parse allotment from spawn return strings (budget=<N>)
# Assert each allotment ≈ root.limit // 3
```

NOTE: After gather+release, budget freed for the next spawn is NOT a live allotment update (Pitfall 3 in RESEARCH). Migrate the "survivor allotment strictly increases" assertion to: "after child-a gather, a new spawn gets a larger even slice." Drop the `xfail` marker.

---

**`TestNoOversell::test_concurrent_allocation_never_oversells` (lines 219–234)**

Current:
```python
allocator = multiagent.M13Allocator(reserve=reserve)
await asyncio.gather(*[allocator.allocate(h) for h in many])
total = sum(allocator.snapshot().values())
assert total <= reserve
granted = len(allocator.snapshot())
assert granted == reserve // multiagent.M13Allocator.VIABLE_FLOOR or (...)
```

V8 migration target — test `SessionTreeManager.allocate_child` concurrency:
```python
# Mirrors TestConcurrency in test_session_tree.py:167-176
root = SessionTreeNode.create_root(cwd=tmp_path, limit=30_000 + 100)
mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
# Many concurrent allocations; sum of granted ≤ root.limit - reserve
results = await asyncio.gather(
    *[mgr.allocate_child(VIABLE_FLOOR) for _ in range(64)],
    return_exceptions=True
)
granted = [r for r in results if isinstance(r, SessionTreeNode)]
total = sum(c.envelope["limit"] for c in granted)
assert total <= root.envelope["limit"] - mgr._reserve
```

The `multiagent.M13Allocator.VIABLE_FLOOR` reference must be replaced with `multiagent.DEFAULT_VIABLE_FLOOR` (or `multiagent.VIABLE_FLOOR`). Drop the `xfail` marker.

---

### Migration: `tests/harness/test_multiagent_recursion.py::TestDepth2`

**File to modify:** `tests/harness/test_multiagent_recursion.py`

#### `TestDepth2::test_nested_budget_is_strictly_bounded` (lines 51–65)

Current (M13Allocator direct, in-memory):
```python
parent = multiagent.M13Allocator(reserve=parent_reserve)
await parent.allocate("child-a")
child_slice = parent.snapshot()["child-a"]
child = multiagent.M13Allocator(reserve=child_slice)
await child.allocate("grandchild")
grandchild_slice = child.snapshot()["grandchild"]
assert grandchild_slice <= child_slice <= parent_reserve
```

V8 migration target — V4-backed, persisted:
```python
# Use SessionTreeManager per-node pattern
root = SessionTreeNode.create_root(cwd=tmp_path, limit=60_000)
root_mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
child = await root_mgr.allocate_child(30_000)  # even split of root
child_mgr = SessionTreeManager(child, reserve=0, cwd=tmp_path)
grandchild = await child_mgr.allocate_child(15_000)
assert grandchild.envelope["limit"] <= child.envelope["limit"] <= root.envelope["limit"]
# Also assert disk persistence
nodes = _load_nodes_from_disk(tmp_path, root.id)
assert child.id in nodes
# grandchild persisted under child's root_id (per-node manager)
```

Drop the `xfail` marker.

---

#### `TestDepth2::test_three_distinct_panels_then_clean_teardown` (lines 67–301)

This test uses the REAL `attach_multiagent_tools` recursion path (already using real tool surface per M13-05 correction). The only change is:
1. Drop the `xfail` marker (test is green from V8 onward).
2. The tool invocation path is unchanged — the provider, renderer, and assertion structure stay exactly the same.
3. The `node_manager=` parameter replaces `allocator=None` in the `attach_multiagent_tools` call (lines 241–250).

`TestBackCompatRecursionPinIntact` (lines 304–358) — **UNCHANGED** (byte-stable).

---

## Shared Patterns

### Session-Tree Disk Helpers
**Source:** `tests/harness/test_session_tree.py` lines 59–73
**Apply to:** `test_multiagent_session_tree.py` (copy verbatim as module-level helpers)
```python
def _sessions_tree_dir(cwd: Path, root_id: str) -> Path:
    return cwd / ".voss" / "sessions" / root_id

def _node_path(cwd: Path, root_id: str, node_id: str) -> Path:
    return _sessions_tree_dir(cwd, root_id) / f"{node_id}.json"

def _load_nodes_from_disk(cwd: Path, root_id: str) -> dict[str, dict]:
    tree_dir = _sessions_tree_dir(cwd, root_id)
    nodes: dict[str, dict] = {}
    for path in tree_dir.glob("*.json"):
        data = json.loads(path.read_text())
        nodes[data["id"]] = data
    return nodes
```

### `finalize_node` Idempotent Pattern
**Source:** `voss/harness/session_tree.py` lines 115–133
**Apply to:** `multiagent.py` (subagent_gather, _teardown_orphans), `cli.py` (session finally)
```python
# Always guard with `if h.node is not None:` before calling finalize_node
# finalize_node is already idempotent (node._finalized guard at line 123)
if h.node is not None:
    finalize_node(h.node, exit_reason="done"|"error"|"interrupt",
                  final=h.result or "", cwd=cwd)
```

### `asyncio.Lock` No-Oversell Pattern
**Source:** `voss/harness/session_tree.py` lines 194–225 (`allocate_child`)
**Apply to:** Even-split check in `subagent_spawn` (multiagent.py)
- All check-and-allocate logic must be inside a single `async with self._lock:` block.
- Never hold the lock across `create_task` — lock only for the budget math.

### Per-Turn vs. Per-Session Scoping
**Source:** `voss/harness/cli.py` lines 2019–2028 (`attach_multiagent_tools` call position)
**Apply to:** Chat root creation in `_run_repl`
- `attach_multiagent_tools` is called ONCE per `_run_repl` (session-scoped, outside the turn loop).
- `SessionTreeNode.create_root` + `SessionTreeManager` MUST follow the same pattern — created at `_run_repl` level, NOT inside the per-turn dispatch or per-turn `run_turn` call (Pitfall 4 in RESEARCH).

### Test Class Non-xfail Convention
**Source:** `tests/harness/test_multiagent_fanout.py::TestOrphanTeardown` (line 284 — no `xfail`)
**Apply to:** All V8 test classes in `test_multiagent_session_tree.py`
- New V8 tests are GREEN-from-wave-0 (not scaffolded as xfail). They must be hard gates.
- Migrated `TestEvenSplitRebalance`, `TestNoOversell`, `TestDepth2` — drop `xfail` markers once migrated.

### Viable-Floor Denial String Convention
**Source:** `voss/harness/multiagent.py` lines 349–351
**Apply to:** `subagent_spawn` even-split check in V8
```python
return f"<denied: budget below viable floor — cannot spawn {agent!r}>"
```

### No Depth Constant Invariant
**Source:** `tests/harness/test_multiagent_recursion.py::TestBackCompatRecursionPinIntact` (lines 304–358)
**Apply to:** All V8 changes to `multiagent.py` and `session_tree.py`
- VIABLE_FLOOR and DEFAULT_VIABLE_FLOOR are budget constants — NOT depth constants.
- Names `MAX_DEPTH`, `DEPTH_LIMIT`, `RECURSION_LIMIT` must NOT appear in `subagents.py`.
- `VIABLE_FLOOR` goes in `multiagent.py` or `session_tree.py`, never in `subagents.py`.

---

## No Analog Found

No files in this phase lack an analog. All patterns have direct sources in the existing codebase.

---

## Anti-Pattern Catalog (from RESEARCH)

| Anti-Pattern | Where It Bites | Correct Pattern |
|---|---|---|
| Hold lock across `create_task` | `subagent_spawn` even-split block | Release lock before `allocate_child`; use `BudgetAllocationError` as authoritative guard |
| Finalized children stay in `_children` | `SessionTreeManager.allocate_child` available calc | Add `release_child(node_id)` + call from gather/teardown |
| Per-turn `create_root` | `_run_repl` call position | `create_root` at `_run_repl` entry, NOT inside turn loop |
| `finalize_node` omitted on cancel in `_teardown_orphans` | Orphan nodes stay open on disk | `if h.node is not None: finalize_node(..., exit_reason="interrupt")` |
| `VIABLE_FLOOR` in `subagents.py` | Breaks `test_subagent_recursion.py::test_no_module_level_depth_constant` | Keep in `multiagent.py` or `session_tree.py` only |
| `allocator=` call site not updated in `cli.py` | `TypeError` on V8 boot | Update `cli.py:2019` to `node_manager=_chat_tree` simultaneously with signature change |

---

## Metadata

**Analog search scope:** `voss/harness/`, `tests/harness/`
**Files read:** 8 source files + 2 planning docs
**Pattern extraction date:** 2026-06-06
