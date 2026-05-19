---
phase: M13-multi-agent-in-chat-caps-01d
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/harness/conftest.py
  - tests/harness/test_multiagent_fanout.py
  - tests/harness/test_multiagent_steer.py
  - tests/harness/test_multiagent_recursion.py
  - tests/harness/tui/test_subagent_reveal.py
  - tests/e2e/test_multiagent_chat_e2e.py
  - tests/harness/tui/test_keymap_baseline.py
autonomous: true
requirements: [MAG-01, MAG-02, MAG-03, MAG-04, MAG-05, MAG-06, MAG-07, MAG-08]

must_haves:
  truths:
    - "A scripted multi-agent provider fixture (parent + per-child scripts extending FakeStreamingProvider) is importable from any tests/harness test"
    - "Every MAG-01..MAG-08 observable signal from M13-VALIDATION.md has a collectable red/xfail test asserting it"
    - "The back-compat regression guard proves tests/harness/test_subagent_recursion.py collects and passes unmodified (no depth/max_depth added by M13)"
    - "test_keymap_baseline.py has additive ctrl+o (-> toggle_subagent_detail) and ctrl+c (-> interrupt, unchanged) assertion rows"
    - "All new M13 tests COLLECT without import errors and are RED (fail or xfail) — no green false-positives, no collection errors"
  artifacts:
    - path: "tests/harness/conftest.py"
      provides: "scripted_multiagent_provider fixture (additive — existing fixtures untouched)"
      contains: "def scripted_multiagent_provider"
      min_lines: 290
    - path: "tests/harness/test_multiagent_fanout.py"
      provides: "MAG-01 concurrency overlap + MAG-03 even-split/rebalance + MAG-04 no-oversell race/exactly-once/depth-bound red tests"
      contains: "class TestConcurrentInFlight"
      min_lines: 60
    - path: "tests/harness/test_multiagent_steer.py"
      provides: "MAG-05 correction-vs-control red test"
      contains: "class TestCorrectionChangesBehavior"
      min_lines: 30
    - path: "tests/harness/test_multiagent_recursion.py"
      provides: "MAG-06 depth-2 nested budget + nested panels + no-leak red test + back-compat guard"
      contains: "class TestDepth2"
      min_lines: 40
    - path: "tests/harness/tui/test_subagent_reveal.py"
      provides: "MAG-02 quiet-by-default + ctrl+o reveal + MAG-07 post-gather region-clean red tests"
      contains: "class TestPostGatherRegionClean"
      min_lines: 40
    - path: "tests/e2e/test_multiagent_chat_e2e.py"
      provides: "MAG-08 headline transcript red e2e"
      contains: "def test_multiagent_chat_e2e"
      min_lines: 25
    - path: "tests/harness/tui/test_keymap_baseline.py"
      provides: "additive ctrl+o/ctrl+c keymap-resolution assertion rows (existing rows untouched)"
      contains: "toggle_subagent_detail"
  key_links:
    - from: "tests/harness/test_multiagent_fanout.py"
      to: "tests/harness/conftest.py::scripted_multiagent_provider"
      via: "pytest fixture argument"
      pattern: "scripted_multiagent_provider"
    - from: "tests/harness/test_multiagent_fanout.py"
      to: "voss.harness.multiagent"
      via: "guarded import inside test body (module created in W1)"
      pattern: "voss\\.harness\\.multiagent"
    - from: "tests/harness/tui/test_keymap_baseline.py"
      to: "voss.harness.tui.keymap.KEYMAP"
      via: "binding-resolution assertion for ctrl+o"
      pattern: "ctrl\\+o"
---

<objective>
Stand up the complete Wave 0 RED test scaffold for phase M13 (Multi-agent in Chat, MAG-01..MAG-08) plus the shared scripted multi-agent provider fixture. This plan writes ZERO production code — it only creates failing/xfail tests that pin every observable signal seam from M13-VALIDATION.md so subsequent waves have a deterministic green target, and it adds a back-compat regression guard that proves M13 keeps the subagent recursion-pinning contract intact.

Purpose: Nyquist compliance — no implementation wave may proceed without a red test it must turn green. The fixture is shared (one source of scripted-provider truth for fanout/steer/recursion/e2e).
Output: 1 additive conftest fixture + 5 new red/xfail test files + 1 additively-extended keymap baseline test, all collectable, all red (except the two intentional green back-compat guards).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-SPEC.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-CONTEXT.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md

<interfaces>
<!-- Scripted-provider analog the fixture MUST extend. Executor uses these directly — no codebase exploration needed. -->

From tests/harness/test_agent_loop.py:76-113 (FakeStreamingProvider — the analog to extend):
```
@dataclass
class FakeStreamingProvider:
    scripts: list[list[ProviderStreamEvent]]
    stream_calls: list[dict] = field(default_factory=list)
    complete_calls: list[dict] = field(default_factory=list)
    record_run_return: Any = None
    _stream_index: int = 0
    def stream(self, **kwargs): ...          # returns async-gen over scripts[_stream_index]; appends kwargs to stream_calls
    async def complete(self, **kwargs): ...  # returns ProviderResponse(text="", model=..., 0,0,0.0, raw={}, parsed=record_run_return)
```

From voss/harness/providers.py:30-93 (stream event constructors the scripts use):
```
TextDelta(text: str)
ToolUseStart(id: str, name: str)
ToolUseDelta(id: str, partial_json: str)
ToolUseEnd(id: str)
Usage(prompt_tokens, completion_tokens, cost_usd, cache_creation_input_tokens=0, cache_read_input_tokens=0)
Done(stop_reason: str)
ParsedPlan(plan: Plan)              # terminal event carrying a structured Plan
ProviderStreamEvent = Union[TextDelta, ToolUseStart, ToolUseDelta, ToolUseEnd, Usage, Done, ParsedPlan]
```

From tests/harness/test_agent_loop.py:148-160 (canonical "done in one iter" script shape, via _done_script):
```
[TextDelta(text="..."), ParsedPlan(plan=plan), Usage(prompt_tokens=10, completion_tokens=5, cost_usd=0.001), Done(stop_reason="end_turn")]
```

From tests/harness/test_agent_loop.py:192-207 (how a scripted provider drives the loop):
```
result = await _run_turn_exec("do thing", tools={}, cwd=tmp_path, renderer=renderer, provider=provider, model="stub-model")
```

From tests/harness/tui/test_live_visualization.py:25-49 (TUI pilot analog):
```
app = VossTUIApp()
async with app.run_test() as pilot:
    renderer = TextualRenderer(app=pilot.app)
    renderer.show_subagent_start("reviewer", "abc", 2000)
    await pilot.pause()
    panels = list(pilot.app.query(SubAgentPanel))
```

From tests/e2e/test_chat_e2e.py:14-23 + tests/e2e/runner.py:1-31 (e2e CliRunner — auto StubProvider via generated sitecustomize):
```
def test_x(cli_runner: CliRunner) -> None:
    r = cli_runner.run("chat", "--plain", stdin="<prompt>\n/exit\n", timeout=20.0)
    assert r.returncode == 0, r.output
```

From tests/harness/tui/test_keymap_baseline.py:1-45 (parametrized table + resolution helper to extend additively):
```
from voss.harness.tui.keymap import KEYMAP, Binding
# rows are (key, context_substr); resolution: hit = [b for b in KEYMAP if b.key == key and context_substr in b.context]
# test_keymap_size_at_least_14 asserts len(KEYMAP) >= 14 (adding a row keeps it green — leave it)
```

From tests/harness/test_subagent_recursion.py:23-40 (the back-compat pin M13 must NOT break):
```
sig = inspect.signature(subagents.run_subagent)         # NO "depth"/"max_depth" param
for attr in ("MAX_DEPTH","DEPTH_LIMIT","RECURSION_LIMIT"): assert not hasattr(subagents, attr)
```
</interfaces>

<read_first>
- `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md` — Per-Task Verification Map (the exact observable signal per MAG); Wave 0 Requirements checklist; Security Domain threat refs.
- `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md` §"Test files (NEW)" + §"Shared scripted-provider analog" + §"test_keymap_baseline.py (MOD)" — the per-file analog map and exact assertions each red test must carry.
- `tests/harness/test_agent_loop.py` (lines 60-210) — `FakeStreamingProvider`, `_make_plan`, `_done_script`, `RecordingRenderer`, `_run_turn_exec` drive pattern. SOURCE-OF-TRUTH analog for the fixture.
- `tests/harness/conftest.py` (all 291 lines) — THE FILE BEING MODIFIED. Existing autouse fixtures (`isolated_state`, `git_repo`, `precompiled_harness`, `parity_project`, `tmp_voss_repo`, `pre_m8_*`, `fake_session_corpus`, `chroma_disabled_env`) MUST stay byte-stable; the new fixture is appended only.
- `tests/harness/tui/test_live_visualization.py` (lines 1-55) — pilot `run_test()`/`pilot.pause()`/`query(SubAgentPanel)` analog for the reveal test.
- `tests/e2e/test_chat_e2e.py` (lines 1-40) + `tests/e2e/runner.py` (lines 1-35) — `CliRunner` + `cli_runner` fixture + auto-StubProvider sitecustomize for the headline e2e analog.
- `tests/harness/tui/test_keymap_baseline.py` (all 45 lines) — THE FILE BEING MODIFIED. Parametrized row table; additive rows only, existing rows + `test_keymap_size_at_least_14` untouched.
- `tests/harness/test_subagent_recursion.py` (lines 1-45) — the back-compat contract the regression guard asserts (collects + passes unmodified).
- `voss/harness/providers.py` (lines 30-93) — the stream-event dataclasses the scripts construct.
</read_first>

<tasks>

<task type="auto">
  <name>Task 1: Shared scripted multi-agent provider fixture + fanout/steer/recursion harness red tests</name>
  <files>tests/harness/conftest.py, tests/harness/test_multiagent_fanout.py, tests/harness/test_multiagent_steer.py, tests/harness/test_multiagent_recursion.py</files>
  <read_first>
    - tests/harness/conftest.py (all 291 lines — preserve every existing fixture verbatim; append only)
    - tests/harness/test_agent_loop.py:60-210 (FakeStreamingProvider / _make_plan / _done_script / _run_turn_exec drive)
    - voss/harness/providers.py:30-93 (TextDelta/ToolUseStart/ToolUseEnd/Usage/Done/ParsedPlan/ProviderStreamEvent)
    - .planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md (MAG-01/03/04/05/06 rows — exact observable signals + Security Domain threat refs)
    - .planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md §"Test files (NEW)" (the per-test assertion list)
  </read_first>
  <action>
APPEND (do not rewrite) a `scripted_multiagent_provider` pytest fixture to the END of `tests/harness/conftest.py`. Every existing fixture (`isolated_state`, `git_repo`, `precompiled_harness`, `parity_project`, `tmp_voss_repo`, `pre_m8_architecture_md`, `pre_m8_session_json`, `fake_session_corpus`, `chroma_disabled_env`) and all existing imports MUST remain byte-identical — verify with the regression check in acceptance_criteria before finishing. The fixture builds a provider double using the `FakeStreamingProvider` idiom from `test_agent_loop.py:76` (replicate the minimal `stream`/`complete` pair using `voss.harness.providers` events; do NOT import the test module — copy the dataclass shape). It must support a `scripts: dict[str, list[list[ProviderStreamEvent]]]` keyed by logical agent role ("parent", "child-a", "child-b", "grandchild", ...) so one fixture instance can deterministically drive a parent plus N children plus a grandchild. Provide script-builder helpers per the `_make_plan`/`_done_script` analog: a plan that emits a spawn-style tool call, a plan that emits a steer tool call, a plan that emits a gather tool call, and a terminal done plan. Per D-11 the fixture is hermetic (no live network, no real provider). Docstring must cite it as the M13 shared scripted-provider truth (M13-PATTERNS §"Shared scripted-provider analog").

CREATE `tests/harness/test_multiagent_fanout.py` with `from __future__ import annotations`, class-based pytest (project rule), `tmp_path`-based. Classes and their RED assertions (per M13-VALIDATION MAG-01/03/04 rows):
- `TestConcurrentInFlight` (MAG-01): assert ≥2 children observably in-flight at the same instant — each child stub records a wall-clock window; assert windows overlap (NOT serial); spy that `voss.harness.multiagent.ChildRegistry.active()` returns ≥2 between spawn and gather.
- `TestEvenSplitRebalance` (MAG-03): with reserve R and N children, assert each `allocator.snapshot()[h] ≈ R // N`; after one child `release()`, assert a surviving child's allotment strictly increases; assert the panel `BudgetMeter` reflects the new total.
- `TestNoOversell` (MAG-04, must-not-happen, threat T-M13 oversell): `await asyncio.gather(*[allocator.allocate(h) for h in many])` against reserve R → assert `sum(allocator.snapshot().values()) <= R` and denied-count matches floor math; double `release(h)` → assert no double-credit (Σ still ≤ R, exactly-once); depth-bound: grandchild allotment ≤ child slice ≤ parent reserve (threat T-M13 recursion-DoS).
`voss.harness.multiagent` does NOT exist until W1. To keep COLLECTION clean while staying RED: do NOT import `voss.harness.multiagent` at module scope. Decorate each test class (or method) with `@pytest.mark.xfail(reason="W1 multiagent.py not yet implemented", raises=(ImportError, AttributeError, AssertionError), strict=False)` and import the module inside the test body. `strict=False` is correct for W0 (later waves flip these xfail→xpass; tightening to strict is out of W0 scope). Do NOT use `importorskip` (skip is not RED). Cite threat refs T-M13 oversell / T-M13 recursion-DoS in the `TestNoOversell` docstring.

CREATE `tests/harness/test_multiagent_steer.py` — `from __future__ import annotations`, class `TestCorrectionChangesBehavior` (MAG-05, threat T-M13 mis-steer): use the `scripted_multiagent_provider` fixture with a child script that BRANCHES on injected-guidance presence (emits a different `final` when steered). Assert WITH-correction child output != no-correction control output; the child is scripted for ≥2 iterations so the `agent.py:830` drain is observably hit (cite RESEARCH Pitfall 2 in the docstring: a child that decides "done" before the drain never consumes a pending steer — so ≥2 iterations are mandatory). xfail-guard the multiagent import identically to Task 1's pattern.

CREATE `tests/harness/test_multiagent_recursion.py` — `from __future__ import annotations`, class `TestDepth2` (MAG-06, threat T-M13 recursion-DoS): scripted parent→child→grandchild via the fixture. Assert (a) 3 distinct `panel_id`s mounted concurrently, (b) grandchild allotment ≤ child slice ≤ parent reserve at all 3 levels, (c) post-gather zero `SubAgentPanel`. The test MUST NOT introduce or reference any `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` symbol (recursion bounded by viable-floor only — keeps the back-compat pin green). xfail-guard the multiagent import identically. (Task 3 extends this same file with the green back-compat guard class — leave room.)

NEVER inline a full implementation of `multiagent.py` in any test or `<action>` — the tests assert behavior against the not-yet-existing module by name only.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py tests/harness/test_multiagent_recursion.py --collect-only -q 2>&1 | tail -3 && python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py tests/harness/test_multiagent_recursion.py -q 2>&1 | tail -4</automated>
  </verify>
  <acceptance_criteria>
    - SOURCE: `git diff --stat tests/harness/conftest.py` shows ONLY appended lines (zero deletions/edits to existing fixtures or imports); `python -c "import ast; ast.parse(open('tests/harness/conftest.py').read())"` exits 0; `git diff tests/harness/conftest.py | grep -c '^-[^-]'` returns 0 (no removed lines).
    - SOURCE: `grep -c "def scripted_multiagent_provider" tests/harness/conftest.py` returns 1; each of the three new test files contains `from __future__ import annotations` and at least one `class Test`.
    - BEHAVIOR: `pytest --collect-only` for the three files exits 0 with zero collection errors (no module-scope `voss.harness.multiagent` import).
    - TEST-COMMAND: `pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py tests/harness/test_multiagent_recursion.py -q` reports 0 passed, 0 errors, and ≥1 xfailed (all MAG tests RED).
  </acceptance_criteria>
  <done>The shared fixture is appended to conftest (existing fixtures byte-stable, AST parses), the three harness test files collect cleanly and run RED (xfail, never passed, never errored), each MAG-01/03/04/05/06 observable signal from M13-VALIDATION has a named class asserting it, and no test introduces a depth/max_depth symbol.</done>
</task>

<task type="auto">
  <name>Task 2: TUI reveal + headline e2e red tests + additive keymap-baseline rows</name>
  <files>tests/harness/tui/test_subagent_reveal.py, tests/e2e/test_multiagent_chat_e2e.py, tests/harness/tui/test_keymap_baseline.py</files>
  <read_first>
    - tests/harness/tui/test_keymap_baseline.py (all 45 lines — THE FILE BEING MODIFIED; existing rows + test_keymap_size_at_least_14 + test_every_binding_has_description_and_action stay byte-stable)
    - tests/harness/tui/test_live_visualization.py:1-55 (pilot run_test/pause/query(SubAgentPanel) analog)
    - tests/e2e/test_chat_e2e.py:1-40 + tests/e2e/runner.py:1-35 (CliRunner + cli_runner fixture + auto-StubProvider)
    - .planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md (MAG-02/07/08 rows + Wave 0 keymap-baseline requirement)
    - .planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md §"tests/harness/tui/test_subagent_reveal.py" + §"tests/e2e/test_multiagent_chat_e2e.py" + §"test_keymap_baseline.py (MOD)"
  </read_first>
  <action>
CREATE `tests/harness/tui/test_subagent_reveal.py`, modeled on `test_live_visualization.py:25-49` (`VossTUIApp().run_test()` + `pilot.pause()` + `query(SubAgentPanel)`). `from __future__ import annotations`; match the neighbor file's explicit `@pytest.mark.asyncio` decorator style (the TUI test files use it explicitly even though `asyncio_mode="auto"`). Classes/RED assertions per M13-VALIDATION MAG-02/07:
- `TestQuietByDefault` (MAG-02 a/b): after a child panel is mounted, assert the body `Vertical` (`#panel-body-{parent_id}`) `styles.display == "none"` by default; after a (not-yet-existing) `app.action_toggle_subagent_detail()` it contains ≥1 streamed-step `Static`; assert the `BudgetMeter` leaves the em-dash placeholder and `update_budget` increments ≥1× before collapse.
- `TestPostGatherRegionClean` (MAG-07, threat T-M13 orphan / T-M13 ui-thread): after a multi-child fan-out + gather, assert `len(pilot.app.query(SubAgentPanel)) == 0` and `app._side_owner`/`app._side_pinned` match a pre-spawn snapshot (M9-08 contract).
The reveal action + multiagent fan-out path do not exist until W2B/W2A. Decorate the action-toggle / fan-out-dependent tests with `@pytest.mark.xfail(reason="W2 reveal/fanout not yet implemented", raises=(AttributeError, ImportError, AssertionError), strict=False)` so they COLLECT but run RED. Do NOT import `voss.harness.multiagent` at module scope.

CREATE `tests/e2e/test_multiagent_chat_e2e.py`, modeled on `test_chat_e2e.py:14-23` using the `cli_runner` fixture (the e2e runner auto-installs the deterministic StubProvider via generated `sitecustomize.py` per `tests/e2e/runner.py:1-31` — NO provider plumbing in the test). `def test_multiagent_chat_e2e(cli_runner)`: one NL request via `stdin=` asking for parallel sub-agent work, then `/exit`. Assert the headline transcript (MAG-08): ≥2 concurrent panels referenced, ≥1 budget tick per child, ≥1 applied correction, ≥1 rebalance event, an aggregated multi-child turn line, clean post-gather region — all in one test. Multiagent tools are not wired into chat until W4, so mark the test `@pytest.mark.xfail(reason="W4 chat integration not yet wired", strict=False)`; keep `timeout=30.0` per the e2e analog.

MODIFY `tests/harness/tui/test_keymap_baseline.py` ADDITIVELY ONLY: do NOT touch `test_keymap_size_at_least_14`, do NOT remove/reorder any existing parametrize row, do NOT alter `test_every_binding_has_description_and_action`. ADD one row to the `test_keymap_includes_ui_spec_row` parametrize list: `("ctrl+o", "main")`. Leave the existing `("ctrl+c", "global")` row untouched. ADD a NEW test function `test_ctrl_o_resolves_to_toggle_subagent_detail` asserting there exists a `KEYMAP` binding with `key == "ctrl+o"` whose `.action == "toggle_subagent_detail"`. ADD a NEW test function `test_ctrl_c_still_interrupt` asserting the `ctrl+c` binding's `.action == "interrupt"` is unchanged (the back-compat half of the keymap guard). Do NOT xfail-mark the keymap assertions — they assert a static module table and must be hard RED that W2B turns green. `test_ctrl_c_still_interrupt` MUST PASS now (ctrl+c already resolves to `interrupt` at keymap.py:37) — it is GREEN from W0. `test_ctrl_o_resolves_to_toggle_subagent_detail` + the new `("ctrl+o","main")` parametrize case fail RED now (intended W0 state, W2B turns green).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/tui/test_subagent_reveal.py tests/e2e/test_multiagent_chat_e2e.py tests/harness/tui/test_keymap_baseline.py --collect-only -q 2>&1 | tail -3 && python -m pytest tests/harness/tui/test_keymap_baseline.py -q 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - SOURCE: `git diff tests/harness/tui/test_keymap_baseline.py | grep -c '^-[^-]'` returns 0 (no deleted/modified existing lines — additive only); `python -c "import ast; ast.parse(open('tests/harness/tui/test_keymap_baseline.py').read())"` exits 0; `grep -c "toggle_subagent_detail" tests/harness/tui/test_keymap_baseline.py` ≥ 1.
    - BEHAVIOR: all three files collect with zero errors; `test_subagent_reveal.py` + `test_multiagent_chat_e2e.py` report 0 passed (xfail RED).
    - TEST-COMMAND: `pytest tests/harness/tui/test_keymap_baseline.py -q` shows ALL pre-existing tests still passing (no regression), `test_ctrl_c_still_interrupt` PASSED, and `test_ctrl_o_resolves_to_toggle_subagent_detail` + the `ctrl+o` parametrize case FAILED RED.
  </acceptance_criteria>
  <done>The TUI reveal test and headline e2e collect cleanly and run xfail-RED; `test_keymap_baseline.py` is extended additively with a GREEN ctrl+c-still-interrupt guard and a RED ctrl+o-resolution assertion; no existing keymap test regressed.</done>
</task>

<task type="auto">
  <name>Task 3: Back-compat regression guard + full Wave 0 red/collection audit</name>
  <files>tests/harness/test_multiagent_recursion.py</files>
  <read_first>
    - tests/harness/test_subagent_recursion.py (all 45 lines — the contract being guarded: no depth/max_depth on run_subagent, no MAX_DEPTH/DEPTH_LIMIT/RECURSION_LIMIT module attr)
    - tests/harness/test_multiagent_recursion.py (the file from Task 1 being extended with the guard class)
    - .planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md §"Wave 0 Requirements" (regression-guard checklist) + §"Validation Sign-Off"
  </read_first>
  <action>
EXTEND `tests/harness/test_multiagent_recursion.py` (created in Task 1) with a new class `TestBackCompatRecursionPinIntact` — the M13 back-compat regression guard. Without modifying `tests/harness/test_subagent_recursion.py`, it MUST assert the pinning contract still holds: (1) import `voss.harness.subagents`; assert `inspect.signature(subagents.run_subagent)` has neither `depth` nor `max_depth` parameters; (2) assert `subagents` has no `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` module attribute; (3) prove the existing pinning suite still collects+passes by `subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/harness/test_subagent_recursion.py"], cwd=<repo root>, capture_output=True)` and assert `returncode == 0` (do NOT call `pytest.main` re-entrantly inside the running session). This class is UNIQUE: GREEN from Wave 0 onward (it asserts the CURRENT, correct, unmodified state) and must stay green through every later wave — it is the tripwire that fails loudly if any wave adds a depth constant. Add a module docstring line distinguishing this green-from-W0 guard from the xfail-RED MAG `TestDepth2` class in the same file. Do NOT xfail-mark this class.

Then perform the full Wave 0 audit (no new files): run the complete new-test surface and confirm the red/green split exactly matches M13-VALIDATION — every MAG signal RED (xfail), `TestBackCompatRecursionPinIntact` + `test_ctrl_c_still_interrupt` GREEN, and the unmodified `tests/harness/test_subagent_recursion.py` GREEN. If any MAG test is accidentally green (false positive — e.g. an assertion that passes vacuously) or any file errors at collection, fix the offending test (tighten the assertion or correct the xfail import guard). Wave 0 is complete only when the split is exactly: MAG signals RED, both back-compat guards GREEN, zero collection errors.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest "tests/harness/test_multiagent_recursion.py::TestBackCompatRecursionPinIntact" -q 2>&1 | tail -3 && python -m pytest tests/harness/test_subagent_recursion.py -q 2>&1 | tail -3 && python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py tests/harness/test_multiagent_recursion.py tests/harness/tui/test_subagent_reveal.py tests/e2e/test_multiagent_chat_e2e.py --collect-only -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - SOURCE: `grep -c "class TestBackCompatRecursionPinIntact" tests/harness/test_multiagent_recursion.py` returns 1; the class body references `run_subagent`, the three forbidden constant names, and a `subprocess.run` of `tests/harness/test_subagent_recursion.py`; the file does NOT define or import any `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` symbol for production use (only as forbidden-name assertions).
    - BEHAVIOR: `pytest tests/harness/test_multiagent_recursion.py::TestBackCompatRecursionPinIntact -q` exits 0 (GREEN from W0); `pytest tests/harness/test_subagent_recursion.py -q` exits 0 (unmodified pin still passes).
    - TEST-COMMAND: full Wave 0 `--collect-only` across all 5 new files exits 0 with zero errors; the combined run shows 0 passed among MAG signal tests (all xfail RED) and the two back-compat guards passing.
  </acceptance_criteria>
  <done>`TestBackCompatRecursionPinIntact` is added to the recursion test file and is GREEN from Wave 0; the unmodified `tests/harness/test_subagent_recursion.py` still collects+passes; the full Wave 0 red/green split is verified (every MAG signal RED, both back-compat guards GREEN, zero collection errors).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test-author → test-harness | This plan writes only tests/fixtures. The boundary of concern is test integrity: a vacuously-passing red test would let a real M13 defect ship undetected. |
| M13 future code → back-compat surface (`subagents.py`) | Wave 0 erects the tripwire that detects if a later M13 wave breaches the recursion-pinning contract (no `depth`/`max_depth`). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M13-01 | Spoofing (false-green) | MAG xfail scaffolds | mitigate | `strict=False` xfail + Task 3 audit explicitly asserts 0 passed among MAG signal tests — a vacuous green is treated as a Wave 0 failure to fix, not accept |
| T-M13-02 | Tampering (back-compat breach) | `subagents.py` recursion pin | mitigate | `TestBackCompatRecursionPinIntact` runs the unmodified `test_subagent_recursion.py` in a subprocess + asserts no `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` — green-from-W0 tripwire |
| T-M13-oversell | Tampering | `M13Allocator` no-oversell (asserted, not built here) | mitigate | `TestNoOversell` (red W0 → green W1/W3) pins `Σ ≤ R` race + exactly-once release + depth-bound; cited in the test docstring |
| T-M13-recursion-DoS | Denial of Service | recursive spawn depth bound | mitigate | `TestDepth2` + `TestNoOversell` depth-bound assertion pin viable-floor denial without a depth constant (red W0) |
| T-M13-mis-steer | Tampering | steer-to-wrong/finished-child | mitigate | `TestCorrectionChangesBehavior` (red W0) pins correction-vs-control + ≥2-iteration drain semantics |
| T-M13-orphan | Denial of Service | orphaned child tasks / leaked panels | mitigate | `TestPostGatherRegionClean` (red W0) pins zero `SubAgentPanel` + M9-08 region snapshot post-gather |
| T-M13-ui-thread | Tampering | cross-thread widget mutation | mitigate | TUI pilot reveal/post-gather tests exercise the renderer/app seam on the app's loop (no worker threads introduced) |
| T-M13-priv | Elevation of Privilege | child PermissionGate scope | accept | Wave 0 scaffold only; child-gate-identity assertion lands with the W2A fan-out test surface (no production code here to escalate) |
| T-M13-SC | Tampering | npm/pip/cargo installs | accept | M13 installs zero external packages (RESEARCH §"Package Legitimacy Audit": N/A); no install task in this plan — nothing to slopcheck |
</threat_model>

<verification>
- `pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py tests/harness/test_multiagent_recursion.py tests/harness/tui/test_subagent_reveal.py tests/e2e/test_multiagent_chat_e2e.py --collect-only -q` → exit 0, zero collection errors.
- `pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py tests/harness/test_multiagent_recursion.py tests/harness/tui/test_subagent_reveal.py tests/e2e/test_multiagent_chat_e2e.py -q` → 0 passed among MAG signal tests (all xfail RED), 0 errors.
- `pytest "tests/harness/test_multiagent_recursion.py::TestBackCompatRecursionPinIntact" -q` → exit 0 (GREEN from W0).
- `pytest tests/harness/tui/test_keymap_baseline.py -q` → all pre-existing tests + `test_ctrl_c_still_interrupt` PASS; `test_ctrl_o_resolves_to_toggle_subagent_detail` + `("ctrl+o","main")` case FAIL RED.
- `pytest tests/harness/test_subagent_recursion.py -q` → exit 0 (back-compat pin unmodified, still passes).
- `git diff tests/harness/conftest.py tests/harness/tui/test_keymap_baseline.py | grep -c '^-[^-]'` → 0 (both modifications are strictly additive).
</verification>

<success_criteria>
- 1 additive `scripted_multiagent_provider` fixture appended to `tests/harness/conftest.py` (every existing fixture byte-stable; AST parses).
- 5 new test files created: `test_multiagent_fanout.py`, `test_multiagent_steer.py`, `test_multiagent_recursion.py`, `tui/test_subagent_reveal.py`, `e2e/test_multiagent_chat_e2e.py` — all collect cleanly, all MAG signal tests RED (xfail).
- Every MAG-01..MAG-08 observable signal from M13-VALIDATION has a named class/function asserting it.
- `tests/harness/tui/test_keymap_baseline.py` extended additively: GREEN `test_ctrl_c_still_interrupt`, RED `test_ctrl_o_resolves_to_toggle_subagent_detail`; no existing keymap test regressed.
- `TestBackCompatRecursionPinIntact` GREEN from W0; unmodified `tests/harness/test_subagent_recursion.py` still passes.
- Zero collection errors across the full new-test surface; zero false-green MAG tests.
- No `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` symbol introduced for production use anywhere.
</success_criteria>

<output>
Create `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-01-SUMMARY.md` when done.
</output>
