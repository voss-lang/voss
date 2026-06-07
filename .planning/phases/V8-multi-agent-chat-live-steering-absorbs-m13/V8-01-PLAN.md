---
phase: V8-multi-agent-chat-live-steering-absorbs-m13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/test_multiagent_session_tree.py
autonomous: true
requirements: [VMAG-10, VMAG-UNIFY, VMAG-07, VMAG-ROOT]
must_haves:
  truths:
    - "A /agent spawn creates a persisted V4 session-tree node under the chat root"
    - "A child-of-child spawn persists as a nested node; the invariant holds at every level"
    - "The chat session has a persisted root node with a default envelope (60k) + reserve; exhaustion denies further spawns"
    - "Concurrent chat spawns cannot oversell the chat root"
  artifacts:
    - path: "tests/harness/test_multiagent_session_tree.py"
      provides: "RED test classes driving the V8 planned surface (TestPersistOnSpawn/TestUnifiedAllocator/TestPersistedRecursion/TestViableFloorTermination/TestChatRootEnvelope/TestConcurrentNoOversellChatRoot)"
      contains: "class TestPersistOnSpawn"
  key_links:
    - from: "tests/harness/test_multiagent_session_tree.py"
      to: "voss.harness.multiagent.attach_multiagent_tools(node_manager=...)"
      via: "tool-surface invocation against the V4-backed allocation path"
      pattern: "node_manager="
---

<objective>
Lay the Wave 0 RED scaffold for V8: a NEW test file `tests/harness/test_multiagent_session_tree.py` whose six classes drive the REAL planned V8 surface (persisted spawns, unified V4 allocation, recursive persisted fan-out, viable-floor termination, chat-root envelope, concurrent no-oversell). These tests are RED now (the V8 surface — `node_manager=` parameter, `ChildHandle.node`, `release_child`, persisted child nodes — does not exist yet) and GREEN after V8-02 implements it.

Purpose: Per V8-VALIDATION.md, every V8 task traces to a test row. This file is the Nyquist feedback substrate for VMAG-10/UNIFY/07/ROOT. The tests are written against the V4-backed `attach_multiagent_tools(node_manager=...)` contract V8-02 will deliver — NOT against a fictional API. Per memory `gsd-scaffold-fictional-api`, there is NO `xfail(strict=False)` masking: tests are plain assertions that fail loudly until V8-02 lands.

Output: One new test file with six test classes + module-level disk helpers + a copied `_NullRenderer`, reusing the existing `scripted_multiagent_provider` conftest fixture.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-SPEC.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-VALIDATION.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-PATTERNS.md

<interfaces>
<!-- The V4 session-tree surface the tests assert against (verified on disk 2026-06-06). -->

From voss/harness/session_tree.py:
- `SessionTreeNode.create_root(*, cwd: Path, limit: int) -> SessionTreeNode` — writes `.voss/sessions/<root_id>/<root_id>.json`; envelope `{"limit": limit, "spent": 0}`; `parent_run_id=None`; `root_id == id`.
- `SessionTreeManager(root_node, *, reserve: int, cwd: Path)` — `.allocate_child(limit, *, scope=None, role=None) -> SessionTreeNode` (async, asyncio.Lock, raises `BudgetAllocationError` when `limit > root.limit - reserve - sum(active children limits)`). On allocate, child gets `root_id=self._root.id`, `parent_run_id=self._root.id`, persisted file.
- `finalize_node(node, *, exit_reason: str, final: str = "", cwd: Path)` — idempotent; writes `terminal_state={"exit_reason", "final"}`; `exit_reason` must be in `EXIT_REASONS` (already contains done/interrupt/error/budget/timeout/killed).
- `export_tree(root_id, cwd) -> {"root_id", "nodes": [...]}` — exists on disk; reads `.voss/sessions/<root_id>/*.json`.
- `BudgetAllocationError` — raised on oversell.

From voss/harness/multiagent.py (V8-02 TARGET surface — does NOT exist yet, tests drive it):
- `attach_multiagent_tools(tools, *, registry, cwd, renderer, provider, model, gate, cognition=None, node_manager: SessionTreeManager | None = None)` — parameter RENAMED from `allocator` to `node_manager` in V8-02.
- `ChildHandle` gains `node: Any = None` (last field).
- `DEFAULT_PARENT_RESERVE = 30_000`, `DEFAULT_VIABLE_FLOOR = 2_000`, and a `VIABLE_FLOOR` alias — module-level constants kept.
- Tools registered: `subagent_spawn`, `subagent_steer`, `subagent_status`, `subagent_gather`. Invoke via `tools["subagent_spawn"].invoke(agent=..., task=...)`.

From tests/harness/conftest.py (existing fixture — reuse, do not recreate):
- `scripted_multiagent_provider` fixture → factory with `.provider(role) -> ScriptedMultiAgentProvider`, `.scripts: dict[role -> list[stream]]`, builders `spawn_plan(children, *, rationale, final)`, `steer_plan(handle, guidance)`, `gather_plan(handles, *, final)`, `done_plan(final, *, rationale)`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Module helpers + RED tests for persist/unify/root (TestPersistOnSpawn, TestUnifiedAllocator, TestChatRootEnvelope, TestConcurrentNoOversellChatRoot)</name>
  <files>tests/harness/test_multiagent_session_tree.py</files>
  <read_first>
    - `tests/harness/test_session_tree.py` lines 59-73 (the `_sessions_tree_dir`/`_node_path`/`_load_nodes_from_disk` disk helpers) and lines 167-176 (`TestConcurrency` no-oversell pattern) — copy the helper functions verbatim as module-level functions.
    - `tests/harness/test_multiagent_fanout.py` lines 24-33 (`_NullRenderer` — copy verbatim), lines 57-60 (fixture wiring), and the `attach_multiagent_tools(...)` call pattern + `tools["subagent_spawn"].invoke(...)` tool invocation.
    - `tests/harness/conftest.py` lines 314-449 (the `scripted_multiagent_provider` fixture API — `provider(role)`, `scripts`, `spawn_plan`/`gather_plan`/`done_plan`).
    - V8-PATTERNS.md sections "test_multiagent_session_tree.py (test — CREATE)" (lines 503-703) — the file header, helpers, fixture usage, `_NullRenderer`, `attach_multiagent_tools` node_manager call pattern, persisted-node assertions, and the `TestPersistOnSpawn`/`TestChatRootEnvelope`/`TestConcurrentNoOversellChatRoot` class structures.
    - V8-RESEARCH.md "Research Focus Area 5: Actual Test Surface Reality" (the new-tests table) + "Research Focus Area 4: Persistence Wiring".
  </read_first>
  <action>
    Create `tests/harness/test_multiagent_session_tree.py`. Module docstring lists the six VMAG-tagged classes. `from __future__ import annotations`; import `asyncio`, `json`, `pathlib.Path`, `pytest`. Copy the three disk helpers (`_sessions_tree_dir`, `_node_path`, `_load_nodes_from_disk`) verbatim from test_session_tree.py:59-73. Copy `_NullRenderer` verbatim from test_multiagent_fanout.py:24-33.

    Write a module-level helper `_attach(tools, *, provider_factory, cwd, node_manager)` that calls `multiagent.attach_multiagent_tools(tools, registry=multiagent.SubagentRegistry(), cwd=cwd, renderer=_NullRenderer(), provider=provider_factory.provider("root"), model="stub", gate=None, cognition=None, node_manager=node_manager)` — this is the canonical V8 invocation (note `node_manager=`, not `allocator=`). Add a small `_parse_budget(spawn_return: str) -> int` helper that extracts the integer from the `budget=<N>` token in a `subagent_spawn` return string.

    Implement four classes (all plain async/sync tests — NO `pytest.mark.xfail`; these are GREEN-from-wave-0 hard gates per V8-PATTERNS "Test Class Non-xfail Convention"):

    `TestPersistOnSpawn` (VMAG-10): (a) `test_spawn_creates_node_file` — create root via `SessionTreeNode.create_root(cwd=tmp_path, limit=60_000)`, build a `SessionTreeManager(root, reserve=30_000, cwd=tmp_path)`, `_attach`, script the spawned role's provider with `done_plan`, invoke `subagent_spawn(agent="child-a", task="t")`, then assert a node file for the new child exists under `_sessions_tree_dir(tmp_path, root.id)` with `parent_run_id == root.id` and `envelope["limit"] > 0`. (b) `test_gather_finalizes_node` — spawn then `subagent_gather()`, assert the child's on-disk `terminal_state is not None` and `terminal_state["exit_reason"] == "done"`. (c) `test_tree_reconstructs_from_disk` — spawn 2 children + gather, then drop in-memory refs and reload via `_load_nodes_from_disk(tmp_path, root.id)`; assert root + 2 children are present and each child's `parent_run_id == root.id` (the chain reconstructs without the chat transcript).

    `TestUnifiedAllocator` (VMAG-UNIFY): (a) `test_no_m13allocator_attribute` — assert `not hasattr(multiagent, "M13Allocator")` (the in-memory allocator is removed by V8-02). (b) `test_spawn_allocates_via_v4_manager` — after a spawn, assert the `node_manager._children` list (the V4 manager) holds the allocated child node, proving allocation went through V4, not a separate in-memory system.

    `TestChatRootEnvelope` (VMAG-ROOT): (a) `test_root_node_created_with_envelope` — `create_root(cwd=tmp_path, limit=60_000)`; assert file at `_node_path(tmp_path, root.id, root.id)` and `envelope["limit"] == 60_000`. (b) `test_exhaustion_denies_spawn` — root `limit=6_000`, `SessionTreeManager(root, reserve=3_000, cwd=tmp_path)`, viable-floor 2_000; spawn repeatedly until a `subagent_spawn` return string starts with `<denied:`; assert the denial is returned as a string (no exception escapes).

    `TestConcurrentNoOversellChatRoot` (VMAG-ROOT): `test_concurrent_no_oversell` — root `limit=30_000`, `reserve=10_000`; `asyncio.gather` many concurrent `subagent_spawn` invocations; assert `sum(c.envelope["limit"] for c in node_manager._children) + node_manager._reserve <= root.envelope["limit"]`. Mirror test_session_tree.py:167-176.

    Do NOT add any `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` reference. Do NOT use `xfail`. The tests reference the V8-02 surface and WILL fail until V8-02 lands — that is the intended RED state.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - The file `tests/harness/test_multiagent_session_tree.py` exists and is collectible by pytest (no import/collection errors).
    - Running `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestPersistOnSpawn -q` shows FAILURES (RED), failing because `attach_multiagent_tools` does not accept `node_manager=` yet (TypeError) or `ChildHandle.node`/persisted nodes are absent — NOT because of a NameError in the test file itself.
    - `grep -nE 'MAX_DEPTH|DEPTH_LIMIT|RECURSION_LIMIT' tests/harness/test_multiagent_session_tree.py` returns nothing.
    - `grep -c 'xfail' tests/harness/test_multiagent_session_tree.py` returns 0.
    - `grep -c 'node_manager=' tests/harness/test_multiagent_session_tree.py` returns ≥ 1.
  </acceptance_criteria>
  <done>The four persist/unify/root classes are collectible and RED, failing against the missing V8-02 surface (not against test-internal errors). No xfail markers, no depth constants.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: RED tests for recursion (TestPersistedRecursion, TestViableFloorTermination)</name>
  <files>tests/harness/test_multiagent_session_tree.py</files>
  <read_first>
    - The module helpers + `_NullRenderer` + `_attach` written in Task 1 (same file).
    - `tests/harness/test_multiagent_recursion.py` lines 178-204 (the `_PanelRecordingRenderer` inner class — copy verbatim for panel tracking in recursion tests) and the `TestBackCompatRecursionPinIntact` no-depth-constant assertions (the contract V8 must not violate).
    - V8-PATTERNS.md "TestPersistedRecursion structure" (lines 671-688) + "No Depth Constant Invariant" shared pattern (lines 881-886).
    - V8-RESEARCH.md "Research Focus Area 1: Recursive Allocation Mechanism" — the per-node-manager mechanism (a child node becomes a parent via `SessionTreeManager(child_node, reserve=VIABLE_FLOOR, cwd=cwd)`; nested nodes link via `parent_run_id=child_node.id`).
  </read_first>
  <action>
    Append two classes to `tests/harness/test_multiagent_session_tree.py` (both plain, no `xfail`).

    `TestPersistedRecursion` (VMAG-07): (a) `test_grandchild_node_persisted` — drive a 3-level fan-out through the tool surface: chat root → child → grandchild. Script the child role's provider to itself emit a `subagent_spawn` for a grandchild then `gather`, and the grandchild role with `done_plan`. After the top-level gather, glob the session directories under `tmp_path/".voss"/"sessions"` and assert a grandchild node exists whose `parent_run_id == <child node id>` (NOT the chat root id) — i.e. the recursion chains `parent_run_id` per level. Assert the budget invariant at each level: for the child manager, `sum(active children limits) + reserve <= child.envelope["limit"]`, and for the root, `sum(...) + reserve <= root.envelope["limit"]`. Because V8 uses a per-node `SessionTreeManager`, nested nodes persist under their parent node's `root_id` directory; the test must glob across `*/` session dirs (use `(tmp_path/".voss"/"sessions").glob("*/*.json")`) and follow the `parent_run_id` chain — document this in a test comment. (b) `test_invariant_holds_at_each_level` — assert the per-level `sum(children)+reserve <= parent` numerically from the on-disk envelopes.

    `TestViableFloorTermination` (VMAG-07): (a) `test_viable_floor_denies_below_floor` — root with a small envelope (e.g. `limit=5_000`, `reserve=0`, viable floor 2_000): spawning a 3rd child should be denied because `available // n < VIABLE_FLOOR`; assert the denial string. (b) `test_no_module_level_depth_constant` — assert `not hasattr(multiagent, "MAX_DEPTH")`, `not hasattr(multiagent, "DEPTH_LIMIT")`, `not hasattr(multiagent, "RECURSION_LIMIT")`, AND import `voss.harness.subagents` and assert none of those three names exist on it either (the recursion is budget-structural, not depth-bounded). This pins the "no depth constant" property across both modules.

    Copy `_PanelRecordingRenderer` from test_multiagent_recursion.py:178-204 verbatim as an inner helper if the recursion tests need panel-call tracking; otherwise `_NullRenderer` suffices.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestPersistedRecursion tests/harness/test_multiagent_session_tree.py::TestViableFloorTermination -q 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `TestPersistedRecursion` and `TestViableFloorTermination` are collectible and RED (fail against the missing V8-02 `node_manager`/persisted-recursion surface), not against test-internal NameErrors.
    - `test_no_module_level_depth_constant` asserts absence of `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` on BOTH `voss.harness.multiagent` and `voss.harness.subagents`.
    - `grep -c 'xfail' tests/harness/test_multiagent_session_tree.py` still returns 0.
    - The recursion test globs across session directories (`grep -c 'sessions.*glob\|glob.*json' tests/harness/test_multiagent_session_tree.py` returns ≥ 1) and follows `parent_run_id` (`grep -c 'parent_run_id' tests/harness/test_multiagent_session_tree.py` returns ≥ 1).
  </acceptance_criteria>
  <done>Both recursion classes are collectible and RED against the missing V8-02 surface; the no-depth-constant pin covers both multiagent.py and subagents.py; no xfail markers.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q` collects six classes and reports failures (RED) caused by the absent V8-02 surface (TypeError on `node_manager=`, missing `ChildHandle.node`, no persisted child nodes) — NOT collection/NameError failures.
- No `xfail` markers anywhere in the file (memory `gsd-scaffold-fictional-api`: no false-green masking).
- No `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` reference in the file.
- The pre-existing `tests/.../test_multiagent_chat_e2e.py::test_multiagent_chat_e2e` failure is out of scope and must not be touched by this plan.
</verification>

<success_criteria>
- `tests/harness/test_multiagent_session_tree.py` exists with the six VMAG-tagged classes, module disk helpers, copied `_NullRenderer`, and reuse of `scripted_multiagent_provider`.
- All six classes are collectible and RED against the planned V8-02 surface.
- Zero xfail markers; zero depth constants.
</success_criteria>

<output>
Create `.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-01-SUMMARY.md` when done.
</output>
