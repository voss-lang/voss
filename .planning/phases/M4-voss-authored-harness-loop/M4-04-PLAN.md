---
phase: M4
plan: 04
type: execute
wave: 3
depends_on: [M4-01, M4-02, M4-03]
files_modified:
  - tests/harness/conftest.py
  - tests/harness/test_voss_loop_parity.py
  - tests/harness/test_dog07_smoke.py
autonomous: true
requirements:
  - DOG-07
tags:
  - parity
  - dogfood-smoke
  - integration
  - wave-3

must_haves:
  truths:
    - "`tests/harness/test_voss_loop_parity.py` runs ONE fixture task through both the Python `run_turn` (parity oracle, D-09) and the compiled `.voss-cache/harness/loop.py:run_turn`, with a `FakeProvider` returning a hard-coded `Plan` (Pitfall 6 — NOT StubProvider fingerprint-based)."
    - "Parity test asserts: (a) `python_result.final == voss_result.final`; (b) tool-call name sequence identical; (c) tool-call args identical."
    - "Parity test uses a session-scoped pre-compile fixture: copy `voss/harness/agent/*.voss` into a tmp project root and run `python -m voss.cli compile voss/harness/agent/ --project-root <tmp>` once per test session (Q-5)."
    - "`tests/harness/test_dog07_smoke.py` runs `VOSS_HARNESS=compiled python -m voss.cli do '<fixture task>'` as a SUBPROCESS (testing the real CLI dispatch path, not in-process)."
    - "Smoke test sets `VOSS_HERMETIC=1` in the subprocess env to force `StubProvider` (M3 D-01 carry-forward; CI has no live credentials)."
    - "Smoke test asserts: subprocess exit code == 0 AND stdout is non-empty (D-12 (c) success bar)."
    - "Parity test and smoke test both depend on `harness_cache.assert_fresh` passing — if the cache is stale (e.g. .voss source changed but cache wasn't rebuilt), both tests fail loudly with `StaleHarnessCacheError`."
  artifacts:
    - path: "tests/harness/conftest.py"
      provides: "Session-scoped pre-compile fixture for parity + smoke tests (Q-5)"
      contains: "scope=\"session\""
    - path: "tests/harness/test_voss_loop_parity.py"
      provides: "D-11 parity contract: same fixture, both backends, identical TurnResult.final + tool sequence"
      contains: "FakeProvider"
    - path: "tests/harness/test_dog07_smoke.py"
      provides: "DOG-07 / D-12 (c) success bar: VOSS_HARNESS=compiled voss do exits 0 with non-empty final"
      contains: "VOSS_HARNESS"
  key_links:
    - from: "tests/harness/test_voss_loop_parity.py"
      to: "voss/harness/agent.py::run_turn (Python parity oracle) + .voss-cache/harness/loop.py::run_turn (compiled)"
      via: "FakeProvider with canned Plan; both backends invoked with same _run helper"
      pattern: "FakeProvider"
    - from: "tests/harness/test_dog07_smoke.py"
      to: "voss/harness/cli.py:_resolve_run_turn (compiled branch)"
      via: "subprocess with VOSS_HARNESS=compiled + VOSS_HERMETIC=1 env"
      pattern: "VOSS_HARNESS"
    - from: "tests/harness/conftest.py (precompiled_harness fixture)"
      to: "voss/harness/cache.py::write_manifest + voss/cli.py:compile dir mode"
      via: "subprocess invocation of `voss compile voss/harness/agent/ --project-root <tmp>`"
      pattern: "subprocess.run"
---

<objective>
Land the two tests that prove M4 success criteria D-11 (parity) and D-12 (c) (DOG-07 real-turn under compiled backend). Both tests share a session-scoped pre-compile fixture (Q-5) that runs `voss compile voss/harness/agent/` once into a tmp project root.

1. **Parity test** (D-11 — `tests/harness/test_voss_loop_parity.py`): The in-tree analog is `tests/harness/test_agent_integration.py:21-50` (`FakeProvider` + canned `Plan`). M4-RESEARCH Pitfall 6 mandates `FakeProvider`, NOT `StubProvider` — parity is on `TurnResult` fields + tool-call sequence, NOT on prompt-fingerprint reproducibility. A divergent prompt structure between backends would make the StubProvider returns differ; `FakeProvider` forces the same `Plan` into both backends regardless.

2. **DOG-07 smoke test** (D-12 (c) — `tests/harness/test_dog07_smoke.py`): Subprocess invocation of `VOSS_HARNESS=compiled python -m voss.cli do '<fixture task>'`. Subprocess (not in-process) because the goal is to exercise the real CLI dispatch path including `_resolve_run_turn` reading env, `assert_fresh` validating cache, dynamic import of `loop.py`, and `asyncio.run(run_turn(...))` end-to-end. `VOSS_HERMETIC=1` forces `StubProvider` (no creds needed in CI).

Purpose: This plan closes the M4 success bar. D-12 says M4 passes when (a) `voss check voss/harness/agent/` exits 0 — landed in M4-03; (b) `voss compile voss/harness/agent/` emits 5 .py + manifest — landed in M4-03; (c) `VOSS_HARNESS=compiled voss do "<fixture>"` exits 0 with non-empty `TurnResult.final` — landed HERE (smoke test); (d) parity test passes — landed HERE (parity test). Live-provider parity is explicitly out-of-scope (deferred to M5 per CONTEXT Deferred Ideas).

Output:
- `tests/harness/conftest.py` — extend (or create if absent) with `precompiled_harness` session-scoped fixture.
- `tests/harness/test_voss_loop_parity.py` — NEW (1 test asserting parity).
- `tests/harness/test_dog07_smoke.py` — NEW (1 test asserting subprocess exit 0 + non-empty stdout).
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
@.planning/phases/M4-voss-authored-harness-loop/M4-03-PLAN.md
@voss/harness/agent.py
@voss/harness/cache.py
@voss/harness/cli.py
@voss/harness/tools.py
@voss/harness/permissions.py
@voss/harness/render.py
@voss_runtime/providers/base.py
@tests/harness/test_agent_integration.py

<interfaces>
<!-- Key contracts extracted from the tree + M4-01/02/03 outputs. -->

From voss/harness/agent.py:
- `Plan(rationale: str, steps: list[ToolCall], confidence: float, final_when_done: str, open_question: str | None)` — pydantic v2 model.
- `ToolCall(name: str, args: dict)`.
- `TurnResult(plan, confidence, final, tool_results, cost_usd)` dataclass.
- `run_turn(task, *, tools, cwd, renderer, ..., provider, ..., permissions) -> TurnResult`.

From voss_runtime/providers/base.py:
- `ProviderResponse(text, model, prompt_tokens, completion_tokens, cost_usd, raw, parsed)`.

From tests/harness/test_agent_integration.py:21-50 (the FakeProvider analog to mirror):
- Class with `__init__(plan)` storing canned Plan + calls list.
- `async def complete(*, messages, model, response_format=None, **_) -> ProviderResponse`: stores call, returns `ProviderResponse(text=plan.model_dump_json(), parsed=plan if response_format is Plan else None, ...)`.
- `def count_tokens(*, text, model) -> int: return 1`.

From voss/harness/cache.py (M4-02):
- `CACHE_HARNESS_DIR = ".voss-cache/harness"` constant.
- `assert_fresh(project_root)` raises on stale.

From voss/harness/cli.py (M4-03):
- `_resolve_run_turn()` reads `VOSS_HARNESS` env → config → `"python"`; raises `StaleHarnessCacheError` before dynamic import on compiled+stale.

From voss/harness/tools.py:
- `make_toolset(cwd: Path) -> dict[str, ToolEntry]` — returns the standard toolset jailed to cwd.

From voss/harness/permissions.py:
- `PermissionGate(auto_yes=True)` — bypass-prompts mode used by tests.

From voss/harness/render.py:
- `PlainRenderer()` — non-TTY renderer suitable for tests.

Fixture-task design per M4-PATTERNS.md:
- Task text: `"noop summary of fixture.md"`.
- Plan returned by FakeProvider:
  - rationale: `"read the noop fixture"`
  - steps: `[ToolCall(name="fs_read", args={"path": "fixture.md"})]`
  - confidence: `0.95` (above default 0.60 threshold; ensures the plan branch is taken)
  - final_when_done: `"contents: {{step_0}}"`
  - open_question: None
- After dispatch: `_run_step_loop` reads `fixture.md` (which the fixture writes) → results[0] = "noop fixture body\n" → final = "contents: noop fixture body\n".

Q-5 fixture design (M4-RESEARCH §"Open Questions"):
- Session-scoped fixture creates a tmp project, copies the 5 .voss files into `<tmp>/voss/harness/agent/`, runs subprocess `python -m voss.cli compile voss/harness/agent/ --project-root <tmp>`, returns the tmp project Path.
- ALSO writes `fixture.md` into the tmp project (per-test or per-session).
- All parity + smoke tests reuse this fixture so the compile cost (~1s) is amortized.

Pitfall 6 (Pattern 6 mandate):
- Use FakeProvider, NOT StubProvider. The compiled side might construct prompts slightly differently than Python `run_turn` (different whitespace, different field ordering); StubProvider.fingerprint() hashes messages so divergent prompts → divergent canned responses → divergent Plan → false parity failure. FakeProvider returns the SAME canned Plan unconditionally, so the parity test isolates `run_turn` behavior from prompt-fingerprint reproducibility.

Pitfall 4 (test ordering):
- The parity test calls `harness_cache.assert_fresh(project)` BEFORE the dynamic import to surface stale-cache problems loudly. The smoke test relies on `_resolve_run_turn` doing the same internally.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Session-scoped pre-compile fixture + parity test (D-11)</name>
  <files>tests/harness/conftest.py, tests/harness/test_voss_loop_parity.py</files>
  <read_first>
    - tests/harness/conftest.py if it exists (otherwise create); check whether it already defines a `project` or `cwd_repo` fixture
    - tests/harness/test_agent_integration.py:1-180 (FakeProvider, `_run` helper, project fixture pattern)
    - voss_runtime/providers/base.py (ProviderResponse dataclass shape)
    - voss/harness/agent.py (Plan, ToolCall, TurnResult, run_turn signature; M4-03's _run_step_loop)
    - voss/harness/tools.py:make_toolset (jails toolset to cwd)
    - voss/harness/permissions.py:PermissionGate (auto_yes mode)
    - voss/harness/render.py:PlainRenderer
    - voss/harness/cache.py:assert_fresh, CACHE_HARNESS_DIR
    - voss/harness/agent/ — all 5 .voss files from M4-03 (the precompile fixture copies these)
    - M4-RESEARCH.md §"Pattern 6: Parity test fixture (D-11)" (lines ~625-710)
    - M4-PATTERNS.md §"tests/harness/test_voss_loop_parity.py (NEW) — Wave 3 Pattern 6"
    - M4-RESEARCH.md §"Pitfall 6: Parity test passes locally because dev has Anthropic key, fails CI because StubProvider used" (lines ~822-832)
    - M4-RESEARCH.md §"Open Question Q-5" (session-scoped pre-compile fixture)
  </read_first>
  <behavior>
    - `precompiled_harness` session-scoped fixture: receives `tmp_path_factory`; creates a tmp project dir; copies `voss/harness/agent/*.voss` into `<tmp>/voss/harness/agent/`; runs `subprocess.run([sys.executable, "-m", "voss.cli", "compile", "voss/harness/agent/", "--project-root", str(tmp)], cwd=str(tmp), check=True)`; returns the tmp project Path.
    - `parity_project` function-scoped fixture: depends on `precompiled_harness`; writes `fixture.md` into the tmp project (text `"noop fixture body\n"`); returns the tmp project Path.
    - Parity test `test_python_and_compiled_backends_agree(parity_project)`:
        - Imports `run_turn` from `voss.harness.agent` (Python parity oracle).
        - Calls `harness_cache.assert_fresh(parity_project)` (loud-fail if cache is bad).
        - Dynamic-imports `voss_compiled_harness_loop_test` from `parity_project / harness_cache.CACHE_HARNESS_DIR / "loop.py"`.
        - Constructs `FakeProvider(_fixture_plan())` with the canned Plan described in interfaces.
        - Defines `_run(project, run_turn)` helper that calls `asyncio.run(run_turn("noop summary of fixture.md", tools=make_toolset(project), cwd=project, renderer=PlainRenderer(), provider=FakeProvider(_fixture_plan()), permissions=PermissionGate(auto_yes=True)))`.
        - Asserts `py_result.final == voss_result.final`.
        - Asserts `[s.name for s in py_result.plan.steps] == [s.name for s in voss_result.plan.steps]`.
        - Asserts `[s.args for s in py_result.plan.steps] == [s.args for s in voss_result.plan.steps]`.
    - The compile step happens ONCE per pytest session; subsequent tests share the artifact.
    - If the compiled `loop.py` doesn't exist (compile failed during M4-03), the fixture's `subprocess.run(..., check=True)` raises and tests fail loudly with a clear traceback.
  </behavior>
  <action>
    Edit (or create) `tests/harness/conftest.py`. If a file already exists, append the new fixtures alongside existing ones; do NOT remove existing fixtures. Add a session-scoped `precompiled_harness(tmp_path_factory)` fixture that: (1) calls `tmp_path_factory.mktemp("voss-m4-project")` to obtain the project root; (2) creates `<tmp>/voss/harness/agent/` and copies each `voss/harness/agent/*.voss` file from the repo root into it (`shutil.copy2`); (3) runs `subprocess.run([sys.executable, "-m", "voss.cli", "compile", "voss/harness/agent/", "--project-root", str(tmp)], cwd=str(tmp), check=True, capture_output=True, text=True)` — if it fails, the CalledProcessError surfaces stderr; (4) returns the tmp project Path. Use `Path(__file__).resolve().parents[2]` (or equivalent) to locate the repo root for source copy.

    In the same conftest.py, add a function-scoped `parity_project(precompiled_harness, tmp_path)` fixture (or skip the function-scope wrapper if `precompiled_harness` already has fixture-isolated state) that: writes `fixture.md` with content `"noop fixture body\n"` into `precompiled_harness / "fixture.md"`; returns the same Path. (Note: `fixture.md` is read by `fs_read` jailed to that path; ensure `make_toolset(project)` is constructed with the same project as cwd.)

    Create `tests/harness/test_voss_loop_parity.py` (NEW) per M4-PATTERNS.md target shape. Module-level docstring: `"""M4 D-11: same fixture, two backends, identical TurnResult.final + tool sequence."""`. Imports: `asyncio`, `pathlib.Path`, `pytest`, `Plan` + `ToolCall` from `voss.harness.agent`, `PermissionGate` from `voss.harness.permissions`, `PlainRenderer` from `voss.harness.render`, `make_toolset` from `voss.harness.tools`. Define inline `class FakeProvider` per Pitfall 6 (NOT StubProvider) with the constructor + `async def complete` + `def count_tokens` per the interfaces section. Define `_fixture_plan() -> Plan` returning the canned Plan described in interfaces (rationale, single fs_read step, confidence 0.95, `"contents: {{step_0}}"` template). Define `_run(project, run_turn)` helper that wraps the standard `asyncio.run(run_turn(...))` call with the full kwarg set. Define `test_python_and_compiled_backends_agree(parity_project)`: import `run_turn as python_run_turn` from `voss.harness.agent`; `from voss.harness import cache as harness_cache`; call `harness_cache.assert_fresh(parity_project)`; build the importlib spec for `parity_project / harness_cache.CACHE_HARNESS_DIR / "loop.py"` with module name `"voss_compiled_harness_loop_test"`; `module_from_spec` + `exec_module`; extract `compiled_run_turn = mod.run_turn`. Run both: `py_result = _run(parity_project, python_run_turn)`; `voss_result = _run(parity_project, compiled_run_turn)`. Assert the three equalities per the behavior section.

    Decision references: D-09 (Python parity oracle stays; `voss.harness.agent.run_turn` is the reference); D-11 (single fixture task in M4; broader matrix deferred); D-12 (d) (parity test green is M4 gate); Pitfall 6 (FakeProvider not StubProvider); Q-5 (session-scoped pre-compile).
  </action>
  <verify>
    <automated>pytest tests/harness/test_voss_loop_parity.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_voss_loop_parity.py -q` exits 0 with 1 passed.
    - `pytest tests/harness/ -q -m "not live"` exits 0 (no regressions in other harness tests; the new conftest fixtures don't break existing tests).
    - `grep -n 'class FakeProvider' tests/harness/test_voss_loop_parity.py` returns 1 match (FakeProvider inline, not StubProvider).
    - `grep -F 'StubProvider' tests/harness/test_voss_loop_parity.py` returns no matches (Pitfall 6 invariant).
    - `grep -n 'precompiled_harness' tests/harness/conftest.py` returns at least 1 match (fixture exists).
    - On test failure, the `_resolve_run_turn`+`assert_fresh` path is implicitly exercised: an absent or stale cache surfaces as `subprocess.CalledProcessError` from the precompile fixture (catastrophic, loud) or `StaleHarnessCacheError` from `assert_fresh` (also loud).
  </acceptance_criteria>
  <done>Session-scoped pre-compile fixture lands; parity test runs both backends through FakeProvider; final + tool sequence asserted equal; full harness test suite green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: DOG-07 subprocess smoke test (D-12 (c))</name>
  <files>tests/harness/test_dog07_smoke.py</files>
  <read_first>
    - tests/harness/conftest.py (the `precompiled_harness` fixture from Task 1 — reused here)
    - tests/examples/helpers.py (if exists) for the `run_voss` subprocess pattern (M3 carry-forward)
    - tests/cli/test_run.py:22-58 (subprocess + capture_output pattern)
    - voss/harness/cli.py (do_cmd entry — confirms `python -m voss.cli do <task>` or `python -m voss.harness.cli do <task>` is the invocation; check which is the actual command line)
    - M4-RESEARCH.md §"Open Question Q-5" + §"Pitfall 4"
    - M4-PATTERNS.md §"tests/harness/test_dog07_smoke.py (NEW) — Wave 3"
    - M4-VALIDATION.md row `dog-07-smoke` (the canonical contract)
    - M3-CONTEXT.md D-01 (auto-StubProvider via `VOSS_HERMETIC=1`)
  </read_first>
  <behavior>
    - Test `test_dog07_voss_do_through_compiled_harness(precompiled_harness)`:
        - Writes `fixture.md` (text `"noop fixture body\n"`) into the `precompiled_harness` project (idempotent — Task 1's parity_project fixture may have already done this, but writing again is safe).
        - Sets env: `env = os.environ.copy()`, `env["VOSS_HARNESS"] = "compiled"`, `env["VOSS_HERMETIC"] = "1"` (M3 D-01 forces StubProvider; no real provider needed).
        - Runs `subprocess.run([sys.executable, "-m", "voss.cli", "do", "noop summary of fixture.md"], cwd=str(precompiled_harness), env=env, capture_output=True, text=True, timeout=30)`.
        - Asserts `result.returncode == 0` (with `result.stderr` in the assertion message for debuggability).
        - Asserts `result.stdout.strip()` is truthy (non-empty final, D-12 (c)).
    - Test uses the SAME `precompiled_harness` session fixture as the parity test — no double-compile cost.
    - On a stale cache the test fails loudly: the subprocess exits non-zero with `StaleHarnessCacheError` in stderr (Pitfall 4 verification at the boundary).
    - The CLI module path is `voss.cli` per existing CLI tests (the `main` click group); if `voss.harness.cli do` is the correct entry instead, use that — read `voss/harness/cli.py` to confirm whether `do_cmd` is registered under `voss.cli` (top-level) or `voss.harness.cli` (subgroup).
  </behavior>
  <action>
    Verify the subprocess invocation form by reading `voss/cli.py` and `voss/harness/cli.py`: confirm whether `voss do` is exposed via `python -m voss.cli` (top-level command group registering harness commands) or via `python -m voss.harness.cli` (separate entry). Use whichever is the actual canonical invocation. The existing `tests/cli/` tests use `voss.cli`; the harness suite likely uses the same form (CLI is unified).

    Create `tests/harness/test_dog07_smoke.py` (NEW). Module docstring: `"""DOG-07 / D-12 (c) smoke: VOSS_HARNESS=compiled voss do '<fixture>' exits 0 with non-empty final."""`. Imports: `os`, `subprocess`, `sys`, `pathlib.Path`, `pytest`. Define `test_dog07_voss_do_through_compiled_harness(precompiled_harness: Path)`. Body: write `fixture.md`; build env dict; subprocess.run with the args described in behavior; assertions per behavior section. Include `result.stderr` in the assertion failure message so CI logs show the real failure on stale cache or codegen regression. Add a 30-second `timeout=30` to the subprocess call to fail fast if the harness hangs.

    Do NOT add the smoke test to the parity test file — keep them separate so failure diagnosis is precise: parity failure points at semantic divergence; smoke failure points at the CLI dispatch / boot path.

    Per M4-VALIDATION row `dog-07-smoke`: the verification command is literally a bash smoke `VOSS_HARNESS=compiled python -m voss.cli do "<fixture>"`. The pytest version captures the same intent in a hermetic, CI-runnable shape.

    Decision references: D-08 (`VOSS_HARNESS=compiled` env-flag); D-12 (c) (M4 success bar — real turn, non-empty final); M3 D-01 (`VOSS_HERMETIC=1` auto-StubProvider for hermetic CI); Pitfall 4 (loud failure surfaces in subprocess stderr).
  </action>
  <verify>
    <automated>pytest tests/harness/test_dog07_smoke.py tests/harness/test_voss_loop_parity.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_dog07_smoke.py -q` exits 0 with 1 passed.
    - Both Wave-3 tests pass together: `pytest tests/harness/test_dog07_smoke.py tests/harness/test_voss_loop_parity.py -q` exits 0 with 2 passed.
    - `grep -n 'VOSS_HARNESS' tests/harness/test_dog07_smoke.py` returns at least 1 match.
    - `grep -n 'VOSS_HERMETIC' tests/harness/test_dog07_smoke.py` returns at least 1 match.
    - `grep -n 'subprocess.run' tests/harness/test_dog07_smoke.py` returns 1 match (subprocess invocation, not in-process).
    - `pytest tests/harness/ -q -m "not live"` exits 0 (full harness suite green).
  </acceptance_criteria>
  <done>DOG-07 smoke test passes via subprocess; precompiled_harness fixture reused; full harness suite green; M4 success bar (D-12 b/c/d) verified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test subprocess env (`VOSS_HARNESS`, `VOSS_HERMETIC`) | Set explicitly in test code; closed scope to the subprocess. |
| Temp project root (`tmp_path_factory`) | pytest-managed; auto-cleaned between sessions. |
| `fixture.md` content | Test-controlled string; no untrusted input. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M4-W3-parity-divergence | Repudiation | Parity test asserting equality | mitigate | FakeProvider with canned Plan ensures both backends see identical input regardless of prompt-fingerprint reproducibility (Pitfall 6). Tool-call name + args asserted, not just `final` string (M4-VALIDATION row `parity-test`). |
| T-M4-W3-stale-mask | Repudiation | Smoke test under stale cache | mitigate | Subprocess inherits `VOSS_HARNESS=compiled` which forces `assert_fresh` BEFORE dynamic import. Stale cache surfaces as subprocess non-zero exit with `StaleHarnessCacheError` in stderr. No silent fallback. |
| T-M4-W3-hermetic-leak | Information Disclosure | Smoke test accidentally calling live provider | mitigate | `VOSS_HERMETIC=1` env explicitly set in subprocess. Test does NOT pass through `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` (only `os.environ.copy()` is used — if those are set in dev shell they're inherited, but `VOSS_HERMETIC=1` forces the StubProvider path regardless via M3 D-01 auto-fallback). |
| T-M4-W3-fixture-pollution | Tampering | Session fixture state leaking across tests | accept | pytest auto-cleans `tmp_path_factory` directories after the session; no persistent state pollution. |
| T-M4-W3-subprocess-timeout | Availability | Smoke test hangs on a runtime regression | mitigate | `timeout=30` on `subprocess.run` raises `TimeoutExpired` after 30s; CI fails fast rather than timing out at the global pytest timeout. |
</threat_model>

<verification>
After both tasks land:
1. `pytest tests/harness/test_voss_loop_parity.py tests/harness/test_dog07_smoke.py -q` exits 0 with 2 passed.
2. `pytest tests/harness/ -q -m "not live"` exits 0 (full harness suite green).
3. Run `pytest tests/harness/test_voss_loop_parity.py -q --setup-show` once to confirm the `precompiled_harness` session fixture only runs once across the parity + smoke tests (Q-5 cost amortization).
4. M4-VALIDATION rows `parity-test` and `dog-07-smoke` flip from ❌ to ✓.
5. M4 success bar D-12 (b), (c), (d) all green: (b) compile produces 5 .py + manifest (verified by the precompile fixture succeeding); (c) `VOSS_HARNESS=compiled voss do` exits 0 with non-empty final (smoke test); (d) parity test passes.
</verification>

<success_criteria>
- Session-scoped `precompiled_harness` fixture amortizes the compile cost across both Wave-3 tests.
- Parity test (D-11) asserts identical `TurnResult.final` + tool-call sequence between Python and compiled backends using `FakeProvider` (Pitfall 6 mandate).
- Smoke test (D-12 (c)) runs `VOSS_HARNESS=compiled voss do '<fixture>'` as a subprocess; exits 0; non-empty stdout.
- `harness_cache.assert_fresh` is exercised by both tests (parity test calls it directly; smoke test exercises it via `_resolve_run_turn` inside the subprocess).
- No live-provider calls; `VOSS_HERMETIC=1` enforced in the subprocess; tests pass in CI without credentials.
- Full `tests/harness/ -m "not live"` suite green.
</success_criteria>

<output>
After completion, create `.planning/phases/M4-voss-authored-harness-loop/M4-04-SUMMARY.md` documenting:
- Final shape of `precompiled_harness` (session fixture body, cwd handling, source-copy mechanism).
- Confirmation that `voss.cli` (not `voss.harness.cli`) is the correct subprocess entry — or whichever was found to be canonical.
- Parity test runtime + smoke test runtime (helps Wave 4 CI budgeting).
- All 4 D-12 success criteria green:
    - (a) `voss check voss/harness/agent/` exit 0 — landed M4-03.
    - (b) `voss compile voss/harness/agent/` produces 5 .py + manifest — landed M4-03; verified by precompile fixture in this plan.
    - (c) `VOSS_HARNESS=compiled voss do "<fixture>"` exit 0 with non-empty final — landed HERE.
    - (d) parity test green — landed HERE.
- Final outstanding M4 work: M4-05 (CI gate yaml + README install one-liner + doctor cache-freshness row).
</output>
