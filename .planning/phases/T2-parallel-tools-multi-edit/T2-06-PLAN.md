---
phase: T2-parallel-tools-multi-edit
plan: 06
type: execute
wave: 5
depends_on: [T2-03, T2-05]
files_modified:
  - tests/perf/__init__.py
  - tests/perf/test_parallel_read_speedup.py
autonomous: false
requirements: [PAR-01, PAR-05]
must_haves:
  truths:
    - "tests/perf/ directory exists with an __init__.py marking it a discoverable pytest package"
    - "tests/perf/test_parallel_read_speedup.py contains a benchmark that constructs a 6-step plan of stub `slow_read` tools each awaiting asyncio.sleep(0.05) and dispatches via _run_step_loop"
    - "Default-cap benchmark (max_parallel_reads=8) measures parallel wall-clock and asserts parallel_ms <= 60% × serial_ms (SPEC PAR-05 Success Criteria #1: ≥40% wall-clock drop)"
    - "Cap=1 sanity benchmark forces serial (max_parallel_reads=1) and asserts wall-clock >= 250ms (6 × 50ms × 0.85 floor) — exposes any parallelism leak in the supposed-serial path"
    - "Benchmark uses time.perf_counter (or time.monotonic — both monotonic; perf_counter is the higher-res convention) for wall-clock measurement"
    - "Benchmark uses stub tools with deterministic asyncio.sleep — NO live disk or network timing (SPEC PAR-05 line 62 explicit)"
    - "Benchmark uses RuntimeConfig reset_config + configure(max_parallel_reads=N) for each test scope to avoid singleton contamination across tests"
    - "Per-task verification map row T2-05-02 (per VALIDATION.md) maps to this benchmark"
    - "Human-verify checkpoint at the end confirms phase completion by running the full T2 test suite + the benchmark + spot-checking telemetry JSONL"
  artifacts:
    - path: "tests/perf/__init__.py"
      provides: "Empty package marker to make tests/perf/ pytest-discoverable"
      contains: ""
    - path: "tests/perf/test_parallel_read_speedup.py"
      provides: "Two pytest functions: test_parallel_read_speedup_default_cap + test_parallel_read_speedup_cap_1_sanity"
      contains: "test_parallel_read_speedup_default_cap\\|test_parallel_read_speedup_cap_1_sanity"
  key_links:
    - from: "tests/perf/test_parallel_read_speedup.py"
      to: "voss/harness/agent.py:_run_step_loop"
      via: "direct call to await _run_step_loop(plan.steps, SLOW_TOOLS, None, NullRenderer(), recorder=None) with two cap configs"
      pattern: "_run_step_loop\\(.*SLOW_TOOLS"
    - from: "tests/perf/test_parallel_read_speedup.py"
      to: "voss_runtime.configure"
      via: "configure(max_parallel_reads=N) wraps each benchmark run to set the cap"
      pattern: "configure\\(max_parallel_reads"
---

<objective>
Land the SPEC PAR-05 perf gate: a self-contained, deterministic, stub-timed
benchmark proving the partition scheduler achieves ≥40% wall-clock drop on
a 6-step read batch vs. serial baseline. Two test functions:
1. Default-cap (max_parallel_reads=8) — asserts parallel_ms ≤ 60% × serial_ms
2. Cap=1 sanity — asserts forced-serial wall-clock ≥ 250ms (sanity check that
   parallelism doesn't leak through when cap=1; also serves as the serial
   baseline for human inspection)

This is the final T2 phase plan, depending on T2-03 (the partition scheduler
that produces the speedup) and T2-05 (the fs_read_many tool the LLM uses in
real plans — referenced in the benchmark's docstring as the canonical
parallel-read consumer). The benchmark uses STUB tools with asyncio.sleep,
not live disk reads or fs_read_many directly, because SPEC PAR-05 line 62
explicitly disallows live IO timing in CI.

This plan ends with a `checkpoint:human-verify` task that confirms the entire
T2 phase is end-to-end runnable: full test suite green, benchmark passes,
telemetry JSONL shows batch.start/end events as expected, RunRecord.batches
populated correctly, no asyncio task leaks.

Purpose: Closes SPEC PAR-05 "Success Criteria 1" (40% wall-clock drop) and
serves as the ship-readiness gate for T2.

Output: tests/perf/ directory + __init__.py + benchmark file; checkpoint
approval marking T2 complete.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-VALIDATION.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-03-PLAN.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-05-PLAN.md
@voss/harness/agent.py
@voss/harness/tools.py
</context>

<interfaces>
After T2-03 ships, `voss.harness.agent._run_step_loop` is the partition
scheduler. Its signature (from T2-03):
```
async def _run_step_loop(
    plan_steps,
    tools: dict[str, ToolEntry],
    permissions: PermissionGate | None,
    renderer: Renderer,
    *,
    recorder: RunRecorder | None = None,
) -> list[str]:
```

`Plan` and `ToolCall` are imported from voss.harness.agent (or voss_runtime —
discover via grep).

`@tool` decorator + `ToolEntry`:
- `from voss_runtime import tool`
- `from voss.harness.tools import ToolEntry`

`configure` + `reset_config`:
- `from voss_runtime import configure, get_config`
- Use a `reset_config()` helper if exposed; else just call `configure(max_parallel_reads=N)` which dataclass-replaces the singleton

Pytest asyncio: project sets `asyncio_mode = "auto"` in pyproject.toml, so
plain `async def test_*` works without `@pytest.mark.asyncio`.

NullRenderer for benchmark: lift from T1/T2-03's conftest (tests/harness/
conftest.py) — discover via `grep -n "NullRenderer\|class.*Renderer" tests/`.
Alternatively define a minimal local class in the benchmark file with
`show_tool_call(*a, **kw): pass`.

Benchmark structure (from RESEARCH.md Code Example 5 — adapt verbatim,
adjusting only sleep duration if 50ms × 6 = 300ms feels too long for CI):

```python
import asyncio, time
import pytest

from voss.harness.agent import _run_step_loop, Plan, ToolCall
from voss.harness.tools import ToolEntry
from voss_runtime import tool, configure

# Stub tool — module-level so the @tool decorator registers once.
@tool(name="slow_read", description="Stub read that sleeps 50ms.")
async def slow_read(path: str) -> str:
    await asyncio.sleep(0.05)
    return f"contents of {path}"

SLOW_TOOLS = {"slow_read": ToolEntry(descriptor=slow_read, is_mutating=False)}


class NullRenderer:
    def show_tool_call(self, *a, **kw): pass


def _make_plan(n: int):
    return Plan(
        rationale="benchmark",
        steps=[ToolCall(name="slow_read", args={"path": f"f{i}.txt"}) for i in range(n)],
        confidence=1.0,
        final_when_done="ok",
    )


async def test_parallel_read_speedup_default_cap():
    configure(max_parallel_reads=8)
    plan = _make_plan(6)

    t0 = time.perf_counter()
    await _run_step_loop(plan.steps, SLOW_TOOLS, None, NullRenderer(), recorder=None)
    parallel_ms = (time.perf_counter() - t0) * 1000

    configure(max_parallel_reads=1)
    t0 = time.perf_counter()
    await _run_step_loop(plan.steps, SLOW_TOOLS, None, NullRenderer(), recorder=None)
    serial_ms = (time.perf_counter() - t0) * 1000

    assert parallel_ms <= serial_ms * 0.6, (
        f"parallel {parallel_ms:.1f}ms not <= 60% of serial {serial_ms:.1f}ms"
    )


async def test_parallel_read_speedup_cap_1_sanity():
    configure(max_parallel_reads=1)
    plan = _make_plan(6)
    t0 = time.perf_counter()
    await _run_step_loop(plan.steps, SLOW_TOOLS, None, NullRenderer(), recorder=None)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    # 6 reads × 50ms = 300ms ± slop; under 250ms means parallelism leaked
    assert elapsed_ms >= 250, (
        f"cap=1 ran too fast ({elapsed_ms:.1f}ms) — parallelism leaked"
    )
```

Sleep duration tuning: 50ms × 6 = 300ms serial baseline. 50ms is generous
enough to tolerate CI jitter (kernel-level sleep precision is ~1-10ms on
Linux/macOS containers). If CI proves flaky, bump to 80ms × 6 = 480ms in
a later tune; the ratio invariant (≤60%) survives any duration as long as
it's well above kernel scheduling noise.

Test isolation: configure() dataclass-replaces a module-level singleton.
The two tests must NOT cross-contaminate. Option A: use an autouse fixture
that resets to default after each test. Option B: each test sets configure
explicitly at the start (the pattern above). Choose B for clarity — each
test owns its cap configuration.

The cap=1 sanity test serves two functions:
1. Validates that the partition scheduler actually respects cap=1
   (no parallelism leak; if it did, the assertion would fail since
    cap=1 with 6 × 50ms sleeps should take ~300ms)
2. Provides a serial baseline for the default-cap test's denominator
   (separately measured in the same test for atomicity)
</interfaces>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: tests/perf/ directory scaffold + benchmark file</name>
  <files>tests/perf/__init__.py, tests/perf/test_parallel_read_speedup.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (PAR-05 + Success Criteria 1 + acceptance criteria 19-20)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md (D-19)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md (Pattern 7, Code Example 5)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (section "tests/perf/test_parallel_read_speedup.py (NEW DIR + NEW FILE)")
    - .planning/phases/T2-parallel-tools-multi-edit/T2-03-PLAN.md (just-shipped _run_step_loop signature)
    - pyproject.toml (confirm `asyncio_mode = "auto"`; `grep -n "asyncio_mode" pyproject.toml`)
    - voss/harness/agent.py (after T2-03 — locate Plan + ToolCall imports; verify _run_step_loop signature matches expectations)
    - tests/harness/conftest.py (locate NullRenderer if exported; otherwise define inline)
  </read_first>
  <behavior>
    - tests/perf/__init__.py exists and is empty (pytest package discovery)
    - tests/perf/test_parallel_read_speedup.py contains TWO async test functions matching the SPEC PAR-05 acceptance criteria
    - test_parallel_read_speedup_default_cap PASSES when the partition scheduler from T2-03 dispatches 6 stub reads via asyncio.gather with cap=8
    - test_parallel_read_speedup_default_cap measures parallel_ms via time.perf_counter delta around await _run_step_loop with cap=8
    - test_parallel_read_speedup_default_cap measures serial_ms via the same call pattern but with cap=1
    - test_parallel_read_speedup_default_cap asserts `parallel_ms <= serial_ms * 0.6` (SPEC PAR-05 Success Criteria #1: ≥40% wall-clock drop → parallel ≤ 60% of serial)
    - test_parallel_read_speedup_default_cap FAILS deliberately if T2-03's scheduler is regressed to serial — this is the safety net
    - test_parallel_read_speedup_cap_1_sanity PASSES when cap=1 produces a wall-clock close to 6 × sleep duration (≥ 250ms with 50ms sleep × 6)
    - test_parallel_read_speedup_cap_1_sanity FAILS if cap=1 somehow runs in parallel (the partition scheduler with cap=1 must still produce serial wall-clock)
    - Benchmark uses ONLY stub tools (asyncio.sleep) — NO live disk reads, NO live network — to keep CI deterministic
    - Benchmark uses NO renderer machinery beyond a NullRenderer no-op
    - Benchmark uses NO recorder (recorder=None) to isolate scheduler timing from recorder overhead
    - configure(max_parallel_reads=N) sets the singleton; each test owns its cap explicitly (no cross-test contamination)
  </behavior>
  <action>
    1. Create the directory: `mkdir -p tests/perf` (or use Write to create
       a file inside, which creates the directory).

    2. Create `tests/perf/__init__.py` as an empty file (pytest needs
       __init__.py for test discovery on some configurations; also makes
       the dir a proper Python package).

    3. Create `tests/perf/test_parallel_read_speedup.py` with the structure
       in <interfaces> above. Key implementation notes:

       - Module-level `@tool(name="slow_read", ...)` decorator registers
         the stub tool ONCE. If the @tool decorator from voss_runtime
         raises on re-registration, wrap in a try/except ImportError or
         use a fixture-scoped registration. Check by reading voss_runtime/
         and looking for how @tool handles duplicates.

       - Plan + ToolCall imports: `from voss.harness.agent import Plan,
         ToolCall, _run_step_loop, BatchInvariantError`. (BatchInvariantError
         is needed only if a regression test wants to assert classification
         catch — optional for this benchmark.)

       - NullRenderer: if `tests/harness/conftest.py` defines/exports
         a NullRenderer (lifted in T1-07 / T2-03), import it. Otherwise
         define inline:
         ```
         class NullRenderer:
             def show_tool_call(self, *a, **kw): pass
             def stream_delta(self, *a, **kw): pass
             def finalize_stream(self, *a, **kw): pass
         ```
         The benchmark only calls .show_tool_call (via _invoke_step_with_gate)
         and possibly some renderer methods inside the dispatch path; provide
         no-ops for all the methods the scheduler calls. Inspect T2-03's
         _invoke_step_with_gate body to enumerate; current body calls
         `renderer.show_tool_call(step.name, step.args, ..., status)`.

       - Test isolation: each test calls `configure(max_parallel_reads=N)`
         at the start. After the test, the singleton remains at the last
         configured value; the NEXT test resets it explicitly. Optionally
         add a `@pytest.fixture(autouse=True)` that resets to default 8
         after each test in this module — see what T2-02's test file
         established and mirror.

       - Sleep duration is 50ms × 6 = 300ms serial baseline. If CI proves
         flaky, the planner can re-tune; do not increase preemptively
         without measurement.

    4. Run the benchmark locally to confirm it passes against T2-03's
       partition scheduler. Capture the actual measured times in the
       SUMMARY (e.g., "parallel=60ms, serial=300ms, ratio=0.20 → PASS").

    Do NOT introduce a conftest.py in tests/perf/ unless pytest discovery
    fails — the project-level conftest + `asyncio_mode = "auto"` should
    cover it.

    Do NOT add a third benchmark (e.g., cap=4 mid-point) — only the two
    acceptance benchmarks per SPEC.

    Do NOT add a CI workflow update; SPEC PAR-05 acceptance is satisfied
    by the test existing + passing. CI inclusion is a follow-up if dogfood
    surfaces flake.
  </action>
  <verify>
    <automated>uv run pytest tests/perf/test_parallel_read_speedup.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - file assertion: `test -f tests/perf/__init__.py` succeeds
    - file assertion: `test -f tests/perf/test_parallel_read_speedup.py` succeeds
    - source assertion: `grep -n "def test_parallel_read_speedup_default_cap\|def test_parallel_read_speedup_cap_1_sanity" tests/perf/test_parallel_read_speedup.py` returns 2 matches
    - source assertion: `grep -n "asyncio.sleep" tests/perf/test_parallel_read_speedup.py` returns 1 match (the stub tool body)
    - source assertion: `grep -nE "configure\(max_parallel_reads=" tests/perf/test_parallel_read_speedup.py` returns >= 3 matches (default-cap test sets 8 then 1; sanity test sets 1)
    - source assertion: `grep -F "serial_ms * 0.6" tests/perf/test_parallel_read_speedup.py` returns 1 match (the 40%-drop assertion)
    - benchmark assertion: `uv run pytest tests/perf/test_parallel_read_speedup.py::test_parallel_read_speedup_default_cap -x -q` exits 0
    - sanity assertion: `uv run pytest tests/perf/test_parallel_read_speedup.py::test_parallel_read_speedup_cap_1_sanity -x -q` exits 0
    - speedup measurement: the SUMMARY captures actual parallel_ms and serial_ms numbers proving the ratio is well under 0.6
    - regression assertion: `uv run pytest tests/perf/test_parallel_read_speedup.py tests/harness/test_partition_scheduler.py -x -q` passes
    - test command: `uv run pytest tests/perf/test_parallel_read_speedup.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>tests/perf/ directory scaffolded with __init__.py; benchmark file contains the two SPEC PAR-05 acceptance tests; default-cap test passes proving parallel ≤ 60% × serial (≥40% wall-clock drop); cap=1 sanity test passes proving forced-serial dispatch.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Phase-final T2 verification by developer</name>
  <what-built>
    All 6 plans T2-01 through T2-06 are implemented:

    - T2-01: BatchRecord schema + IterationRecord.batches additive field + RunRecorder.begin_batch/end_batch API
    - T2-02: RuntimeConfig.max_parallel_reads field + get_max_parallel_reads loader + cli.py bootstrap wiring
    - T2-03: Partition scheduler rewrite + BatchInvariantError + batch.start/end telemetry + recorder.begin_batch/end_batch wiring + _run_turn_exec exit_reason="batch-invariant" handler
    - T2-04: fs_edit_many tool (atomic validate-then-write-once, M9-05 DiffModal integration with skip-is-strict)
    - T2-05: fs_read_many tool (bundled response, per-slot error envelopes, 30KB cap)
    - T2-06: Self-contained micro-benchmark proving ≥40% wall-clock drop

    The full T2 phase is now end-to-end runnable: read-only steps execute in parallel, mutations stay serialized, fs_read_many bundles N file reads, fs_edit_many atomically applies N edits to one file, and the perf gate proves the speedup.
  </what-built>
  <how-to-verify>
    1. Run the full T2 unit + tool suite:
       `uv run pytest tests/harness/test_session_roundtrip.py tests/harness/test_recorder.py tests/harness/test_agent_config.py tests/harness/test_cli_bootstrap.py tests/harness/test_partition_scheduler.py tests/harness/test_permissions.py tests/harness/tools/test_fs_edit_many.py tests/harness/tools/test_fs_read_many.py tests/perf/test_parallel_read_speedup.py -v`
       Expected: all tests PASS, exit code 0.

    2. Run the full harness regression to confirm no T1/M1/M2 regression:
       `uv run pytest tests/harness/ -x -q`
       Expected: all tests PASS.

    3. Eyeball the benchmark output for the actual speedup numbers:
       `uv run pytest tests/perf/test_parallel_read_speedup.py -v -s`
       Expected: parallel_ms is well under 60% of serial_ms (e.g., 60ms vs 300ms = 20%, a 5x speedup). Capture both numbers.

    4. Run a live `voss do "read 3 files in parallel and tell me what's in them"` against a real provider (or stub-provider mode) on a fixture repo with 3+ readable files:
       Expected:
         - The agent's plan uses fs_read_many (or 3 fs_read calls inside one batch)
         - Wall-clock for the read step is meaningfully faster than 3x single-file latency
         - `.voss/sessions/<id>.json` has a `RunRecord.iterations[0].batches: [{batch_index: 0, parallel_count: 3, ...}]`

    5. Inspect the latest telemetry JSONL for batch.start/end events:
       `tail -100 .voss/telemetry/*.jsonl | grep -E "batch\\.(start|end)"`
       Expected: paired batch.start + batch.end for each multi-step batch, with monotonic batch_index, parallel_count matching the plan's read-batch width, and ok_count/err_count totals.

    6. Spot-check fs_edit_many with a 2-edit plan against a fixture file:
       Either via a unit test invocation OR a manual `voss do` request.
       Expected:
         - DiffModal walks 2 hunks
         - Accepting both writes the file once
         - Rejecting one cancels the whole batch (file unchanged)
         - Skipping one also cancels (strict semantics)

    7. Verify BatchInvariantError surface: planters of a synthetic mutating-in-batch (via the unit test) confirm exit_reason="batch-invariant" appears in the RunRecord JSON.

    8. Confirm the SPEC PAR-05 wall-clock drop is captured in the SUMMARY with concrete numbers.

    9. Approve or surface issues with specific failing test names / output.
  </how-to-verify>
  <resume-signal>Type "approved" to mark T2 complete and ship-ready, or describe specific failures / regressions found during verification. If the wall-clock drop is below the 40% gate due to CI environment variance, capture the measured numbers in the SUMMARY and approve only if the partition scheduler is observably parallel (cap=1 sanity passing is the load-bearing safety net).</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| benchmark timing → CI green/red signal | Stub-timed deterministic sleep keeps the wall-clock invariant stable across CI environments; live IO would introduce flake |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T2-06-01 | Denial of Service | benchmark flake on slow CI runners falsely fails | mitigate | 50ms sleep × 6 steps = 300ms serial baseline; the 60% ratio is generous (5x speedup is typical with 6 reads). If flake emerges, planner re-tunes sleep duration (the ratio invariant is duration-independent as long as duration >> scheduling noise). Sanity test (cap=1) also passing rules out true parallelism regressions when the default-cap test is flaky |
| T-T2-06-02 | Tampering | benchmark using live IO masks regressions | mitigate | Benchmark uses ONLY asyncio.sleep stubs — SPEC PAR-05 line 62 explicitly forbids live disk/network; the @tool stub `slow_read` makes the contract crystal-clear |
| T-T2-06-03 | Tampering | configure() singleton contamination across tests | mitigate | Each benchmark test explicitly calls configure(max_parallel_reads=N) at the start; no reliance on default state; SUMMARY documents the per-test configuration pattern |
| T-T2-06-SC | Tampering | npm/pip/cargo installs | accept | No new third-party packages in this plan (RESEARCH.md "Package Legitimacy Audit" — none) |
</threat_model>

<verification>
- `uv run pytest tests/perf/test_parallel_read_speedup.py -x -q` passes
- Default-cap test asserts parallel_ms ≤ serial_ms × 0.6 (≥40% drop)
- Cap=1 sanity test asserts wall-clock ≥ 250ms (forced-serial proof)
- Full T2 test suite green: `uv run pytest tests/harness/test_session_roundtrip.py tests/harness/test_recorder.py tests/harness/test_agent_config.py tests/harness/test_cli_bootstrap.py tests/harness/test_partition_scheduler.py tests/harness/test_permissions.py tests/harness/tools/test_fs_edit_many.py tests/harness/tools/test_fs_read_many.py tests/perf/test_parallel_read_speedup.py -x -q` passes
- No T1/M1/M2 regression: `uv run pytest tests/harness/ -x -q` passes
- Human-verify checkpoint approved
- Concrete parallel_ms and serial_ms numbers captured in the SUMMARY
</verification>

<success_criteria>
- tests/perf/ directory exists with __init__.py
- test_parallel_read_speedup_default_cap PASSES with parallel ≤ 60% × serial (SPEC PAR-05 Success Criteria #1)
- test_parallel_read_speedup_cap_1_sanity PASSES with wall-clock ≥ 250ms (sanity baseline)
- Phase-final human-verify checkpoint reaches "approved" state
- Full T2 test suite green, no harness regression
- Telemetry JSONL spot-check confirms batch.start/end emit correctly during a live voss do
- RunRecord.iterations[*].batches populated with concrete BatchRecord entries
</success_criteria>

<output>
Create `.planning/phases/T2-parallel-tools-multi-edit/T2-06-SUMMARY.md` when done with:
- Exact parallel_ms and serial_ms numbers from the default-cap benchmark
- Exact wall-clock number from the cap=1 sanity benchmark
- Confirmation that the full T2 test suite passes (paste the pytest count)
- Confirmation that the harness regression suite passes
- Approve-signal from the human-verify checkpoint
- Any follow-up notes (e.g., CI inclusion of the perf gate, fixture coverage gaps, re-tune candidates)
- A SPEC acceptance criteria checklist (all 22 boxes ticked) with the test function that proves each
</output>
