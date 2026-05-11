---
phase: M4
plan: 03
type: execute
wave: 2
depends_on: [M4-01, M4-02]
files_modified:
  - voss/harness/agent.py
  - voss/harness/tools.py
  - voss/harness/cli.py
  - voss/harness/agent/loop.voss
  - voss/harness/agent/router.voss
  - voss/harness/agent/planner.voss
  - voss/harness/agent/executor.voss
  - voss/harness/agent/reviewer.voss
  - tests/harness/test_boot_dispatch.py
autonomous: true
requirements:
  - DOG-01
  - DOG-02
  - DOG-03
  - DOG-04
  - DOG-05
  - DOG-07
tags:
  - dogfood
  - voss-authoring
  - boot-dispatch
  - wave-2

must_haves:
  truths:
    - "`voss/harness/agent/loop.voss` exists and is the orchestration entry: imports `_run_step_loop`, `TurnResult`, `ToolEntry`, `PermissionGate` via NAME-form `use voss::harness::...`; declares `fn run_turn(...)` with the same signature as `voss/harness/agent.py:run_turn`; wraps the pipeline in `ctx(budget: N tokens) { ... }`; calls `route_intent`, `plan_task`, `_run_step_loop`, `review`, `clarify` (forward-references to sibling .voss files / Python helpers)."
    - "`voss/harness/agent/router.voss` exists and is pure `.voss`: a `fn route_intent(task: string) -> string` using `probable<string>` + confidence gate `@ p >= 0.80`."
    - "`voss/harness/agent/planner.voss` exists and uses `probable<Plan>` with `use voss::harness::agent::Plan` import (NAME form per Pitfall 1)."
    - "`voss/harness/agent/executor.voss` exists and forwards to `_run_step_loop` (the Python helper extracted in this plan); compiled `.voss-cache/harness/executor.py` contains `await _run_step_loop(` (Pitfall 2 sentinel)."
    - "`voss/harness/agent/reviewer.voss` exists, uses `try/catch`, calls `_substitute_placeholders` (Python helper) and constructs/returns a `TurnResult` (via Python helper `_make_turn_result` if named-arg constructor syntax cannot be relied on)."
    - "Per-file minimum substantive content (D-01 20-40 LOC target): `voss/harness/agent/loop.voss` ≥ 20 non-comment LOC; `router.voss` ≥ 8; `planner.voss` ≥ 8; `executor.voss` ≥ 6; `reviewer.voss` ≥ 12. Stub-file fallback is prohibited — these floors make DOG-01..DOG-05 substantive, not file-existence trivia."
    - "`voss check voss/harness/agent/` exits 0 (all five files parse + analyze)."
    - "`voss compile voss/harness/agent/` exits 0 and produces 5 `.py` artifacts + `_manifest.json` under `.voss-cache/harness/`."
    - "`voss/harness/agent.py` exposes new `async def _run_step_loop(plan_steps, tools, permissions, renderer) -> list[str]` (extracted from existing tool-dispatch loop at lines 184-207) and `_substitute_placeholders(template: str, results: list[str]) -> str` (mirrors agent.py:210-211 substitution loop). Existing `run_turn` body is refactored to call `await _run_step_loop(plan.steps, tools, permissions, renderer)` in place of the inline loop — preserving identical semantics (parity oracle invariant for D-09)."
    - "`voss/harness/tools.py:ToolEntry` exposes `invoke_dict(self, args: dict) -> Any` returning `self.descriptor.invoke(**args)`."
    - "`voss/harness/cli.py:_resolve_run_turn()` exists, reads `VOSS_HARNESS` env > `[harness] backend` config > `\"python\"` default; raises `click.ClickException` on invalid backend; calls `harness_cache.assert_fresh(cwd)` BEFORE dynamic import when backend == compiled (Pitfall 4); returns the resolved `run_turn` callable."
    - "`voss/harness/cli.py:do_cmd` (and `chat_cmd`) call `_resolve_run_turn()` per-invocation rather than relying on the module-top `from .agent import run_turn` import."
    - "`tests/harness/test_agent_integration.py` continues to pass — the `_run_step_loop` extraction is a pure refactor; no behavior change."
  artifacts:
    - path: "voss/harness/agent/loop.voss"
      provides: "DOG-01: orchestration .voss with ctx budget + pipeline calls"
      min_lines: 20
      contains: "fn run_turn"
    - path: "voss/harness/agent/router.voss"
      provides: "DOG-02: probable<string> intent router"
      min_lines: 8
      contains: "probable<string>"
    - path: "voss/harness/agent/planner.voss"
      provides: "DOG-03: probable<Plan> planner with use import"
      min_lines: 8
      contains: "probable<Plan>"
    - path: "voss/harness/agent/executor.voss"
      provides: "DOG-04: thin executor forwarding to _run_step_loop"
      min_lines: 6
      contains: "_run_step_loop"
    - path: "voss/harness/agent/reviewer.voss"
      provides: "DOG-05: try/catch final synthesis"
      min_lines: 12
      contains: "try"
    - path: "voss/harness/agent.py"
      provides: "_run_step_loop, _substitute_placeholders, optional _make_turn_result helpers; run_turn refactored to delegate"
      contains: "async def _run_step_loop"
    - path: "voss/harness/tools.py"
      provides: "ToolEntry.invoke_dict spread helper"
      contains: "def invoke_dict"
    - path: "voss/harness/cli.py"
      provides: "_resolve_run_turn() backend dispatch; do_cmd/chat_cmd use per-invocation resolve"
      contains: "_resolve_run_turn"
    - path: "tests/harness/test_boot_dispatch.py"
      provides: "Wave-2 sentinel: env > config > default resolution; invalid backend raises; cache pre-compile fixture exercises compiled path"
      contains: "_resolve_run_turn"
  key_links:
    - from: "voss/harness/agent/loop.voss"
      to: "voss/harness/agent.py::_run_step_loop"
      via: "use voss::harness::agent::_run_step_loop + auto-await via M4-01 codegen patch"
      pattern: "_run_step_loop"
    - from: "voss/harness/agent/executor.voss"
      to: "voss/harness/agent.py::_run_step_loop"
      via: "NAME-import + bare-Identifier call (no `for` loop in .voss; no `**kwargs` spread)"
      pattern: "_run_step_loop"
    - from: "voss/harness/cli.py::_resolve_run_turn"
      to: "voss/harness/cache.py::assert_fresh"
      via: "called BEFORE dynamic import (Pitfall 4); raises StaleHarnessCacheError on stale"
      pattern: "harness_cache.assert_fresh"
    - from: "voss/harness/cli.py::do_cmd"
      to: "voss/harness/cli.py::_resolve_run_turn"
      via: "per-invocation resolve replaces module-top run_turn import"
      pattern: "run_turn = _resolve_run_turn()"
---

<objective>
Author the five `.voss` files that ARE the M4 dogfood, plus the Python-side helpers and boot-path dispatch they require. Three coupled changes:

1. **Python helpers** (D-04 + Q-2/Q-3 in M4-RESEARCH): Extract `_run_step_loop` from `voss/harness/agent.py:184-207` so both backends call the same code (Pitfall 8 mitigation — preserves the parity-oracle invariant D-09). Add `_substitute_placeholders` for `{{step_N}}` substitution (mirrors agent.py:210-211 loop). Optional `_make_turn_result(...)` factory if `.voss` named-arg constructor syntax for `TurnResult(plan: ..., final: ..., ...)` cannot be relied on. Add `ToolEntry.invoke_dict(args: dict)` as the `**kwargs`-spread workaround for `.voss` callers.

2. **Five `.voss` files** (DOG-01..DOG-05): Thin control-flow under `voss/harness/agent/`. NAME-imports only (per Pitfall 1; aliased module imports cosmetic-only and deferred). Pipeline structure: `loop.voss` (ctx budget + dispatch) → `router.voss` (probable intent) → `planner.voss` (probable Plan) → `executor.voss` (forward to `_run_step_loop`) → `reviewer.voss` (final synthesis + try/catch).

3. **Boot-path dispatch** (DOG-07 prep, D-08): Add `voss/harness/cli.py:_resolve_run_turn()` that reads `VOSS_HARNESS` env > config.toml `[harness] backend` > `"python"`. Calls `harness_cache.assert_fresh(cwd)` BEFORE dynamic import (Pitfall 4). Replace module-top `from .agent import run_turn` with per-invocation `_resolve_run_turn()` calls in `do_cmd` and `chat_cmd`. Keep the module-level alias `_python_run_turn` for in-process callers if needed.

Purpose: This plan delivers DOG-01..DOG-05 (the five `.voss` files) and the boot dispatch DOG-07 needs (D-08). The parity test (M4-04 Wave 3) depends on `_resolve_run_turn` working AND on the compiled `loop.py` being importable. Wave 0 (codegen auto-await) and Wave 1 (dir-walk + cache module) are hard prerequisites — without them the compiled output is broken (Pitfall 2) or unreachable (Pitfall 4).

Output:
- `voss/harness/agent.py` — +~25 LOC (helpers extracted; run_turn refactored to delegate; behavior preserved).
- `voss/harness/tools.py` — +~3 LOC (`invoke_dict`).
- `voss/harness/cli.py` — +~35 LOC (`_resolve_run_turn` + call-site updates in `do_cmd` and `chat_cmd`).
- 5 × `voss/harness/agent/*.voss` — NEW (~100 LOC total; each 8-30 LOC of thin control flow).
- `tests/harness/test_boot_dispatch.py` — NEW (4 tests).
- After this plan: `voss check voss/harness/agent/` exits 0; `voss compile voss/harness/agent/` produces 5 `.py` + `_manifest.json`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md
@.planning/phases/M4-voss-authored-harness-loop/M4-RESEARCH.md
@.planning/phases/M4-voss-authored-harness-loop/M4-PATTERNS.md
@.planning/phases/M4-voss-authored-harness-loop/M4-VALIDATION.md
@.planning/phases/M4-voss-authored-harness-loop/M4-01-PLAN.md
@.planning/phases/M4-voss-authored-harness-loop/M4-02-PLAN.md
@voss/harness/agent.py
@voss/harness/tools.py
@voss/harness/cli.py
@voss/harness/permissions.py
@voss/harness/config.py
@voss/grammar.lark
@samples/classify.voss
@samples/research.voss
@samples/support.voss
@tests/harness/test_agent_integration.py

<interfaces>
<!-- Key contracts extracted from the tree at commit 99d292e + M4-01/M4-02 outputs. -->

From voss/harness/agent.py (run_turn signature, lines 100-112; what loop.voss exports must match):
```python
async def run_turn(
    task: str,
    *,
    tools: dict,
    cwd: Path,
    renderer,
    confidence_threshold: float = 0.60,
    token_budget: int = 60000,
    model: str | None = None,
    provider=None,
    history=None,
    permissions=None,
) -> TurnResult:
```

From voss/harness/agent.py (lines 184-207, the tool-dispatch loop being extracted):
- Iterates `plan.steps`; uses `gate = permissions or PermissionGate(auto_yes=True)`; calls `entry.invoke(**step.args)`; awaits the coroutine; captures errors; calls `renderer.show_tool_call(...)` at each step.
- Returns `results: list[str]`.

From voss/harness/agent.py (lines 210-211, the substitution loop):
- `for i, r in enumerate(results): final = final.replace(f"{{{{step_{i}}}}}", r)` — exact target for `_substitute_placeholders`.

From voss/harness/agent.py (Plan/ToolCall/TurnResult — D-02 thin .voss; .voss imports these as pydantic types):
- `Plan(rationale, steps: list[ToolCall], confidence: float, final_when_done: str, open_question: str | None)` at lines 35-56.
- `TurnResult(plan, confidence, final, tool_results, cost_usd)` dataclass at line 82.

From voss/harness/tools.py:14-38:
- `@dataclass class ToolEntry: name: str; descriptor: ToolDescriptor; is_mutating: bool; mode_required: Mode | None`
- `def invoke(self, **kwargs) -> Any: return self.descriptor.invoke(**kwargs)` — line 37-38.

From voss/harness/cli.py:
- Module-top: `from .agent import run_turn` at line 23 — this plan replaces with `_resolve_run_turn()` per-invocation.
- `_resolve_auth_or_die(preference)` at 108-147 — analog for `_resolve_run_turn` (resolve-before-run pattern).
- `do_cmd` at 177-246 — call-site for `run_turn`.
- `chat_cmd` at 271-292 — second call-site.
- `_resolve_default_model` at 38-56 — already calls `harness_config.load_harness_config()`.

From voss/harness/config.py:
- `load_harness_config()` returns `dict[str, str]` parsed from `~/.config/voss/config.toml` `[harness]` section.
- No code change needed if `_resolve_run_turn` reads `.get("backend")` inline (Q-3 recommendation).

From voss/harness/cache.py (landed in M4-02):
- `assert_fresh(project_root: Path) -> None` raises `StaleHarnessCacheError` on stale.
- `CACHE_HARNESS_DIR = ".voss-cache/harness"`.

From voss/harness/diagnostics.py (landed in M4-02):
- `StaleHarnessCacheError(VossError)` already exists.

From voss/grammar.lark + samples (verified):
- `ctx_stmt: "ctx" "(" budget_kwarg ")" "{" block "}"` — line 128.
- `budget_kwarg: IDENT ":" budget_kwarg_value` — line 130-131; supports `budget: 60000 tokens`.
- `try_stmt: "try" block "catch" [NAME] block` — line 133.
- `confidence_gate: ... @ p >= NUMBER` — lines 73-74.
- `arg: named_arg | expr` and `named_arg: IDENT ":" expr` — lines 68-69 (CONFIRMED: named-arg call syntax exists in .voss, so `TurnResult(plan: plan, final: final, ...)` is supported provided the call target is treated as a callable that accepts named args; codegen lowers to Python kwargs — verify with a tiny .voss test if uncertain; fallback is `_make_turn_result(...)` Python helper).
- `.voss` has NO `for` loop (verified absent in stmt rules grammar.lark:88-98).
- `.voss` has NO `**kwargs` spread.
- `type_expr` (line 17-22) supports generics like `probable<Plan>`, `probable<string>`, `list<string>`.

Header convention (M3 D-14 carry-forward, applied to all five .voss files):
- Two leading `#` comment lines: filename + one-line primitive summary.

NAME-imports-only invariant (Pitfall 1; Shared Pattern in M4-PATTERNS.md):
- `use voss::harness::run_turn` ✓
- `use voss::harness as h` + `h.run_turn(...)` ✗ (deferred from M4 even though M4-01 grammar lands the `as` clause; aliased member-call auto-await is NOT extended in M4 per M4-PATTERNS.md and M4-RESEARCH §Pattern 1b).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Python helpers — `_run_step_loop`, `_substitute_placeholders`, `ToolEntry.invoke_dict`; refactor run_turn to delegate</name>
  <files>voss/harness/agent.py, voss/harness/tools.py</files>
  <read_first>
    - voss/harness/agent.py (entire file — Plan/ToolCall at 35-56, PLAN_SYSTEM at 64-79, TurnResult at 82, run_turn at 100-231, the tool loop at 184-207, the substitution at 210-211, _summarize at 234-238)
    - voss/harness/tools.py (entire file — ToolEntry at 14-38, make_toolset at 41+)
    - voss/harness/permissions.py (PermissionGate.check signature; M1 D-05 strict tier)
    - voss/harness/render.py (renderer.show_tool_call signature — used inside _run_step_loop)
    - tests/harness/test_agent_integration.py (FakeProvider, run_turn invocations — must continue to pass post-refactor)
    - M4-RESEARCH.md §"Pattern 2 caveats" + §"Open Question Q-2" + §"Open Question Q-6"
    - M4-PATTERNS.md §"voss/harness/agent.py (MODIFY — extract `_run_step_loop`) — Wave 2" and §"voss/harness/tools.py:ToolEntry.invoke_dict (MODIFY, +3 LOC) — Wave 2"
  </read_first>
  <behavior>
    - `_run_step_loop(plan_steps, tools, permissions, renderer)` is an async function whose body is the verbatim logic from `voss/harness/agent.py:184-207`: permission gate check, tool invoke with `await entry.invoke(**step.args)`, error capture, renderer events, results aggregation.
    - `_substitute_placeholders(template: str, results: list[str]) -> str` returns `template` with `{{step_0}}`, `{{step_1}}`, ... replaced by `results[0]`, `results[1]`, ... — exact mirror of agent.py:210-211.
    - `run_turn` body is refactored to call `await _run_step_loop(plan.steps, tools, permissions, renderer)` in place of the inline loop. The remaining run_turn body (ctx scope, planner ask, confidence gate, history append, final synthesis) is unchanged — same TurnResult is returned for the same inputs.
    - `ToolEntry.invoke_dict(self, args: dict) -> Any` returns `self.descriptor.invoke(**args)` (pure passthrough; the only purpose is to give `.voss` callers a spread-free entry point).
    - Existing `tests/harness/test_agent_integration.py` continues to pass — the refactor is behavior-preserving.
    - If `.voss` named-arg constructor syntax for `TurnResult(plan: plan, ...)` proves unreliable during Task 3 implementation, add `_make_turn_result(plan, confidence, final, tool_results, cost_usd=0.0) -> TurnResult` as a fallback factory in this task (cheap to include preemptively; reviewer.voss calls it).
  </behavior>
  <action>
    Edit `voss/harness/agent.py`. Define `async def _run_step_loop(plan_steps, tools, permissions, renderer) -> list[str]` near the bottom of the module (after `_summarize`). Body is the verbatim block from lines 184-207 (the tool-dispatch loop), with `plan.steps` parameterised to `plan_steps`. Preserve all existing semantics: `gate = permissions or PermissionGate(auto_yes=True)`; iterate; lookup `entry = tools.get(step.name)`; check permission via `gate.check(step.name, step.args, is_mutating=entry.is_mutating)`; emit renderer events; `await entry.invoke(**step.args)`; capture errors as `<error: ...>`; append to `results`; return `results`.

    Define `def _substitute_placeholders(template: str, results: list[str]) -> str` near `_run_step_loop`. Body: loop `for i, r in enumerate(results): template = template.replace(f"{{{{step_{i}}}}}", r)`; return `template`. Mirror agent.py:210-211 exactly.

    Define `def _make_turn_result(plan, confidence, final, tool_results, cost_usd=0.0) -> TurnResult: return TurnResult(plan=plan, confidence=confidence, final=final, tool_results=tool_results, cost_usd=cost_usd)` as a preemptive fallback factory for reviewer.voss (Task 3 may or may not use it depending on named-arg constructor support; cheap insurance per the M4-PATTERNS.md Open Assumption note).

    Refactor `run_turn` body: replace the inline tool-dispatch loop at lines 184-207 with `results = await _run_step_loop(plan.steps, tools, permissions, renderer)`. Replace the substitution loop at 210-211 with `final = _substitute_placeholders(final, results)`. Do NOT change run_turn's signature, parameter defaults, or external behavior. The pre-existing `gate = permissions or PermissionGate(auto_yes=True)` line that lived above the inline loop now lives inside `_run_step_loop`; remove the now-dead duplicate in `run_turn`.

    Edit `voss/harness/tools.py`. Add `def invoke_dict(self, args: dict) -> Any: return self.descriptor.invoke(**args)` as a new method on `ToolEntry` (immediately after the existing `invoke(self, **kwargs)`). Same return type. The descriptor field is already typed.

    Decision references: D-02 (thin .voss — Python keeps tool registry, prompt, models); D-04 (`.voss` does NOT redeclare tools or bypass permission gate; calls back into Python helpers); D-09 (parity oracle — `run_turn` semantics preserved); Q-2/Q-6 (`_run_step_loop` extraction is the cleanest unblock for executor.voss).
  </action>
  <verify>
    <automated>pytest tests/harness/test_agent_integration.py tests/harness/ -q -m "not live"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_agent_integration.py -q` exits 0 (no behavior change in run_turn).
    - `pytest tests/harness/ -q -m "not live"` exits 0 (full harness suite green; existing tests cover the refactored path).
    - `grep -n 'async def _run_step_loop' voss/harness/agent.py` returns 1 match.
    - `grep -n 'def _substitute_placeholders' voss/harness/agent.py` returns 1 match.
    - `grep -n 'def _make_turn_result' voss/harness/agent.py` returns 1 match.
    - `grep -n 'def invoke_dict' voss/harness/tools.py` returns 1 match.
    - `grep -n 'results = await _run_step_loop' voss/harness/agent.py` returns 1 match (run_turn now delegates).
    - The inline tool loop is gone: `grep -c 'for i, step in enumerate(plan.steps)' voss/harness/agent.py` returns 0 (only the new helper body has the loop now, and it iterates `plan_steps` not `enumerate(plan.steps)` — though semantically equivalent).
  </acceptance_criteria>
  <done>Helpers extracted; ToolEntry.invoke_dict added; run_turn refactored to delegate (semantics preserved per parity-oracle invariant); full tests/harness/ suite green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Boot-path dispatch — `_resolve_run_turn` + per-invocation use in do_cmd/chat_cmd</name>
  <files>voss/harness/cli.py, tests/harness/test_boot_dispatch.py</files>
  <read_first>
    - voss/harness/cli.py (entire file — module imports line 23, _resolve_auth_or_die at 108-147, _resolve_default_model at 38-56, do_cmd at 177-246, chat_cmd at 271-292, _run_repl at 360-489)
    - voss/harness/config.py (load_harness_config — returns dict[str, str])
    - voss/harness/cache.py (M4-02 output — assert_fresh, CACHE_HARNESS_DIR constant)
    - voss/harness/diagnostics.py (M4-02 output — StaleHarnessCacheError class)
    - voss/exceptions.py (VossError base)
    - tests/harness/test_agent_integration.py:21-50 (FakeProvider pattern — reused in boot dispatch tests)
    - M4-RESEARCH.md §"Pattern 5: Boot-path dispatch (DOG-07, D-08)" (lines ~569-625)
    - M4-PATTERNS.md §"voss/harness/cli.py:_resolve_run_turn (NEW helper) — Wave 2 Pattern 5" and §"tests/harness/test_boot_dispatch.py (NEW) — Wave 2"
    - M4-RESEARCH.md §"Pitfall 4" (assert_fresh BEFORE dynamic import)
  </read_first>
  <behavior>
    - `_resolve_run_turn()` (no args) reads in order: `os.environ.get("VOSS_HARNESS")` → `harness_config.load_harness_config().get("backend")` → `"python"` default.
    - Backend values other than `"python"` or `"compiled"` raise `click.ClickException` with message `f"invalid VOSS_HARNESS={backend!r}: expected 'python' or 'compiled'"`.
    - When backend == `"python"`: returns the `run_turn` callable from `voss.harness.agent` (the parity oracle, D-09).
    - When backend == `"compiled"`: calls `harness_cache.assert_fresh(Path.cwd())` BEFORE any dynamic import; then `importlib.util.spec_from_file_location("voss_compiled_harness_loop", cwd / harness_cache.CACHE_HARNESS_DIR / "loop.py")`, `module_from_spec`, `exec_module`; returns `mod.run_turn`.
    - `do_cmd` (and `chat_cmd` if it currently uses `run_turn` directly) call `run_turn = _resolve_run_turn()` per-invocation, immediately before the `asyncio.run(run_turn(...))` call.
    - Module-top `from .agent import run_turn` at line 23 is either removed OR aliased to `_python_run_turn` (researcher's preference per M4-PATTERNS.md: keep the alias as a name to preserve any in-process callers and for `_resolve_run_turn`'s python-branch import; alternative is per-call `from .agent import run_turn` inside the python branch — Pattern 5 example uses the latter, which is fine).
    - Test: with `VOSS_HARNESS` unset, `_resolve_run_turn() is voss.harness.agent.run_turn` (D-08 default).
    - Test: with `VOSS_HARNESS=compiled` and a pre-compiled cache in cwd, `_resolve_run_turn()` returns a callable named `run_turn` from a module distinct from `voss.harness.agent`.
    - Test: `VOSS_HARNESS=rust` raises `click.ClickException`.
    - Test: with env unset and `load_harness_config` monkeypatched to return `{"backend": "compiled"}`, the compiled path is selected (config fallback).
    - Test: with `VOSS_HARNESS=compiled` and a stale cache (sha mismatch), `_resolve_run_turn()` raises `StaleHarnessCacheError` BEFORE importing the cached `loop.py` — assert via `assert "voss_compiled_harness_loop" not in sys.modules`.
  </behavior>
  <action>
    Edit `voss/harness/cli.py`. Add `def _resolve_run_turn():` near `_resolve_auth_or_die` (~lines 108-147 region). Imports inside the function (deferred for fast CLI startup): `from . import config as harness_config` (already a common pattern in this file); use `os.environ.get("VOSS_HARNESS")`; resolve `backend` per the env > config > default chain. If `backend not in ("python", "compiled")`, raise `click.ClickException(f"invalid VOSS_HARNESS={backend!r}: expected 'python' or 'compiled'")`. If `backend == "python"`, `from .agent import run_turn` and return it. If `backend == "compiled"`: `from . import cache as harness_cache`; `cwd = Path.cwd()`; call `harness_cache.assert_fresh(cwd)` (NO try/except — loud propagation per D-10); then `import importlib.util`; build `loop_py = cwd / harness_cache.CACHE_HARNESS_DIR / "loop.py"`; `spec = importlib.util.spec_from_file_location("voss_compiled_harness_loop", loop_py)`; `mod = importlib.util.module_from_spec(spec)`; `spec.loader.exec_module(mod)`; return `mod.run_turn`. Pitfall 4: `assert_fresh` MUST be called before `exec_module`.

    Edit `do_cmd` (cli.py ~line 235-244). Immediately before the `asyncio.run(run_turn(text, ...))` call site, insert `run_turn = _resolve_run_turn()`. Leave the rest of the call unchanged.

    Edit `chat_cmd` (cli.py ~line 271-292). If `run_turn` is referenced (likely indirectly through `_run_repl` calling `do_cmd`-like paths), audit the call chain. If `chat_cmd` directly imports/uses `run_turn`, mirror the do_cmd change. If `chat_cmd` delegates to `_run_repl` which itself imports `run_turn`, leave `chat_cmd` alone and surface the `_run_repl` site as a noted future-work item — the M4 success bar (D-12 (c)) is only `voss do`, so `chat_cmd` need not flip in M4 (per A4 assumption in M4-RESEARCH §Assumptions Log). Document the decision in the summary.

    Decide on the module-top import at line 23. Two acceptable options per M4-PATTERNS.md: (a) keep `from .agent import run_turn as _python_run_turn` for any non-resolved in-process callers and let `_resolve_run_turn`'s python branch use its own `from .agent import run_turn` inside the function; or (b) remove the module-top import entirely and rely on `_resolve_run_turn`'s deferred import. Either is fine; pick the smaller diff after reading line 23's call-site references. Document in the summary.

    Create `tests/harness/test_boot_dispatch.py` (NEW) per M4-PATTERNS.md target tests. Four tests minimum:
    (1) `test_resolve_python_by_default(monkeypatch)` — `monkeypatch.delenv("VOSS_HARNESS", raising=False)`; monkeypatch `load_harness_config` to return `{}` (no backend key); assert `_resolve_run_turn()` is the `voss.harness.agent.run_turn` object.
    (2) `test_invalid_backend_raises(monkeypatch)` — set `VOSS_HARNESS=rust`; expect `click.ClickException`.
    (3) `test_config_fallback(monkeypatch)` — env unset; monkeypatch `voss.harness.config.load_harness_config` to return `{"backend": "python"}`; assert `_resolve_run_turn() is voss.harness.agent.run_turn` (confirms config-fallback path; uses python so no cache pre-compile needed).
    (4) `test_compiled_stale_cache_raises_before_import(tmp_path, monkeypatch)` — `monkeypatch.chdir(tmp_path)`; create `tmp_path/voss/harness/agent/loop.voss` with trivial content; do NOT write a manifest (so cache is missing → stale); `monkeypatch.setenv("VOSS_HARNESS", "compiled")`; expect `StaleHarnessCacheError` (imported from `voss.harness.diagnostics`); after the expected-raise block, `import sys; assert "voss_compiled_harness_loop" not in sys.modules` (Pitfall 4 sentinel).
    (Optional fifth test for compiled-happy-path is deferred to Wave 3 parity test since it requires the .voss files to actually be authored, which is Task 3 of this plan.)

    Decision references: D-08 (env > config > default resolution); D-10 (loud stale-cache; no silent fallback); D-09 (Python parity oracle stays); A4 assumption (`_run_repl`/`chat_cmd` deferred from compiled path; out-of-scope for M4 D-12); Pitfall 4 (assert_fresh before import).
  </action>
  <verify>
    <automated>pytest tests/harness/test_boot_dispatch.py tests/harness/ -q -m "not live"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_boot_dispatch.py -q` exits 0 with 4 passed.
    - `pytest tests/harness/ -q -m "not live"` exits 0 (no regressions from the cli refactor).
    - `grep -n 'def _resolve_run_turn' voss/harness/cli.py` returns 1 match.
    - `grep -n 'harness_cache.assert_fresh' voss/harness/cli.py` returns at least 1 match.
    - `grep -n '_resolve_run_turn()' voss/harness/cli.py` returns at least 2 matches (at least the function def + 1 call site in do_cmd; chat_cmd handling documented in summary).
    - Pitfall 4 invariant verified by Test (4) which asserts `"voss_compiled_harness_loop" not in sys.modules` after the expected raise.
  </acceptance_criteria>
  <done>_resolve_run_turn implemented with env > config > default chain; assert_fresh called before dynamic import; do_cmd uses per-invocation resolve; 4 boot-dispatch tests passing; no regressions in tests/harness/.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Author the five `.voss` files; verify `voss check` + `voss compile` on the dir</name>
  <files>voss/harness/agent/loop.voss, voss/harness/agent/router.voss, voss/harness/agent/planner.voss, voss/harness/agent/executor.voss, voss/harness/agent/reviewer.voss</files>
  <read_first>
    - voss/harness/agent.py (Plan/ToolCall/TurnResult at 35-89 — the types .voss imports; _run_step_loop signature from Task 1; _substitute_placeholders signature)
    - voss/grammar.lark (especially: type_expr lines 17-22 for generics like `probable<Plan>`; stmt rules lines 88-98 — NO `for` loop; budget_kwarg lines 130-131; confidence_gate 73-74; try_stmt 133; use_stmt 174-175 — Wave 0 patched in M4-01; arg/named_arg 68-69)
    - voss/codegen.py (post M4-01: ExpressionEmitter.use_imported_names; auto-await for use-imported callees at lines 441-446)
    - samples/classify.voss (entire — probable<T> + confidence gate reference)
    - samples/research.voss (entire — agent + ctx + try/catch + use imports reference)
    - samples/support.voss (entire — header convention + memory references; M4 does NOT use memory)
    - M4-RESEARCH.md §"Pattern 2: The .voss file shapes (DOG-01..DOG-05)" (lines ~312-415)
    - M4-PATTERNS.md §"voss/harness/agent/loop.voss" through §"voss/harness/agent/reviewer.voss"
    - M4-RESEARCH.md §"Pitfall 1" (NAME imports only; no `use voss::harness as h`)
    - M4-RESEARCH.md §"Pitfall 2" (auto-await prereq — landed in M4-01)
  </read_first>
  <behavior>
    - All five files exist under `voss/harness/agent/` (DOG-01..DOG-05).
    - `voss check voss/harness/agent/` exits 0; aggregated summary printed.
    - `voss compile voss/harness/agent/` exits 0 and produces 5 `.py` artifacts plus `_manifest.json` under `.voss-cache/harness/`.
    - The compiled `.voss-cache/harness/executor.py` contains the substring `await _run_step_loop(` — proves Pitfall 2 mitigation works end-to-end. (M4-VALIDATION row `executor-voss-file`.)
    - All five files use NAME-form `use voss::harness::...` imports (NOT aliased `as` form). Even though M4-01 lands the grammar, M4 does NOT exercise aliased member calls per Pitfall 1.
    - Each file opens with two `#` header lines: filename + one-line primitive summary (M3 D-14 carry-forward).
    - `.voss` files contain only control-flow primitives: `ctx`, `probable<T>`, confidence gates, `try/catch`, `let`, `return`, `if/else`, calls. No pydantic model definitions; no prompt strings; no `@tool` declarations (D-02).
  </behavior>
  <action>
    Create `voss/harness/agent/loop.voss`. Header: `# loop.voss\n# Demonstrates: ctx(budget), probable<Plan> gate, dispatch into _run_step_loop, try/catch via reviewer.`. Imports (NAME form): `use voss::harness::agent::_run_step_loop`. Optional: `use voss::harness::agent::TurnResult` (if reviewer.voss does not own the result construction). Define `fn run_turn(task: string, tools: any, cwd: any, renderer: any, confidence_threshold: float = 0.60, token_budget: int = 60000, model: any = null, provider: any = null, history: any = null, permissions: any = null) -> any` matching agent.py:100-112. Body: `ctx(budget: 60000 tokens) { let route = route_intent(task); let plan_result: probable<any> = plan_task(task, tools, route, provider, model); if plan_result @ p >= confidence_threshold { let results = _run_step_loop(plan_result.value.steps, tools, permissions, renderer); return review(plan_result.value, results, history, task) } else { return clarify(plan_result.value, renderer) } }`. Use `any` for complex types that don't parse cleanly (`dict<string, ToolEntry>` is rejected by some `type_expr` interpretations; `any` is the safe shape per M4-PATTERNS.md). `route_intent`, `plan_task`, `review`, `clarify` are forward-references resolved across files via NAME-form `use voss::harness::agent::<file>::<symbol>` imports (e.g. `use voss::harness::agent::router::route_intent`). Each `.voss` file produces its own `.py` under `.voss-cache/harness/`; loop.py imports the sibling stage modules. The analyzer must resolve these cross-file references for `voss check voss/harness/agent/` to pass. If cross-file resolution fails after attempting cross-file `use voss::harness::agent::<file>::<symbol>` imports, the executor MUST emit `## PLANNING INCONCLUSIVE — cross-file analyzer resolution required for D-01 substantive content` and STOP. Do NOT degrade to stub files; that violates D-01's 20-40 LOC target and reduces DOG-01..DOG-05 to file-existence trivia. The planner has not authorized scope reduction; surface the analyzer gap to the user for a follow-up planning pass that either lands cross-file analyzer support in M4 Wave 0 or splits the phase.

    Create `voss/harness/agent/router.voss`. Header: `# router.voss\n# Demonstrates: probable<string> for intent classification.`. Pure `.voss` — no imports. Define `fn route_intent(task: string) -> string { let intent: probable<string> = ask("Is this a slash command or natural-language task? " + task); if intent @ p >= 0.80 { return intent.value } else { return "natural" } }`. The `ask(...)` runtime is provided by the codegen-injected `voss_runtime` imports (codegen.py:152-154 auto-adds these).

    Create `voss/harness/agent/planner.voss`. Header: `# planner.voss\n# Demonstrates: probable<Plan>, ask with schema.`. Import: `use voss::harness::agent::Plan` (NAME form). Define `fn plan_task(task: string, tools: any, route: string, provider: any, model: any) -> probable<Plan> { let plan: probable<Plan> = ask("Task: " + task); return plan }`. The confidence gate is in loop.voss, not here.

    Create `voss/harness/agent/executor.voss`. Header: `# executor.voss\n# Demonstrates: thin forwarder to Python _run_step_loop (no for loop / no **kwargs in .voss).`. Import: `use voss::harness::agent::_run_step_loop`. Define `fn execute_steps(plan: any, tools: any, permissions: any, renderer: any) -> any { return _run_step_loop(plan.steps, tools, permissions, renderer) }`. The auto-await from M4-01 fires because `_run_step_loop` is in `use_imported_names`. Acceptance includes a grep for `await _run_step_loop(` in the compiled `executor.py`.

    Create `voss/harness/agent/reviewer.voss`. Header: `# reviewer.voss\n# Demonstrates: try/catch around final synthesis; calls Python _substitute_placeholders + _make_turn_result.`. Imports: `use voss::harness::agent::_substitute_placeholders`, `use voss::harness::agent::_make_turn_result`. Define `fn review(plan: any, results: any, history: any, task: string) -> any { try { let final = _substitute_placeholders(plan.final_when_done, results); return _make_turn_result(plan, plan.confidence, final, results, 0.0) } catch e { return _make_turn_result(plan, 0.0, "<error during review>", results, 0.0) } }`. Also define `fn clarify(plan: any, renderer: any) -> any { let question = plan.open_question; return _make_turn_result(plan, plan.confidence, question, [], 0.0) }`. Using `_make_turn_result` (the Task 1 fallback factory) sidesteps the named-arg constructor open question.

    After all five files exist, run `voss check voss/harness/agent/` and `voss compile voss/harness/agent/ --project-root <repo root>` manually (no automated test in this task — Task 2 boot dispatch tests don't exercise the .voss files; the M4-04 parity test will). Confirm exit 0 + 5 .py + _manifest.json appear under `.voss-cache/harness/`. Grep `.voss-cache/harness/executor.py` for `await _run_step_loop(`.

    Cross-file resolution requirement: each of the five `.voss` files MUST carry substantive content per D-01 (20-40 LOC each; min-line floors enforced in this plan's `must_haves.truths` and `acceptance_criteria`). If `voss check voss/harness/agent/loop.voss` reports undefined `route_intent`/`plan_task`/`review`/`clarify` because the analyzer does not cross-link sibling files, attempt cross-file `use voss::harness::agent::<file>::<symbol>` imports first. If that still fails, STOP and emit `## PLANNING INCONCLUSIVE — cross-file analyzer resolution required for D-01 substantive content`. Do NOT degrade to stub files (1-2 line re-exports) — that violates D-01's 20-40 LOC per-file target and silently reduces DOG-01..DOG-05 to file-existence-only acceptance, which is scope reduction. The acceptance criteria below grep for minimum line counts per file to make this fallback path naturally inaccessible.

    Decision references: D-01 (pipeline split — one stage per file, with the consolidation caveat above); D-02 (thin .voss — no pydantic / prompts / @tool); D-04 (executor calls Python helper, no privileged tool-call path); Pattern 2 + Pitfalls 1, 2, 3 (NAME imports, auto-await, cache jail).
  </action>
  <verify>
    <automated>python -m voss.cli check voss/harness/agent/ && python -m voss.cli compile voss/harness/agent/ --project-root . && test -f .voss-cache/harness/loop.py && test -f .voss-cache/harness/router.py && test -f .voss-cache/harness/planner.py && test -f .voss-cache/harness/executor.py && test -f .voss-cache/harness/reviewer.py && test -f .voss-cache/harness/_manifest.json && grep -q 'await _run_step_loop' .voss-cache/harness/executor.py</automated>
  </verify>
  <acceptance_criteria>
    - All five files exist: `ls voss/harness/agent/{loop,router,planner,executor,reviewer}.voss` succeeds.
    - `python -m voss.cli check voss/harness/agent/` exits 0.
    - `python -m voss.cli compile voss/harness/agent/ --project-root .` exits 0.
    - `.voss-cache/harness/{loop,router,planner,executor,reviewer}.py` all exist after compile.
    - `.voss-cache/harness/_manifest.json` exists; `python -c "import json; m=json.load(open('.voss-cache/harness/_manifest.json')); assert m['version']==1; assert len(m['sources'])==5"` exits 0.
    - `grep -q 'await _run_step_loop' .voss-cache/harness/executor.py` exits 0 (Pitfall 2 sentinel — proves codegen auto-await fires on the use-imported helper).
    - `grep -c '^# ' voss/harness/agent/loop.voss` returns at least 2 (header convention M3 D-14).
    - Per-file substantive-content gates (D-01 floors; stub-file fallback blocker). Use comment-stripped line counts: `grep -vc '^\s*#' voss/harness/agent/loop.voss` ≥ 20; `grep -vc '^\s*#' voss/harness/agent/router.voss` ≥ 8; `grep -vc '^\s*#' voss/harness/agent/planner.voss` ≥ 8; `grep -vc '^\s*#' voss/harness/agent/executor.voss` ≥ 6; `grep -vc '^\s*#' voss/harness/agent/reviewer.voss` ≥ 12. If any file falls below its floor, the implementation has degraded toward stubs — STOP and emit `## PLANNING INCONCLUSIVE`.
    - Manual review: each `.voss` file contains only control flow per D-02 (no pydantic models, no prompt strings, no `@tool` declarations). Reviewer signs off in M4-04 manual-only verification per M4-VALIDATION.
  </acceptance_criteria>
  <done>Five `.voss` files exist with per-file substantive content meeting the D-01 LOC floors (20/8/8/6/12); `voss check voss/harness/agent/` exits 0 with cross-file `use` imports resolving; `voss compile` produces 5 .py + manifest; executor.py contains `await _run_step_loop`. Stub-file fallback is prohibited per D-01.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `VOSS_HARNESS` env var → `_resolve_run_turn` | Closed-enum input (`python` / `compiled`); invalid values raise `click.ClickException`. |
| `~/.config/voss/config.toml` `[harness] backend` → `_resolve_run_turn` | Same closed-enum semantics; absent key falls through to env or default. |
| Dynamic import of `.voss-cache/harness/loop.py` | Path is `Path.cwd() / .voss-cache/harness/loop.py` (project-local). `assert_fresh` validates sha256(sources) before `exec_module`. |
| `.voss` source text → compiled Python | All `use` imports compile to literal `from X import Y` lines via codegen.py:142-148 (no template injection). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M4-W2-boot-spoof | Spoofing | `_resolve_run_turn` env-var dispatch | mitigate | Closed enum validation (`python`/`compiled` only); raises ClickException on anything else. Per D-08, env-var resolution explicit; no auto-detect / silent fallback. |
| T-M4-W2-stale-rce | Tampering / RCE | Dynamic import of stale `.voss-cache/harness/loop.py` | mitigate | `assert_fresh(cwd)` raises BEFORE `exec_module` (Pitfall 4); sha256 over SOURCE `.voss` files validates that the on-disk artifacts derived from the current sources. Sentinel test in Task 2 (`test_compiled_stale_cache_raises_before_import`) asserts `voss_compiled_harness_loop` is NOT in `sys.modules` post-raise. |
| T-M4-W2-permission-bypass | Elevation of Privilege | `.voss` calling tools | mitigate | D-04 invariant: `.voss` does NOT have a privileged tool-call path. `executor.voss` forwards to Python `_run_step_loop` which embeds the M1 strict-tier `PermissionGate.check`. No new code path bypasses the gate. |
| T-M4-W2-cwd-jail | Tampering | `_resolve_run_turn` reads `Path.cwd()` | mitigate | The `cwd` used is the invoking process's working directory (consistent with `voss compile`'s implicit project_root per Q-4); documented in M4-05 install one-liner. Manifest sha matches against source files within the same cwd-rooted tree. |
| T-M4-W2-grammar-injection | Tampering | `.voss` files reading user-controlled content | accept | The five `.voss` files in `voss/harness/agent/` are repo-controlled source. No runtime injection surface; they're compiled at build/install time, not at user-task time. |
| T-M4-W2-cross-link | Tampering | Forward-references in loop.voss (route_intent/plan_task/...) | mitigate | Documented as a planner-time decision: either cross-file linkage works in the current analyzer, or fallback to consolidated single-file with stub sibling files. Either way the analyzer validates: no undefined symbols escape `voss check`. |
</threat_model>

<verification>
After all three tasks land:
1. `pytest tests/harness/test_agent_integration.py tests/harness/test_boot_dispatch.py tests/harness/ -q -m "not live"` exits 0.
2. `python -m voss.cli check voss/harness/agent/` exits 0.
3. `python -m voss.cli compile voss/harness/agent/ --project-root .` exits 0.
4. `ls .voss-cache/harness/` shows the 5 `.py` files + `_manifest.json`.
5. `grep -q 'await _run_step_loop' .voss-cache/harness/executor.py` exits 0.
6. M4-VALIDATION rows `loop-voss-file`, `router-voss-file`, `planner-voss-file`, `executor-voss-file`, `reviewer-voss-file`, `run-step-loop-helper`, `boot-dispatch` flip from ❌ to ✓.
</verification>

<success_criteria>
- All five `.voss` files exist under `voss/harness/agent/` (DOG-01..DOG-05).
- `voss check voss/harness/agent/` exits 0.
- `voss compile voss/harness/agent/` exits 0 and emits 5 `.py` + `_manifest.json`.
- Compiled `executor.py` contains `await _run_step_loop(` (Pitfall 2 mitigation verified end-to-end).
- `_run_step_loop` + `_substitute_placeholders` + `_make_turn_result` + `ToolEntry.invoke_dict` all added; `run_turn` refactored to delegate (parity-oracle semantics preserved per D-09).
- `_resolve_run_turn()` implemented with env > config > default chain; `assert_fresh` precedes dynamic import (Pitfall 4); `do_cmd` uses per-invocation resolve.
- `tests/harness/test_boot_dispatch.py` passes with 4 tests; full tests/harness/ suite green.
</success_criteria>

<output>
After completion, create `.planning/phases/M4-voss-authored-harness-loop/M4-03-SUMMARY.md` documenting:
- Final layout of the 5 `.voss` files (single-file consolidated vs cross-file split — whichever was chosen).
- Exact LOC added per Python file.
- Decision on module-top `from .agent import run_turn` (removed vs aliased).
- Decision on chat_cmd (left on python path per A4, or flipped — should be deferred).
- All 4 boot-dispatch tests + tests/harness/ regression suite green.
- Sample of `.voss-cache/harness/_manifest.json` (showing all 5 sources, sha256 of each, voss_version).
</output>
