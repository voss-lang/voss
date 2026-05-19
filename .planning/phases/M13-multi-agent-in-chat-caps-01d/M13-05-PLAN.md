---
phase: M13-multi-agent-in-chat-caps-01d
plan: 05
type: execute
wave: 3
depends_on: [M13-03]
files_modified:
  - voss/harness/multiagent.py
autonomous: true
requirements: [MAG-06]
must_haves:
  truths:
    - "A child agent can itself invoke subagent_spawn/steer/status/gather (depth > 1) because its toolset re-receives the four M13 tools"
    - "A grandchild's allotment is bounded by its parent-child's slice (grandchild ≤ child slice ≤ parent reserve at every nesting level)"
    - "Recursive spawns are denied solely by the viable-budget-floor — no depth/max_depth/MAX_DEPTH/DEPTH_LIMIT/RECURSION_LIMIT constant exists anywhere"
    - "A depth-2 fan-out (parent → child → grandchild) mounts 3 distinct SubAgentPanel ids concurrently and all 3 collapse cleanly (zero panels leak after gather)"
    - "tests/harness/test_subagent_recursion.py passes unmodified (subagents.py byte-stable; no depth guard introduced)"
  artifacts:
    - path: "voss/harness/multiagent.py"
      provides: "Recursive child-toolset wiring: per-child slice-scoped sub-M13Allocator handed into the child run_turn toolset via attach_multiagent_tools; fresh uuid4().hex[:12] panel_id per child at every depth"
      contains: "attach_multiagent_tools"
  key_links:
    - from: "voss/harness/multiagent.py (_run_child / child toolset build)"
      to: "voss/harness/multiagent.py (attach_multiagent_tools on the child toolset with the child's sub_allocator + a fresh child-scoped ChildRegistry)"
      via: "recursive attach: child's make_toolset result gets attach_multiagent_tools(..., allocator=child.sub_allocator, registry=<fresh per-child registry>)"
      pattern: "attach_multiagent_tools\\("
    - from: "voss/harness/multiagent.py M13Allocator(reserve=child.allotment)"
      to: "grandchild allotment = child.allotment // n (slice-scoped, never exceeds child slice)"
      via: "sub_allocator constructed with reserve=allotment, viable_floor=allocator.viable_floor"
      pattern: "M13Allocator\\(reserve="
---

<objective>
Make recursive sub-agent spawning (depth > 1, MAG-06) actually work by extending `voss/harness/multiagent.py` so that every spawned child's `run_turn` toolset re-receives the four M13 tools (`subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather`) bound to a **slice-scoped sub-`M13Allocator`** carved from that child's own allotment (D-07), with a **fresh `uuid.uuid4().hex[:12]` panel_id per child at every depth** (Pitfall 5 collision avoidance).

The recursive no-oversell invariant holds for free: each level's allocator only ever divides *its own* reserve, so a grandchild's allotment = `child.allotment // n` ≤ `child.allotment` ≤ parent reserve at every nesting level. Recursion is bounded **exclusively** by the existing viable-floor denial (`M13Allocator.allocate` returns `None` when the even slice drops below `viable_floor`) — there is **no** `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` constant, so the back-compat pinning test `tests/harness/test_subagent_recursion.py` stays green unmodified and `subagents.py` is never touched.

Purpose: Greens MAG-06 — the depth-2 nested-budget + nested-panels + no-leak requirement, which is the recursive arm of the must-not-happen no-oversell guard.
Output: Extended `voss/harness/multiagent.py` (additive recursion wiring only; M13-03's flat fan-out path unchanged) turning `tests/harness/test_multiagent_recursion.py::TestDepth2` green while keeping the M13-02/M13-03 fanout/steer suites and `test_subagent_recursion.py` green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-SPEC.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-CONTEXT.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md

<read_first>
<!-- The executor MUST read these before writing any code. -->

1. `voss/harness/multiagent.py` — the live state after M13-03. This plan EXTENDS it. Read:
   - `M13Allocator` (`__init__(*, reserve, viable_floor)`, `viable_floor` property, `allocate` returning `int | None` on viable-floor denial, idempotent `release`, `_rebalance_locked`, `snapshot`) — created in M13-02, do NOT redefine.
   - `ChildHandle` dataclass — note it already carries a `sub_allocator: "M13Allocator"` field (RESEARCH lines 218-226). M13-03 already constructs `sub_alloc = M13Allocator(reserve=allotment, viable_floor=allocator.viable_floor)` per child (RESEARCH line 248). This plan WIRES that existing `sub_allocator` into the child's toolset; it does not invent a new allocator.
   - `ChildRegistry` (`add`/`get`/`active`/`all`) — created in M13-02.
   - `subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather` and `attach_multiagent_tools(...)` and `PanelBridgeRenderer` and the child-launch coroutine (`_run_child` or equivalent helper) — created in M13-03. This plan modifies the child-toolset build inside that helper ONLY.

2. `voss/harness/subagents.py` lines 76-103 (`run_subagent` analog) and 106-135 (`attach_subagent_tool` parameter list `registry, cwd, renderer, provider, model, gate, cognition`) — DO NOT EDIT this file; it is the byte-stable back-compat anchor. Read only to mirror the `make_toolset(cwd, renderer=...)` + `attach_*` shape.

3. `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-RESEARCH.md`:
   - Pattern 1 (lines 207-255) — the non-blocking spawn body M13-03 built; line 248 `sub_alloc = M13Allocator(reserve=allotment, viable_floor=allocator.viable_floor)` and line 249 `_run_child(agent, task, queue, bridge, allotment, sub_alloc, ...)` are the exact recursion seam this plan completes.
   - Pattern 2 (lines 257-307) and §"Recursive no-oversell (MAG-06 / D-07)" (line 305) — why per-level `reserve` division makes the invariant hold; no `max_depth` constant.
   - Flow diagram lines 145-166 — "child may itself call subagent_spawn → slice-scoped sub-M13Allocator (D-07)".
   - Pitfall 5 (lines 511-516) — fresh `uuid.uuid4().hex[:12]` handle == `panel_id` per child at EVERY depth; grandchildren get handles from the *child's* registry; assert 3 distinct ids + zero leak.
   - "Adding `depth`/`max_depth`/`MAX_DEPTH`" anti-pattern (line 442) and Reserve source (line 669) — viable-floor is the ONLY recursion bound; floor < `reserve // expected_fanout`.

4. `tests/harness/test_subagent_recursion.py` (entire file, ~56 lines) — the back-compat pinning test. Confirm the forbidden tokens it asserts absent on the `voss.harness.subagents` module: `run_subagent` has no `depth`/`max_depth` parameter; `subagents` has no `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` attribute. This plan must add NONE of those tokens to `multiagent.py` either (project rule: forbidden project-wide so harness/test consistency holds).

5. `tests/harness/test_multiagent_recursion.py` — the Wave-0 RED scaffold authored by M13-01. This is the contract this plan greens (`TestDepth2`). Read its asserts (3 distinct concurrent `panel_id`s; grandchild allotment ≤ child slice ≤ parent reserve at all 3 levels; zero `SubAgentPanel` after gather). Do not modify the test; satisfy it.
</read_first>

<interfaces>
<!-- Contracts already established by M13-02 / M13-03 in voss/harness/multiagent.py. -->
<!-- Executor uses these directly — they exist after the M13-03 dependency completes. -->

M13Allocator (M13-02):
  __init__(self, *, reserve: int, viable_floor: int) -> None
  @property viable_floor(self) -> int
  async allocate(self, handle: str) -> int | None      # None == viable-floor denial (recursion bound)
  async release(self, handle: str) -> None              # idempotent via _credited_finished set
  snapshot(self) -> dict[str, int]                      # handle -> current allotment

ChildHandle (M13-02, dataclass — mutable):
  handle: str
  task: asyncio.Task
  queue: asyncio.Queue
  panel_id: str            # == handle (Pitfall 5: fresh uuid4().hex[:12] per child every depth)
  allotment: int
  sub_allocator: "M13Allocator"   # already M13Allocator(reserve=allotment, viable_floor=parent.viable_floor)
  done: bool = False
  result: str | None = None

ChildRegistry (M13-02):
  add(h: ChildHandle) -> None
  get(handle: str) -> ChildHandle | None
  active(self) -> list[ChildHandle]
  all(self) -> list[ChildHandle]

attach_multiagent_tools (M13-03) — parameter list MIRRORS subagents.attach_subagent_tool:
  attach_multiagent_tools(tools, *, registry, cwd, renderer, provider, model, gate, cognition=None,
                          allocator: M13Allocator) -> None
  # registers subagent_spawn/steer/status/gather into `tools`, closing over `allocator` + `registry`

Child launch helper (M13-03, working name _run_child) — builds the child toolset via
  make_toolset(cwd, renderer=PanelBridgeRenderer(base_renderer, panel_id=handle))
  and runs run_turn(..., steer_inbox=queue). THIS is where this plan inserts the recursive attach.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire the slice-scoped sub-allocator + fresh per-child panel_id into the recursive child toolset</name>
  <files>voss/harness/multiagent.py</files>
  <action>
Extend ONLY the child-launch helper (`_run_child` or whatever M13-03 named it — read `multiagent.py` to confirm the exact name and signature; it already receives the child's `sub_alloc`/`sub_allocator` argument per RESEARCH line 249).

Inside that helper, after `child_tools = make_toolset(cwd, renderer=PanelBridgeRenderer(base_renderer, panel_id=handle))` (M13-03 line equivalent), add a recursive `attach_multiagent_tools(...)` call that re-registers the four M13 tools onto `child_tools` so the child can itself fan out (D-07). Bind it to:
  - `allocator=` the child's own `sub_allocator` (the slice-scoped `M13Allocator(reserve=child.allotment, viable_floor=parent_allocator.viable_floor)` M13-03 already constructs — pass it through; do NOT construct a new one here and do NOT reuse the parent allocator),
  - `registry=` a FRESH per-child `ChildRegistry()` instance (each nesting level owns its own registry so grandchild handles never collide with sibling/parent handles and `subagent_gather` at a given level only awaits that level's children),
  - the same `cwd`, `provider`, `model`, `gate`, `cognition` already threaded into the child, and a `renderer=` that is the child's `PanelBridgeRenderer` base (so a grandchild's `subagent_spawn` mounts its OWN panel via a fresh handle).

Implement the per-child fresh panel_id rule explicitly (Pitfall 5): every `subagent_spawn` invocation — at ANY depth — must mint `handle = uuid.uuid4().hex[:12]` and use that same value as the child's `panel_id`. Confirm the M13-03 `subagent_spawn` body already does `handle = uuid.uuid4().hex[:12]; panel_id = handle` (RESEARCH lines 240-245); because each recursive `attach_multiagent_tools` closes over its own fresh `ChildRegistry`, a grandchild spawned by a child gets a brand-new uuid handle/panel_id distinct from the child's — no DOM id collision (`#panel-body-{parent_id}`, sub_agent_panel.py:57-59). If M13-03's spawn body shares any handle/panel_id state across the closure, fix it so the uuid mint is per-invocation, not per-attach.

Recursive no-oversell holds structurally and requires NO new accounting: the child's `sub_allocator` has `reserve = child.allotment`, so a grandchild's `allocate()` returns `child.allotment // n` (≤ `child.allotment` ≤ parent reserve). When that even slice falls below `viable_floor`, `allocate()` returns `None` and `subagent_spawn` returns the existing `<denied: budget below viable floor …>` string — this denial is the SOLE recursion bound (D-07). Do NOT add, reference, import, or define ANY of: `depth`, `max_depth`, `MAX_DEPTH`, `DEPTH_LIMIT`, `RECURSION_LIMIT`, a depth counter, a nesting-level parameter, or a stack-depth check — anywhere in `multiagent.py`. (Forbidden project-wide: `tests/harness/test_subagent_recursion.py` pins their absence on `subagents`, and the harness/test consistency rule extends the ban to `multiagent.py`.)

Hard constraints (additive only — do not regress M13-03):
  - Do NOT edit `voss/harness/subagents.py`, `agent.py`, `cli.py`, or any TUI file. This plan touches `voss/harness/multiagent.py` only.
  - Do NOT change `M13Allocator`, `ChildHandle`, `ChildRegistry`, `PanelBridgeRenderer`, the `steer_inbox` drain, or the flat-fanout `subagent_spawn`/`steer`/`status`/`gather` tool bodies beyond the minimal recursive-attach insertion (and the per-invocation uuid fix if M13-03 left handle/panel_id at attach scope).
  - The child's `subagent_gather` must await only ITS fresh registry's children (level-local gather) and `release()` on its own `sub_allocator` — never the parent allocator/registry. This keeps the exactly-once rebalance and Σ ≤ reserve invariant per level.
  - Keep `subagents.py` byte-stable: run a git diff check and confirm zero changes outside `multiagent.py`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "import ast,sys; src=open('voss/harness/multiagent.py').read(); toks=('max_depth','MAX_DEPTH','DEPTH_LIMIT','RECURSION_LIMIT'); body='\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#')); sys.exit(1 if any(t in body for t in toks) or ('depth' in body) else 0)" && pytest tests/harness/test_multiagent_recursion.py::TestDepth2 -x -q && pytest tests/harness/test_subagent_recursion.py -x -q && git diff --name-only -- voss/harness/subagents.py voss/harness/agent.py voss/harness/cli.py | grep -q . && echo "UNEXPECTED EDIT" && exit 1 || echo OK</automated>
  </verify>
  <done>
`tests/harness/test_multiagent_recursion.py::TestDepth2` is green: a depth-2 parent→child→grandchild fan-out mounts 3 distinct `panel_id`s concurrently, grandchild allotment ≤ child slice ≤ parent reserve at all 3 levels, and zero `SubAgentPanel` remain after gather. `tests/harness/test_subagent_recursion.py` passes unmodified. `git diff` shows changes ONLY in `voss/harness/multiagent.py`. Grep over non-comment lines of `multiagent.py` finds zero occurrences of `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Regression-pin the flat fanout/steer suites + back-compat anchor green under the recursion change</name>
  <files>voss/harness/multiagent.py</files>
  <action>
No new production code unless a regression is found. Run the M13-02/M13-03 suites to prove the recursive-attach insertion did not regress the flat (depth-1) path or the byte-stable back-compat anchors:
  - `tests/harness/test_multiagent_fanout.py` (MAG-01/03/04: concurrency overlap, even-split rebalance, no-oversell race, exactly-once release) MUST stay green — the recursive attach must not perturb the top-level allocator/registry.
  - `tests/harness/test_multiagent_steer.py` (MAG-05 correction-vs-control) MUST stay green — the child `steer_inbox` queue and drain are untouched by this plan.
  - `tests/harness/test_subagent_recursion.py` MUST stay green unmodified (re-assert; this is the must-not-happen guard that no depth constant slipped in).
  - Full harness merge gate `pytest tests/harness/ -x -q` to catch any cross-file fallout from the `multiagent.py` extension.

If any of these regress, the fault is in Task 1's recursive-attach insertion (most likely: a grandchild-level `subagent_gather` reaching the parent allocator/registry, a shared `ChildRegistry` instance across attach calls, or a handle/panel_id minted at attach scope instead of per-spawn-invocation). Fix it in `multiagent.py` by making the per-child registry/sub_allocator strictly level-local and the uuid mint strictly per-`subagent_spawn`-call. Do NOT relax any test, do NOT add a depth guard, do NOT edit `subagents.py`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py tests/harness/test_multiagent_recursion.py tests/harness/test_subagent_recursion.py -x -q && pytest tests/harness/ -x -q</automated>
  </verify>
  <done>
`tests/harness/test_multiagent_fanout.py`, `tests/harness/test_multiagent_steer.py`, `tests/harness/test_multiagent_recursion.py`, and `tests/harness/test_subagent_recursion.py` all pass; the full `pytest tests/harness/ -x -q` merge gate is green. No test files were modified; no depth constant exists in `multiagent.py`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| parent agent → child agent (recursive) | A child agent (already a trusted local agent) invokes `subagent_spawn` to launch a grandchild. The untrusted vector is an LLM-driven plan that *always* emits `subagent_spawn`, attempting unbounded recursive growth. No new network/disk/secret surface — in-memory orchestration of an already-trusted local agent (M13-VALIDATION §"Security Domain"). |
| child allocator → child sub-allocator | Budget reserve is subdivided across nesting levels; the tampering vector is a level over-allocating beyond its own slice (recursive oversell). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M13-recursion-DoS | Denial of Service | `multiagent.py` recursive `attach_multiagent_tools` → child `subagent_spawn` → `M13Allocator.allocate` | mitigate | Recursion is bounded SOLELY by the viable-budget-floor: a child's `sub_allocator` has `reserve = child.allotment`; a grandchild's even slice = `child.allotment // n`; when that drops below `viable_floor`, `allocate()` returns `None` and `subagent_spawn` returns `<denied: budget below viable floor …>` — the spawn never happens. The reserve strictly shrinks at each level (`allotment ≤ parent reserve`), so the floor is reached in O(log) depth and Python-stack OOM/RecursionError is structurally impossible for budget-respecting plans. Mitigation is verified by `test_multiagent_recursion.py::TestDepth2` (grandchild ≤ child slice ≤ parent reserve at all 3 levels) and the no-oversell race in `test_multiagent_fanout.py::TestNoOversell`. NO `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` constant is used — a depth cap would break `test_subagent_recursion.py` (the pinning test asserting recursion stays floor-bounded, not depth-bounded). |
| T-M13-oversell | Tampering | per-level `M13Allocator` (`reserve`/`_active`/`_credited_finished`) | mitigate | Each nesting level's allocator divides ONLY its own reserve; the child's `sub_allocator` is constructed with `reserve = child.allotment` (≤ parent reserve), so Σ(grandchild allotments) ≤ child.allotment ≤ parent reserve transitively at every depth. The existing `asyncio.Lock` check-and-allocate (M13-02, O1-proven) makes the per-level guard race-safe; `_credited_finished` keeps rebalance exactly-once. This plan adds NO accounting — the invariant holds structurally from per-level reserve division. Verified by `test_multiagent_recursion.py::TestDepth2` and `test_multiagent_fanout.py::TestNoOversell` (Σ ≤ R under racing recursive spawns). |
| T-M13-recursion-orphan | Denial of Service | child-level `ChildRegistry` + level-local `subagent_gather` | mitigate | Each nesting level owns a FRESH `ChildRegistry`; a level's `subagent_gather` awaits only its own registry's children and releases on its own `sub_allocator` — grandchild tasks cannot orphan a parent-level gather, and a finished level's panels collapse via the existing M9-08 `app.collapse_subagent` path. Verified by `test_multiagent_recursion.py::TestDepth2` post-gather assertion (zero `SubAgentPanel` mounted across all 3 levels). |
| T-M13-panelid-collision | Tampering | `SubAgentPanel` DOM ids (`#panel-body-{parent_id}`, sub_agent_panel.py:57-59) | mitigate | Every `subagent_spawn` at every depth mints a fresh `uuid.uuid4().hex[:12]` handle used as the `panel_id` (Pitfall 5); grandchildren draw handles from the child's own registry. Distinct ids prevent `DuplicateIds` Textual errors and wrong-panel `update_subagent`/`collapse_subagent` matches. Verified by `test_multiagent_recursion.py::TestDepth2` (3 distinct concurrent `panel_id`s, all collapse cleanly). |
| T-M13-priv | Elevation of Privilege | child/grandchild toolset construction | accept | Each recursive child reuses the SAME parent `PermissionGate` (`gate=` threaded unchanged through `attach_multiagent_tools`, identical posture to existing `run_subagent`). A grandchild gets no broader scope than its parent. No new privilege surface; same as the already-shipped flat path. |
| T-M13-SC | Tampering | npm/pip/cargo installs | accept | No package-manager installs in this plan — additive edit to one existing in-repo module (`voss/harness/multiagent.py`); no new dependencies. M13-VALIDATION confirms M13 adds no auth/session/crypto/network/persistence surface. |
</threat_model>

<verification>
- `pytest tests/harness/test_multiagent_recursion.py::TestDepth2 -x -q` is green (MAG-06: depth-2 nested budget + nested panels + no-leak).
- `pytest tests/harness/test_subagent_recursion.py -x -q` passes UNMODIFIED (back-compat pinning test — no depth guard introduced).
- `pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py -x -q` stay green (M13-02/M13-03 not regressed by the recursion wiring).
- `pytest tests/harness/ -x -q` full harness merge gate green (per M13-VALIDATION per-wave sampling: `pytest tests/harness/ -x -q && pytest tests/harness/test_subagent_recursion.py -x -q`).
- `git diff --name-only` shows changes ONLY in `voss/harness/multiagent.py` (`subagents.py`/`agent.py`/`cli.py`/TUI byte-stable).
- Non-comment-line grep of `voss/harness/multiagent.py` finds zero `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT`.
</verification>

<success_criteria>
- A child agent's toolset re-receives `subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather` bound to its own slice-scoped `sub_allocator` and a fresh level-local `ChildRegistry` (D-07 recursion enabled).
- A grandchild's allotment = `child.allotment // n` ≤ `child.allotment` ≤ parent reserve, verified at all 3 levels by `TestDepth2`.
- Recursion is bounded exclusively by viable-floor denial; no depth constant exists anywhere in `multiagent.py`.
- Depth-2 fan-out mounts 3 distinct `panel_id`s concurrently and all collapse cleanly (zero leaked `SubAgentPanel`).
- `tests/harness/test_subagent_recursion.py` and the M13-02/M13-03 fanout+steer suites stay green; `subagents.py` is byte-stable.
- MAG-06 satisfied (rolls up into the M13-06 headline e2e).
</success_criteria>

<output>
Create `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-05-SUMMARY.md` when done.
</output>
