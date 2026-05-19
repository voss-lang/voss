---
phase: M13-multi-agent-in-chat-caps-01d
plan: 02
type: execute
wave: 1
depends_on: [M13-01]
files_modified:
  - voss/harness/multiagent.py
autonomous: true
requirements: [MAG-03, MAG-04]
must_haves:
  truths:
    - "M13Allocator divides a parent reserve evenly across active children and rebalances when a child finishes"
    - "Total allocated child budget never exceeds the reserve, even under concurrent racing allocations"
    - "A finished child's freed budget is credited exactly once on rebalance (no double-count)"
    - "A spawn is denied (None) when the even slice falls below the viable floor, which bounds recursion without a depth constant"
    - "subagents.py stays byte-stable (the allocator/registry live in a new module)"
  artifacts:
    - path: "voss/harness/multiagent.py"
      provides: "M13Allocator + ChildHandle + ChildRegistry (in-memory, chat-turn-scoped)"
      contains: "class M13Allocator"
      min_lines: 70
  key_links:
    - from: "tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance"
      to: "voss.harness.multiagent.M13Allocator"
      via: "import + allocate/release/snapshot calls"
      pattern: "from voss\\.harness\\.multiagent import"
    - from: "tests/harness/test_multiagent_fanout.py::TestNoOversell"
      to: "voss.harness.multiagent.M13Allocator"
      via: "asyncio.gather over allocate() + double release()"
      pattern: "M13Allocator"
---

<objective>
Create the NEW module `voss/harness/multiagent.py` and land its in-memory foundation: the `M13Allocator` (even-split-of-reserve budget allocator with an `asyncio.Lock` race-safe check-and-allocate, idempotent exactly-once `release`, and viable-floor spawn denial that bounds recursion), the `ChildHandle` dataclass, and the `ChildRegistry` (in-memory, chat-turn-scoped child tracker).

Purpose: This is the pure, unit-testable core that every later M13 wave builds on. The allocator enforces the must-not-happen MAG-04 no-oversell invariant; the registry/handle are the in-memory substrate (no disk — O1 owns persistence). Putting these in a NEW module keeps `subagents.py` byte-stable so the `test_subagent_recursion.py` pinning test stays green.

Output: `voss/harness/multiagent.py` with `M13Allocator`, `ChildHandle`, `ChildRegistry`. Greens the allocator / no-oversell / even-split-rebalance unit classes scaffolded red in M13-01.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

# Phase authority (LOCKED — requirements + HOW)
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-SPEC.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-CONTEXT.md

# Verified code anchors + the allocator reference shape + OQ-A1 resolution material
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-RESEARCH.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md

# Per-phase Nyquist validation map (locks the test class names this plan greens)
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md

# O1 allocator analog — LIFT (copy) the asyncio.Lock check-and-allocate Pattern 2; do NOT import O1
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md

<interfaces>
<!-- Contracts the executor needs. Do not explore the codebase for these. -->

OQ-A1 resolution inputs (M13-RESEARCH.md "Reserve source", lines 669-673; A1 risk row, line 642):
  - Chat `run_turn` (cli.py:1695) passes NO `token_budget` → `_run_turn_exec` uses the
    DEFAULT `token_budget: int = 60_000` at voss/harness/agent.py:419 (VERIFIED this plan:
    line 419 of `async def run_turn(...)` signature is `token_budget: int = 60_000`).
  - M13 must INVENT the reserve (D-05 "a parent reserve is carved"); value is
    Claude's-discretion-adjacent. RESEARCH recommends a fraction of the 60_000 default,
    leaving the parent its own working budget. Viable-floor must be
    < reserve // expected_fanout (sensible default: low-thousands of tokens, enough
    for ≥1 child iteration).

M13Allocator reference shape (LIFTED from O1-PATTERNS Pattern 2 / M13-RESEARCH Pattern 2,
lines 257-303 — copy, do NOT import O1):
```python
import asyncio

class M13Allocator:
    """Even-split-of-reserve, in-memory, chat-turn-scoped. NOT O1 SessionTreeManager."""
    def __init__(self, *, reserve: int, viable_floor: int) -> None:
        self._reserve = reserve
        self._viable_floor = viable_floor
        self._active: dict[str, int] = {}            # handle -> current allotment
        self._lock = asyncio.Lock()
        self._credited_finished: set[str] = set()    # exactly-once rebalance guard

    @property
    def viable_floor(self) -> int: return self._viable_floor

    async def allocate(self, handle: str) -> int | None:
        async with self._lock:                       # D-06 race-safe check-and-allocate
            n = len(self._active) + 1                 # include the new child
            even = self._reserve // n
            if even < self._viable_floor:             # D-07 viable-floor → bounds recursion
                return None                           # caller emits <denied: …>
            self._active[handle] = even
            self._rebalance_locked()                  # even-split existing too
            return self._active[handle]

    async def release(self, handle: str) -> None:
        async with self._lock:
            if handle in self._credited_finished:     # MAG-04 exactly-once
                return
            self._credited_finished.add(handle)
            self._active.pop(handle, None)
            self._rebalance_locked()                  # freed slice → survivors

    def _rebalance_locked(self) -> None:
        if not self._active: return
        even = self._reserve // len(self._active)
        for h in self._active: self._active[h] = even
        # INVARIANT (assert in tests): sum(self._active.values()) <= self._reserve

    def snapshot(self) -> dict[str, int]:
        return dict(self._active)                     # for panel BudgetMeter ticks
```

Imports/dataclass idiom (analog: voss/harness/subagents.py:1-12, 22-27 — mirror style,
NOT frozen for ChildHandle since task/result are mutable):
```python
from __future__ import annotations
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any
```

Handle id scheme (project-wide; matches RunRecorder/SessionRecord; cited
O1-PATTERNS lines 110-120): `uuid.uuid4().hex[:12]`.

Test contract this plan must green (from M13-VALIDATION.md per-task map, scaffolded red
in M13-01; class names are LOCKED):
  - tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance  (MAG-03)
  - tests/harness/test_multiagent_fanout.py::TestNoOversell          (MAG-04)
  - Test posture: pytest 8 + pytest-asyncio `asyncio_mode = "auto"` (pyproject.toml:75 —
    VERIFIED this plan); plain `async def test_...` (no `@pytest.mark.asyncio`);
    class-based; `tests/harness/conftest.py` `isolated_state` autouse fixture applies
    automatically (no declaration needed).

Hard back-compat constraint (M13-PATTERNS "subagents.py MOD — but effectively UNCHANGED";
M13-RESEARCH line 442): NO `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT`
identifier anywhere in this module — recursion is bounded ONLY by the viable-floor `None`
return. `tests/harness/test_subagent_recursion.py` pins absence of those names; it must
stay green unmodified.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Resolve OQ-A1 and create voss/harness/multiagent.py with M13Allocator</name>
  <files>voss/harness/multiagent.py</files>
  <read_first>
    - M13-RESEARCH.md "Reserve source" (lines 669-673) + A1 risk row (line 642) — the OQ-A1 inputs
    - M13-RESEARCH.md Pattern 2 (lines 257-307) — the M13Allocator reference shape + recursive no-oversell + asyncio.Lock rationale
    - O1-PATTERNS.md "asyncio.Lock for the allocation guard" + "Concurrency / no-oversell allocator" Shared Pattern — the lifted (not imported) precedent
    - voss/harness/subagents.py lines 1-12, 22-27 — import + dataclass idiom to mirror (DO NOT EDIT this file)
    - voss/harness/agent.py line 419 — confirm `token_budget: int = 60_000` default to cite in the OQ-A1 docstring
    - M13-VALIDATION.md per-task map rows MAG-03 / MAG-04 — the TestEvenSplitRebalance / TestNoOversell behaviors this code must satisfy
  </read_first>
  <action>
    Create the NEW file `voss/harness/multiagent.py` (it does not exist — VERIFIED this plan; this is additive and keeps `subagents.py` byte-stable; do NOT edit `subagents.py`).

    File header: `from __future__ import annotations` first, then stdlib imports `asyncio`, `uuid`, `from dataclasses import dataclass, field`, `from typing import Any`. Mirror the `subagents.py:1-12` import idiom; do NOT import from `voss/harness/session_tree.py` or any O1 module — the O1 allocator is COPIED, not imported.

    RESOLVE RESEARCH Open Question A1 in a module-level docstring AND a named constant block at the top of the module, citing the agent.py:419 anchor verbatim:
      - Define `DEFAULT_PARENT_RESERVE: int = 30_000` — document it as "half of the chat parent's effective working budget; the chat `run_turn` call (cli.py:1695) passes no `token_budget`, so `_run_turn_exec` uses the default `token_budget: int = 60_000` at agent.py:419. M13 carves DEFAULT_PARENT_RESERVE from that 60_000, leaving the parent ~30_000 for its own orchestration turn (D-05: 'a parent reserve is carved')."
      - Define `DEFAULT_VIABLE_FLOOR: int = 2_000` — document it as "minimum allotment that still funds ≥1 child iteration; must be < reserve // expected_fanout so a first/second spawn is allowed but unbounded recursion is denied. With DEFAULT_PARENT_RESERVE=30_000 this allows up to floor(30_000/2_000)=15 concurrent first-level children before denial; in the recursive case a child's sub-allocator reserve = that child's allotment (D-07, slice-scoped), so depth is bounded naturally without any depth/max_depth constant (RESEARCH line 442; preserves test_subagent_recursion.py)."
      - These two constants are Claude's-discretion per CONTEXT "Claude's Discretion" ("Exact viable-budget-floor threshold value (sensible default; must bound recursion)") and RESEARCH A1. Document the choice and the agent.py:419 citation inline; do NOT add a `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` identifier.

    Implement `class M13Allocator` exactly per the reference shape in `<interfaces>` (LIFTED from O1-PATTERNS Pattern 2 / M13-RESEARCH Pattern 2 — copied, not imported):
      - `__init__(self, *, reserve: int, viable_floor: int)` storing `_reserve`, `_viable_floor`, `_active: dict[str, int] = {}`, `_lock = asyncio.Lock()`, `_credited_finished: set[str] = set()`.
      - `viable_floor` read-only `@property` returning `_viable_floor` (the recursive sub-allocator constructor needs to read it back per D-07).
      - `async def allocate(self, handle: str) -> int | None`: under `async with self._lock`, compute `n = len(self._active) + 1`, `even = self._reserve // n`; if `even < self._viable_floor` return `None` (the D-07 viable-floor denial — this is the recursion bound, NO depth constant); else set `self._active[handle] = even`, call `self._rebalance_locked()`, return `self._active[handle]`.
      - `async def release(self, handle: str) -> None`: under `async with self._lock`, if `handle in self._credited_finished` return immediately (MAG-04 exactly-once — the must-not-happen double-credit guard); else add to `_credited_finished`, `self._active.pop(handle, None)`, call `self._rebalance_locked()`.
      - `def _rebalance_locked(self) -> None`: if `_active` empty return; `even = self._reserve // len(self._active)`; set every active handle's allotment to `even`. (Caller already holds the lock; do NOT re-acquire — name encodes the precondition.)
      - `def snapshot(self) -> dict[str, int]`: return `dict(self._active)` (defensive copy; consumed later by panel BudgetMeter ticks).
      Invariant the tests assert and the implementation must hold: `sum(allocator.snapshot().values()) <= reserve` at all times, including under `asyncio.gather` racing allocations (the `asyncio.Lock` is what makes check-and-allocate atomic — single asyncio loop; `asyncio.Lock` not `threading.Lock`, per RESEARCH line 307).

    Do NOT add the spawn/steer/status/gather tools, `PanelBridgeRenderer`, `attach_multiagent_tools`, or any `run_turn`/`agent.py` change — those are M13-03/M13-04/M13-05 scope. This plan is the pure allocator + registry foundation only.
  </action>
  <acceptance_criteria>
    - Source: M13-RESEARCH Pattern 2 (lines 257-307) + OQ-A1 (lines 669-673) + agent.py:419 default
    - Behavior: `M13Allocator` even-splits a reserve across active handles, rebalances on release, denies below the viable floor (returns None), and credits a freed slice exactly once
    - Test command: `pytest tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance tests/harness/test_multiagent_fanout.py::TestNoOversell -x -q` passes
  </acceptance_criteria>
  <verify>
    <automated>python -c "import ast,sys; t=ast.parse(open('voss/harness/multiagent.py').read()); src=open('voss/harness/multiagent.py').read(); names={n.id for n in ast.walk(t) if isinstance(n,ast.Name)}|{getattr(n,'name','') for n in ast.walk(t)}; banned={'depth','max_depth','MAX_DEPTH','DEPTH_LIMIT','RECURSION_LIMIT'}; bad=banned & names; assert not bad, f'forbidden recursion identifier: {bad}'; assert 'class M13Allocator' in src; assert 'asyncio.Lock' in src; assert '419' in src, 'must cite agent.py:419 default in OQ-A1 docstring'; print('multiagent.py structure OK')" && pytest tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance tests/harness/test_multiagent_fanout.py::TestNoOversell -x -q</automated>
  </verify>
  <done>
    `voss/harness/multiagent.py` exists with `M13Allocator` (asyncio.Lock check-and-allocate, exactly-once release, viable-floor None denial), `DEFAULT_PARENT_RESERVE`/`DEFAULT_VIABLE_FLOOR` constants with the OQ-A1 rationale + agent.py:419 citation in the docstring, zero forbidden recursion identifiers, and `TestEvenSplitRebalance` + `TestNoOversell` from `tests/harness/test_multiagent_fanout.py` pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add ChildHandle dataclass and ChildRegistry to multiagent.py</name>
  <files>voss/harness/multiagent.py</files>
  <read_first>
    - voss/harness/subagents.py lines 22-27 — the `@dataclass` idiom to mirror (ChildHandle is NOT frozen: task/result/done are mutable)
    - M13-CONTEXT.md D-02 — "Children tracked in an in-memory `ChildRegistry` keyed by handle, scoped to the chat turn. No disk."
    - M13-CONTEXT.md "Claude's Discretion" — "ChildRegistry data structure + handle id scheme" is the planner/executor's call
    - O1-PATTERNS.md lines 110-120 — `uuid.uuid4().hex[:12]` handle id scheme (project-wide convention)
    - M13-PATTERNS.md "Analog A" — ChildHandle mirrors the SubagentSpec dataclass idiom but is mutable
  </read_first>
  <action>
    In the SAME file `voss/harness/multiagent.py` (created in Task 1), add the registry/handle in-memory substrate (D-02: in-memory, chat-turn-scoped, no disk — O1 owns persistence; do NOT import or anticipate O1's `SessionTreeManager`).

    Add `@dataclass class ChildHandle` (NOT `frozen` — `done`/`result` mutate over the child's lifetime, unlike the frozen `SubagentSpec` analog):
      - `id: str` — the `uuid.uuid4().hex[:12]` handle (also serves as the `panel_id` per RESEARCH Pattern 1 line 245).
      - `task: Any = None` — placeholder for the future `asyncio.Task` (typed `Any` to avoid importing/awaiting anything here; M13-03 populates it). Do NOT create or await any task in this plan.
      - `allotment: int = 0` — the budget slice this child received from `M13Allocator.allocate`.
      - `done: bool = False` — lifecycle flag flipped by the future gather path.
      - `result: str | None = None` — aggregated child output, set on completion by the future gather path.
      Keep the field set minimal — only what the allocator/registry foundation needs. Queue/sub-allocator/bridge fields are added by later waves (M13-03/M13-05); do NOT add them speculatively.

    Add `class ChildRegistry` — a thin in-memory map keyed by handle id, scoped to one chat turn (a fresh instance per fan-out; no disk, no global singleton):
      - `__init__(self) -> None`: `self._children: dict[str, ChildHandle] = {}`.
      - `def add(self, handle: ChildHandle) -> None`: `self._children[handle.id] = handle`.
      - `def get(self, handle_id: str) -> ChildHandle | None`: `self._children.get(handle_id)` (the future `subagent_steer` validates the target via this — steer to an unknown/finished child must be a no-op, T-M13 mis-steer mitigation; this plan only provides the lookup).
      - `def active(self) -> list[ChildHandle]`: return the list of handles whose `done is False` (the MAG-01 concurrency-overlap proof spies this; ≥2 between spawn and gather).
      - `def all(self) -> list[ChildHandle]`: return all handles regardless of `done` (the gather path iterates this).
      Provide a module-level helper `def new_handle_id() -> str: return uuid.uuid4().hex[:12]` so M13-03 mints ids consistently with the project-wide scheme (O1-PATTERNS 110-120) — do NOT inline `uuid.uuid4()` at call sites in later waves.

    Still NO spawn/steer/gather tools, NO `PanelBridgeRenderer`, NO `agent.py`/`run_turn` change — strictly the in-memory foundation. Confirm the forbidden-identifier guard still holds after this addition.
  </action>
  <acceptance_criteria>
    - Source: M13-CONTEXT D-02 + "Claude's Discretion" (registry structure + handle scheme) + O1-PATTERNS lines 110-120
    - Behavior: `ChildRegistry` tracks `ChildHandle`s in memory keyed by id; `active()` returns not-done handles, `all()` returns every handle, `get()` returns None for unknown ids
    - Test command: `pytest tests/harness/test_multiagent_fanout.py -x -q` (the allocator + registry foundation classes pass; spawn-dependent classes such as TestConcurrentInFlight may remain red until M13-03 — that is expected and not this plan's gate)
  </acceptance_criteria>
  <verify>
    <automated>python -c "import ast; src=open('voss/harness/multiagent.py').read(); t=ast.parse(src); names={n.id for n in ast.walk(t) if isinstance(n,ast.Name)}|{getattr(n,'name','') for n in ast.walk(t)}; banned={'depth','max_depth','MAX_DEPTH','DEPTH_LIMIT','RECURSION_LIMIT'}; bad=banned&names; assert not bad, f'forbidden recursion identifier: {bad}'; assert 'class ChildHandle' in src and 'class ChildRegistry' in src and 'def new_handle_id' in src; import voss.harness.multiagent as m; r=m.ChildRegistry(); h=m.ChildHandle(id=m.new_handle_id()); r.add(h); assert r.get(h.id) is h and r.get('nope') is None; assert r.active()==[h] and r.all()==[h]; h.done=True; assert r.active()==[] and r.all()==[h]; assert len(m.new_handle_id())==12; print('ChildRegistry/ChildHandle OK')" && pytest tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance tests/harness/test_multiagent_fanout.py::TestNoOversell -x -q && pytest tests/harness/test_subagent_recursion.py -x -q</automated>
  </verify>
  <done>
    `voss/harness/multiagent.py` additionally defines mutable `ChildHandle`, `ChildRegistry` (`add`/`get`/`active`/`all`), and `new_handle_id()`; the MAG-03/MAG-04 allocator classes still pass; `tests/harness/test_subagent_recursion.py` passes unmodified (back-compat anchor intact — no forbidden recursion identifiers, `subagents.py` untouched).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| parent chat agent → child spawn (allocator) | The allocator is the single budget-allocation chokepoint; concurrent (racing) `allocate()` calls from fan-out cross here. M13 adds no auth/network/persistence surface — blast radius is in-memory + (later) UI only. |
| recursive child → grandchild (sub-allocator) | A child re-receiving a slice-scoped allocator can recursively request allocation; the viable-floor denial is the only recursion bound (no depth constant). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M13-01 (oversell) | Tampering | `M13Allocator.allocate` under concurrent `asyncio.gather` | mitigate | `asyncio.Lock`-guarded check-and-allocate (D-06, O1-proven live race precedent). Invariant `sum(snapshot().values()) <= reserve` holds at every depth. Asserted by `TestNoOversell` (mandatory MAG-04 race test). |
| T-M13-02 (double-credit) | Tampering | `M13Allocator.release` called twice for a finished handle | mitigate | `_credited_finished: set` exactly-once guard; second `release(h)` is a no-op. Asserted by `TestNoOversell` (double-release → no double-credit, Σ ≤ reserve). |
| T-M13-03 (recursion-DoS) | Denial of Service | recursive spawn via slice-scoped sub-allocator | mitigate | Viable-floor denial: `allocate` returns `None` once `reserve // n < viable_floor`. Recursion bounded WITHOUT a `depth`/`max_depth` constant (preserves `test_subagent_recursion.py`). Depth-bound asserted in M13-05; non-recursive denial math here. |
| T-M13-04 (mis-steer) | Tampering | `ChildRegistry.get` for an unknown/finished handle | accept (this plan) | `ChildRegistry.get` returns `None` for unknown ids and exposes `done`, giving the future `subagent_steer` (M13-03) the validation hook to no-op a steer to a wrong/finished child. No steer surface exists in this plan — lookup primitive only. |
| T-M13-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan — stdlib + project-internal only (`asyncio`, `uuid`, `dataclasses`, `typing`). No new dependency; no `[ASSUMED]`/`[SUS]` package; no legitimacy checkpoint required. |
</threat_model>

<verification>
- `voss/harness/multiagent.py` is a NEW file; `voss/harness/subagents.py` is byte-identical to its pre-M13 state (`git diff --stat voss/harness/subagents.py` empty).
- `pytest tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance tests/harness/test_multiagent_fanout.py::TestNoOversell -x -q` — both green (MAG-03 even-split+rebalance; MAG-04 no-oversell race + exactly-once + depth-bound math).
- `pytest tests/harness/test_subagent_recursion.py -x -q` — green unmodified (back-compat pinning anchor; no `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` introduced).
- AST guard: no forbidden recursion identifier anywhere in `multiagent.py`; module imports cleanly (stdlib + project-internal only; no O1 import).
- OQ-A1 resolved in-module: `DEFAULT_PARENT_RESERVE` + `DEFAULT_VIABLE_FLOOR` constants present with documented rationale citing the agent.py:419 `token_budget: int = 60_000` default.
</verification>

<success_criteria>
- `M13Allocator` enforces `Σ(active allotments) ≤ reserve` under racing concurrent `allocate()` (no oversell) — `TestNoOversell` passes.
- Even-split + rebalance-on-release with exactly-once freed-slice credit — `TestEvenSplitRebalance` + `TestNoOversell` (double-release branch) pass.
- Viable-floor `None` denial bounds recursion with NO depth constant — denial math asserted; `test_subagent_recursion.py` stays green.
- `ChildHandle` + `ChildRegistry` provide the in-memory chat-turn-scoped substrate (`add`/`get`/`active`/`all`/`new_handle_id`); no disk, no O1 dependency.
- `subagents.py` byte-stable; module is stdlib + project-internal only; OQ-A1 documented with the agent.py:419 citation.
</success_criteria>

<output>
Create `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-02-SUMMARY.md` when done.
</output>
