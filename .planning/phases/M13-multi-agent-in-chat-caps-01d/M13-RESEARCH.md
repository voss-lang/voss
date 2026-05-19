# Phase M13: Multi-agent in Chat (CAPS-01d) — Research

**Researched:** 2026-05-18
**Domain:** Python asyncio harness wiring + orchestration — concurrent sub-agent fan-out, in-memory budget allocator, between-iteration steer channel, Textual panel bridge
**Confidence:** HIGH (all anchors verified by codebase read; one MEDIUM area flagged: parent-loop-stays-live mechanics)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Non-blocking spawn. Add a fan-out tool on the `subagent_run` path that schedules each child as an `asyncio` task and returns child handle id(s) immediately — the parent turn continues while children run. Concurrency = harness-local `asyncio` (`create_task`/`gather`), explicitly NOT `VossAgent.spawn`. Forced by MAG-05.
- **D-02:** Children tracked in an in-memory `ChildRegistry` keyed by handle, scoped to the chat turn. No disk (O1 owns persistence). Existing serial `subagent_run` + `/agent spawn` slash stay as-is for back-compat; the new non-blocking tools are additive.
- **D-03:** Per-child `asyncio.Queue` inbox. Parent calls a `subagent_steer(handle, guidance)` tool; guidance enqueued to the targeted child. Parent → child only, harness-mediated. Trigger is autonomous parent (LLM) only — no human-redirect, no child↔child.
- **D-04:** Steer cadence = between agent iterations. The child's `run_turn` loop drains its inbox at the loop boundary (after a tool round, before the next model call) and injects drained guidance as a steering message into the child's next iteration. No mid-tool-call preemption/cancellation. Deterministic + stub-testable.
- **D-05:** M13-local even-split-of-reserve allocator, in-memory. A parent reserve is carved, divided evenly across currently-active children, rebalanced when a child finishes (freed slice credited exactly once). Surfaced live in each panel's `BudgetMeter`. Not O1's `SessionTreeManager`.
- **D-06:** No-oversell guard = `asyncio.Lock`-guarded check-and-allocate at the single spawn site. Σ(active child allotments) ≤ parent reserve at every nesting depth.
- **D-07:** Recursion (depth > 1, MAG-06): a child's toolset gets the same spawn/steer/gather tools plus a sub-allocator scoped to that child's own slice. Recursion bounded naturally by a viable-budget floor — a spawn is denied when its allocatable slice falls below the floor. No separate hard depth cap.
- **D-08:** Wire the currently-dead `show_subagent_progress` / `app.update_subagent` seam (`renderer.py:203`, never called today). Each child's `Renderer` is wrapped with a bridge that posts per-step lines + budget ticks to that child's `SubAgentPanel` via `parent_id`. Reuse the existing M9 `SubAgentPanel` / `BudgetMeter` widgets — no new panel widget types unless nesting strictly requires it.
- **D-09:** Panel is quiet by default (compact: header + `BudgetMeter` + mini-status; no per-step body flood). Detail/streamed-step view revealed by Ctrl+O. Ctrl+C stays interrupt (`keymap.py:37` global `interrupt`, unchanged). Add a single new `ctrl+o` binding to `keymap.py` — additive only.
- **D-10:** A `subagent_gather` tool awaits all outstanding handles, aggregates each child result into the parent turn, then triggers the existing `app.collapse_subagent` cleanup so every `SubAgentPanel` is removed and the side-region pin/owner state is restored per the existing M9-08 contract (`app.py:184`).
- **D-11:** Deterministic + hermetic, stub provider, no live network (T7/T8 precedent). The headline e2e + no-oversell race test + correction-changes-behavior test + concurrency-proof + depth-2 test + post-gather region-clean assertion all run under the stub.

### Claude's Discretion

- Exact tool names (`subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather` working names — planner finalizes, consistent with `SPAWN_TOOL_NAME` detection in `renderer.py`).
- `ChildRegistry` data structure + handle id scheme.
- Renderer-bridge wiring technique (how the child Renderer posts to `parent_id` panel without cross-thread hazards — note renderer thread-safety comment `renderer.py:7`).
- `gather` aggregation output format in the turn.
- Exact viable-budget-floor threshold value (sensible default; must bound recursion).
- Reveal/detail view layout inside the expanded panel.
- Whether the new non-blocking tools subsume or sit beside `subagent_run` internally (back-compat of `/agent spawn` slash is the only hard constraint).

### Deferred Ideas (OUT OF SCOPE)

- O1 Session-Tree substrate (disk-persisted tree, generalized fan-out cage) — O1 builds *on* M13's raw in-memory fan-out; M13 stays minimal.
- User-driven manual child redirect — rejected for M13 (autonomous-parent only).
- Mid-tool-call preemptive cancellation of a child — rejected (steer cadence is between-iterations only).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAG-01 | Concurrent fan-out on `subagent_run` path; ≥2 children in flight simultaneously | §"Fan-out shape" + Architecture Pattern 1 (asyncio.create_task on ChildRegistry); §"Open Question 1" resolves the parent-stays-live mechanic |
| MAG-02 | Live, quiet-by-default panels; Ctrl+O reveal | §"Renderer bridge" (D-08), Pattern 4; §"Pitfall: renderer thread hazard" reconciles renderer.py:7; keymap-additive pattern verified |
| MAG-03 | Even-split reserve budget partitioning + rebalance | Pattern 2 (M13-local allocator lifted from O1-RESEARCH Pattern 2); §"Reserve source" identifies the synthetic-reserve origin |
| MAG-04 | No-oversell invariant (recursive), race-safe | Pattern 2 `asyncio.Lock` check-and-allocate; O1-RESEARCH live race-test precedent (10 concurrent → 8 succeed) |
| MAG-05 | Autonomous-parent course-correction into running child | Pattern 3 (per-child `asyncio.Queue` drained at the verified `run_turn` loop boundary line 832); §"Open Question 1" |
| MAG-06 | Recursive spawn depth > 1; nested budget + nested panels | Pattern 5 (slice-scoped sub-allocator); §"Pitfall: panel-id collision on nesting"; `test_subagent_recursion.py` constraint |
| MAG-07 | Gather + clean teardown; M9-08 region restore | Pattern 6 (`subagent_gather` → `app.collapse_subagent`); verified `collapse_subagent` already does M9-08 restore |
| MAG-08 | Headline e2e transcript | §"Validation Architecture"; `FakeStreamingProvider` scripted-stream precedent (test_agent_loop.py:77) |
</phase_requirements>

---

## Summary

M13 is a pure wiring + orchestration phase on the existing `subagent_run` path. Every primitive it needs already exists in the codebase or is directly liftable from O1-RESEARCH; there are **no new third-party dependencies** and **no new architectural inventions** — only six new harness tools, one in-memory registry, one M13-local allocator (a copy of O1's `asyncio.Lock` allocator, not an import), one additive `run_turn` parameter, one additive keymap binding, and a renderer-bridge that finally supplies the missing caller for the dead `show_subagent_progress` seam.

**The single riskiest unknown — and it is now resolved (MEDIUM→HIGH after investigation):** "How does the parent turn stay live between spawn and gather so the autonomous mid-run steer is possible *within one chat turn*?" Answer: the parent `run_turn` loop is **already iterative** (`_run_turn_exec` while-loop, `agent.py:583`). A non-blocking `subagent_spawn` tool that calls `asyncio.create_task(...)` and returns a handle string immediately lets the parent's *next loop iteration* call `subagent_steer` and then `subagent_gather` — children run as detached tasks on the same event loop while the parent keeps planning. No change to the parent loop's *structure* is required; the parent simply needs ≥2 iterations (spawn iter → steer iter → gather iter), which the existing loop already supports (`max_iterations` default 8). The fan-out tools must NOT `await` child completion (that is exactly what today's serial `subagent_run` does wrong, `subagents.py:92`).

**The second key finding — threading model reconciliation:** The `renderer.py:7` "subagents run in worker threads" comment is **stale/aspirational for M13's path**. Today `subagent_run` is dispatched via `_invoke_step_with_gate` (`agent.py:1104`) as a plain `await entry.invoke(...)` — same event loop, same thread, no `to_thread`/`run_in_executor`/worker. Under D-01 the children become `asyncio.create_task` coroutines — **still single-threaded, same event loop**. The `_post` helper (`renderer.py:55`) already handles both cases correctly (`threading.current_thread() is main_thread()` → direct call). So the renderer bridge is safe by construction *as long as the child runs as an asyncio task on the app's loop* (it does). The thread hazard the comment warns about only applies to the M9-05 permissions-bridge modal path, which is out of M13 scope.

**Primary recommendation:** Add `voss/harness/multiagent.py` (new: `ChildRegistry`, `ChildHandle`, `M13Allocator`, the four non-blocking tools, and a `PanelBridgeRenderer` wrapper). Add **one** additive kwarg `steer_inbox: asyncio.Queue | None = None` to `run_turn`/`_run_turn_exec` and drain it at the verified loop boundary `agent.py:832` (between `all_iter_records.append` and the budget check / `iteration_index += 1`). Add `node_budget`/reserve via the same additive `token_budget=` kwarg O1 also uses. Leave `subagents.py:run_subagent` and `cli.py:_agent`/`agent_spawn_cmd` untouched (back-compat). Add one `Binding("ctrl+o", "main", "toggle_subagent_detail", ...)` to `keymap.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Concurrent fan-out scheduling | Harness (`multiagent.py` spawn tool) | `asyncio` event loop | Tool calls `asyncio.create_task`; same loop as parent `run_turn` — no threads, no `VossAgent.spawn` (LOCKED out) |
| Child lifecycle tracking | Harness (`ChildRegistry`, in-memory) | — | Chat-turn-scoped; no disk (O1 owns persistence) |
| Budget even-split + no-oversell | Harness (`M13Allocator`, `asyncio.Lock`) | — | M13-local copy of O1 Pattern 2; NOT O1 `SessionTreeManager` |
| Steer message transport | Harness (`asyncio.Queue` per child) | — | Parent→child only; harness-mediated; no pub/sub |
| Steer injection point | `agent.py` `_run_turn_exec` loop boundary (line 832) | Child `run_turn` | Drain between iterations; additive `steer_inbox` kwarg only |
| Per-child step/budget rendering | TUI (`SubAgentPanel`/`BudgetMeter` via bridge) | `renderer._post` | Reuse M9 widgets; bridge supplies the dead `show_subagent_progress` caller |
| Reveal/detail toggle | TUI (`app` action + `keymap.py` `ctrl+o`) | — | Additive binding; Ctrl+C stays interrupt |
| Gather + region restore | Harness (`subagent_gather` tool) → TUI (`app.collapse_subagent`) | — | `collapse_subagent` already does M9-08 restore (`app.py:184-207`) |
| Recursive sub-allocation | Harness (slice-scoped child `M13Allocator`) | — | Child toolset re-receives the four tools + a sub-allocator over its own slice |

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python ≥ 3.11 | `create_task`, `gather`, `Queue`, `Lock` for fan-out + steer + allocator guard | Already used in `agent.py` (`asyncio.Semaphore`, `asyncio.gather`, `asyncio.CancelledError`) [VERIFIED: codebase read agent.py:10,1191,1215,985] |
| `dataclasses` (stdlib) | Python ≥ 3.7 | `ChildHandle` / registry value type | Project-wide harness dataclass idiom [VERIFIED: subagents.py:22, session.py] |
| `uuid` (stdlib) | — | Child handle id | Matches `RunRecorder.start()` / `SessionRecord.new()` `uuid.uuid4().hex[:12]` [VERIFIED: O1-PATTERNS lines 110-120] |
| `voss_runtime.BudgetScope` | (project) | Optional per-child spend scope (token_limit) | Already consumed via `ContextScope` in `run_turn`; M13 only needs the `token_budget` soft cap (see Reserve source) [VERIFIED: budget.py read] |
| `voss.harness.agent.run_turn` | (project) | Child agent loop (the recursion target) | The exact loop M13 hooks; additive kwarg only [VERIFIED: agent.py:412] |
| `voss.harness.tui.widgets.SubAgentPanel` / `BudgetMeter` | (project) | Per-child render target | Reuse unchanged; em-dash zero-total contract already correct [VERIFIED: sub_agent_panel.py:66] |

### Supporting (existing seams M13 wires)

| Seam | Location | Purpose | When to Use |
|------|----------|---------|-------------|
| `TextualRenderer.show_subagent_progress` | `renderer.py:203` | DEAD — never called today | M13 bridge becomes its first caller (D-08) |
| `app.update_subagent` | `app.py:176` | Appends body line + updates budget meter, matched by `parent_id` | Bridge target for per-step ticks |
| `app.mount_subagent_panel` / `collapse_subagent` | `app.py:169,184` | Mount on spawn; collapse + M9-08 restore on gather | spawn → mount; gather → collapse |
| `_run_turn_exec` while-loop boundary | `agent.py:832` (after `all_iter_records.append`, before budget check) | Verified safe steer-drain point | D-04 inbox drain |
| `KEYMAP` tuple | `keymap.py:20` | Single-source binding table → `VossTUIApp.BINDINGS` (`app.py:39`) | Add one `ctrl+o` binding |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Harness-local `asyncio.create_task` fan-out | `voss_runtime.VossAgent.spawn`/`gather` | LOCKED OUT by SPEC/CONTEXT — runtime primitive stays a `.voss` concern; M13 must not route through it (confirmed `voss_runtime/agent.py:74` is a separate `asyncio.create_task` wrapper not wired to chat) |
| New `multiagent.py` module | Extend `subagents.py` in place | New module keeps back-compat surface (`run_subagent`, `attach_subagent_tool`) byte-stable and `test_subagent_recursion.py` passing; recommended |
| M13-local allocator copy | Import O1 `SessionTreeManager` | LOCKED OUT — O1 builds on M13; circular/premature dependency. Copy the *pattern* (≈30 lines), not the module |

**Installation:** None — zero external packages.

**Version verification:** All stdlib + project-internal. No registry check applicable.

---

## Package Legitimacy Audit

Not applicable — M13 installs zero external packages. (slopcheck/registry verification skipped: no third-party packages in scope.)

---

## Architecture Patterns

### System Architecture Diagram

```
voss chat user NL request
        │
        ▼
Parent run_turn  (_run_turn_exec while-loop, agent.py:583 — ITERATIVE, max_iterations≈8)
        │
   iter k: plan → tool round
        │
        ├─► subagent_spawn(agent, task)  [NEW non-blocking tool]
        │        │  M13Allocator.allocate()  ←── asyncio.Lock (no-oversell check-and-allocate)
        │        │  asyncio.create_task(_run_child(...))   ── detached, SAME event loop
        │        │  ChildRegistry[handle] = ChildHandle(task, queue, panel_id, alloc)
        │        └─► returns handle string IMMEDIATELY (does NOT await)   ──┐
        │                                                                   │
   iter k+1: parent sees handle, decides correction                        │ children run
        │                                                                   │ concurrently
        ├─► subagent_steer(handle, guidance)  [NEW tool]                    │ as asyncio tasks
        │        └─► ChildRegistry[handle].queue.put_nowait(guidance)       │
        │                                                                   ▼
        │                                              child run_turn loop (own _run_turn_exec)
        │                                                  iter: plan → tools
        │                                                  ── BOUNDARY agent.py:832 ──
        │                                                  drain steer_inbox (D-04)
        │                                                  inject guidance → next iter messages
        │                                                  child Renderer = PanelBridgeRenderer
        │                                                      → show_subagent_progress
        │                                                      → app.update_subagent(parent_id,…)
        │                                                      → SubAgentPanel body + BudgetMeter
        │                                                  child may itself call subagent_spawn
        │                                                      → slice-scoped sub-M13Allocator (D-07)
        │
   iter k+n:
        └─► subagent_gather()  [NEW tool]
                 │  await asyncio.gather(*[h.task for h in registry])  (return_exceptions=True)
                 │  M13Allocator.release(handle) per finish → rebalance (credit-once)
                 │  aggregate child .final into parent turn result
                 └─► app.collapse_subagent(parent_id) per panel
                          → removes SubAgentPanel(s)
                          → M9-08 restore (_side_owner/_side_pinned, app.py:188-207)

Ctrl+O ──► app.action_toggle_subagent_detail  (keymap.py NEW "main"-context binding)
Ctrl+C ──► app.action_interrupt  (keymap.py:37 UNCHANGED — cancels active_turn_task)
```

### Recommended Project Structure

```
voss/harness/
├── multiagent.py        # NEW: ChildRegistry, ChildHandle, M13Allocator,
│                        #      subagent_spawn/steer/status/gather tools,
│                        #      PanelBridgeRenderer, attach_multiagent_tools()
├── subagents.py         # UNCHANGED (back-compat: run_subagent, attach_subagent_tool,
│                        #      SPAWN_TOOL_NAME, /agent spawn + voss agent spawn)
├── agent.py             # MODIFIED: one additive kwarg steer_inbox + drain at line 832
├── cli.py               # MODIFIED: call attach_multiagent_tools() next to
│                        #      attach_subagent_tool() at ~1634 (additive)
└── tui/
    ├── keymap.py        # MODIFIED: +1 Binding("ctrl+o","main","toggle_subagent_detail",…)
    └── app.py           # MODIFIED: + action_toggle_subagent_detail + per-panel detail state
                         #      (SubAgentPanel/BudgetMeter widgets UNCHANGED)

tests/harness/
├── test_multiagent_fanout.py        # NEW: concurrency proof, no-oversell race, rebalance
├── test_multiagent_steer.py         # NEW: correction-changes-behavior vs control
├── test_multiagent_recursion.py     # NEW: depth-2 nested budget + nested panels
└── tui/test_subagent_reveal.py      # NEW: quiet-by-default + ctrl+o reveal
tests/e2e/
└── test_multiagent_chat_e2e.py      # NEW: headline transcript (stub provider)
```

### Pattern 1: Non-blocking spawn tool (MAG-01 / D-01)

```python
# Source: composed from subagents.run_subagent (subagents.py:76) +
#         agent._invoke_step_with_gate await-dispatch (agent.py:1104) +
#         O1-RESEARCH allocator. The KEY difference vs today: NO await on child.
import asyncio
import uuid
from dataclasses import dataclass, field

@dataclass
class ChildHandle:
    handle: str
    task: asyncio.Task
    queue: asyncio.Queue          # D-03 steer inbox
    panel_id: str                 # SubAgentPanel parent_id
    allotment: int                # tokens this child owns (D-05)
    sub_allocator: "M13Allocator" # D-07 slice-scoped, for grandchildren
    done: bool = False
    result: str | None = None

class ChildRegistry:
    """In-memory, chat-turn-scoped. NO disk (O1 owns persistence)."""
    def __init__(self) -> None:
        self._children: dict[str, ChildHandle] = {}
    def add(self, h: ChildHandle) -> None: self._children[h.handle] = h
    def get(self, handle: str) -> ChildHandle | None: return self._children.get(handle)
    def active(self) -> list[ChildHandle]:
        return [h for h in self._children.values() if not h.done]
    def all(self) -> list[ChildHandle]: return list(self._children.values())

# tool body (working name subagent_spawn — planner finalizes):
async def subagent_spawn(agent: str, task: str) -> str:
    handle = uuid.uuid4().hex[:12]
    allotment = await allocator.allocate(handle)      # asyncio.Lock guarded (Pattern 2)
    if allotment is None:
        return f"<denied: budget below viable floor — cannot spawn {agent!r}>"
    queue: asyncio.Queue = asyncio.Queue()
    panel_id = handle
    bridge = PanelBridgeRenderer(base_renderer, panel_id=panel_id)
    bridge.start_panel(name=agent, budget_total=allotment)         # mount panel
    sub_alloc = M13Allocator(reserve=allotment, viable_floor=allocator.viable_floor)
    coro = _run_child(agent, task, queue, bridge, allotment, sub_alloc, ...)
    t = asyncio.create_task(coro)                      # DETACHED — same loop
    registry.add(ChildHandle(handle, t, queue, panel_id, allotment, sub_alloc))
    return f"spawned {agent} handle={handle} budget={allotment}"   # RETURNS NOW
```

**Why this works for MAG-05 (the riskiest unknown, resolved):** The parent `run_turn` is the existing iterative `_run_turn_exec` while-loop (`agent.py:583`, `max_iterations` default 8 via `cfg.max_iterations`). `subagent_spawn` returns a string in the same tool round; the parent's *next* iteration sees the handle in its replayed tool results (`_serialize_iter_for_replay`, `agent.py:354`) and can emit `subagent_steer` then `subagent_gather` in later iterations. Children run as `asyncio.create_task` coroutines on the same loop and make progress whenever the parent `await`s (every provider stream call yields). **No change to the parent loop structure is required** — only that the spawn tool must not block. [VERIFIED: agent.py:583-839 loop structure + 1104 await-dispatch + cli.py:1695 chat run_turn call]

### Pattern 2: M13-local even-split allocator with asyncio.Lock (MAG-03/04/06 — D-05/06/07)

```python
# Source: LIFTED (copied, not imported) from O1-RESEARCH.md Pattern 2 (lines 204-246).
# O1's live race test: 10 concurrent 100-token allocations vs 900 w/o lock → all 10
# succeed (oversell); WITH asyncio.Lock → correct. M13 needs the SAME guard.
import asyncio

class M13Allocator:
    """Even-split-of-reserve, in-memory, chat-turn-scoped. NOT O1 SessionTreeManager."""
    def __init__(self, *, reserve: int, viable_floor: int) -> None:
        self._reserve = reserve
        self._viable_floor = viable_floor
        self._active: dict[str, int] = {}   # handle -> current allotment
        self._lock = asyncio.Lock()
        self._credited_finished: set[str] = set()  # exactly-once rebalance guard

    @property
    def viable_floor(self) -> int: return self._viable_floor

    async def allocate(self, handle: str) -> int | None:
        async with self._lock:                          # D-06 race-safe check-and-allocate
            n = len(self._active) + 1                    # include the new child
            even = self._reserve // n
            if even < self._viable_floor:                # D-07 viable-floor → bounds recursion
                return None                              # caller emits <denied: …>
            self._active[handle] = even
            self._rebalance_locked()                     # even-split existing too
            return self._active[handle]

    async def release(self, handle: str) -> None:
        async with self._lock:
            if handle in self._credited_finished:        # MAG-04 exactly-once
                return
            self._credited_finished.add(handle)
            self._active.pop(handle, None)
            self._rebalance_locked()                     # freed slice → survivors

    def _rebalance_locked(self) -> None:
        if not self._active: return
        even = self._reserve // len(self._active)
        for h in self._active: self._active[h] = even
        # INVARIANT (assert in tests): sum(self._active.values()) <= self._reserve

    def snapshot(self) -> dict[str, int]:
        return dict(self._active)                        # for panel BudgetMeter ticks
```

**Recursive no-oversell (MAG-06 / D-07):** A child's `sub_allocator` is `M13Allocator(reserve=child.allotment, viable_floor=...)`. A grandchild's allotment is `child.allotment // n` ≤ `child.allotment` ≤ parent slice. The invariant `Σ(active) ≤ reserve` holds at every level because each level's allocator only ever divides *its own* reserve. The viable-floor denial (returning `None`) is what naturally bounds recursion depth — no `max_depth` constant (which would break `test_subagent_recursion.py`). [VERIFIED: O1-RESEARCH Pattern 2 + test_subagent_recursion.py:34-40 forbids MAX_DEPTH/DEPTH_LIMIT/RECURSION_LIMIT]

**Why `asyncio.Lock` and not `threading.Lock`:** The harness is one asyncio loop; children are `create_task` coroutines on it. `asyncio.Lock` suspends the coroutine; `threading.Lock` would deadlock. [VERIFIED: O1-RESEARCH line 244 + budget.py single-loop model]

### Pattern 3: Steer inbox drain at the verified run_turn boundary (MAG-05 / D-04)

The exact safe boundary in `_run_turn_exec` is **`agent.py` line 832**, immediately after `all_iter_records.append(rec._iterations[-1])` (end of a non-terminating iteration's bookkeeping) and **before** the budget check (`if ctx.token_budget and ctx.tokens_used >= ctx.token_budget`, line 832-837) and `iteration_index += 1` (line 839). This is "after a tool round, before the next model call" exactly as D-04 specifies — the next loop turn rebuilds `messages` (line 601) and re-streams the provider (line 629).

```python
# Source: agent.py:828-839 — additive insert. NEW kwarg only.
# run_turn / _run_turn_exec signature gains ONE param:
#   steer_inbox: asyncio.Queue | None = None
# (additive — test_subagent_recursion.py only forbids depth/max_depth, NOT this)

                total_completion_tokens += iter_completion_tokens
                all_iter_records.append(rec._iterations[-1])

                # --- M13 D-04: drain steer inbox between iterations ---
                if steer_inbox is not None:
                    drained: list[str] = []
                    while not steer_inbox.empty():
                        try:
                            drained.append(steer_inbox.get_nowait())
                        except asyncio.QueueEmpty:
                            break
                    if drained:
                        guidance = "\n".join(drained)
                        # inject as a steering user message visible to next iter.
                        # Cleanest hook: append to history (replayed via
                        # _serialize_iter_for_replay) OR a dedicated rider line.
                        # Recommendation: a synthetic prior-iter user message so
                        # it lands in `messages` on the next loop (line 606-609).
                        rec.note_steer(guidance)   # NEW recorder hook (or reuse history)
                # ------------------------------------------------------

                if (ctx.token_budget and ctx.tokens_used >= ctx.token_budget):
                    exit_reason = "budget"
                    break
                iteration_index += 1
```

**Why this boundary is correct and safe:**
- It is the only point where an iteration is fully committed (`rec.end_iteration` already called at line 806) and the next iteration's `messages` list has not yet been built (built at line 601 on next loop entry).
- The `asyncio.CancelledError` handler (line 985) and `BatchInvariantError` handler (line 939) are *outside* the while-loop body — draining here does not interfere with the cancellation/interrupt contract (the Ctrl+C precedence comment at line 989-991 still holds).
- `asyncio.Queue.get_nowait()` raises `asyncio.QueueEmpty` (must import / catch) — non-blocking drain, deterministic under the stub.
- The terminating-iteration branch (`_is_done_plan`, line 716) `break`s before reaching line 832, so a child that decides "done" before draining will not consume a pending steer — acceptable per D-04 (no mid-tool preemption; steer applies only if the child runs another iteration). Tests must script the child to take ≥2 iterations to observe the correction. [VERIFIED: agent.py:716,788,806,828-839,985]

**Injection mechanism (Claude's discretion, recommended):** The child's loop replays prior iterations as messages via `_serialize_iter_for_replay` (`agent.py:354`, appended at line 606-609). The least-invasive injection is to add the drained guidance as an extra user-role message in the next iteration's `messages` list (a sibling to the replay messages), OR append to the child's `EpisodicMemory` history (which `_run_turn_exec` reads into `history_block` at line 514-519). The history route requires the child's `run_turn` to receive a live `history` object the steer path can mutate — the spawn tool already constructs `EpisodicMemory(capacity=20)` (subagents.py:99 analog); keep a reference in `ChildHandle` if using that route. **Recommend the synthetic-message route** (no shared mutable history across the loop boundary; deterministic).

### Pattern 4: PanelBridgeRenderer — wire the dead seam (MAG-02 / D-08)

```python
# Source: renderer.py:203 (dead show_subagent_progress) + _post thread-safety
#         (renderer.py:55) + sub_agent_panel.py update_budget/append_body.
# The child gets THIS wrapper as its `renderer=` arg so its show_* calls
# fan into the parent's SubAgentPanel keyed by panel_id (== parent_id).

class PanelBridgeRenderer:
    """Wraps the parent renderer; routes child step/budget into its panel.

    Delegates everything to the base renderer, but for the subagent-visual
    methods it targets a fixed panel_id. Safe because the child runs as an
    asyncio task on the SAME loop/thread as the app (see Pitfall: thread).
    """
    def __init__(self, base, *, panel_id: str) -> None:
        self._base = base
        self._panel_id = panel_id

    def start_panel(self, *, name: str, budget_total: int) -> None:
        # mounts SubAgentPanel(parent_id=panel_id) via existing seam
        if hasattr(self._base, "show_subagent_start"):
            self._base.show_subagent_start(name, self._panel_id, budget_total)

    # Per-step + budget tick — THIS is the missing caller for renderer.py:203
    def step(self, line: str, used: int) -> None:
        if hasattr(self._base, "show_subagent_progress"):
            self._base.show_subagent_progress(self._panel_id, line, used)

    def end_panel(self, n_results: int = 1) -> None:
        if hasattr(self._base, "show_subagent_end"):
            self._base.show_subagent_end(self._panel_id, n_results)

    # Delegate the full Renderer protocol to the base so run_turn works:
    def __getattr__(self, attr):
        return getattr(self._base, attr)
```

The child's `run_turn` drives the standard renderer protocol. To get *per-step* lines into the panel without flooding (D-09 quiet-by-default), the bridge's `step()` is called from the child's iteration bookkeeping (e.g., once per iteration with a compact summary + the allocator's current `used` from `allocator.snapshot()`), NOT on every `stream_delta`. `app.update_subagent` already appends to the panel body and calls `panel.update_budget(used)` which moves the `BudgetMeter` off the em-dash placeholder (`sub_agent_panel.py:66-71`, em-dash only when `budget_total<=0`). [VERIFIED: renderer.py:203-207, app.py:176-182, sub_agent_panel.py:51-71]

### Pattern 5: Quiet-by-default + Ctrl+O reveal (MAG-02 / D-09)

```python
# keymap.py — ADD exactly one line (additive; T8 keymap-additive precedent).
# Context "main" so it doesn't collide with input typing; Ctrl+C row UNCHANGED.
KEYMAP = (
    ...,
    Binding("ctrl+c", "global", "interrupt", "Interrupt turn; press again to exit"),  # UNCHANGED line 37
    Binding("ctrl+o", "main", "toggle_subagent_detail", "Reveal/hide sub-agent step detail"),  # NEW
    ...,
)
# NOTE: VossTUIApp.BINDINGS filters context in ("global","input","modal")
#       (app.py:42). "main"-context bindings are NOT auto-added there — M9
#       main-context keys (j/k/g/G/f) are handled via the focused TurnView /
#       a separate binding path. Planner MUST verify how "main" bindings are
#       dispatched (check TurnView.BINDINGS or app focus routing) and place
#       ctrl+o consistently. See Open Question 2.
```

Quiet-by-default means: the `SubAgentPanel` shows header + `BudgetMeter` + a one-line mini-status; the per-step body lines are mounted into `#panel-body-{parent_id}` (already happens via `append_body`, `sub_agent_panel.py:61`) but the body `Vertical` is **display:none by default** and toggled visible by `action_toggle_subagent_detail`. The streamed steps are *captured* live (so reveal shows real history) but not *rendered* until toggled. [VERIFIED: sub_agent_panel.py:59 body is its own `Vertical(id=f"panel-body-{parent_id}")` — togglable via `.styles.display`]

### Pattern 6: subagent_gather + M9-08 teardown (MAG-07 / D-10)

```python
# Source: app.collapse_subagent (app.py:184-207) ALREADY does M9-08 restore.
async def subagent_gather() -> str:
    handles = registry.all()
    tasks = [h.task for h in handles]
    results = await asyncio.gather(*tasks, return_exceptions=True)  # concurrent join
    lines = []
    for h, r in zip(handles, results):
        await allocator.release(h.handle)         # rebalance, credit-once (MAG-04)
        if isinstance(r, Exception):
            lines.append(f"[{h.handle}] <error: {r}>")
        else:
            h.done = True; h.result = h.result or str(r)
            lines.append(f"[{h.handle}] {h.result}")
        bridge_for(h).end_panel(1)                 # → app.collapse_subagent(panel_id)
    return "Aggregated sub-agent results:\n" + "\n".join(lines)
```

`app.collapse_subagent(parent_id, n)` already: removes matching `SubAgentPanel`(s); if no panels remain and not pinned, restores `CodeIntelPanel` and sets `_side_owner="code_intel"`; appends a `"✓ gathered · N results"` turn line (`app.py:184-207`). M13's gather must call it once per panel; the M9-08 contract is honored *for free* — no new region logic. The aggregated string returned by the tool is folded into the parent turn via the normal tool-result replay (`_serialize_iter_for_replay`). [VERIFIED: app.py:184-207]

### Anti-Patterns to Avoid

- **`await`ing the child inside the spawn tool.** This is exactly today's serial bug (`subagents.py:92` `result = await run_turn(...)`). The new spawn tool MUST `create_task` and return immediately, or MAG-05 (mid-run steer within one turn) is structurally impossible.
- **Holding `M13Allocator._lock` across `run_turn`.** Lock guards only check-and-allocate / release. Holding it during child execution serializes all children (kills MAG-01). (O1-RESEARCH Pitfall 3.)
- **Importing O1 `SessionTreeManager`.** LOCKED OUT. Copy the ~30-line allocator pattern into `multiagent.py`. O1 builds on M13, not the reverse.
- **Adding `depth`/`max_depth`/`MAX_DEPTH` to bound recursion.** Breaks `test_subagent_recursion.py:23-40` (pinning test). Recursion is bounded by the viable-floor denial only.
- **Mutating `SubAgentPanel`/`BudgetMeter` widget classes.** D-08 says reuse unchanged; only `app.py` gains the toggle action + per-panel detail-visibility state.
- **Touching `keymap.py:37` (Ctrl+C).** Must stay `interrupt`. Add a *new* `ctrl+o` row only.
- **Cross-thread widget mutation from the child.** The child is an asyncio task on the app's loop — `_post` (renderer.py:55) detects main-thread and calls directly. Do NOT introduce `to_thread`/worker for children (would re-introduce the renderer.py:7 hazard the comment warns about).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent spawn join | Manual task list + polling loop | `asyncio.gather(*tasks, return_exceptions=True)` | Already the harness idiom (`agent.py:1215`); cancellation-correct |
| No-oversell race safety | Custom counter / CAS | `asyncio.Lock` check-and-allocate | O1 proved the exact race; lock is zero-cost uncontested |
| Steer transport | Custom callback / pub-sub bus | `asyncio.Queue` per child | D-03 LOCKED; `get_nowait()`+`QueueEmpty` is deterministic |
| Handle ids | Custom scheme | `uuid.uuid4().hex[:12]` | Matches `RunRecorder`/`SessionRecord` project-wide |
| Panel mount/collapse + region restore | New side-region state machine | `app.mount_subagent_panel` / `collapse_subagent` | M9-08 contract already implemented & tested (`app.py:184-207`) |
| Cross-thread render safety | New thread bridge | Existing `renderer._post` | Already handles main-thread vs off-loop correctly |
| Child agent loop | New runner | `agent.run_turn` (additive kwarg) | The recursion target; reuse, don't fork |

**Key insight:** M13 is wiring, not invention. Every "hard" sub-problem (race-safe budget, region restore, thread-safe render, cancellation-correct gather) already has a verified implementation in the repo or in O1-RESEARCH. The phase risk is *integration sequencing*, not algorithmic.

---

## Runtime State Inventory

M13 is **in-memory only, chat-turn-scoped** (D-02 explicitly: no disk; O1 owns persistence). It is effectively greenfield for runtime state — there is no existing multi-agent-in-chat state to migrate. Each category, explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `ChildRegistry`/`M13Allocator`/queues are in-memory, discarded at chat-turn end. No DB, no file. Verified: D-02 + SPEC out-of-scope "Disk persistence … O1". | None |
| Live service config | None — no external service. The only "config" is `cfg.max_iterations` (read, not written) and the synthetic reserve (see Reserve source). | None |
| OS-registered state | None — no OS scheduler/daemon/process registration. Children are asyncio tasks on the existing loop. | None |
| Secrets/env vars | None — no new secret keys or env vars. `VOSS_NO_UNICODE` (existing) unaffected. | None |
| Build artifacts | None — new `multiagent.py` module only; no compiled artifact, no egg-info rename, no entry-point change. `pyproject.toml` unchanged. | None |

**Nothing found in any category — verified by D-02 (in-memory, no disk) and SPEC Boundaries (disk persistence is O1, not M13).**

---

## Common Pitfalls

### Pitfall 1: Parent loop starvation / parent finishes before children steered

**What goes wrong:** The parent's `run_turn` reaches a "done" plan (`_is_done_plan`, agent.py:716) and `break`s before it ever calls `subagent_steer`/`subagent_gather`, leaving children orphaned (tasks still running, panels mounted, no gather).
**Why it happens:** The LLM (or stub script) emits a terminating plan too early; or the parent never re-plans because the spawn tool result didn't signal "more work pending".
**How to avoid:** (1) The spawn tool's return string must make the pending-gather obligation explicit ("handle=… — call subagent_gather when ready"). (2) A defensive `subagent_gather`-on-turn-teardown safety net: on parent `run_turn` exit (any `exit_reason`), if `ChildRegistry` has un-gathered handles, cancel their tasks and `collapse_subagent` each panel so nothing leaks. (3) Tests must script the parent stub to take ≥3 iterations (spawn → steer → gather). [VERIFIED: agent.py:716 done-break is before line 832]
**Warning signs:** `SubAgentPanel` instances remain mounted after a turn; `asyncio` "Task was destroyed but it is pending" warnings.

### Pitfall 2: Steer lands after the child's terminating iteration

**What goes wrong:** Parent enqueues guidance, but the child already produced a `_is_done_plan` and `break`ed at line 788 before reaching the drain point (line 832). The correction is silently dropped.
**Why it happens:** D-04 explicitly forbids mid-tool preemption; the drain is between iterations only, and the terminating iteration short-circuits before the drain.
**How to avoid:** This is *acceptable per D-04* but must be made deterministic in tests: script the child stub to take ≥2 iterations so the steer is observably consumed before the child's done-iteration. Document the "steer only affects a child that runs another iteration" semantic in the gather/steer tool descriptions so the parent LLM doesn't over-rely on it. The correction-changes-behavior test (MAG-05) must control for this by comparing a ≥2-iteration child with vs without injected guidance. [VERIFIED: agent.py:788 done-break precedes line 832 drain]
**Warning signs:** Flaky steer test; correction "sometimes" applies.

### Pitfall 3: Renderer cross-thread hazard (the renderer.py:7 reconciliation)

**What goes wrong:** A child mutates a Textual widget from off the app's event loop → Textual raises / corrupts the UI.
**Why it happens:** The `renderer.py:7` comment says "subagents run in worker threads". If a planner *believes* that and adds `asyncio.to_thread`/a worker for children, the bridge's direct widget calls become unsafe.
**How to avoid:** Confirmed: today `subagent_run` is dispatched as a plain `await entry.invoke(...)` on the same loop/thread (`agent.py:1104`), NOT in a thread (no `to_thread`/`run_in_executor`/`Thread` in `subagents.py` or the dispatch path — verified by grep). Under D-01 children are `asyncio.create_task` coroutines — **still same loop, same (main) thread**. `renderer._post` (renderer.py:55) checks `threading.current_thread() is threading.main_thread()` and calls directly when true. So the bridge is safe **iff children stay asyncio tasks (not threads)** — which D-01 mandates. Treat the renderer.py:7 comment as scoped to the M9-05 permissions-modal bridge (out of M13 scope), not the M13 fan-out path. Do NOT introduce threads for children. [VERIFIED: grep no to_thread/Thread in subagents.py/agent.py dispatch; renderer.py:55-71 _post logic]
**Warning signs:** `RuntimeError: ... not running in the event loop`; Textual `MessagePump` errors during a child step.

### Pitfall 4: Double-credit on rebalance (MAG-04 must-not-happen)

**What goes wrong:** A child's freed budget is credited to survivors twice (once on its task completing, once on explicit `gather` release), oversell appears on rebalance.
**Why it happens:** Two release paths (task done-callback + gather loop) both call `allocator.release(handle)`.
**How to avoid:** `M13Allocator.release` is idempotent via `self._credited_finished: set` (Pattern 2). First release for a handle credits + rebalances; subsequent releases are no-ops. The mandatory MAG-04 test must call release twice for the same handle and assert `Σ(active) ≤ reserve` and the survivor allotment didn't jump twice. [VERIFIED: O1-RESEARCH double-finalize Pitfall 1 analog; M13 mirrors with a set guard]
**Warning signs:** Survivor `BudgetMeter` total exceeds reserve; `assert sum(active.values()) <= reserve` fails after a finish.

### Pitfall 5: Nested panel id collision (MAG-06)

**What goes wrong:** A grandchild's `SubAgentPanel` uses the same `parent_id` as the child (both derive from a non-unique source), so `app.update_subagent`/`collapse_subagent` (which match by `parent_id`, app.py:178,186) update/remove the wrong panel — or a leak.
**Why it happens:** `SubAgentPanel` widget ids are derived from `parent_id` (`#panel-body-{parent_id}`, `#panel-budget-{parent_id}`, sub_agent_panel.py:57-59). Reusing an id across depth collides at the Textual DOM level.
**How to avoid:** Every spawned child (any depth) gets a fresh `uuid.uuid4().hex[:12]` handle used as its `panel_id`. Grandchildren get their own handles from the *child's* sub-allocator/registry. Assert in the depth-2 test that 3 distinct panel ids exist concurrently and all 3 collapse cleanly (zero `SubAgentPanel` after gather). [VERIFIED: sub_agent_panel.py:57-59 id derivation; app.py:178,186 parent_id match]
**Warning signs:** `DuplicateIds` Textual error; a panel that never collapses; depth-2 test leaves a panel mounted.

### Pitfall 6: "main"-context binding not actually dispatched

**What goes wrong:** `ctrl+o` added to `KEYMAP` with context `"main"` but `VossTUIApp.BINDINGS` only includes `global|input|modal` (`app.py:42`), so the binding is silently never active.
**Why it happens:** M9 `main`-context keys (j/k/g/G/f) are dispatched via a different path than `App.BINDINGS` (likely `TurnView.BINDINGS` or focus routing). Copy-pasting a `global` row would make ctrl+o work but might collide with input typing.
**How to avoid:** Planner must inspect how existing `"main"`-context bindings (`keymap.py:29-36`) reach an action handler and place `ctrl+o` through the *same* mechanism. If `main` bindings are on `TurnView`, add the action there; if M9 actually surfaces them via app focus, follow that. Add a `test_keymap_baseline`-style assertion that `ctrl+o` resolves to `toggle_subagent_detail` in whatever table M9 uses. [VERIFIED: app.py:39-43 filter excludes "main"; keymap.py:29-36 has working main-context rows — dispatch path needs confirmation → Open Question 2]
**Warning signs:** `test_keymap_baseline.py` passes but Ctrl+O does nothing in the running TUI.

### Pitfall 7: Steer kwarg breaks an existing run_turn caller

**What goes wrong:** Adding `steer_inbox` non-additively (positional, or changing call sites) breaks `subagents.run_subagent` / chat / `voss do` callers.
**Why it happens:** `run_turn` has many call sites (cli.py:1362,1695,1782; subagents.py:92; multiagent child).
**How to avoid:** Add `steer_inbox: asyncio.Queue | None = None` as a keyword-only param with a default, threaded `run_turn`→`_run_turn_exec` exactly like the existing optional params (`history`, `cognition`). Only the M13 child passes it. `test_subagent_recursion.py` only forbids `depth`/`max_depth` names — `steer_inbox` is safe. Existing callers unchanged. [VERIFIED: agent.py:412-429 keyword-only optional-default convention; test_subagent_recursion.py:23-40]
**Warning signs:** `TypeError: run_turn() missing/unexpected argument`; `test_subagent_recursion.py` red.

---

## Code Examples

### Verified: the iterative parent loop M13 relies on (no structural change needed)

```python
# Source: voss/harness/agent.py:583-839
while iteration_index < max_iterations:          # max_iterations = cfg.max_iterations (default 8)
    ...
    if _is_done_plan(this_iter_plan):            # line 716 — terminating iter breaks here
        ... ; break                              # (BEFORE the line-832 drain point)
    results = await _run_step_loop(this_iter_plan.steps, ...)   # line 791 tool round
    ...
    all_iter_records.append(rec._iterations[-1])                # line 830
    # <<< M13 D-04 STEER DRAIN INSERTS HERE (line 832) >>>
    if ctx.token_budget and ctx.tokens_used >= ctx.token_budget:  # line 832-837
        exit_reason = "budget"; break
    iteration_index += 1                          # line 839
```

This is *already* a re-planning loop: spawn in iter k, steer in iter k+1, gather in iter k+n. [VERIFIED: codebase read]

### Verified: tool dispatch is same-loop await (no thread)

```python
# Source: voss/harness/agent.py:1104 (_invoke_step_with_gate)
res = await entry.invoke(**step.args)            # same event loop, same thread
```

No `to_thread`/`run_in_executor`/`Thread` anywhere in `subagents.py` or the dispatch path. The renderer.py:7 "worker threads" note does not apply to the M13 path. [VERIFIED: grep + codebase read]

### Verified: collapse_subagent already does M9-08 restore (gather is free)

```python
# Source: voss/harness/tui/app.py:184-207
def collapse_subagent(self, parent_id: str, n_results: int = 0) -> None:
    for panel in list(self.query(SubAgentPanel)):
        if getattr(panel, "parent_id", None) == parent_id:
            panel.remove()
    side = self.query_one("#side")
    if not list(side.query(SubAgentPanel)):
        if not self._side_pinned or self._side_owner == "code_intel":
            self._side_owner = "code_intel"
            ...   # re-mount CodeIntelPanel  (M9-08 contract)
    self.query_one("#main", TurnView).append_turn("gather", f"✓ gathered · {n_results} results")
```

M13's gather calls this once per panel; region restore is automatic. [VERIFIED: codebase read]

### Verified: hermetic scripted streaming provider (D-11 test posture)

```python
# Source: tests/harness/test_agent_loop.py:77-163  (FakeStreamingProvider + _done_script)
class FakeStreamingProvider:
    scripts: list[list[ProviderStreamEvent]]
    def stream(self, **kwargs):
        script = self.scripts[self._stream_index]; self._stream_index += 1
        async def _gen():
            for ev in script: yield ev
        return _gen()
    async def complete(self, **kwargs):  # used by _record_run_call
        return ProviderResponse(text="", parsed=self.record_run_return, ...)

def _done_script(*, plan):  # one scripted iteration
    return [TextDelta("..."), ParsedPlan(plan=plan),
            Usage(prompt_tokens=10, completion_tokens=5, cost_usd=0.001),
            Done(stop_reason="end_turn")]
```

M13 tests script *separate* `scripts` lists for parent and each child stub, controlling iteration counts so steer/concurrency are deterministic. No live network. [VERIFIED: codebase read]

### Verified: BudgetMeter em-dash contract (panel "moves off em-dash" acceptance)

```python
# Source: voss/harness/tui/widgets/sub_agent_panel.py:66-71
def update_budget(self, used: int) -> None:
    self.budget_used = max(0, int(used))
    meter = self.query_one(f"#panel-budget-{self.parent_id}", BudgetMeter)
    meter.used = self.budget_used; meter.total = self.budget_total; meter.refresh()
```

Em-dash placeholder shows only when `budget_total <= 0` (widget docstring + W5 contract). Spawning with a real `allotment` as `budget_total` and ticking `used` satisfies MAG-02's "leaves the em-dash, increments ≥1 time". [VERIFIED: codebase read]

---

## State of the Art

| Old Approach (today) | M13 Approach | Impact |
|----------------------|--------------|--------|
| `subagent_run` `await`s one child to completion (serial, blocking, single child) — subagents.py:92 | Non-blocking `subagent_spawn` → `create_task`, returns handle; concurrent children | MAG-01; parent stays live (MAG-05 possible) |
| Child gets a fresh bare `Renderer`, no panel bridge — subagents.py:91 | Child gets `PanelBridgeRenderer(parent_id=handle)` | MAG-02; dead `show_subagent_progress` finally called |
| No budget scope on child; `SubAgentPanel.budget_total=0` (always em-dash) | M13-local even-split allocator; real `budget_total` per child | MAG-03/04; meter ticks live |
| No child-input channel anywhere in repo | Per-child `asyncio.Queue` drained at run_turn line 832 | MAG-05 |
| `show_subagent_progress` defined but never called (renderer.py:203) | Bridge is its first caller | MAG-02 |
| Flat single-level recursion, no budget on nested | Slice-scoped sub-allocator per child; viable-floor denial | MAG-06 |
| `collapse_subagent` handles only the one serial child | Called per concurrent panel; M9-08 restore reused as-is | MAG-07 |

**Not changed by M13 (back-compat):**
- `subagents.run_subagent` / `attach_subagent_tool` / `SPAWN_TOOL_NAME` — unchanged (serial path stays)
- `/agent spawn` slash (cli.py:1115) and `voss agent spawn` CLI (cli.py:2430) — unchanged
- `SubAgentPanel` / `BudgetMeter` widget classes — unchanged
- `keymap.py:37` Ctrl+C → interrupt — unchanged

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Synthetic parent reserve value (M13 invents one; chat does not pass a `token_budget` today so default is 60_000) | Reserve source | If a "real" parent budget must be the reserve, allocator needs a different source; LOW risk — D-05 says "a parent reserve is carved", value is Claude's-discretion-adjacent. Planner should pick a sensible default reserve (e.g. a fraction of the 60_000 default `token_budget`) and document it. |
| A2 | Steer injection as a synthetic next-iteration user message is the least-invasive route | Pattern 3 | If the child's loop ignores extra `messages` entries, may need the `history`/`EpisodicMemory` route instead; MEDIUM — verify by reading how `messages` (agent.py:601-609) is consumed by the provider stub vs real provider. |
| A3 | `"main"`-context keymap rows are dispatched via TurnView/focus, not `App.BINDINGS` | Pattern 5 / Pitfall 6 / OQ2 | If ctrl+o is placed in the wrong table it silently no-ops; MEDIUM — planner MUST trace the M9 main-context dispatch path before placing the binding. |
| A4 | Defensive gather-on-teardown is needed to prevent orphaned tasks/panels | Pitfall 1 | If the parent LLM/stub always gathers, the safety net is belt-and-suspenders; LOW — adding it is cheap and strictly safer. |
| A5 | `renderer.py:7` worker-thread note does not apply to the M13 asyncio-task path | Pitfall 3 | If some path *does* run children in threads, bridge needs `call_from_thread`; LOW — verified no threads in dispatch, and `_post` already handles both cases anyway. |

**These five are the items discuss-phase already partially covered (Claude's Discretion); A2 and A3 are the two that most need confirmation during planning.**

---

## Open Questions (RESOLVED)

1. **How does the parent turn stay live between spawn and gather within ONE chat turn? — RESOLVED.**
   - What we know: `cli.py:1695` calls `run_turn(line, ...)` per chat input; `_run_turn_exec` is an iterative while-loop (`agent.py:583`, `max_iterations` default 8).
   - Resolution: No structural change to the parent loop. A non-blocking `subagent_spawn` (`create_task` + immediate return) lets the parent's *subsequent* iterations call `steer` then `gather`. Children progress as asyncio tasks whenever the parent `await`s the provider. The ONLY requirement: the parent stub/LLM must take ≥3 iterations (spawn/steer/gather). Tests script this deterministically. Confidence HIGH after reading agent.py:583-839 + 716/788 break points + 1104 dispatch.

2. **Which dispatch table actually fires `"main"`-context keymap bindings? — RESOLVED (M13-04 `<oq_a3_resolution>`).**
   - What we know: `VossTUIApp.BINDINGS` filters to `global|input|modal` (`app.py:42`), yet `keymap.py:29-36` has working `"main"` rows (j/k/g/G/f/ctrl+f).
   - What's unclear: Whether those reach an action via `TurnView.BINDINGS`, app focus routing, or a separate M9 mechanism.
   - **Resolution (M13-04, verified against live code):** `"main"` is M9's *declarative single-source registry tier* — `TurnView` has no `BINDINGS`/actions and no `action_scroll_*`/`jump_*`/`open_search` handlers exist; the `"main"` contract = a `KEYMAP` row **+** an `action_<name>` method on `VossTUIApp` (the `action_fork_turn` precedent, `app.py:136`), with `test_keymap_baseline.py` as that contract's acceptance test. `ctrl+o` is placed on exactly that mechanism (KEYMAP row + `VossTUIApp.action_toggle_subagent_detail`), not a `TurnView.BINDINGS`, not a widened `App.BINDINGS` filter, not a `"global"` row; proven by the additive keymap-baseline resolution assertion. (Pitfall 6 / A3.)

3. **Steer injection mechanism: synthetic message vs shared `EpisodicMemory`. — RESOLVED (M13-03 Task 1).**
   - What we know: child `run_turn` builds `messages` fresh each iter (agent.py:601) and reads `history.last(6)` into `history_block` (agent.py:514).
   - **Resolution (M13-03 Task 1, verified against live code):** synthetic next-iteration user message is the **only** correct route, not merely "recommended" — `history_block` is built once before the loop and never rebuilt (`agent.py:513-519`), so a shared-`EpisodicMemory` route physically cannot surface a mid-run steer. The :830 drain buffers into `pending_steer`, injected as one `{"role":"user"}` entry in the per-iteration `messages` build (agent.py:599-610) and cleared after one injection; no shared mutable state across the loop boundary; the correction-changes-behavior stub script branches on injected-guidance presence to prove behavior change. (A2.)

---

## Reserve source (MAG-03 grounding — answers research question 4)

**Where does the parent budget / `ctx(budget:)` value live in chat today?** It does **not** — the chat `run_turn` call (`cli.py:1695`) passes NO `token_budget`, so `_run_turn_exec` uses the default `token_budget: int = 60_000` (`agent.py:419`). The `ContextScope(token_budget=token_budget, ...)` (agent.py:580) wraps the parent turn at 60k. There is no per-spawn budget anywhere today (`SubAgentPanel.budget_total` is fed `0` → em-dash, confirmed renderer.py:175 `int((args).get("budget_total") or 0)`).

**Therefore M13 must invent the reserve** (consistent with D-05 "a parent reserve is carved"). Recommended: the `M13Allocator` takes an explicit `reserve` int chosen at fan-out time — a sensible default is a fraction of the parent's effective `token_budget` (e.g. carve `reserve` from the 60_000 default, leaving the parent its own working budget). The exact value is Claude's-discretion-adjacent (A1); the planner should pick one, document it, and make it the allocator constructor arg. The recursive case: a child's sub-allocator `reserve` = that child's `allotment` (slice-scoped, D-07). The viable-floor (also Claude's discretion) must be < `reserve // expected_fanout` so a first spawn is allowed but unbounded recursion is denied — a sensible default floor is in the low thousands of tokens (enough for ≥1 child iteration). [VERIFIED: cli.py:1695 (no token_budget arg), agent.py:419,580, renderer.py:175]

---

## Environment Availability

All dependencies stdlib or project-internal. No external tools/services to probe.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `asyncio` (stdlib) | fan-out, queue, lock | ✓ | Python 3.11+ | — |
| `uuid` (stdlib) | handle ids | ✓ | Python 3.11+ | — |
| `voss.harness.agent.run_turn` | child loop | ✓ | project | — |
| `voss.harness.tui` (`SubAgentPanel`,`app`) | render bridge | ✓ | project | — |
| `pytest` + `pytest-asyncio` | async/concurrency tests | ✓ | `asyncio_mode="auto"` in pyproject.toml | — |
| Textual `App.run_test()` pilot | TUI reveal/teardown tests | ✓ | used by `test_live_visualization.py` | — |

**No missing dependencies.** No fallbacks needed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8+ with pytest-asyncio (`asyncio_mode="auto"` — no `@pytest.mark.asyncio` needed; verified O1-RESEARCH + pyproject.toml) |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `pytest tests/harness/test_multiagent_fanout.py -x -q` |
| Full suite command | `pytest tests/harness/ tests/e2e/test_multiagent_chat_e2e.py -x -q` |
| Provider posture | Hermetic `FakeStreamingProvider` (test_agent_loop.py:77) — scripted per-agent `stream()`, `complete()` for `_record_run_call`; NO live network (D-11) |
| TUI posture | `VossTUIApp().run_test()` + `pilot.pause()` (test_live_visualization.py precedent) |

### Phase Requirements → Test Map

| Req | Observable signal / test seam | Test Type | Automated Command | File Exists? |
|-----|-------------------------------|-----------|-------------------|-------------|
| MAG-01 | ≥2 children observably in-flight at the same instant: each child stub records a wall-clock window; assert window overlap (NOT serial). Spy `ChildRegistry.active()` ≥ 2 between spawn and gather. | unit/concurrency | `pytest tests/harness/test_multiagent_fanout.py::TestConcurrentInFlight -x` | ❌ Wave 0 |
| MAG-02 | (a) `SubAgentPanel` `BudgetMeter` leaves em-dash and `update_budget` called ≥1×/child before collapse (assert `meter.total>0` and `used` increments). (b) Body `Vertical` `display==none` by default; after `action_toggle_subagent_detail` it contains ≥1 streamed step Static. | TUI (pilot) | `pytest tests/harness/tui/test_subagent_reveal.py -x` | ❌ Wave 0 |
| MAG-03 | With reserve R, N children: each `allocator.snapshot()[h] ≈ R//N`; after one child `release()`, a survivor's allotment strictly increases; panel `BudgetMeter` reflects the new total. | unit | `pytest tests/harness/test_multiagent_fanout.py::TestEvenSplitRebalance -x` | ❌ Wave 0 |
| MAG-04 (must-not-happen) | **Recursive no-oversell race:** `asyncio.gather(*[allocator.allocate(h) for h in many])` against R; assert `sum(allocator.snapshot().values()) <= R` AND denied-count matches floor math. **Exactly-once:** call `release(h)` twice; assert survivor allotment did not double-credit and Σ ≤ R. **Depth-bound:** grandchild allotment ≤ child slice. | unit/concurrency | `pytest tests/harness/test_multiagent_fanout.py::TestNoOversell -x` | ❌ Wave 0 |
| MAG-05 | Scripted parent enqueues guidance via `subagent_steer` mid-run; child stub script BRANCHES on guidance presence (e.g. emits different `final`). Assert child output WITH correction != no-correction control, and the steer was consumed at the line-832 drain (≥2 child iterations). | unit | `pytest tests/harness/test_multiagent_steer.py::TestCorrectionChangesBehavior -x` | ❌ Wave 0 |
| MAG-06 | Depth-2: parent→child→grandchild. Assert (a) 3 distinct `panel_id`s mounted concurrently; (b) grandchild allotment ≤ child slice ≤ parent reserve at all 3 levels; (c) after gather, zero `SubAgentPanel` mounted (no leak). | unit + TUI | `pytest tests/harness/test_multiagent_recursion.py::TestDepth2 -x` | ❌ Wave 0 |
| MAG-07 | After multi-child fan-out + gather: parent turn result string references all child handles/results; `len(app.query(SubAgentPanel))==0`; `app._side_owner`/`_side_pinned` match pre-spawn snapshot (M9-08). | TUI (pilot) | `pytest tests/harness/tui/test_subagent_reveal.py::TestPostGatherRegionClean -x` | ❌ Wave 0 |
| MAG-08 | One stub-provider `voss chat` e2e: 1 NL request → ≥2 concurrent panels, ≥1 budget tick/child, ≥1 applied correction, ≥1 rebalance event, aggregated multi-child turn output, clean post-gather region — ALL asserted in one test. | e2e | `pytest tests/e2e/test_multiagent_chat_e2e.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/harness/test_multiagent_fanout.py -x -q` (+ the specific new file the task touched)
- **Per wave merge:** `pytest tests/harness/ -x -q && pytest tests/harness/test_subagent_recursion.py -x -q` (regression: back-compat pinning test MUST stay green)
- **Phase gate:** `pytest tests/harness/ tests/harness/tui/ tests/e2e/test_multiagent_chat_e2e.py -x -q` fully green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/test_multiagent_fanout.py` — concurrency proof (MAG-01), even-split+rebalance (MAG-03), no-oversell race + exactly-once + depth-bound (MAG-04)
- [ ] `tests/harness/test_multiagent_steer.py` — correction-changes-behavior vs control (MAG-05)
- [ ] `tests/harness/test_multiagent_recursion.py` — depth-2 nested budget + nested panels + no-leak (MAG-06)
- [ ] `tests/harness/tui/test_subagent_reveal.py` — quiet-by-default + ctrl+o reveal (MAG-02), post-gather region clean (MAG-07)
- [ ] `tests/e2e/test_multiagent_chat_e2e.py` — headline transcript (MAG-08); model on `tests/e2e/test_chat_e2e.py` (stdin-script) + `tests/e2e/runner.py` `CliRunner`
- [ ] Shared fixture: a scripted multi-agent provider (parent script + per-child scripts) extending `FakeStreamingProvider` (test_agent_loop.py:77) — likely a new conftest fixture in `tests/harness/`
- [ ] Regression guard: `tests/harness/test_subagent_recursion.py` MUST pass unmodified (no `depth`/`max_depth`/`MAX_DEPTH` added)
- [ ] Keymap-baseline assertion that `ctrl+o → toggle_subagent_detail` resolves (extend `tests/harness/tui/test_keymap_baseline.py`) and `ctrl+c` still → `interrupt`

*Framework already present (pytest + pytest-asyncio + Textual pilot). All gaps are new test files, not infra.*

---

## Security Domain

`security_enforcement` not explicitly disabled in config — section included. M13 adds no auth/session/crypto surface; it is in-memory orchestration of an already-trusted local agent.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no auth surface) |
| V3 Session Management | no | — (in-memory, chat-turn-scoped, no persisted session) |
| V4 Access Control | partial | Child inherits the parent's `PermissionGate` (same as today's `run_subagent`, subagents.py:85); no privilege escalation introduced — children get the SAME gate, not a broader one |
| V5 Input Validation | yes (partial) | Steer guidance + task strings are LLM/parent-controlled text passed as message content; treated as data (no eval/exec); `asyncio.Queue` carries plain strings |
| V6 Cryptography | no | — (no crypto) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded recursive spawn (resource exhaustion) | Denial of Service | Viable-budget-floor denial in `M13Allocator.allocate` (D-07) — recursion bounded without a depth constant |
| Budget oversell race (allocator) | Tampering | `asyncio.Lock` check-and-allocate (D-06, O1-proven) |
| Orphaned child tasks after parent turn ends | Denial of Service | Defensive gather/cancel-on-teardown safety net (Pitfall 1) |
| Steer message to wrong/finished child | Tampering | `ChildRegistry.get(handle)` validates handle; steer to a `done` child is a no-op (queue drained never) — assert in steer test |
| Cross-thread UI corruption | Tampering | Children stay asyncio tasks (NOT threads); `renderer._post` main-thread-safe (Pitfall 3) |
| Permission escalation via child | Elevation of Privilege | Child reuses parent `PermissionGate` unchanged (no broader scope granted) — same posture as existing `run_subagent` |

**No new secret material, no new network egress, no new persisted data.** M13's blast radius is in-memory + UI only.

---

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` in the Voss project root (verified — only `~/.claude/CLAUDE.md` global + memory sidecar, neither project-binding for code). Constraints derive from `.planning/` + global behavioral guidelines:

- **Surgical changes (global guideline 3):** M13 must be additive. New `multiagent.py`; one additive `run_turn` kwarg; one additive keymap row; one additive `app` action. Do NOT refactor `subagents.py`, `agent.py` loop structure, or the widgets.
- **Simplicity first (global guideline 2):** No speculative abstraction. The allocator is ~30 lines (copied O1 pattern), not a generic budget framework. No new widget types (D-08).
- **Voss conventions (STATE.md / O1 precedent):** Python harness (not Rust/TS); stdlib + `voss_runtime` only; no new third-party deps; `uuid.uuid4().hex[:12]` id scheme; `from __future__ import annotations` header; class-based pytest with `tmp_path`; deterministic hermetic stub-provider tests (T7/T8/O1).
- **Back-compat is a hard constraint (D-02 + SPEC):** `/agent spawn` slash, `voss agent spawn` CLI, `subagent_run` serial tool, `SPAWN_TOOL_NAME`, `test_subagent_recursion.py` all stay working/green.
- **`.voss/` durability (PROJECT.md):** N/A — M13 writes NO disk state (D-02; O1 owns persistence).

---

## Sources

### Primary (HIGH confidence — all codebase-read or design-locked)

- `voss/harness/subagents.py` — `run_subagent` (serial `await` at :92), `attach_subagent_tool`, `SPAWN_TOOL_NAME` [VERIFIED: read]
- `voss/harness/agent.py` — `_run_turn_exec` iterative loop (:583), done-break (:716,:788), step round (:791), **steer-drain boundary (:832)**, budget check (:832-837), CancelledError handler (:985), tool dispatch `await` (:1104), `_serialize_iter_for_replay` (:354), default `token_budget=60_000` (:419) [VERIFIED: read]
- `voss/harness/cli.py` — chat `run_turn` call w/o token_budget (:1695), `attach_subagent_tool` wiring (:1634), `/agent` slash (:1115), `voss agent spawn` (:2430), `_run_turn_cancellable` (:262) [VERIFIED: read]
- `voss/harness/tui/renderer.py` — dead `show_subagent_progress` (:203), `_post` thread logic (:55), worker-thread note scope (:7), `SPAWN_TOOL_NAME` detection (:170-181) [VERIFIED: read]
- `voss/harness/tui/app.py` — `mount_subagent_panel` (:169), `update_subagent` (:176), `collapse_subagent` + M9-08 restore (:184-207), `BINDINGS` filter excludes "main" (:39-43), `action_interrupt` (:113), `register_turn_task` (:75) [VERIFIED: read]
- `voss/harness/tui/widgets/sub_agent_panel.py` — `append_body`/`update_budget` (:61-71), em-dash contract, body `Vertical` id scheme (:57-59) [VERIFIED: read]
- `voss/harness/tui/keymap.py` — `Binding` dataclass, `ctrl+c→interrupt` (:37), main-context rows (:29-36) [VERIFIED: read]
- `voss_runtime/budget.py` — `BudgetScope` ContextVar re-entry semantics, single-loop model [VERIFIED: read]
- `voss_runtime/agent.py` — `VossAgent.spawn`/`AgentHandle`/`gather` confirmed as a SEPARATE `asyncio.create_task` wrapper NOT wired to chat (LOCKED out) [VERIFIED: grep :74-109]
- `tests/harness/test_subagent_recursion.py` — pinning test forbids `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` [VERIFIED: read]
- `tests/harness/test_agent_loop.py` — `FakeStreamingProvider`/`_done_script` hermetic scripted-stream pattern (:77-163) [VERIFIED: read]
- `tests/harness/tui/test_live_visualization.py` — `run_test()` pilot + SubAgentPanel mount/collapse precedent [VERIFIED: read]
- `tests/e2e/test_chat_e2e.py` — stdin-scripted `voss chat --plain` e2e precedent [VERIFIED: read]
- `.planning/phases/M13-SPEC.md` + `M13-CONTEXT.md` — MAG-01..08, D-01..D-11 (LOCKED) [VERIFIED: read]
- `.planning/phases/O1-RESEARCH.md` / `O1-PATTERNS.md` — `asyncio.Lock` allocator Pattern 2 (lifted as M13-local copy), no-oversell live race precedent, reserve/token_budget interplay [VERIFIED: read]

### Secondary (MEDIUM confidence — needs planning confirmation)

- Steer injection via synthetic next-iteration message vs shared `EpisodicMemory` (A2 — confirm against provider message consumption)
- `"main"`-context keymap dispatch path (A3 — confirm `TurnView.BINDINGS`/focus routing before placing `ctrl+o`)

### Tertiary (LOW confidence / ASSUMED)

- Exact reserve value and viable-floor threshold (A1 — Claude's-discretion-adjacent; planner picks + documents a sensible default)

---

## Metadata

**Confidence breakdown:**
- Fan-out shape / parent-stays-live (MAG-01/05): HIGH — resolved by reading the actual iterative loop + dispatch path
- Allocator (MAG-03/04/06): HIGH — direct lift of O1's live-race-proven Pattern 2
- Steer boundary (MAG-05/D-04): HIGH for the *location* (agent.py:832 verified); MEDIUM for the *injection mechanism* (A2)
- Renderer bridge / thread reconciliation (MAG-02): HIGH — verified no threads in dispatch; `_post` handles both
- Keymap reveal (MAG-02/D-09): MEDIUM — "main"-context dispatch path needs confirmation (Pitfall 6 / OQ2)
- Gather/teardown (MAG-07): HIGH — `collapse_subagent` already does M9-08 restore
- Test posture (MAG-08): HIGH — `FakeStreamingProvider` + pilot + chat-e2e precedents all exist

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (stable Python harness; re-verify only if `agent.py` loop, `subagents.py`, or `tui/app.py` change)
