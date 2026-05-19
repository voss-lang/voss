# Phase M13: Multi-agent in Chat (CAPS-01d) - Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 13 (1 new module, 6 modified, 5 new test files, 1 modified test)
**Analogs found:** 13 / 13 (all in-repo; this is a wiring/sequencing phase — no greenfield)

All RESEARCH line anchors were re-verified against the live codebase during mapping. Where the anchor drifted, the corrected line is noted in the pattern entry. Code excerpts below are the *exact* source to copy/extend from.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/multiagent.py` (NEW) | service / orchestrator | event-driven + pub-sub (parent→child) | `voss/harness/subagents.py` (tool-attach + run_subagent) + O1 allocator pattern | role-match (composed; no single exact analog) |
| `voss/harness/agent.py` (MOD) | core loop | request-response (iterative) | self (existing optional-kwarg convention at `run_turn` :412-429; loop boundary :830-839) | exact (additive insert into existing structure) |
| `voss/harness/subagents.py` (MOD) | service | event-driven | self (unchanged — back-compat anchor) | exact (no edit; pinning target) |
| `voss/harness/cli.py` (MOD) | config / wiring | request-response | `attach_subagent_tool(...)` call site `cli.py:1634-1643` | exact |
| `voss/harness/tui/renderer.py` (MOD) | renderer bridge | streaming (per-step push) | dead `show_subagent_progress` `renderer.py:203-204` + `_post` `:55-70` | exact (supply missing caller) |
| `voss/harness/tui/app.py` (MOD) | provider / UI mutator | event-driven | `mount_subagent_panel`/`update_subagent`/`collapse_subagent` `app.py:169-207` | exact (reuse + add toggle action) |
| `voss/harness/tui/widgets/sub_agent_panel.py` (MOD) | component | streaming | self — body `Vertical` `:59`, `append_body`/`update_budget` `:61-71` | exact (additive display toggle) |
| `voss/harness/tui/keymap.py` (MOD) | config | event-driven | `Binding("ctrl+c","global",...)` `keymap.py:37`; main rows `:29-36` | exact (one additive row) |
| `tests/harness/test_multiagent_fanout.py` (NEW) | test | concurrency / unit | `tests/harness/test_agent_loop.py:76-100` (`FakeStreamingProvider`) | exact |
| `tests/harness/test_multiagent_steer.py` (NEW) | test | unit | `tests/harness/test_agent_loop.py:76-100` (scripted branch) | exact |
| `tests/harness/test_multiagent_recursion.py` (NEW) | test | unit | `tests/harness/test_agent_loop.py:76-100` + `test_subagent_recursion.py` (no-depth-guard pin) | exact |
| `tests/harness/tui/test_subagent_reveal.py` (NEW) | test | TUI pilot | `tests/harness/tui/test_live_visualization.py:25-49` (`run_test()` + `pilot.pause()`) | exact |
| `tests/e2e/test_multiagent_chat_e2e.py` (NEW) | test (e2e) | e2e subprocess | `tests/e2e/test_chat_e2e.py:14-23` (`CliRunner` stdin script) | exact |
| `tests/harness/tui/test_keymap_baseline.py` (MOD) | test | unit | self — parametrized row table `:13-35` | exact (add `ctrl+o`/`ctrl+c` rows) |

---

## Pattern Assignments

### `voss/harness/multiagent.py` (NEW — service/orchestrator, event-driven + pub-sub)

This is the only "near-greenfield" file, but every sub-pattern is liftable. It composes three analogs: (a) the `subagents.py` tool-attach/dataclass idiom, (b) the O1 `asyncio.Lock` allocator, (c) the `subagents.run_subagent` child-launch shape with the **critical inversion: do NOT `await` the child**.

**Why a new module (not extend `subagents.py`):** `tests/harness/test_subagent_recursion.py:34-40` pins that `subagents` has **no** `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` module attribute and `run_subagent` has no `depth`/`max_depth` param. Putting the allocator/registry in `subagents.py` risks tripping that pinning test. New module keeps `subagents.py` byte-stable.

**Analog A — imports + dataclass + tool-attach idiom** — `voss/harness/subagents.py:1-12, 22-27, 106-135`:
```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from voss_runtime import EpisodicMemory, tool
from .agent import run_turn
from .permissions import PermissionGate
from .render import Renderer
from .tools import ToolEntry, make_toolset

@dataclass(frozen=True)
class SubagentSpec:        # ← mirror this dataclass idiom for ChildHandle (NOT frozen — mutable done/result)
    id: str
    description: str
    role_prompt: str

def attach_subagent_tool(tools: dict[str, ToolEntry], *, registry, cwd, renderer,
                         provider, model, gate, cognition=None) -> None:
    @tool(name="subagent_run", description="Run a registered Voss subagent on a bounded task.")
    async def subagent_run(agent: str, task: str) -> str:
        ...
    tools["subagent_run"] = ToolEntry(descriptor=subagent_run, is_mutating=True)
```
Copy this exact `@tool(...)` → `tools[name] = ToolEntry(descriptor=..., is_mutating=True)` registration shape for each of `subagent_spawn`/`subagent_steer`/`subagent_status`/`subagent_gather`. Name `attach_multiagent_tools(...)` with the same parameter list as `attach_subagent_tool` (`registry, cwd, renderer, provider, model, gate, cognition`).

**Analog B — the child-launch body to INVERT** — `voss/harness/subagents.py:76-103`:
```python
async def run_subagent(*, agent_id, task, registry, cwd, renderer, provider,
                       model, gate, cognition=None) -> str:
    spec = registry.get(agent_id)
    if spec is None:
        return f"<error: unknown subagent {agent_id!r}>"
    child_tools = make_toolset(cwd, renderer=renderer)
    result = await run_turn(                       # ← M13 ANTI-PATTERN: do NOT await here
        agent_task(spec, task),
        tools=child_tools, cwd=cwd, renderer=renderer, model=model,
        provider=provider, history=EpisodicMemory(capacity=20),
        permissions=gate, cognition=cognition,
    )
    return result.final
```
M13's `subagent_spawn` reuses everything *except* line 92: replace `result = await run_turn(...)` with `task_obj = asyncio.create_task(run_turn(..., steer_inbox=queue))` + immediate handle return. `make_toolset(cwd, renderer=child_bridge)` becomes `make_toolset(cwd, renderer=PanelBridgeRenderer(...))` and the child toolset must itself receive `attach_multiagent_tools(...)` for recursion (D-07).

**Analog C — M13Allocator (`asyncio.Lock` check-and-allocate)** — lifted from `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md` Pattern 2 / O1-RESEARCH lines 204-246. Full target shape is in `M13-RESEARCH.md` Pattern 2 (lines 257-303). Key invariant to assert in tests: `sum(allocator.snapshot().values()) <= reserve` at every depth. `release()` is idempotent via a `_credited_finished: set` guard (exactly-once rebalance, MAG-04).

**Handle id scheme** — `uuid.uuid4().hex[:12]` (project-wide; matches `RunRecorder`/`SessionRecord`; cited O1-PATTERNS 110-120).

---

### `voss/harness/agent.py` (MOD — core loop, additive kwarg + drain)

**Analog: the existing keyword-only optional-default convention** — `voss/harness/agent.py:412-429` (VERIFIED current):
```python
async def run_turn(
    task: str,
    *,
    tools: dict[str, ToolEntry],
    cwd: Path,
    renderer: Renderer,
    confidence_threshold: float = 0.60,
    token_budget: int = 60_000,
    model: str | None = None,
    provider: ModelProvider | None = None,
    history: EpisodicMemory | None = None,
    permissions: PermissionGate | None = None,
    session_id: str | None = None,
    cognition=None,
    prior_context: dict | None = None,
    voss_md_text: str | None = None,
    project_index_text: str = "",
) -> TurnResult:
```
Add `steer_inbox: asyncio.Queue | None = None` as one more keyword-only param with a default — exactly mirroring `history`/`cognition`. Thread it `run_turn` → `_run_turn_exec` the same way those optionals are threaded. Pitfall 7 (RESEARCH): non-additive change breaks `cli.py` + `subagents.py:92` callers.

**Drain insertion point — VERIFIED at `agent.py:830-839`** (RESEARCH said "line 832"; the `all_iter_records.append` landmark is line **830**, the budget check is **832-837**, `iteration_index += 1` is **839** — insert BETWEEN 830 and 832):
```python
                total_cost_usd += iter_cost
                total_prompt_tokens += iter_prompt_tokens
                total_completion_tokens += iter_completion_tokens
                all_iter_records.append(rec._iterations[-1])      # line 830

                # <<< M13 D-04 steer-inbox drain inserts HERE (between :830 and :832) >>>

                if (
                    ctx.token_budget
                    and ctx.tokens_used >= ctx.token_budget
                ):                                                # lines 832-837
                    exit_reason = "budget"
                    break

                iteration_index += 1                              # line 839
```
Drain pattern (non-blocking, deterministic) — see `M13-RESEARCH.md` Pattern 3 (lines 313-344): `while not steer_inbox.empty(): drained.append(steer_inbox.get_nowait())` guarded by `except asyncio.QueueEmpty`. Inject drained guidance as a synthetic next-iteration user message (RESEARCH A2 recommendation — least-invasive, no shared mutable state). Note: terminating iterations `break` *before* this point (`_is_done_plan` break is earlier in the loop), so a child that decides "done" never consumes a pending steer — acceptable per D-04; tests must script ≥2 child iterations.

**Hard constraints:** Do not restructure the while-loop. Do not touch the `asyncio.CancelledError` handler (outside the loop body — keeps the Ctrl+C interrupt contract intact). Additive only.

---

### `voss/harness/subagents.py` (MOD — but effectively UNCHANGED)

Listed as MOD only because RESEARCH's structure table lists it; the actual instruction is **do not edit it**. `run_subagent` (`:76-103`), `attach_subagent_tool` (`:106-135`), and `SPAWN_TOOL_NAME = "subagent_run"` (`:19`) are the back-compat anchor. `tests/harness/test_subagent_recursion.py:23-40` pins: no `depth`/`max_depth` on `run_subagent`, no `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` module attr. The new tools live in `multiagent.py`. The renderer's `SPAWN_TOOL_NAME` import (`renderer.py:40`) must keep resolving — do not rename or move the constant.

---

### `voss/harness/cli.py` (MOD — config/wiring, request-response)

**Analog: the existing `attach_subagent_tool` call site** — `voss/harness/cli.py:1634-1643` (VERIFIED current):
```python
    attach_subagent_tool(
        tools,
        registry=subagent_registry,
        cwd=cwd,
        renderer=renderer,
        provider=provider,
        model=lambda: get_config().default_model,
        gate=gate,
        cognition=bundle,
    )
```
Add an `attach_multiagent_tools(tools, registry=..., cwd=..., renderer=..., provider=..., model=lambda: get_config().default_model, gate=gate, cognition=bundle)` call **immediately after** this block — same kwargs, additive. Do NOT remove or alter the `attach_subagent_tool` call (back-compat). `/agent spawn` slash (~`cli.py:1115`) and `voss agent spawn` CLI (~`cli.py:2430`) stay untouched.

---

### `voss/harness/tui/renderer.py` (MOD — renderer bridge, streaming)

**Analog: the dead seam to wire + the thread-safe post helper.**

`_post` thread-safety helper — `voss/harness/tui/renderer.py:55-70` (VERIFIED current):
```python
    def _post(self, fn, *args, **kwargs) -> None:
        """Safely invoke a widget method on the app's event loop."""
        try:
            on_main = threading.current_thread() is threading.main_thread()
            if on_main:
                fn(*args, **kwargs)
                return
            try:
                self.app.call_from_thread(fn, *args, **kwargs)
            except Exception:
                fn(*args, **kwargs)
        except Exception as exc:
            try:
                self.app.log(f"TextualRenderer error: {exc}")
            except Exception:
                pass
```

The dead seam M13 supplies the missing caller for — `voss/harness/tui/renderer.py:194-207` (VERIFIED current):
```python
    def show_subagent_start(self, name: str, parent_id: str, budget_total: int = 0) -> None:
        panel = SubAgentPanel(name=name, parent_id=parent_id,
                              budget_used=0, budget_total=budget_total)
        self._post(self.app.mount_subagent_panel, panel)

    def show_subagent_progress(self, parent_id: str, body_line: str, used: int = 0) -> None:
        self._post(self.app.update_subagent, parent_id, body_line, used)   # ← line 203-204: NEVER CALLED today

    def show_subagent_end(self, parent_id: str, n_results: int = 0) -> None:
        self._post(self.app.collapse_subagent, parent_id, n_results)
```

`PanelBridgeRenderer` (lives in `multiagent.py`, per RESEARCH Pattern 4) wraps the base renderer and routes child step/budget into a fixed `panel_id`: `start_panel` → `show_subagent_start`, `step(line, used)` → `show_subagent_progress` (FIRST caller of the dead seam), `end_panel` → `show_subagent_end`, with `__getattr__` delegating the rest of the Renderer protocol to the base. **Thread reconciliation (RESEARCH Pitfall 3):** the `renderer.py:7` "subagents run in worker threads" docstring is stale for the M13 path — children are `asyncio.create_task` coroutines on the *same* loop/thread; `_post` already handles both cases. Do NOT introduce `to_thread`/`Thread` for children. Leave the `renderer.py:7` docstring as-is unless the planner adds a one-line clarification (additive only).

---

### `voss/harness/tui/app.py` (MOD — provider/UI mutator, event-driven)

**Analog: the M9-04 mutators + M9-08 region restore (reuse unchanged)** — `voss/harness/tui/app.py:169-207` (VERIFIED current):
```python
    def mount_subagent_panel(self, panel: "SubAgentPanel") -> None:
        self.show_subagent_panel()  # M9-08 ownership (respects pin)
        side = self.query_one("#side")
        side.mount(panel)
        side.display = True
        side.styles.display = "block"

    def update_subagent(self, parent_id: str, body_line: str, used: int = 0) -> None:
        for panel in self.query(SubAgentPanel):
            if getattr(panel, "parent_id", None) == parent_id:
                panel.append_body(body_line)
                if used:
                    panel.update_budget(used)
                return

    def collapse_subagent(self, parent_id: str, n_results: int = 0) -> None:
        for panel in list(self.query(SubAgentPanel)):
            if getattr(panel, "parent_id", None) == parent_id:
                panel.remove()
        side = self.query_one("#side")
        if not list(side.query(SubAgentPanel)):
            if not self._side_pinned or self._side_owner == "code_intel":
                self._side_owner = "code_intel"
                if self._code_intel_panel:
                    if self._code_intel_panel not in list(side.children):
                        side.mount(self._code_intel_panel)
                    side.display = True
                    side.styles.display = "block"
            else:
                side.display = False
                side.styles.display = "none"
        try:
            self.query_one("#main", TurnView).append_turn(
                "gather", f"✓ gathered · {n_results} results"
            )
        except Exception:
            pass
```
`collapse_subagent` **already** does the full M9-08 restore (CodeIntelPanel re-mount / hide per `_side_pinned`/`_side_owner`) — D-10 gets region restore for free; call it once per panel. **ADD only**: `action_toggle_subagent_detail` (new action method) + per-panel detail-visibility state. It must iterate `self.query(SubAgentPanel)` and flip each panel's body `Vertical` `.styles.display` between `"none"` and `"block"`. Do NOT modify `mount_subagent_panel`/`update_subagent`/`collapse_subagent` or any `_side_*` logic. `BINDINGS` filter is `app.py:39-43` (`global|input|modal` only — see Shared Patterns / keymap note).

---

### `voss/harness/tui/widgets/sub_agent_panel.py` (MOD — component, streaming)

**Analog: self.** `voss/harness/tui/widgets/sub_agent_panel.py:51-71` (VERIFIED current):
```python
    def compose(self) -> ComposeResult:
        yield Static(self.agent_name, classes="agent-header")
        yield BudgetMeter(used=self.budget_used, total=self.budget_total,
                          classes="mini-status", id=f"panel-budget-{self.parent_id}")
        yield Vertical(id=f"panel-body-{self.parent_id}", classes="agent-body")   # ← line 59: toggle target

    def append_body(self, line: str) -> None:
        body = self.query_one(f"#panel-body-{self.parent_id}", Vertical)
        body.mount(Static(line, markup=False))

    def update_budget(self, used: int) -> None:
        self.budget_used = max(0, int(used))
        meter = self.query_one(f"#panel-budget-{self.parent_id}", BudgetMeter)
        meter.used = self.budget_used
        meter.total = self.budget_total
        meter.refresh()
```
Quiet-by-default (D-09): the body `Vertical` (`:59`) gets `display: none` by default (compose-time or via `DEFAULT_CSS` for `.agent-body`). Steps still stream in via `append_body` (captured but not visible). The Ctrl+O reveal flips `#panel-body-{parent_id}` `.styles.display`. **Constraint (RESEARCH anti-pattern):** do NOT change the `BudgetMeter` em-dash contract (em-dash only when `budget_total <= 0`) and do NOT add new widget classes — additive display toggle on the existing body `Vertical` only. `append_body`/`update_budget` reused unchanged.

---

### `voss/harness/tui/keymap.py` (MOD — config, additive one row)

**Analog: the Ctrl+C row (UNCHANGED) + the additive table convention** — `voss/harness/tui/keymap.py:20-39` (VERIFIED current):
```python
KEYMAP: tuple[Binding, ...] = (
    Binding("tab", "global", "focus_next", "Cycle focus to next region"),
    ...
    Binding("f", "main", "fork_turn", "Fork session from focused turn"),
    Binding("ctrl+f", "main", "open_search", "Open in-pane search"),
    Binding("ctrl+c", "global", "interrupt", "Interrupt turn; press again to exit"),  # line 37 — UNCHANGED
    Binding("ctrl+l", "global", "redraw", "Redraw screen"),
)
```
Add exactly ONE row: `Binding("ctrl+o", "main", "toggle_subagent_detail", "Reveal/hide sub-agent step detail")`. Do NOT touch line 37 (Ctrl+C stays `interrupt`). **Dispatch caveat (RESEARCH Pitfall 6 / Open Question 2 / Assumption A3 — UNRESOLVED, planner must trace):** `VossTUIApp.BINDINGS` (`app.py:39-43`) filters to `global|input|modal` only — `"main"`-context rows (j/k/g/G/f/ctrl+f) reach actions via a *different* path (likely `TurnView.BINDINGS` or app focus routing, not `App.BINDINGS`). The planner MUST trace how existing `"main"` rows dispatch before placing `ctrl+o`, and place the `toggle_subagent_detail` action handler on the same mechanism. A keymap-baseline assertion must prove `ctrl+o → toggle_subagent_detail` resolves in whatever table M9 main keys use.

---

### Test files (NEW) — analog: `FakeStreamingProvider` + pilot + CliRunner

**Shared scripted-provider analog** — `tests/harness/test_agent_loop.py:76-100` (VERIFIED current):
```python
@dataclass
class FakeStreamingProvider:
    """Async-iterable provider double that scripts one stream per call."""
    scripts: list[list[ProviderStreamEvent]]
    stream_calls: list[dict] = field(default_factory=list)
    complete_calls: list[dict] = field(default_factory=list)
    record_run_return: Any = None
    _stream_index: int = 0

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        script = self.scripts[self._stream_index]
        self._stream_index += 1
        async def _gen():
            for ev in script:
                yield ev
        return _gen()

    async def complete(self, **kwargs):
        self.complete_calls.append(kwargs)
        ...
```
- **`test_multiagent_fanout.py`** (MAG-01/03/04): scripted parent + N child providers; assert ≥2 `ChildRegistry.active()` between spawn/gather (overlap proof); `sum(allocator.snapshot().values()) <= reserve` under `asyncio.gather(*[allocator.allocate(h) for h in many])`; `release()` called twice → no double-credit. Build a shared scripted multi-agent provider fixture (likely a new `tests/harness/conftest.py` fixture extending `FakeStreamingProvider`).
- **`test_multiagent_steer.py`** (MAG-05): child stub script BRANCHES on injected-guidance presence (emits different `final`); assert WITH-correction output != no-correction control; child scripted for ≥2 iterations so the `:830` drain is observably hit.
- **`test_multiagent_recursion.py`** (MAG-06): depth-2 parent→child→grandchild; assert 3 distinct `panel_id`s concurrently, grandchild allotment ≤ child slice ≤ parent reserve, zero `SubAgentPanel` after gather. **Must NOT introduce `depth`/`max_depth`** — recursion bounded by viable-floor only (keeps `test_subagent_recursion.py` green).
- **`tests/harness/tui/test_subagent_reveal.py`** (MAG-02/07): `run_test()` + `pilot.pause()` pattern from `test_live_visualization.py:25-49`:
  ```python
  app = VossTUIApp()
  async with app.run_test() as pilot:
      renderer = TextualRenderer(app=pilot.app)
      renderer.show_subagent_start("reviewer", "abc", 2000)
      await pilot.pause()
      panels = list(pilot.app.query(SubAgentPanel))
      assert any(p.parent_id == "abc" for p in panels)
  ```
  Assert: body `Vertical` `display == "none"` by default; after `action_toggle_subagent_detail` it contains ≥1 streamed step; `BudgetMeter` leaves em-dash + increments ≥1×; post-gather `len(pilot.app.query(SubAgentPanel)) == 0` and `_side_owner`/`_side_pinned` match pre-spawn snapshot.
- **`tests/e2e/test_multiagent_chat_e2e.py`** (MAG-08): `CliRunner` stdin-script pattern from `tests/e2e/test_chat_e2e.py:14-23` (`cli_runner.run("chat", "--plain", stdin="...\n/exit\n", timeout=...)`) — runner auto-installs the deterministic StubProvider via generated `sitecustomize.py` (`tests/e2e/runner.py:1-31`). One NL request → assert ≥2 concurrent panels, ≥1 budget tick/child, ≥1 applied correction, ≥1 rebalance, aggregated turn, clean post-gather region.

### `tests/harness/tui/test_keymap_baseline.py` (MOD — additive parametrize rows)

**Analog: self.** `tests/harness/tui/test_keymap_baseline.py:13-35` parametrized row table. Add `("ctrl+o", "main")` to the param list and an assertion that the binding's `.action == "toggle_subagent_detail"`; keep the existing `("ctrl+c", "global")` row (proves Ctrl+C still `interrupt`). Bump `test_keymap_size_at_least_14` only if it would now fail (it asserts `>= 14`; adding a row keeps it green — leave it).

---

## Shared Patterns

### Concurrency / no-oversell allocator
**Source:** O1-PATTERNS Pattern 2 / `M13-RESEARCH.md` Pattern 2 (lines 257-303) — copied (NOT imported) into `voss/harness/multiagent.py`.
**Apply to:** `multiagent.py` (M13Allocator); asserted by `test_multiagent_fanout.py`, `test_multiagent_recursion.py`.
**Rule:** `asyncio.Lock`-guarded check-and-allocate; `release()` idempotent via `_credited_finished: set`; invariant `sum(_active.values()) <= reserve` at every depth; viable-floor denial bounds recursion (no `max_depth` constant — pinned by `test_subagent_recursion.py`).

### Tool registration idiom
**Source:** `voss/harness/subagents.py:117-135`
**Apply to:** all four new tools in `multiagent.py`.
```python
@tool(name="...", description="...")
async def the_tool(...) -> str: ...
tools["..."] = ToolEntry(descriptor=the_tool, is_mutating=True)
```

### Thread-safe widget mutation
**Source:** `voss/harness/tui/renderer.py:55-70` (`_post`)
**Apply to:** all child→panel pushes via `PanelBridgeRenderer`.
**Rule:** never mutate Textual widgets directly from a child path — go through `renderer._post` (already main-thread/off-loop safe). Children stay asyncio tasks (NOT threads).

### Additive optional kwarg threading
**Source:** `voss/harness/agent.py:412-429` (`history`/`cognition` keyword-only optional-default convention)
**Apply to:** `steer_inbox: asyncio.Queue | None = None` on `run_turn` → `_run_turn_exec`.
**Rule:** keyword-only, defaulted, threaded identically to existing optionals. Non-additive change breaks `cli.py` + `subagents.py:92` callers and `test_subagent_recursion.py`.

### M9-08 region-restore reuse
**Source:** `voss/harness/tui/app.py:184-207` (`collapse_subagent`)
**Apply to:** `subagent_gather` teardown (D-10).
**Rule:** call `collapse_subagent(panel_id, n)` once per panel — region pin/owner restore is automatic, no new region logic.

### Hermetic scripted-provider test posture
**Source:** `tests/harness/test_agent_loop.py:76-100` (`FakeStreamingProvider`); `tests/harness/tui/test_live_visualization.py:25-49` (pilot); `tests/e2e/test_chat_e2e.py:14-23` + `tests/e2e/runner.py` (CliRunner StubProvider)
**Apply to:** all 5 new test files.
**Rule:** deterministic, no live network (D-11); per-agent scripts control iteration counts so steer/concurrency are reproducible; `asyncio_mode="auto"` (no `@pytest.mark.asyncio` strictly required, though existing TUI tests use it explicitly — match the neighbor file's style).

---

## No Analog Found

None. Every target file has a strong in-repo analog (or is self-referential additive). `voss/harness/multiagent.py` is the only *new* module and has no single one-to-one analog, but it is fully composed from three verified in-repo/precedent patterns (subagents tool-attach idiom + O1 allocator + subagents child-launch shape inverted) — classified role-match, not greenfield.

| File | Role | Data Flow | Status |
|------|------|-----------|--------|
| `voss/harness/multiagent.py` | service/orchestrator | event-driven + pub-sub | Composed from 3 analogs (A/B/C above) — NOT unanchored greenfield |

---

## Open Items the Planner Must Resolve (carried from RESEARCH)

1. **`"main"`-context keymap dispatch path (A3 / Pitfall 6 / OQ2)** — UNVERIFIED. Trace how existing `"main"` rows (`keymap.py:29-36`) reach actions before placing `ctrl+o`; `App.BINDINGS` excludes `"main"` (`app.py:39-43`). Add a keymap-baseline resolution assertion.
2. **Steer injection mechanism (A2 / OQ3)** — synthetic next-iteration user message recommended (deterministic, no shared mutable state) over shared `EpisodicMemory`. Confirm the provider stub surfaces extra `messages` entries to the scripted plan.
3. **Reserve value + viable-floor threshold (A1)** — chat passes no `token_budget` (defaults 60_000, `agent.py:419`); M13 invents the reserve. Planner picks + documents a sensible default reserve and floor (floor < `reserve // expected_fanout`).

---

## Metadata

**Analog search scope:** `voss/harness/` (subagents.py, agent.py, cli.py, tui/renderer.py, tui/app.py, tui/keymap.py, tui/widgets/sub_agent_panel.py), `tests/harness/`, `tests/harness/tui/`, `tests/e2e/`, plus O1-PATTERNS/O1-RESEARCH precedent.
**Files scanned (read for excerpts):** 11 source + test files; all RESEARCH line anchors re-verified against live code (drift noted: agent.py drain landmark is `:830` `all_iter_records.append`, budget check `:832-837`).
**Pattern extraction date:** 2026-05-18
