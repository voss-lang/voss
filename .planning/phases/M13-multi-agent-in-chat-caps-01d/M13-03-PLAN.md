---
phase: M13-multi-agent-in-chat-caps-01d
plan: 03
type: execute
wave: 2
depends_on: [M13-02]
files_modified:
  - voss/harness/multiagent.py
  - voss/harness/agent.py
  - tests/harness/test_multiagent_fanout.py
autonomous: true
requirements: [MAG-01, MAG-05]
must_haves:
  truths:
    - "A chat-attached subagent_spawn tool call schedules a child as a detached asyncio task and returns a handle string in the SAME tool round (no await on child completion)"
    - "Two or more children are observably in-flight at the same instant between spawn and gather (overlapping run windows, ChildRegistry.active() >= 2), not awaited one-by-one"
    - "subagent_gather joins all outstanding child tasks concurrently, releases each allotment exactly once, aggregates every child result into the parent turn, and collapses each panel"
    - "A scripted parent that calls subagent_steer mid-run into a still-running child observably changes that child's subsequent output versus the no-correction control"
    - "On parent run_turn exit with un-gathered handles, the defensive safety net cancels orphan child tasks and collapses their panels so nothing leaks"
    - "run_turn / _run_turn_exec accept an additive keyword-only steer_inbox; existing callers (subagents.run_subagent, cli chat, voss do) are unchanged and test_subagent_recursion.py stays green"
  artifacts:
    - path: "voss/harness/multiagent.py"
      provides: "Non-blocking subagent_spawn/steer/status/gather tools, PanelBridgeRenderer, attach_multiagent_tools, defensive gather-on-teardown safety net"
      contains: "def attach_multiagent_tools"
    - path: "voss/harness/agent.py"
      provides: "Additive keyword-only steer_inbox kwarg threaded run_turn -> _run_turn_exec + D-04 drain between line 830 (all_iter_records.append) and line 832 (budget check)"
      contains: "steer_inbox"
  key_links:
    - from: "voss/harness/multiagent.py subagent_spawn"
      to: "asyncio.create_task(run_turn(..., steer_inbox=queue))"
      via: "detached task creation, NO await on child"
      pattern: "asyncio\\.create_task"
    - from: "voss/harness/agent.py _run_turn_exec line ~830 drain"
      to: "next-iteration messages list (line ~601-609)"
      via: "steer-buffer captured at drain, consumed as synthetic user message on next loop"
      pattern: "steer_inbox"
    - from: "voss/harness/multiagent.py subagent_gather"
      to: "M13Allocator.release + app.collapse_subagent"
      via: "asyncio.gather(return_exceptions=True) then release-each then end_panel-each"
      pattern: "asyncio\\.gather"
---

<objective>
Wave 2A harness fan-out. Extend the M13-02 `voss/harness/multiagent.py` module (created in the prior wave with `M13Allocator`, `ChildHandle`, `ChildRegistry`) with the four non-blocking orchestration tools, the `PanelBridgeRenderer`, the `attach_multiagent_tools(...)` entry point, and a defensive gather-on-teardown safety net. Add ONE additive keyword-only `steer_inbox: asyncio.Queue | None = None` parameter to `run_turn` / `_run_turn_exec` and the D-04 inbox drain at the verified loop boundary (between `agent.py:830` `all_iter_records.append` and `:832` budget check).

This is the wiring that makes concurrent fan-out (MAG-01) and autonomous mid-run course-correction (MAG-05) actually work on the hardened `subagent_run` path — harness-local asyncio (`create_task`/`gather`), explicitly NOT `VossAgent.spawn`.

Purpose: The serial blocking `subagent_run` (`subagents.py:92` `result = await run_turn(...)`) makes mid-run steering structurally impossible. Inverting the await into `asyncio.create_task` + immediate handle return lets the parent's *next* loop iteration steer then gather while children run as detached tasks on the same loop.

Output: `voss/harness/multiagent.py` extended with `subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather` + `PanelBridgeRenderer` + `attach_multiagent_tools` + teardown safety net; `voss/harness/agent.py` with the additive `steer_inbox` kwarg + line-830 drain. Greens MAG-01 concurrency-overlap and MAG-05 correction-vs-control test classes from the M13-01 Wave 0 scaffold.
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
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-RESEARCH.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md

<interfaces>
<!-- Contracts from M13-02 (depends_on). The executor uses these directly; do NOT redefine. -->
<!-- From voss/harness/multiagent.py (created in M13-02, this plan EXTENDS the same file): -->

ChildHandle (dataclass, NOT frozen — done/result mutate):
  handle: str               # uuid.uuid4().hex[:12]
  task: asyncio.Task | None
  queue: asyncio.Queue      # D-03 per-child steer inbox
  panel_id: str             # SubAgentPanel parent_id (== handle)
  allotment: int            # tokens this child owns (D-05)
  sub_allocator: M13Allocator   # D-07 slice-scoped (recursion is M13-05, not here)
  done: bool = False
  result: str | None = None

ChildRegistry (in-memory, chat-turn-scoped, NO disk):
  add(h: ChildHandle) -> None
  get(handle: str) -> ChildHandle | None
  active() -> list[ChildHandle]   # not done
  all() -> list[ChildHandle]

M13Allocator (asyncio.Lock check-and-allocate; from M13-02):
  __init__(*, reserve: int, viable_floor: int)
  viable_floor -> int                 # property
  async allocate(handle: str) -> int | None   # None == below viable floor (denied)
  async release(handle: str) -> None  # idempotent via _credited_finished set (exactly-once)
  snapshot() -> dict[str, int]        # handle -> current allotment, for BudgetMeter ticks

<!-- M13-02 also documents the chosen synthetic parent `reserve` default and viable-floor
     threshold (RESEARCH OQ-A1). This plan consumes those values; it does NOT re-pick them.
     Read the M13-02 SUMMARY / multiagent.py module docstring for the exact numbers. -->
</interfaces>

<read_first>
Before writing ANY code, the executor MUST read:

1. `voss/harness/multiagent.py` — the M13-02 module being EXTENDED. Confirm the exact
   `M13Allocator` / `ChildHandle` / `ChildRegistry` signatures and the chosen reserve +
   viable-floor defaults (documented there per OQ-A1). This plan adds to that file; it
   does NOT recreate the M13-02 symbols.
2. `voss/harness/subagents.py:76-135` — Analog B (`run_subagent` child-launch body to
   INVERT — line 92 `result = await run_turn(...)` is the exact anti-pattern) + Analog A
   (`attach_subagent_tool` tool-registration idiom: `@tool(name=..., description=...)` →
   `tools[name] = ToolEntry(descriptor=..., is_mutating=True)`; same param list
   `registry, cwd, renderer, provider, model, gate, cognition`). `make_toolset(cwd,
   renderer=renderer)` + `EpisodicMemory(capacity=20)` child construction shape.
3. `voss/harness/agent.py:412-480` — `run_turn` signature + the `_run_turn_exec(...)`
   delegation call (the keyword-only optional-default convention: `history`, `cognition`,
   `prior_context` — `steer_inbox` is threaded EXACTLY like these).
4. `voss/harness/agent.py:481-500` — `_run_turn_exec` signature (add the kwarg here too).
5. `voss/harness/agent.py:510-527` — **OQ-A2 evidence:** `history_block` is built ONCE
   before the while-loop from `history.last(6)` (lines 513-519). The `history`/
   `EpisodicMemory` route is a turn-start snapshot — it is NEVER rebuilt mid-loop, so it
   CANNOT surface a mid-run steer. This is why the synthetic-message route is the ONLY
   correct route, not merely "recommended".
6. `voss/harness/agent.py:599-610` — the per-iteration `messages: list[dict]` build
   (system sys_blocks, system rider, user user_prompt, then `_serialize_iter_for_replay`
   for each prior). **This list is rebuilt EVERY iteration** — the steer landing site.
7. `voss/harness/agent.py:783-840` — the two `all_iter_records.append` sites: line ~787
   (terminating `_is_done_plan` branch, `break`s — drain MUST NOT go here, a "done" child
   never consumes a pending steer per D-04), and line ~830 (non-terminating branch). The
   drain inserts BETWEEN line 830 (`all_iter_records.append(rec._iterations[-1])`) and
   line 832 (`if ctx.token_budget and ctx.tokens_used >= ctx.token_budget`), before
   `iteration_index += 1` (line 839).
8. `M13-RESEARCH.md` Pattern 1 (lines 207-255, non-blocking spawn), Pattern 3 (lines
   309-352, drain boundary + injection mechanism + OQ-A2/A2 assumption), Pattern 4 (lines
   354-392, PanelBridgeRenderer), Pattern 6 (lines 415-435, gather + M9-08 teardown),
   Anti-Patterns (lines 437-445), Pitfall 1 (lines 483-487, defensive teardown net),
   Pitfall 2 (lines 490-495, steer-after-done semantic), Pitfall 7 (lines 525-529,
   additive-kwarg constraint), Assumption A2 (line 643), Open Question 3 (lines 663-665).
9. `M13-PATTERNS.md` §`multiagent.py` (Analog A/B/C), §`agent.py` (drain VERIFIED at
   :830-839, "Hard constraints" — do NOT restructure the while-loop, do NOT touch the
   `asyncio.CancelledError` handler), §"Open Items the Planner Must Resolve" item 2.
10. `M13-VALIDATION.md` Per-Task Verification Map rows MAG-01 and MAG-05 + §"Security
    Domain" (T-M13 oversell / mis-steer / orphan / ui-thread / priv).
</read_first>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Additive steer_inbox kwarg + D-04 inbox drain in agent.py (resolves RESEARCH OQ-A2)</name>
  <files>voss/harness/agent.py</files>
  <read_first>
    agent.py:412-480 (run_turn sig + _run_turn_exec delegation), :481-500
    (_run_turn_exec sig), :510-527 (history_block built once — OQ-A2 evidence),
    :599-610 (per-iteration messages build — steer landing site), :783-840 (both
    all_iter_records.append sites; drain goes between :830 and :832).
    M13-RESEARCH.md Pattern 3 (lines 309-352) + Open Question 3 (lines 663-665) +
    Assumption A2 (line 643). M13-PATTERNS.md §agent.py "Hard constraints".
  </read_first>
  <behavior>
    - Test: `pytest tests/harness/test_multiagent_steer.py::TestCorrectionChangesBehavior -x` — a scripted parent injects guidance into a running child (>= 2 child iterations); child stub BRANCHES on the presence of the injected steering text in its `messages` and emits a different `final`; WITH-correction output != no-correction control output.
    - Test: existing `pytest tests/harness/test_subagent_recursion.py -x -q` still passes UNMODIFIED (no `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` introduced; `steer_inbox` is a permitted additive name).
    - Test: `pytest tests/harness/test_agent_loop.py -x -q` still passes (existing run_turn callers unaffected — kwarg is keyword-only with a default).
    - Edge: when `steer_inbox is None` (every existing caller) the loop behaves byte-identically to before — drain block is fully skipped.
    - Edge: a child that reaches the terminating `_is_done_plan` branch (line ~787) `break`s BEFORE the drain at :830 — a pending steer is NOT consumed (acceptable per D-04 / Pitfall 2; the steer test scripts >= 2 child iterations precisely to observe consumption).
  </behavior>
  <action>
    Add `steer_inbox: asyncio.Queue | None = None` as ONE keyword-only parameter with a default, placed alongside the existing optional-default params (mirror `history` / `cognition` / `prior_context`) in BOTH `run_turn` (after the existing `*,` keyword-only block) and `_run_turn_exec`. Thread it `run_turn` -> `_run_turn_exec` in the delegation call exactly like `history=history` / `cognition=cognition` are threaded (additive — Pitfall 7: a non-additive/positional change breaks `subagents.run_subagent`, cli chat, and `voss do` callers and would trip the `test_subagent_recursion.py` pin). Confirm `import asyncio` is already present at module top (it is — used by `asyncio.Semaphore`/`asyncio.gather`); do NOT add a duplicate import. `asyncio.QueueEmpty` is accessed via the existing `asyncio` import.

    Add a per-turn steer buffer local: introduce `pending_steer: list[str] = []` in the loop-scoped state block (next to `all_iter_records: list[IterationRecord] = []`, around line 583's loop-scoped state region).

    Resolve RESEARCH OQ-A2 (steer injection mechanism) DEFINITIVELY with the synthetic next-iteration user message route — and document WHY the alternative is wrong: `history_block` is built ONCE before the while-loop from `history.last(6)` (agent.py:513-519) and is NEVER rebuilt mid-loop, so mutating the `history`/`EpisodicMemory` object after turn start cannot surface a mid-run steer. The per-iteration `messages` list (agent.py:599-610) IS rebuilt every loop entry. Therefore the synthetic-message route is the ONLY route that lands mid-loop (not merely the "least-invasive" one — RESEARCH Open Question 3 / Assumption A2 are hereby resolved: synthetic message, no shared mutable history).

    DRAIN (between line 830 `all_iter_records.append(rec._iterations[-1])` in the NON-terminating branch and line 832 `if ctx.token_budget and ctx.tokens_used >= ctx.token_budget`, before line 839 `iteration_index += 1`): if `steer_inbox is not None`, non-blockingly drain it — loop `while not steer_inbox.empty():` with `try: drained.append(steer_inbox.get_nowait())` guarded by `except asyncio.QueueEmpty: break`; extend `pending_steer` with the drained strings. Do NOT add any new recorder hook (`rec.note_steer` was a RESEARCH sketch only — keep agent.py recorder surface unchanged; the steer is carried purely in the `pending_steer` local). Do NOT place the drain in the terminating `_is_done_plan` branch (line ~787) — that branch `break`s and a "done" child must not consume a pending steer (D-04 / Pitfall 2).

    INJECTION (in the per-iteration `messages` build, agent.py:599-610): after the existing `for prior in all_iter_records: ... messages.append(a_msg); messages.append(u_msg)` replay loop, if `pending_steer` is non-empty, append exactly one synthetic message `{"role": "user", "content": "[steering from parent agent]\n" + "\n".join(pending_steer)}` to `messages`, then clear `pending_steer` (`pending_steer.clear()`) so the same guidance is injected once and not re-appended on every subsequent iteration. This is a sibling to the replay messages — no mutation of `all_iter_records`, no mutation of `history`/`EpisodicMemory`, no shared mutable state across the loop boundary (deterministic under the stub provider).

    HARD CONSTRAINTS (M13-PATTERNS §agent.py): do NOT restructure the `while iteration_index < max_iterations:` loop. Do NOT touch the `asyncio.CancelledError` handler (line ~985, outside the loop body — preserves the Ctrl+C interrupt contract) or the `BatchInvariantError` handler. Additive insertions only: one kwarg (x2 signatures + x1 delegation), one loop-scoped local, one drain block, one conditional synthetic-message append. Document the messages-list landing trace in a 2-3 line code comment at the injection site referencing agent.py:513-519 (why-not-history) and Pattern 3.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_multiagent_steer.py::TestCorrectionChangesBehavior tests/harness/test_subagent_recursion.py tests/harness/test_agent_loop.py -x -q</automated>
  </verify>
  <done>steer_inbox is a keyword-only defaulted param on both run_turn and _run_turn_exec, threaded in the delegation; the D-04 drain sits strictly between agent.py:830 and :832; injected guidance lands as a single synthetic user message in the next iteration's messages list and is cleared after one injection; TestCorrectionChangesBehavior asserts WITH-correction != control; test_subagent_recursion.py and test_agent_loop.py pass unmodified; steer_inbox=None path is byte-equivalent to pre-change behavior.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Non-blocking subagent_spawn/steer/status/gather tools + PanelBridgeRenderer + attach_multiagent_tools + teardown safety net</name>
  <files>voss/harness/multiagent.py, tests/harness/test_multiagent_fanout.py</files>
  <read_first>
    voss/harness/multiagent.py (M13-02 module — EXTEND, confirm M13Allocator/
    ChildHandle/ChildRegistry signatures + the documented OQ-A1 reserve + viable-floor
    defaults). voss/harness/subagents.py:76-135 (Analog A tool-attach idiom +
    Analog B child-launch body to INVERT — line 92 await is the anti-pattern;
    make_toolset / EpisodicMemory(capacity=20) child shape).
    M13-RESEARCH.md Pattern 1 (207-255), Pattern 4 (354-392), Pattern 6 (415-435),
    Anti-Patterns (437-445), Pitfall 1 (483-487 — defensive teardown), Pitfall 2
    (490-495 — steer-after-done semantic for tool descriptions). M13-PATTERNS.md
    §multiagent.py (Analog A/B/C), Shared Patterns (tool registration idiom,
    thread-safe widget mutation, M9-08 region-restore reuse). M13-VALIDATION.md
    MAG-01/MAG-05 rows + §Security Domain.
  </read_first>
  <behavior>
    - Test: `pytest tests/harness/test_multiagent_fanout.py::TestConcurrentInFlight -x` — a scripted parent + N child providers; assert `ChildRegistry.active() >= 2` observably between spawn and gather (overlapping in-flight windows, NOT awaited one-by-one); each child stub records a wall-clock run window and the windows overlap.
    - Test: `pytest tests/harness/test_multiagent_steer.py -x` — `subagent_steer(handle, guidance)` enqueues to the targeted child's `asyncio.Queue`; steer to an unknown handle is a no-op (returns a benign string, no raise); steer to a `done` child is a no-op (T-M13 mis-steer mitigation).
    - Test: `pytest tests/harness/test_multiagent_fanout.py -x` — `subagent_gather` joins all outstanding tasks via `asyncio.gather(return_exceptions=True)`, calls `allocator.release` once per handle, aggregates each child result into the returned turn string, and triggers `collapse_subagent` per panel.
    - Edge: parent `run_turn` exits with un-gathered handles -> the defensive teardown safety net cancels orphan child tasks and collapses their panels (T-M13 orphan; zero leaked tasks/panels).
    - Test (T-M13-02 mitigation gate — NEW, added by this task to `tests/harness/test_multiagent_fanout.py`): `TestOrphanTeardown` drives a scripted parent that calls `subagent_spawn` but NEVER `subagent_gather`; after the parent turn ends, awaiting `_teardown_orphans()` cancels the still-running child task (`task.cancelled()` is True), calls `allocator.release` for it, and invokes the bridge `end_panel` (panel collapsed); `ChildRegistry` has no live/un-released handle afterward. This is the explicit automated proof that the orphan-DoS mitigation is wired, not just present.
    - Edge: `subagent_spawn` when `allocator.allocate` returns `None` (below viable floor) returns a `<denied: ...>` string and does NOT create a task (recursion bound; this is the spawn-denial surface M13-05 relies on).
  </behavior>
  <action>
    EXTEND `voss/harness/multiagent.py` (the M13-02 file — do NOT recreate `M13Allocator`/`ChildHandle`/`ChildRegistry`; import/use them in-module). Use the chosen OQ-A1 reserve + viable-floor defaults documented by M13-02 (read them from the module; do NOT re-pick).

    `PanelBridgeRenderer` (Pattern 4): a wrapper class `__init__(self, base, *, panel_id: str)` storing `self._base` and `self._panel_id`. `start_panel(self, *, name: str, budget_total: int)` -> `self._base.show_subagent_start(name, self._panel_id, budget_total)` if `hasattr`. `step(self, line: str, used: int)` -> `self._base.show_subagent_progress(self._panel_id, line, used)` if `hasattr` (THIS is the missing caller for the dead `renderer.py:203` seam — but renderer.py itself is NOT edited in this plan; that wiring belongs to M13-04's TUI track. Here the bridge simply CALLS the existing method name). `end_panel(self, n_results: int = 1)` -> `self._base.show_subagent_end(self._panel_id, n_results)` if `hasattr`. `__getattr__(self, attr)` -> `getattr(self._base, attr)` so the child's `run_turn` drives the full Renderer protocol unchanged. Children are asyncio tasks on the SAME loop/thread (NOT threads) — do NOT introduce `to_thread`/`Thread` (Anti-Pattern; the existing `renderer._post` already handles main-thread vs off-loop).

    `subagent_spawn(agent: str, task: str) -> str` (Pattern 1 — the INVERSION of `subagents.py:92`): generate `handle = uuid.uuid4().hex[:12]`; `allotment = await allocator.allocate(handle)`; if `allotment is None` return `f"<denied: budget below viable floor — cannot spawn {agent!r}>"` (no task created). Create `queue: asyncio.Queue = asyncio.Queue()`; `panel_id = handle`; `bridge = PanelBridgeRenderer(base_renderer, panel_id=panel_id)`; `bridge.start_panel(name=agent, budget_total=allotment)`. Build the child via the `subagents.run_subagent` shape: resolve `picked_model = model() if callable(model) else model`, `child_tools = make_toolset(cwd, renderer=bridge)`, child `history = EpisodicMemory(capacity=20)`. Construct the child coroutine as `run_turn(<agent_task(agent, task) equivalent — reuse the registry/spec task framing if a registry is provided, else the raw task string>, tools=child_tools, cwd=cwd, renderer=bridge, model=picked_model, provider=provider, history=history, permissions=gate, cognition=cognition, token_budget=allotment, steer_inbox=queue)`. **Do NOT await it.** `t = asyncio.create_task(coro)`. Register `ChildRegistry.add(ChildHandle(handle=handle, task=t, queue=queue, panel_id=panel_id, allotment=allotment, sub_allocator=<M13-02 slice-scoped allocator built from allotment + the documented viable_floor>))`. Return `f"spawned {agent} handle={handle} budget={allotment} — call subagent_gather when ready"` (Pitfall 1: the return string MUST make the pending-gather obligation explicit so the parent LLM gathers). Child reuses the parent `gate` unchanged (T-M13 priv — no broader scope).

    `subagent_steer(handle: str, guidance: str) -> str` (D-03): `h = registry.get(handle)`; if `h is None` return `f"<no-op: unknown handle {handle!r}>"` (T-M13 mis-steer — validate, never raise); if `h.done` return `f"<no-op: child {handle} already finished>"` (steer to done child = no-op, D-04 / Pitfall 2). Else `h.queue.put_nowait(guidance)` and return `f"steered {handle}"`. The tool description MUST document the "steer only affects a child that runs another iteration; a child that has decided done will not consume it" semantic (Pitfall 2) so the parent LLM does not over-rely on it.

    `subagent_status(handle: str | None = None) -> str`: if `handle` given, return that child's done/result/allotment (from `registry.get` + `allocator.snapshot()`); else summarize all via `registry.all()` + `allocator.snapshot()` (active count, per-handle allotment, done flags). Read-only.

    `subagent_gather() -> str` (Pattern 6): `handles = registry.all()`; `tasks = [h.task for h in handles if h.task is not None]`; `results = await asyncio.gather(*tasks, return_exceptions=True)`. For each `(h, r)` zipped: `await allocator.release(h.handle)` (rebalance + exactly-once credit, MAG-04); if `isinstance(r, Exception)` append `f"[{h.handle}] <error: {r}>"`, else set `h.done = True`, `h.result = h.result or (r.final if hasattr(r, 'final') else str(r))`, append `f"[{h.handle}] {h.result}"`; call the child's bridge `end_panel(1)` (-> existing `app.collapse_subagent(panel_id)` which ALREADY does the full M9-08 region restore — no new region logic; M13-PATTERNS Shared Pattern "M9-08 region-restore reuse"). Return `"Aggregated sub-agent results:\n" + "\n".join(lines)` so it folds into the parent turn via the normal tool-result replay. Keep a per-handle bridge reference (e.g. store the bridge on the `ChildHandle` if M13-02's dataclass allows an extra attr, or maintain an in-`attach` dict `handle -> bridge`) so gather/teardown can call `end_panel`.

    Defensive gather-on-teardown safety net (Pitfall 1 / T-M13 orphan): provide a callable (e.g. `async def _teardown_orphans()`) that, for every `registry.all()` handle that is not `done` and whose task is not finished, cancels the task (`t.cancel()`), `await allocator.release(h.handle)`, and calls the child's bridge `end_panel(1)` so no task/panel leaks if the parent turn exits without gathering. Wire it so it runs on parent turn teardown — the simplest correct hook within this plan's file ownership: expose it from `attach_multiagent_tools` (e.g. return it or stash it where the cli wave M13-06 can invoke it) AND make `subagent_gather` itself idempotently safe to call again. Do NOT modify `agent.py` run_turn teardown for this (file-ownership: agent.py edits in this plan are strictly the steer kwarg + drain). The cli-level invocation HOOK (wiring `_teardown_orphans` into the chat-turn-exit site in `cli.py`) lands in M13-06 — but this plan MUST prove the callable itself works: add a `TestOrphanTeardown` class to `tests/harness/test_multiagent_fanout.py` (the file M13-01 scaffolded; this is the ONLY test file this plan writes — it does NOT overlap M13-04's TUI set) that scripts a parent which spawns but never gathers, then `await _teardown_orphans()` and asserts the child task is cancelled, `allocator.release` ran for it, the bridge `end_panel` was called, and the registry has no un-released handle. This makes the T-M13-02 mitigation an executable gate rather than belt-and-suspenders that could ship un-exercised. Document in the SUMMARY that the cli-level teardown invocation lands in M13-06.

    `attach_multiagent_tools(tools, *, registry, cwd, renderer, provider, model, gate, cognition=None) -> None` (Analog A — SAME parameter list as `attach_subagent_tool`): close over `base_renderer = renderer`, an `M13Allocator` instance (constructed with the OQ-A1 reserve + viable-floor defaults documented by M13-02), and the `ChildRegistry`; register each of the four tools with the exact idiom `@tool(name="subagent_spawn", description="...")` ... then `tools["subagent_spawn"] = ToolEntry(descriptor=subagent_spawn, is_mutating=True)` (spawn/steer/gather `is_mutating=True`; `subagent_status` `is_mutating=False` — read-only). Tool names are FINAL: `subagent_spawn`, `subagent_steer`, `subagent_status`, `subagent_gather` (consistent with — and distinct from — `SPAWN_TOOL_NAME = "subagent_run"` which stays the back-compat anchor; do NOT reuse or shadow `subagent_run`). Do NOT edit `subagents.py`, `cli.py`, `renderer.py`, `app.py`, `keymap.py` in this plan (cli wiring = M13-06; TUI seam = M13-04; recursion sub-allocator handoff = M13-05).

    Anti-patterns to avoid (RESEARCH lines 437-445): never `await` the child inside `subagent_spawn`; never hold `M13Allocator._lock` across `run_turn` (only across allocate/release — M13-02 already scopes it); never import O1 `SessionTreeManager`; never add `depth`/`max_depth`/`MAX_DEPTH`; never mutate `SubAgentPanel`/`BudgetMeter` widget classes; never cross-thread-mutate widgets from the child (children are asyncio tasks on the app loop).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_multiagent_fanout.py::TestConcurrentInFlight tests/harness/test_multiagent_fanout.py::TestOrphanTeardown tests/harness/test_multiagent_steer.py -x -q && python -m pytest tests/harness/test_subagent_recursion.py -x -q</automated>
  </verify>
  <done>multiagent.py exposes subagent_spawn (create_task + immediate handle return, NO await, viable-floor denial returns <denied: ...> with no task), subagent_steer (queue enqueue; no-op for unknown/done handle, never raises), subagent_status (read-only, is_mutating=False), subagent_gather (asyncio.gather return_exceptions=True -> release-each -> aggregate -> collapse-each), PanelBridgeRenderer (start/step/end + __getattr__ delegate), a defensive orphan-teardown net, and attach_multiagent_tools with the subagents.py param list registering all four tools; TestConcurrentInFlight proves >= 2 children in-flight simultaneously; TestOrphanTeardown (added to test_multiagent_fanout.py by this task) proves the defensive net cancels+collapses orphan children (T-M13-02 executable gate); test_subagent_recursion.py + subagents.py byte-stable; no cli.py/renderer.py/app.py/keymap.py edits in this plan (only multiagent.py + agent.py + the additive TestOrphanTeardown in test_multiagent_fanout.py).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| parent chat agent (LLM) → harness fan-out tools | LLM-chosen tool calls (`subagent_spawn`/`steer`/`status`/`gather`) cross into harness orchestration; tool args are LLM-controlled (handle strings, guidance text) |
| harness → child asyncio task | Parent enqueues steer guidance into a per-child `asyncio.Queue`; child drains at the `run_turn` loop boundary |
| child task → SubAgentPanel (UI) | Child `run_turn` drives `PanelBridgeRenderer` which posts step/budget into the app's panel on the same event loop/thread |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M13-01 | Tampering | `subagent_steer` to wrong/finished child | mitigate | `ChildRegistry.get(handle)` validates; unknown handle → benign `<no-op>` string (never raise); `done` child → `<no-op>` (steer to finished child is a no-op per D-04). Asserted by `test_multiagent_steer.py` negative case. |
| T-M13-02 | Denial of Service | orphan child tasks after parent turn ends without gather | mitigate | Defensive teardown net cancels un-gathered child tasks + `allocator.release` + `end_panel` per orphan so no task/panel leaks; spawn return string makes the gather obligation explicit (Pitfall 1). cli-level invocation hook lands M13-06; `subagent_gather` is idempotently re-callable. Asserted via MAG-07 (M13-04) + orphan-net unit coverage here. |
| T-M13-03 | Denial of Service | unbounded recursive spawn → resource exhaustion | mitigate | `subagent_spawn` honors `M13Allocator.allocate` returning `None` below the viable-budget floor (D-07) — no task created on denial; recursion bounded WITHOUT a depth constant (no `depth`/`max_depth`/`MAX_DEPTH` — keeps `test_subagent_recursion.py` green). Recursive handoff itself is M13-05. |
| T-M13-04 | Tampering | budget oversell race under concurrent spawns | accept (here) / mitigate (M13-02) | The race-safe `asyncio.Lock` check-and-allocate lives in `M13Allocator` (delivered + tested in M13-02). This plan only CALLS `allocate`/`release` correctly (exactly-once release in gather, release in teardown); the lock guard itself is not re-implemented here. No new oversell surface introduced by the tools. |
| T-M13-05 | Tampering | cross-thread UI corruption from child render path | mitigate | Children are `asyncio.create_task` coroutines on the app's event loop — NOT threads. `PanelBridgeRenderer` delegates to the existing renderer methods which route through `renderer._post` (main-thread/off-loop safe). No `to_thread`/`Thread` introduced (Anti-Pattern). |
| T-M13-06 | Elevation of Privilege | child agent gains broader permissions than parent | mitigate | Child `run_turn` is constructed with the parent `gate` (`PermissionGate`) passed through unchanged — same posture as the existing `run_subagent`; no broadened scope, no new gate. |
| T-M13-SC | Tampering | npm/pip/cargo installs | mitigate | No new dependencies. `asyncio`/`uuid` are stdlib; `run_turn`/`make_toolset`/`EpisodicMemory`/`tool`/`ToolEntry` are existing in-repo symbols. No package install task → slopcheck N/A; no `[ASSUMED]`/`[SUS]` packages. |

All dispositions resolved. No `high`-severity unmitigated threat. Blast radius = in-memory orchestration + UI only; no new secret material, network egress, or persisted data (M13-VALIDATION §Security Domain).
</threat_model>

<verification>
- `python -m pytest tests/harness/test_multiagent_fanout.py::TestConcurrentInFlight -x -q` — MAG-01: >= 2 children observably in-flight at the same instant (overlapping windows; `ChildRegistry.active() >= 2` between spawn and gather).
- `python -m pytest tests/harness/test_multiagent_steer.py::TestCorrectionChangesBehavior -x -q` — MAG-05: scripted-parent correction into a running child changes the child's output vs the no-correction control; steer consumed at the agent.py:830 drain (child scripted for >= 2 iterations).
- `python -m pytest tests/harness/test_multiagent_steer.py -x -q` — steer no-op for unknown/done handle (T-M13-01).
- `python -m pytest tests/harness/test_subagent_recursion.py -x -q` — back-compat pin: no `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT`; `run_subagent` unchanged; passes UNMODIFIED.
- `python -m pytest tests/harness/test_agent_loop.py -x -q` — additive `steer_inbox` kwarg does not regress existing run_turn behavior (steer_inbox=None path byte-equivalent).
- `python -m pytest tests/harness/test_multiagent_fanout.py::TestOrphanTeardown -x -q` — T-M13-02: spawn-but-never-gather → `_teardown_orphans()` cancels the orphan child task + releases its allotment + collapses its panel; zero leaked task/panel.
- `git diff --stat` shows ONLY `voss/harness/multiagent.py`, `voss/harness/agent.py`, and `tests/harness/test_multiagent_fanout.py` (additive `TestOrphanTeardown` only) modified (subagents.py / cli.py / renderer.py / app.py / keymap.py byte-stable — file-ownership for Wave 2 parallelism with M13-04, whose TUI set does not include test_multiagent_fanout.py).
</verification>

<success_criteria>
- MAG-01: a `subagent_spawn` tool call schedules a detached child task and returns a handle string in the same tool round (no await); `TestConcurrentInFlight` proves >= 2 children in-flight simultaneously, not serial.
- MAG-05: a scripted parent's mid-run `subagent_steer` observably changes the targeted running child's subsequent output vs the no-correction control; the steer is consumed at the verified `agent.py:830`→`:832` drain via a single synthetic next-iteration user message (RESEARCH OQ-A2 resolved: synthetic message, no shared mutable history — because `history_block` is a turn-start snapshot per agent.py:513-519).
- `steer_inbox` is a keyword-only defaulted kwarg on `run_turn` + `_run_turn_exec`, threaded in the delegation; every existing caller is unchanged; `test_subagent_recursion.py` and `test_agent_loop.py` pass unmodified.
- `subagent_gather` joins all children concurrently (`asyncio.gather(return_exceptions=True)`), releases each allotment exactly once, aggregates results into the turn, and collapses each panel (M9-08 restore for free); the defensive teardown net prevents orphan task/panel leaks.
- File ownership respected: only `multiagent.py` (extended) + `agent.py` (additive) + `tests/harness/test_multiagent_fanout.py` (additive `TestOrphanTeardown` class only — M13-01-scaffolded file, not in M13-04's TUI set) touched; zero overlap with M13-04's TUI file set → Wave 2 parallelism holds. `subagents.py`/`/agent spawn`/`voss agent spawn`/`keymap.py:37` byte-stable.
- T-M13-02 (orphan-DoS) is an executable gate: `TestOrphanTeardown` proves `_teardown_orphans()` cancels+releases+collapses an un-gathered child; the cli-level invocation hook is wired in M13-06.
</success_criteria>

<output>
Create `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-03-SUMMARY.md` when done.

The SUMMARY MUST record:
- The exact RESEARCH OQ-A2 resolution as implemented: synthetic next-iteration user message route; the messages-list landing trace (drain at agent.py:830 buffers into `pending_steer`; injected as one `{"role":"user","content":"[steering from parent agent]\n..."}` in the per-iteration messages build at agent.py:599-610; cleared after one injection); and the why-not-history rationale (history_block built once at agent.py:513-519, never rebuilt mid-loop).
- The final tool names (subagent_spawn/steer/status/gather) and is_mutating flags.
- The OQ-A1 reserve + viable-floor defaults consumed from M13-02 (cite the source).
- That the cli-level defensive-teardown invocation hook is deferred to M13-06 (this plan provides the callable + idempotent gather; cli wiring is M13-06's file ownership).
- Confirmation that subagents.py / cli.py / renderer.py / app.py / keymap.py were NOT edited (Wave 2 parallelism + back-compat invariant).
</output>
