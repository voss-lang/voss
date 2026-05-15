# Phase T2: Parallel Tools + Multi-Edit Primitive — Research

**Researched:** 2026-05-15
**Domain:** Python asyncio concurrency in an existing harness loop; pydantic/dataclass schema additions; pytest-asyncio test patterns; Textual modal integration.
**Confidence:** HIGH (the entire stack is in-tree; locked decisions in CONTEXT.md + SPEC.md leave very little exploratory surface).

## Summary

T2 plugs four mechanical extensions into Voss's existing harness, all of them sitting *below* T1's iteration loop:

1. **Partition scheduler** inside `_run_step_loop` (`voss/harness/agent.py:507`) — replaces the strictly-serial `for step in plan_steps` body with a one-pass author-order grouping that emits read-only batches and mutating singletons. Read batches dispatch via `asyncio.gather(*coros, return_exceptions=True)` whose coroutines hold an `asyncio.Semaphore(cap)`.
2. **Two new tools** in `make_toolset` (`voss/harness/tools.py:44`) — `fs_read_many(paths)` (`is_mutating=False`, bundled response with per-slot error sections) and `fs_edit_many(path, edits)` (`is_mutating=True`, atomic validate-then-write-once through the M9-05 DiffModal).
3. **`[agent] max_parallel_reads = 8`** config knob alongside T1's `[agent] max_iterations = 8` in `~/.config/voss/config.toml` — parsed by the regex extension T1-04 already lands.
4. **Telemetry + schema additions** — new `batch.start` / `batch.end` events (symmetric with T1's `iteration.start` / `iteration.end`), `BatchInvariantError`, additive `IterationRecord.batches: list[BatchRecord]`, and new `EXIT_REASONS` entry `"batch-invariant"`.

There is **zero new third-party dependency** (stdlib `asyncio` only) and **zero new module** strictly required — every change lands in files T1 already opens. The work splits cleanly into 6 plans, one per PAR-* requirement.

**Primary recommendation:** Lay down the partition scheduler + `BatchInvariantError` (PAR-01/02) first as a single-PR substrate. Then ship `fs_read_many` (PAR-04) and `fs_edit_many` (PAR-03) in parallel — they share no code surface. Land the `[agent] max_parallel_reads` loader extension (PAR-05) with the partition scheduler. Telemetry + `BatchRecord` (PAR-06) bolt on last because they observe behavior introduced by PAR-01. Benchmark fixture lands with PAR-05.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Partition `plan.steps` into batches | Harness agent loop | — | `_run_step_loop` is the single owner of step dispatch order; this is its core responsibility. |
| Enforce "no mutation in parallel batch" invariant | Harness agent loop | PermissionGate (per-step) | Partition-time invariant is **additional** to the per-step gate check (SPEC PAR-02 + Constraint 7); two layers, not one replaces the other. |
| Apply N edits atomically to one file | Tool function (`fs_edit_many`) | — | Per CONTEXT.md D-01: tool function owns its UX surface; PermissionGate stays narrow (single-edit `_render_diff_preview` unchanged). |
| Bundle N file reads into one response | Tool function (`fs_read_many`) | — | Same pattern as `fs_read` (`tools.py:52`); tool-shaped. |
| Per-hunk diff approval UI | TUI modal (`DiffModal`, M9-05) | Renderer (`show_diff_modal`) | Existing layer; T2 is the first caller to populate >1 hunk. |
| Track `[agent]` config keys | `voss/harness/config.py` regex parser | `voss_runtime/_config.py` (defaults) | T1-04 establishes the section parser; T2 piggybacks one more key (`max_parallel_reads`). |
| Capture per-batch wall-clock + counts | RunRecorder | telemetry.emit | RunRecorder owns iteration-scoped records (T1 substrate); telemetry emits the JSONL events. |
| Bound batch concurrency at N=8 | `asyncio.Semaphore` (per-batch, in scheduler) | — | Scheduler creates and GCs the semaphore per multi-step batch (D-17). |

## User Constraints (from CONTEXT.md)

### Locked Decisions (from CONTEXT.md `<decisions>` block)

- **D-01** `fs_edit_many` builds `list[Hunk]` itself and calls `renderer.show_diff_modal(hunks)` directly. `PermissionGate._render_diff_preview` stays single-edit-only. `PermissionGate.check` fires ONCE for the whole call (per SPEC PAR-03).
- **D-02** Hunk-build sequence: (1) read snapshot once, (2) walk edits left-to-right validating `old` matches uniquely in the *current working buffer*, (3) on any failure abort before modal (return error, no UI), (4) on all-pass build `list[Hunk]` and call `show_diff_modal`, (5) any reject → return `<denied: hunk N rejected>`, otherwise write once.
- **D-03** Modal reject semantics: any hunk's `decision == "reject"` collapses to batch reject. Planner picks (a) inspect per-hunk `DiffDecision` returned by modal vs. (b) add `batch_mode` flag on modal. Both are SPEC-conformant. **Research recommendation:** option (a) — the existing `DiffDecision` already carries per-hunk verdicts (`accept|reject|skip`), so the tool layer just folds them.
- **D-04** Read-batch gather: `asyncio.gather(*coros, return_exceptions=True)`; exceptions stringified to `<error: {exc}>` and placed in the same `results: list[str]` slot the serial loop would produce. Loop continues to next batch on any error.
- **D-05** Per-step `tool.call` / `tool.result` events unchanged. `batch.end` event carries `ok_count` / `err_count`.
- **D-06** Cancel inside `asyncio.gather`: outer `CancelledError` propagates into in-flight coros; T1's `except asyncio.CancelledError` in `_run_turn_exec` finalizes recorder with `exit_reason="interrupt"`. Partial results captured in `IterationRecord` for the cancelled iter.
- **D-07** Cancel siblings, do NOT let batch finish (some "reads" are `git_status` / `voss_check` shell-shaped and not free).
- **D-08** `BatchRecord` nests in T1's `IterationRecord.batches: list[BatchRecord]`. `RunRecord` top-level shape unchanged.
- **D-09** Minimum `BatchRecord` fields: `batch_index: int` (monotonic within iteration), `step_indices: list[int]`, `parallel_count: int`, `wall_clock_ms: int`, `ok_count: int`, `err_count: int`. Mutating singletons emit **no** `BatchRecord` (SPEC PAR-06).
- **D-10** Keep BOTH `fs_edit` and `fs_edit_many`. Two registered tools in `make_toolset`.
- **D-11** Agent prompt (`PLAN_LOOP_SYSTEM` introduced by T1) gets a short paragraph teaching batch semantics. Planner writes the prose; must NOT change `Plan` / `ToolCall` schema.
- **D-12** Bundle format: `=== {path} ===\n{section}\n\n`.
- **D-13** Per-file cap in `fs_read_many`: **30KB**, truncation marker `<truncated, total {N} bytes>` (mirrors `shell_run` at `tools.py:96–97`).
- **D-14** Per-path `jail_path(cwd, path)` validation in `fs_read_many`; jail violations become `<error: path outside cwd: {path}>` in their slot (partial-result semantics).
- **D-15** `[agent]` section locked for T1+T2 co-location. T2 owns the loader extension.
- **D-16** Loader extension shape (per-section function vs. generic) is planner's pick. Constraint: existing `[harness] preferred_model` consumer keeps working.
- **D-17** Semaphore scope: **per-batch**, GC'd after gather completes.
- **D-18** `BatchInvariantError` lives in `voss/harness/agent.py`. Single-class vs. domain hierarchy is planner's pick. Must surface in `RunRecord.exit_reason = "batch-invariant"` (additive enum value joining T1's four).

### Claude's Discretion (from CONTEXT.md)

- `DiffDecision.batch_mode` collapse mechanism (D-03 fork). Research finding below resolves to option (a).
- Exception → result-string formatter (`repr(exc)` vs `str(exc)` vs custom).
- `BatchRecord` exact pydantic field set + timestamp granularity.
- Whether per-step `tool.call` events inside a batch carry a `batch_index` annotation.
- Agent-prompt prose for batch semantics (D-11).
- Config loader refactor shape (D-16).
- `fs_edit_many` return-string format on success and failure-index naming.
- `BatchInvariantError` class hierarchy (single vs. domain).

### Deferred Ideas (OUT OF SCOPE)

- `fs_grep_many` / `fs_glob_many` batch primitives.
- Dependency-graph partitioner (hoisting independent reads ahead of writes).
- Parallel write to disjoint paths.
- Multi-file `fs_edit_many` shape `[{path, old, new}]`.
- Mid-batch incremental result streaming into T1's iteration messages.
- `fs_edit_many` mid-batch partial rollback.
- Process-wide / session-wide parallel-read semaphore.
- `/cost --by-batch` slash surface.
- BatchRecord persisted into `voss resume` replay context.
- `harness.toml [agent]` discoverability via `voss config` slash.
- Cap value re-tuning (30KB per-file).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **PAR-01** | `_run_step_loop` partitions `plan.steps` into read-only batches + mutating singletons; batches dispatch via `asyncio.gather` bounded by `asyncio.Semaphore(max_parallel_reads)` preserving author order. | Standard Stack (asyncio); Pattern 1 (one-pass partition); Pattern 2 (bounded gather); Code Examples 1 & 2; Pitfall 1 (author order); cancel-point map in CONTEXT.md D-06/D-07. |
| **PAR-02** | Partition-time invariant: every step in a multi-step batch has `is_mutating == False`; violation raises `BatchInvariantError`. Per-step `PermissionGate.check` still fires for every step. | Code anchors `permissions.py:169` (`check`) + `tools.py:14` (`ToolEntry.is_mutating`); Pattern 3 (invariant placement); Pitfall 4 (silent serial degrade); `BatchInvariantError` placement (D-18) → `exit_reason="batch-invariant"`. |
| **PAR-03** | `fs_edit_many(path, edits)` registers `is_mutating=True`; validate-then-write-once atomicity; routes through `DiffModal` with N hunks; reject-any → batch denied; reports line delta. | DiffModal/Hunk/DiffDecision API (`voss/harness/tui/widgets/diff_modal.py:21–123`); `renderer.show_diff_modal(hunks, timeout_s)` at `voss/harness/tui/renderer.py:306`; Pattern 4 (hunk-build); Pattern 5 (collapse decisions); Code Example 3; Pitfall 5 (regex hunk drift). |
| **PAR-04** | `fs_read_many(paths)` registers `is_mutating=False`; deterministic bundle `=== {path} ===\n{section}\n\n`; per-path errors inline; never aborts call. | Existing `fs_read` error envelopes at `tools.py:55–61`; `jail_path` (`sandbox.py:29`); Pattern 6 (bundle assembly); Code Example 4; Pitfall 6 (path traversal). |
| **PAR-05** | `[agent] max_parallel_reads` (int, default 8, range 1–32) in `~/.config/voss/config.toml`; out-of-range falls back to default with warning; perf benchmark proves ≤60% wall-clock at default. | T1-04 lays down `[agent]` section parser + `RuntimeConfig.max_iterations`; same pattern extends to `max_parallel_reads`; Pattern 7 (benchmark); Code Example 5; Pitfall 7 (config drift). |
| **PAR-06** | `batch.start` / `batch.end` wrappers; mutating singletons emit **no** wrappers; per-step `tool.call` / `tool.result` unchanged; `IterationRecord.batches: list[BatchRecord]` additive. | T1-01 establishes `IterationRecord` + RunRecord additive pattern; telemetry.emit signature unchanged (`telemetry.py:150`); Pattern 8 (wrapper-only-on-multi-step); Code Example 6; Pitfall 8 (singleton wrapper leak). |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python ≥3.11 [VERIFIED: `pyproject.toml` `requires-python = ">=3.11"`] | `gather`, `Semaphore`, `CancelledError` propagation, `asyncio.current_task()` cancel detection | Codebase already uses `asyncio.gather(*pending, return_exceptions=True)` in `voss_runtime/agent.py:109` and `asyncio.wait` for handle aggregation — same idiom T2 mirrors. |
| `pydantic` (already a dep) | 2.x (transitive via `voss_runtime`) [VERIFIED: imported at `voss/harness/agent.py:16`] | `BatchRecord` if planner picks pydantic over dataclass (CONTEXT.md leaves shape to planner) | Existing `Plan`, `ToolCall`, `RunSemantics` are pydantic `BaseModel`. `RunRecord` and `IterationRecord` are `@dataclass`. **Research recommendation:** match T1 — use `@dataclass` for `BatchRecord` so `dataclasses.asdict` keeps working for JSONL serialization. |
| `pytest` + `pytest-asyncio` | `pytest>=8.0`, `pytest-asyncio>=0.23` [VERIFIED: `pyproject.toml`] | Async test execution; project sets `asyncio_mode = "auto"` so plain `async def test_*` works without decorators | Existing harness tests (`tests/harness/test_recorder.py`, etc.) follow this convention. |
| `pytest-mock` | `>=3.12` [VERIFIED: `pyproject.toml`] | Spying on `telemetry.emit` and `renderer.show_diff_modal` in test fixtures | Already in dev deps. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `time.perf_counter` (stdlib) | — | Wall-clock measurement in benchmark (`tests/perf/test_parallel_read_speedup.py`) | Use this, not `time.monotonic`. `perf_counter` is the highest-resolution monotonic clock available; `time.monotonic` is fine but `perf_counter` is the conventional pick for micro-benchmarks. SPEC PAR-05 line 62 says `time.monotonic` — both work; planner picks. |
| `difflib` (stdlib) | — | Unified diff text for hunks (already used by `permissions.py:compute_diff_text`) | Don't import in `fs_edit_many` for synthesizing hunks — see Pattern 4 (track offsets manually). `compute_diff_text` shows the available shape if planner reuses it for `fs_edit_many` summaries. |
| `dataclasses` (stdlib) | — | `BatchRecord` definition | Match T1's `IterationRecord` (a dataclass per `voss/harness/session.py:70–87`). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.gather(*coros, return_exceptions=True)` | `asyncio.TaskGroup` (Python 3.11+) | TaskGroup gives stronger structured concurrency: any task exception cancels siblings + raises `ExceptionGroup`. **Rejected** because CONTEXT.md D-04 explicitly locks `return_exceptions=True` with per-step error strings (one slot failure must NOT cancel siblings) [CITED: docs.python.org/3/library/asyncio-task.html#asyncio.gather]. TaskGroup's cancel-siblings-on-first-exception is the wrong semantics for a read batch where one file-not-found shouldn't kill the other 5 reads. |
| Per-task semaphore wrap | Outer producer/consumer with `asyncio.Queue` | Queue pattern is overkill for ≤32 task batches. Semaphore + gather is the canonical Python idiom for bounded concurrency [CITED: docs.python.org/3/library/asyncio-sync.html]. |
| `time.perf_counter` | `time.monotonic` | Both are monotonic; `perf_counter` has higher resolution but is otherwise equivalent. Either satisfies SPEC PAR-05. |
| Pydantic `BaseModel` for `BatchRecord` | `@dataclass` | Match T1 (`IterationRecord` is dataclass at `session.py`). Keeps serialization via `dataclasses.asdict` consistent. |

**Installation:** No new dependencies. All stdlib + already-pinned dev deps.

**Version verification:**
- `pytest-asyncio>=0.23` confirmed at `pyproject.toml` line ~30 [VERIFIED: in-tree].
- `requires-python = ">=3.11"` confirmed at `pyproject.toml` [VERIFIED: in-tree]. Python 3.11 is the floor for both `asyncio.TaskGroup` (3.11+) and `ExceptionGroup` (3.11+), so we have access to TaskGroup if a future phase wants it — but T2 explicitly does not.
- Linked Python docs: [asyncio.gather](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather), [asyncio.Semaphore](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore), [asyncio.CancelledError](https://docs.python.org/3/library/asyncio-exceptions.html#asyncio.CancelledError).

## Package Legitimacy Audit

T2 introduces **zero new third-party packages**. All concurrency primitives, time measurement, diff synthesis, and test infrastructure come from the Python standard library or already-pinned dev dependencies (`pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-mock>=3.12`) verified in `pyproject.toml`.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | N/A | No installs in this phase |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

slopcheck was not run because no install action is required. Planner should NOT add any `pip install` task to T2 plans.

## Architecture Patterns

### System Architecture Diagram

```
                       T1's _run_turn_exec while-loop
                                      │
                                      ▼
                            ┌─────────────────────┐
                            │  iteration body     │
                            │  (per-iter)         │
                            └──────────┬──────────┘
                                       │ plan.steps
                                       ▼
                        ┌──────────────────────────────┐
                        │  _run_step_loop (T2 rewrite) │
                        │                              │
                        │  one-pass partition:         │
                        │  walk plan.steps left→right  │
                        │  group consecutive           │
                        │  is_mutating=False steps     │
                        │  into a batch; flush on      │
                        │  mutating step               │
                        └──────────┬───────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        ┌──────────┐         ┌──────────┐         ┌──────────┐
        │ batch[0] │         │ batch[1] │         │ batch[2] │
        │ readers  │         │ writer   │         │ readers  │
        │ (parallel)│        │ (single) │         │ (parallel)│
        └────┬─────┘         └────┬─────┘         └────┬─────┘
             │                    │                    │
             ▼                    ▼                    ▼
    asyncio.Semaphore(8)   per-step gate         asyncio.Semaphore(8)
    asyncio.gather(...     check + invoke        asyncio.gather(...
       return_exceptions      atomically            return_exceptions
       =True)                                       =True)
             │                    │                    │
             │                    │                    │
        emit batch.start    no batch.start         emit batch.start
        emit per-step       (mutating              emit per-step
          tool.call/result    singleton, D-09)       tool.call/result
        emit batch.end                             emit batch.end
             │                    │                    │
             ▼                    ▼                    ▼
        results[0..N-1]      results[i]           results[j..k]
                                   │
                                   ▼
                          results: list[str]  (author order preserved)
                                   │
                                   ▼
                     IterationRecord.tool_results +
                     IterationRecord.batches (additive)
                                   │
                                   ▼
              T1's RunRecord.iterations[i] (no top-level changes)
```

**Critical invariants enforced by the partition diagram:**
1. Author order: a read step never executes before a write authored earlier in `plan.steps`.
2. Reads after a write run in the NEXT batch — never hoisted.
3. Mutating singletons get a degenerate "batch of 1" execution path that emits no `batch.start`/`batch.end` wrapper events (SPEC PAR-06 line 67 + D-09).
4. The semaphore is **per-batch** and GC'd when `gather` returns — no process-wide coordination (D-17).

### Recommended Project Structure

No new directories. All changes land in existing modules:

```
voss/harness/
├── agent.py            # _run_step_loop rewrite, BatchInvariantError, partition helpers
├── tools.py            # fs_read_many + fs_edit_many registered in make_toolset
├── config.py           # load_agent_config / get_max_parallel_reads (extension of T1-04)
├── session.py          # BatchRecord dataclass + IterationRecord.batches field
├── recorder.py         # RunRecorder.begin_batch / end_batch (parallel to begin_iteration)
├── telemetry.py        # NO changes — emit() already accepts arbitrary kinds
└── tui/
    ├── widgets/diff_modal.py   # NO changes — N-hunk API already supports multi-edit
    └── renderer.py             # NO changes — show_diff_modal already accepts list[Hunk]

tests/harness/
├── test_step_loop_partition.py   # NEW — PAR-01 ordering + gather assertions
├── test_fs_edit_many.py          # NEW — 4 PAR-03 fixtures
├── test_fs_read_many.py          # NEW — 4 PAR-04 fixtures
├── test_telemetry_batches.py     # NEW — PAR-06 batch.start/.end assertions
└── test_session_iterations.py    # T1 fixture, EXTEND with batches=[] roundtrip

tests/perf/
└── test_parallel_read_speedup.py # NEW DIR + file — PAR-05 micro-benchmark
```

### Pattern 1: One-pass author-order partitioner

**What:** Walk `plan.steps` left-to-right; collect consecutive read-only steps into a running batch; on a mutating step, flush the running batch (if non-empty), execute the mutating step as its own singleton, continue.

**When to use:** Inside `_run_step_loop`, replacing the current serial for-loop.

**Example:**
```python
# Source: T2-SPEC.md PAR-01 acceptance criteria, lines 32–33
# Pattern (planner produces exact code):
async def _run_step_loop(plan_steps, tools, permissions, renderer, *, recorder=None):
    gate = permissions or PermissionGate(auto_yes=True)
    results: list[str | None] = [None] * len(plan_steps)
    cap = get_config().max_parallel_reads  # T2 adds this knob
    batch_index = 0
    i = 0
    while i < len(plan_steps):
        # Collect a run of consecutive read-only steps
        j = i
        while j < len(plan_steps):
            entry = tools.get(plan_steps[j].name)
            if entry is None or entry.is_mutating:
                break
            j += 1
        if j > i:
            # Read batch [i, j) — could be size 1 if a single read sits between two writes
            await _dispatch_read_batch(
                steps=plan_steps[i:j],
                step_indices=list(range(i, j)),
                tools=tools, gate=gate, renderer=renderer, recorder=recorder,
                results=results, cap=cap,
                batch_index=batch_index if (j - i) > 1 else None,  # singleton -> no wrapper
            )
            if (j - i) > 1:
                batch_index += 1
            i = j
        else:
            # Mutating singleton at position i
            await _dispatch_singleton(
                step=plan_steps[i], step_index=i,
                tools=tools, gate=gate, renderer=renderer, recorder=recorder,
                results=results,
            )
            i += 1
    return [r if r is not None else "<error: missing result>" for r in results]
```

### Pattern 2: Bounded-concurrency gather via `Semaphore`

**What:** Wrap each task body in `async with sem:` so the semaphore acquire/release happens inside the coroutine; the outer `gather` schedules them all immediately, but only `cap` are ever inside the critical section at once.

**When to use:** For read batches in `_dispatch_read_batch`.

**Example:**
```python
# Source: docs.python.org/3/library/asyncio-sync.html (canonical pattern)
async def _dispatch_read_batch(steps, step_indices, tools, gate, renderer, recorder,
                                results, cap, batch_index):
    sem = asyncio.Semaphore(cap)  # per-batch; GC'd after this function returns (D-17)
    t0 = time.perf_counter()

    if batch_index is not None:
        telemetry.emit("batch.start", "info", data={
            "batch_index": batch_index,
            "step_indices": step_indices,
            "parallel_count": len(steps),
        })
        if recorder is not None:
            recorder.begin_batch(batch_index=batch_index, step_indices=step_indices)

    async def run_one(step, slot):
        async with sem:
            text = await _invoke_step_with_gate(step, tools, gate, renderer, recorder)
            results[slot] = text
            return text

    coros = [run_one(s, idx) for s, idx in zip(steps, step_indices)]
    outcomes = await asyncio.gather(*coros, return_exceptions=True)

    ok_count = sum(1 for o in outcomes if not isinstance(o, BaseException))
    err_count = len(outcomes) - ok_count

    if batch_index is not None:
        wall_ms = int((time.perf_counter() - t0) * 1000)
        telemetry.emit("batch.end", "info", data={
            "batch_index": batch_index,
            "wall_clock_ms": wall_ms,
            "ok_count": ok_count,
            "err_count": err_count,
        })
        if recorder is not None:
            recorder.end_batch(wall_clock_ms=wall_ms, ok_count=ok_count, err_count=err_count)
```

### Pattern 3: Invariant-check at partition boundary

**What:** Inside `_dispatch_read_batch`, assert every step's `ToolEntry.is_mutating == False` BEFORE scheduling. Raise `BatchInvariantError` if violated. The partitioner *should* never produce such a batch (the while-loop's inner `break` excludes mutating tools), but a synthetic test (SPEC PAR-02 acceptance criterion 1) bypasses the partitioner — the dispatch-time check defends against that and any future partitioner regression.

**When to use:** First line of `_dispatch_read_batch` for multi-step batches.

**Example:**
```python
class BatchInvariantError(Exception):
    """Raised when a multi-step batch contains a mutating step.

    Indicates a planner bug or partitioner regression. Surfaces in
    RunRecord.exit_reason = "batch-invariant" (additive enum value).
    """

async def _dispatch_read_batch(steps, step_indices, tools, ...):
    if len(steps) > 1:
        for s in steps:
            entry = tools.get(s.name)
            if entry is None or entry.is_mutating:
                raise BatchInvariantError(
                    f"step {s.name!r} in multi-step batch is mutating or unregistered"
                )
    ...
```

The `_run_turn_exec` `except` chain (T1-06 adds `except asyncio.CancelledError`) gains a sibling `except BatchInvariantError` that sets `exit_reason="batch-invariant"` and finalizes the recorder.

### Pattern 4: `fs_edit_many` validate-then-write-once

**What:** Read file once into a string buffer. For each edit in author order: count occurrences of `old` in the *current* buffer; abort on count != 1 (returning `<error: batch rejected at index {i}: {reason}>`). After all edits validate, build `list[Hunk]` from a before/after diff, show modal, on accept-all write the buffer once.

**When to use:** In `fs_edit_many` tool body.

**Hunk-construction approach:** Track offsets as you apply edits. Don't use `difflib.SequenceMatcher` for hunk synthesis — it's slow on large files and introduces semantic mismatch (SequenceMatcher's notion of a hunk vs. M9-05's `Hunk(file, start, lines)` shape). Instead, track each edit's effect on the buffer offset and synthesize `Hunk` objects directly from the before/after substrings + the running line number.

```python
# Source: pattern derived from voss/harness/tui/widgets/diff_modal.py:22 (Hunk shape)
def _build_hunks_for_edits(path: str, snapshot: str, edits: list[dict]) -> tuple[str, list[Hunk]]:
    buf = snapshot
    hunks: list[Hunk] = []
    for i, e in enumerate(edits):
        old, new = e["old"], e["new"]
        count = buf.count(old)
        if count == 0:
            raise EditNotFound(i, path)
        if count > 1:
            raise EditNotUnique(i, count)
        idx = buf.find(old)
        # Line number of edit start in the CURRENT buf
        line_start = buf.count("\n", 0, idx) + 1
        # Compose hunk lines: '-' prefixed old lines + '+' prefixed new lines
        old_lines = [f"- {l}" for l in old.splitlines() or [""]]
        new_lines = [f"+ {l}" for l in new.splitlines() or [""]]
        hunks.append(Hunk(file=path, start=line_start, lines=old_lines + new_lines))
        buf = buf[:idx] + new + buf[idx + len(old):]
    return buf, hunks
```

The buffer returned is what gets written if the modal accepts all hunks. The hunks list is what `renderer.show_diff_modal` receives.

### Pattern 5: Per-hunk decision collapse (D-03 option (a))

**What:** `show_diff_modal` returns `list[DiffDecision]`. The tool function inspects every decision: if ANY `decision == "reject"`, return `<denied: hunk N rejected>` and do not write. `"accept"` and `"skip"` both count as "keep going" (skip means user neither accepted nor rejected — interpret as "I'd rather not approve this one"; SPEC PAR-03 line 46 says reject-any = cancel, so skip is implicitly NOT a rejection). **Research recommendation:** treat `skip` as `accept` to keep the contract simple — the existing modal returns `[]` when cancelled (escape), which is the third rejection signal.

**Example:**
```python
# Source: voss/harness/tui/widgets/diff_modal.py:80–123 (DiffDecision construction)
decisions = renderer.show_diff_modal(hunks, timeout_s=300.0)
if not decisions:
    return f"<denied: modal cancelled or timed out>"
for i, d in enumerate(decisions):
    if d.decision == "reject":
        return f"<denied: hunk {i} rejected>"
# All accepted (or skipped) — write the buffer once.
p.write_text(buf)
delta = buf.count("\n") - snapshot.count("\n")
sign = "+" if delta >= 0 else ""
return f"edited {path} ({sign}{delta} lines, {len(edits)} hunks)"
```

### Pattern 6: Bundled response with per-slot error envelopes

**What:** `fs_read_many` iterates paths; for each, attempt `jail_path` + `read_text` + binary-decode-guard + 30KB cap; place the section (content OR error string) into a section list; join with `=== {path} ===\n` headers.

**When to use:** `fs_read_many` body.

```python
# Source: tools.py:52–61 (fs_read error envelopes) + tools.py:96–97 (truncation marker)
async def fs_read_many(paths: list[str]) -> str:
    if not paths:
        return "<no paths requested>"
    sections: list[str] = []
    for path in paths:
        section_body = _read_one_for_bundle(cwd, path)  # returns content OR <error: ...>
        sections.append(f"=== {path} ===\n{section_body}\n")
    return "\n".join(sections)

def _read_one_for_bundle(cwd: Path, path: str) -> str:
    try:
        p = jail_path(cwd, path)
    except SandboxError:
        return f"<error: path outside cwd: {path}>"
    if not p.exists():
        return f"<error: not found: {path}>"
    if p.is_dir():
        return f"<error: is a directory: {path}>"
    try:
        text = p.read_text()
    except UnicodeDecodeError:
        return f"<error: binary file: {path}>"
    if len(text) > 30_720:  # 30KB cap (D-13)
        text = text[:30_720] + f"\n<truncated, total {len(text)} bytes>"
    return text
```

### Pattern 7: Stub-timed deterministic micro-benchmark

**What:** Inject 6 stub tools, each `await asyncio.sleep(0.05)` (or planner-tuned). Run the partition scheduler against a 6-read plan in two configs: cap=1 (forced serial baseline) and cap=8 (parallel). Measure `time.perf_counter` deltas. Assert parallel ≤ 60% of serial. Also assert cap=1 explicitly produces a wall-clock close to N × sleep (sanity).

**Why deterministic stubs not live disk:** Real disk reads in CI are noisy (~5–50ms variance on a single small file); stub sleep is rock-solid deterministic and exposes the *scheduling* speedup which is the point of PAR-01. SPEC PAR-05 line 62 explicitly disallows live-disk/network timing.

**When to use:** `tests/perf/test_parallel_read_speedup.py`.

### Pattern 8: Wrapper-only-on-multi-step telemetry

**What:** The dispatch path checks `len(steps) > 1` to decide whether to emit `batch.start` / `batch.end`. Singletons (whether read or mutating) skip the wrappers. Telemetry consumers detect "this iteration had a parallel batch" by event presence, not by inspecting `parallel_count=1` (D-09 spec).

```python
# In _dispatch_read_batch (Pattern 2): pass batch_index=None for singletons.
if batch_index is not None:
    telemetry.emit("batch.start", ...)
    recorder.begin_batch(...)
```

For mutating singletons, the dispatch goes through `_dispatch_singleton` which never emits batch events.

### Anti-Patterns to Avoid

- **`asyncio.TaskGroup` for read batches** — Wrong semantics: first exception cancels siblings. CONTEXT.md D-04 requires per-step errors return inline. Use `gather(return_exceptions=True)` instead. [CITED: docs.python.org/3/library/asyncio-task.html#asyncio.gather]
- **Process-wide semaphore** — Increases coupling, no measured benefit at current scale (D-17 deferred).
- **`difflib.SequenceMatcher` for hunk synthesis** — Slow on large files; semantic mismatch with `Hunk(file, start, lines)`. Track offsets manually per Pattern 4.
- **Tool-name pattern matching for classification** — SPEC Constraint 8 forbids it; rely on `ToolEntry.is_mutating` data field (M1 D-06).
- **Hoisting independent reads ahead of writes** — SPEC out-of-scope (Boundaries §2). Stay one-pass left-to-right.
- **Mid-batch `fs_edit_many` partial rollback** — Explicitly rejected in SPEC out-of-scope §6. Validate-then-write-once is the only atomicity model.
- **Bumping `RunRecord` schema_version or adding required fields** — Constraint: M2 `voss resume` must round-trip pre-T2 records. T1-01 already establishes the additive-Optional pattern; T2's `batches` field defaults to `[]`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bounded concurrent task dispatch | A queue + worker pool | `asyncio.Semaphore` + `asyncio.gather` | Stdlib idiom; ≤10 LOC vs. 50+ LOC of state machinery [CITED: docs.python.org/3/library/asyncio-sync.html]. |
| Per-task error capture | Try/except in every coroutine site | `asyncio.gather(*coros, return_exceptions=True)` | Built-in. [CITED: docs.python.org/3/library/asyncio-task.html#asyncio.gather] |
| Cancel propagation through batch | Manual `task.cancel()` plumbing | Outer `CancelledError` propagates into `gather` automatically [CITED: docs.python.org/3/library/asyncio-task.html#asyncio.gather] | "If `gather()` is _cancelled_, all submitted awaitables that have not completed yet are also _cancelled_." |
| Per-hunk approval UI | New modal | M9-05's existing `DiffModal(hunks: list[Hunk])` | Already accepts a list; T2 is the first caller to populate >1 entry. |
| TOML section parsing | Switch to `tomllib` | Extend the existing regex pair (`_HARNESS_BLOCK` / new `_AGENT_BLOCK`) | T1-04 plan locks this approach to keep `voss/harness/config.py` narrow (docstring promise: "Kept narrow on purpose"). Adding tomllib would invalidate that contract. |
| Path jailing inside `fs_read_many` | Re-implement traversal check | `jail_path(cwd, path)` from `voss/harness/sandbox.py:29` | Already used by every other path-taking tool. Catch `SandboxError` to produce inline error envelope. |
| Error envelope format | Invent new prefix | Existing `<error: ...>` convention from `tools.py:55–61` | Model already trained on this shape; consistent across tools. |
| Truncation marker | New format | `<truncated, total {N} bytes>` from `tools.py:96–97` | SPEC D-13 explicitly mandates reuse. |

**Key insight:** Every primitive T2 needs is already in-tree or in the Python stdlib. The phase is a composition exercise, not a build-from-scratch one.

## Common Pitfalls

### Pitfall 1: Reordering reads across writes
**What goes wrong:** A planner-author bug where a read after a write gets hoisted into an earlier batch because the partitioner "knows" the read is independent of the write.
**Why it happens:** Tempting optimization — if `read C` doesn't reference `write B`'s output, why not run it alongside `read A` to save a round-trip?
**How to avoid:** SPEC PAR-01 + Boundaries §2 + Constraint 1 forbid it. Partitioner is strictly one-pass left-to-right grouping by `is_mutating + author order`. Test fixture `[read_A, write_B, read_C, read_D]` must produce exactly `[A], [B], [C, D]` — three batches in that order. If a future plan author writes `[read_A, write_B, read_C]`, the result is `[A], [B], [C]` — *three* singletons, no hoisting.
**Warning signs:** Tests that assert specific orderings of read results across write boundaries should fail loudly if partitioner reorders.

### Pitfall 2: Semaphore released too early
**What goes wrong:** Using `await sem.acquire()` outside `async with` and forgetting `sem.release()` in an `except` path; or wrapping only the slow part of a coroutine, leaving the semaphore released while the coroutine still holds expensive resources.
**Why it happens:** Hand-rolled acquire/release pairs miss exception paths.
**How to avoid:** ALWAYS `async with sem:` wrapping the entire critical section (Pattern 2). [CITED: docs.python.org/3/library/asyncio-sync.html — canonical pattern]

### Pitfall 3: `CancelledError` swallowed in gather
**What goes wrong:** With `return_exceptions=True`, an inner task's `CancelledError` is treated as a result — it does NOT bubble up out of `gather`. If a child task explicitly raises `CancelledError`, sibling tasks continue.
**Why it happens:** `CancelledError` is a `BaseException` subclass; `return_exceptions=True` captures it as a result.
**How to avoid:** Distinguish two cancel scenarios:
  - **Outer cancel** (`_run_turn_exec`'s task is cancelled by `action_interrupt`): `gather` itself is cancelled; ALL in-flight inner coros are cancelled automatically. The `except asyncio.CancelledError` in T1-06's interrupt handler catches the outer propagation. ✓
  - **Inner cancel** (a tool raises `CancelledError` from its own body): per `return_exceptions=True` semantics, this becomes a CancelledError-shaped result in the slot. T2 should reject this case by stringifying it the same as other exceptions: `<error: cancelled>`.

Test it: a fixture that injects a tool which raises `CancelledError` mid-batch must produce a `results` list containing `<error: cancelled>` in that slot AND other reads must complete normally.

### Pitfall 4: Silent serial degradation on classification miss
**What goes wrong:** A new tool registered without `is_mutating` set (or via a code path that defaults to `False`) ends up inside a parallel batch alongside a mutation. SPEC PAR-02 mandates `BatchInvariantError` for this case — NOT silent degrade-to-serial.
**Why it happens:** Defaulting "unknown" to safe-serial is tempting but masks a misclassification bug.
**How to avoid:** Hard-raise. Partition-time invariant check (Pattern 3) explicitly verifies every step in a multi-step batch has `is_mutating == False`. The test (SPEC PAR-02 acceptance criterion 1) plants a synthetic mutating step inside a batch and asserts `BatchInvariantError` raised.

### Pitfall 5: `fs_edit_many` hunk drift
**What goes wrong:** The `old` string in edit #3 matches once in the *original* file but twice in the *buffer after edits #1 and #2*. Or it matched twice in the original but only once after a prior edit removed one occurrence. Either way, the uniqueness check has to run against the *current working buffer*, not a snapshot.
**Why it happens:** It's intuitive to validate all edits against the snapshot upfront. CONTEXT.md D-02 explicitly disambiguates: validate against the *current working buffer* (left-to-right propagation).
**How to avoid:** Pattern 4 propagates `buf` through the loop and runs `count(old)` against `buf`, not `snapshot`. The acceptance criterion in SPEC PAR-03 line 46–47 is the canonical interpretation.

### Pitfall 6: Path traversal via `fs_read_many` slot escape
**What goes wrong:** `paths=["valid.txt", "../../etc/passwd", "other.txt"]` partially succeeds, leaking a file outside cwd into slot #1.
**Why it happens:** Per-slot semantics (D-12, D-14) plus a naive implementation that doesn't jail each path.
**How to avoid:** Pattern 6 — call `jail_path(cwd, path)` per slot inside a `try/except SandboxError`. Jail violation → `<error: path outside cwd: {path}>` in that slot. The other slots proceed normally.

### Pitfall 7: Config knob silently ignored
**What goes wrong:** User sets `[agent] max_parallel_reads = 16` but the agent loop reads the default 8 because the loader caches an old singleton, or the regex doesn't pick up the key, or `RuntimeConfig` was instantiated before `configure(...)` was called from `cli.py`.
**Why it happens:** Multi-source config (TOML file → loader → `RuntimeConfig` singleton → `_run_step_loop` reader) has 3 hops where a stale read can occur.
**How to avoid:** Follow T1-04's pattern: `cli.py` boot calls `configure(max_iterations=..., max_parallel_reads=...)` once with values from `load_agent_config()`, and the loop reads exclusively `get_config().max_parallel_reads`. Test by `monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))` + writing a config file with non-default value + asserting the in-batch semaphore caps at that value (use a hook that records peak in-flight count — SPEC PAR-05 acceptance line 63 mandates this).

### Pitfall 8: Singleton batch leaks `batch.start`/`batch.end`
**What goes wrong:** Mutating singleton emits `batch.start` + `batch.end` because the dispatch code unconditionally wraps. SPEC PAR-06 line 67 explicitly forbids this.
**Why it happens:** Wrapping everything is the simpler code path; the spec asymmetry has to be enforced.
**How to avoid:** Pattern 8 — branch on `len(steps) > 1` (or pass `batch_index=None` for singletons). Acceptance criterion in PAR-06 line 68 asserts a mutating-singleton-only fixture produces ZERO batch events.

### Pitfall 9: `_run_turn_exec`'s while-loop reads `IterationRecord.tool_results` shape that T2 changes
**What goes wrong:** T1-05's `_run_turn_exec` builds `tool_results_for_iter = [{"name": ..., "args": ..., "result": ...} for s, r in zip(plan.steps, results)]`. T2's partition rewrite must preserve `results: list[str]` in author order so this zip still matches positionally.
**Why it happens:** Refactoring the inner loop without preserving the contract.
**How to avoid:** Partition scheduler returns `list[str]` of length `len(plan.steps)`, in author order, with each slot filled (gather error → `<error: ...>` string, never None). This is the **same contract as today**. T1-05's zip is unaffected.

### Pitfall 10: Old fixtures fail because `IterationRecord` doesn't have `batches`
**What goes wrong:** A pre-T2 `IterationRecord` JSON dict (written by T1) is loaded into a T2 codebase that expects `batches` to exist. Without additive-Optional default, deserialization breaks.
**Why it happens:** Breaking the M2 + T1 additive-Optional contract.
**How to avoid:** `IterationRecord.batches: list[BatchRecord] = field(default_factory=list)`. Regression test (T1's pre-T2 fixture round-trip) extends with one assertion: `loaded.iterations[0].batches == []`.

## Runtime State Inventory

Not applicable. T2 is a greenfield feature addition — no renames, no migrations, no schema bumps. The two `_iterations` and `iterations` fields T1 introduces are themselves brand new in v0.2. Stored sessions written by pre-T2 code load via the existing additive-Optional pattern (T1-01 + M2 guarantee); no data migration required.

## Common Pitfalls (cross-reference)

See the 10 numbered pitfalls above.

## Code Examples

Verified patterns from official sources and in-tree references.

### Example 1: `_dispatch_singleton` (mutating step path)
```python
# Source: existing voss/harness/agent.py:517–597 (current serial body), refactored into singleton helper
async def _dispatch_singleton(
    *, step, step_index, tools, gate, renderer, recorder, results
):
    entry = tools.get(step.name)
    if entry is None:
        results[step_index] = f"<error: unknown tool {step.name!r}>"
        renderer.show_tool_call(step.name, step.args, "<unknown tool>", "error")
        telemetry.emit("tool.result", "warn", data={
            "tool": step.name, "ok": False, "error": "unknown_tool",
            "args": telemetry.redact_tool_args(dict(step.args)),
        })
        if recorder is not None:
            recorder.observe(step.name, step.args, "<unknown tool>", ok=False)
        return
    allowed, why = gate.check(step.name, step.args, is_mutating=entry.is_mutating)
    if not allowed:
        text = f"<denied: {why}>"
        results[step_index] = text
        renderer.show_tool_call(step.name, step.args, text, "error")
        telemetry.emit("tool.result", "info", data={
            "tool": step.name, "ok": False, "error": "denied", "why": why,
            "args": telemetry.redact_tool_args(dict(step.args)),
        })
        if recorder is not None:
            recorder.observe(step.name, step.args, text, ok=False)
        return
    telemetry.emit("tool.call", "info", data={
        "tool": step.name,
        "args": telemetry.redact_tool_args(dict(step.args)),
    })
    renderer.show_tool_call(step.name, step.args, "running…", "pending")
    t0 = time.monotonic()
    try:
        res = await entry.invoke(**step.args)
        text = str(res)
    except Exception as e:  # noqa: BLE001 — keep the existing per-step swallow pattern
        text = f"<error: {e}>"
        renderer.show_tool_call(step.name, step.args, text, "error")
        telemetry.emit("tool.result", "warn", data={
            "tool": step.name, "ok": False,
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "error": str(e)[:300],
        })
        results[step_index] = text
        if recorder is not None:
            recorder.observe(step.name, step.args, text, ok=False)
        return
    renderer.show_tool_call(step.name, step.args, _summarize(text), "ok")
    telemetry.emit("tool.result", "info", data={
        "tool": step.name, "ok": True,
        "latency_ms": int((time.monotonic() - t0) * 1000),
        "summary": _summarize(text, 120),
    })
    results[step_index] = text
    if recorder is not None:
        recorder.observe(step.name, step.args, text, ok=True)
```

(`_invoke_step_with_gate` is the same body factored to return `text` instead of writing into `results` — used by read-batch coros.)

### Example 2: Bounded gather (Pattern 2 in full)
See Pattern 2 above. Canonical pattern from Python docs [CITED: docs.python.org/3/library/asyncio-sync.html].

### Example 3: `fs_edit_many` tool body
```python
# Source: SPEC PAR-03 + CONTEXT.md D-01/D-02/D-03 + diff_modal.py Hunk shape
@tool(
    name="fs_edit_many",
    description=(
        "Atomically apply N edits to one file. Each `edits` entry is "
        "{old, new}; each `old` must match uniquely in the working buffer. "
        "Routes through the diff modal per hunk. Rejecting any hunk "
        "cancels the whole batch — file unchanged on disk."
    ),
)
async def fs_edit_many(path: str, edits: list[dict]) -> str:
    p = jail_path(cwd, path)
    if not p.exists():
        return f"<error: not found: {path}>"
    if p.is_dir():
        return f"<error: is a directory: {path}>"
    try:
        snapshot = p.read_text()
    except UnicodeDecodeError:
        return f"<error: binary file: {path}>"

    buf = snapshot
    hunks: list[Hunk] = []
    for i, e in enumerate(edits):
        old, new = e.get("old", ""), e.get("new", "")
        if not old:
            return f"<error: batch rejected at index {i}: empty `old`>"
        count = buf.count(old)
        if count == 0:
            return f"<error: batch rejected at index {i}: `old` not found>"
        if count > 1:
            return f"<error: batch rejected at index {i}: `old` matches {count} times>"
        idx = buf.find(old)
        line_start = buf.count("\n", 0, idx) + 1
        # Hunk lines: '-' old lines then '+' new lines (matching diff_modal.py glyph convention)
        old_lines = [f"- {l}" for l in (old.splitlines() or [""])]
        new_lines = [f"+ {l}" for l in (new.splitlines() or [""])]
        hunks.append(Hunk(file=path, start=line_start, lines=old_lines + new_lines))
        buf = buf[:idx] + new + buf[idx + len(old):]

    # All edits validate. Show modal.
    decisions = renderer.show_diff_modal(hunks, timeout_s=300.0)
    if not decisions:
        return f"<denied: modal cancelled or timed out>"
    for i, d in enumerate(decisions):
        if d.decision == "reject":
            return f"<denied: hunk {i} rejected>"

    p.write_text(buf)
    delta = buf.count("\n") - snapshot.count("\n")
    sign = "+" if delta >= 0 else ""
    return f"edited {path} ({sign}{delta} lines, {len(edits)} hunks)"
```

### Example 4: `fs_read_many` tool body
See Pattern 6 above.

### Example 5: Benchmark fixture skeleton
```python
# Source: SPEC PAR-05 + D-19 (deterministic stub-timed)
# tests/perf/test_parallel_read_speedup.py
import asyncio, time
import pytest

from voss.harness.agent import _run_step_loop
from voss.harness.tools import ToolEntry
from voss_runtime import tool, ToolDescriptor

@tool(name="slow_read", description="Stub read that sleeps 50ms.")
async def slow_read(path: str) -> str:
    await asyncio.sleep(0.05)
    return f"contents of {path}"

SLOW_TOOLS = {"slow_read": ToolEntry(descriptor=slow_read, is_mutating=False)}

def _make_plan(n: int):
    from voss.harness.agent import Plan, ToolCall
    return Plan(
        rationale="benchmark",
        steps=[ToolCall(name="slow_read", args={"path": f"f{i}.txt"}) for i in range(n)],
        confidence=1.0, final_when_done="ok",
    )

async def test_parallel_read_speedup_default_cap(monkeypatch, tmp_path):
    # Configure cap=8 (default)
    from voss_runtime import configure, reset_config
    reset_config()
    configure(max_parallel_reads=8)

    plan = _make_plan(6)

    t0 = time.perf_counter()
    await _run_step_loop(plan.steps, SLOW_TOOLS, None, NullRenderer(), recorder=None)
    parallel_ms = (time.perf_counter() - t0) * 1000

    # Force serial via cap=1
    reset_config(); configure(max_parallel_reads=1)
    t0 = time.perf_counter()
    await _run_step_loop(plan.steps, SLOW_TOOLS, None, NullRenderer(), recorder=None)
    serial_ms = (time.perf_counter() - t0) * 1000

    assert parallel_ms <= serial_ms * 0.6, (
        f"parallel {parallel_ms:.1f}ms not <= 60% of serial {serial_ms:.1f}ms"
    )

async def test_parallel_read_speedup_cap_1_sanity(monkeypatch):
    reset_config(); configure(max_parallel_reads=1)
    plan = _make_plan(6)
    t0 = time.perf_counter()
    await _run_step_loop(plan.steps, SLOW_TOOLS, None, NullRenderer(), recorder=None)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    # 6 reads × 50ms = 300ms ± slop; under 250ms means parallelism leaked through
    assert elapsed_ms >= 250, f"cap=1 ran too fast ({elapsed_ms:.1f}ms) — parallelism leaked"
```

### Example 6: Telemetry assertion fixture
```python
# Source: PAR-06 + existing telemetry.emit spy pattern in tests/harness/
async def test_batch_telemetry_events(monkeypatch, tmp_path):
    events: list[dict] = []
    monkeypatch.setattr("voss.harness.telemetry.emit",
                        lambda kind, level, *a, **kw: events.append({"kind": kind, **kw.get("data", {})}))
    # Build a plan with one 4-read batch.
    plan = Plan(steps=[ToolCall(name="fs_read", args={"path": f"f{i}.txt"}) for i in range(4)],
                rationale="x", confidence=1.0, final_when_done="ok")
    # ... write 4 fixture files into tmp_path ...
    await _run_step_loop(plan.steps, make_toolset(tmp_path), None, NullRenderer(), recorder=None)

    starts = [e for e in events if e["kind"] == "batch.start"]
    ends = [e for e in events if e["kind"] == "batch.end"]
    assert len(starts) == 1 and len(ends) == 1
    assert starts[0]["parallel_count"] == 4
    assert starts[0]["batch_index"] == 0
    assert ends[0]["batch_index"] == 0
    # Per-step events still fire
    tool_calls = [e for e in events if e["kind"] == "tool.call"]
    assert len(tool_calls) == 4
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Strictly-serial `for step in plan_steps` in `_run_step_loop` (`agent.py:517`) | Order-preserving partition scheduler with bounded `asyncio.gather` | T2 (this phase) | 6-read scenario goes from 6× single-read latency to 1× single-read latency. 40%+ wall-clock drop on the SPEC PAR-05 benchmark. |
| Multi-edit requires N `fs_edit` calls (each writing to disk + opening modal) | `fs_edit_many(path, edits=[...])` — single tool call, atomic snapshot-then-write, single modal walk with N hunks | T2 | Reduces modal-walk fatigue + makes multi-edit observable as one mutation in the recorder. |
| Multi-file read = N `fs_read` calls | `fs_read_many(paths=[...])` — one bundle response | T2 | Reduces tool-call count in plans where the model needs to read several files. |
| No concurrency cap (single thread serial) | `[agent] max_parallel_reads = 8` (configurable 1–32) | T2 | First in-tree concurrency knob below the iteration level. |
| Telemetry: per-step `tool.call` / `tool.result` only | + `batch.start` / `batch.end` for multi-step batches | T2 (PAR-06) | JSONL consumers see batch structure without inferring it from timestamps. |
| `RunRecord.iterations[i]` (T1) — only tool_results | + `IterationRecord.batches: list[BatchRecord]` | T2 (PAR-06) | Batch wall-clock + ok/err counts persist for `voss resume` + future cost-by-batch analysis. |

**Deprecated/outdated:** None. T2 is purely additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | T1 has shipped or will ship before T2 (T1-01 IterationRecord + T1-04 [agent] section loader + T1-05 while-loop + T1-06 cancel handler). | Multiple — partition scheduler reuses T1's `IterationRecord`, T2's `max_parallel_reads` piggybacks the T1-04 `[agent]` loader, batch cancel relies on T1's `except CancelledError` chain. | If T2 ships before T1 is complete, the planner must include a Wave 0 that lays down a minimal `IterationRecord` subset + `[agent]` loader extension. CONTEXT.md D-15 names T2 as the loader owner if T1 doesn't get there first. **Mitigation:** every plan that touches files T1 modifies should re-grep its assumptions immediately before execution; planner should add a Wave-0 dependency probe. |
| A2 | `voss_runtime/_config.py` `RuntimeConfig` accepts `max_parallel_reads` as a `dataclasses.replace` kwarg through `configure(...)` — same as T1-04 adds `max_iterations`. | Pattern 2 + Pattern 7 + Pitfall 7. | If `RuntimeConfig` rejects unknown kwargs (it's a `@dataclass` so `configure(**kwargs)` uses `dataclasses.replace`), the field must be declared at `RuntimeConfig` definition. T1-04 establishes that field add; T2 adds one more. Very low risk. |
| A3 | `time.perf_counter` is acceptable to SPEC PAR-05 line 62 (which says `time.monotonic`). | Pattern 7 + Code Example 5. | If the planner literally enforces `time.monotonic`, swap one identifier. Both are monotonic; `perf_counter` is the higher-resolution variant. Zero behavior risk. |
| A4 | The `DiffModal.action_cancel` (Escape key) producing `decisions = []` is the third rejection signal alongside per-hunk `"reject"`. | Pattern 5 + Code Example 3. | If the planner wants to surface "cancel" differently from "any reject", the empty-list path can return `<denied: cancelled>` while per-hunk reject returns `<denied: hunk N rejected>` — both deny the batch. The acceptance criterion (PAR-03 line 46) just requires "reject-any → batch denied". Low risk; ergonomic decision only. |
| A5 | `RuntimeConfig.max_parallel_reads` 30KB cap value for `fs_read_many` is appropriate (`30 * 1024 = 30720` bytes). | Pattern 6 + Code Example "fs_read_many". | D-13 locks 30KB; planner may re-tune after benchmark. Worst case: too small → frequent truncation hurts model performance; too large → context-window pressure. Re-tune deferred to dogfood. |
| A6 | Treating modal decision `"skip"` as equivalent to `"accept"` (i.e., NOT a rejection) preserves SPEC semantics. | Pattern 5 + Code Example 3. | SPEC PAR-03 line 46 says "reject-any". Skip is the user's third option (between accept and reject). Calling skip = "neither accept nor reject" → most natural reading is "permit the edit", since the alternative (skip = deny) makes the modal's keybindings nearly identical (`n` and `s` would both deny). The planner can flip this to "skip = deny" easily; the impact is one line in Pattern 5. **Surface this to the user during discuss-phase** if it wasn't already locked. *(CONTEXT.md does not explicitly disambiguate — flagging here for user confirmation.)* |
| A7 | `asyncio.Semaphore` correctly bounds peak in-flight even when individual coroutines hit a slow path (e.g., a stub `await asyncio.sleep` longer than expected). | Pattern 2 + SPEC PAR-05 acceptance criterion line 63. | `Semaphore.acquire` blocks; once held, a coro can run for any duration. Cap is on *concurrency*, not on per-task latency. Test should observe peak in-flight via a hook (`asyncio.Lock` + counter, or `asyncio.Semaphore` introspection of `_value` is not stable API — use the explicit-counter pattern in Code Example 5 if SPEC PAR-05 acceptance line 63 wants this). |

**Of these 7 assumptions, A6 is the only one that should surface to the user during /gsd:discuss-phase rerun OR be flagged as the planner's call.** A1–A5, A7 are mechanical and resolve in plan execution.

## Open Questions

1. **`"skip"` decision in DiffModal: deny or permit?**
   - What we know: M9-05's `DiffModal` returns `DiffDecision(decision='accept'|'reject'|'skip')` per hunk. SPEC PAR-03 says "reject-any → batch denied".
   - What's unclear: whether `skip` collapses to accept (permissive) or reject (strict). Not addressed in CONTEXT.md D-03.
   - Recommendation: planner picks. Default to **strict** (skip → batch denied) because atomicity invariant favors safety. If the user wanted per-hunk acceptance, they wouldn't have launched `fs_edit_many`. Document in `T2-03-PLAN.md` SUMMARY.

2. **`BatchInvariantError` exception hierarchy: standalone or `HarnessError` parent?**
   - What we know: D-18 locks placement in `agent.py`; class hierarchy is planner's discretion.
   - What's unclear: whether T2 introduces `HarnessError` as a parent for future use, or just raises `BatchInvariantError(Exception)` direct.
   - Recommendation: standalone `class BatchInvariantError(Exception)` — YAGNI applies. No other harness exceptions exist today (`SandboxError(RuntimeError)` is the closest neighbor and it picks `RuntimeError`, not a domain root). If a future phase wants a hierarchy, refactor then.

3. **Per-step `tool.call` event `batch_index` annotation: add or skip?**
   - What we know: CONTEXT.md flags this as Claude's Discretion. Constraint: M2 RunRecord ledger unchanged.
   - What's unclear: trade-off between schema mutation (per-step events grow a new field) and JSONL-consumer ergonomics (consumers can already infer batch_index from `batch.start/.end` event timestamps and step_indices).
   - Recommendation: **skip the annotation** in T2. Reasoning: SPEC PAR-06 line 65 says "Per-step events unchanged — preserves M2 `RunRecord` schema". Adding `batch_index` to `tool.call` is a schema mutation. Consumers can compute it from event proximity. If a future telemetry consumer needs the field, add it then.

4. **Wave ordering inside T2**
   - What we know: 6 PAR-* requirements; PAR-01/02 shared substrate; PAR-03/04 independent tools; PAR-05/06 observability + perf gate.
   - What's unclear: precise wave structure — planner decides.
   - Recommendation: Wave 1 = PAR-01 + PAR-02 + PAR-05 config loader (substrate, sequential). Wave 2 = PAR-03 || PAR-04 (parallel — different files in `tools.py`). Wave 3 = PAR-06 telemetry + `BatchRecord` schema + recorder hooks (observes Wave 1+2 behavior). Wave 4 = PAR-05 micro-benchmark + acceptance suite (depends on everything). 4 waves, 6 plans.

5. **Cap value 30KB total bundle budget**
   - What we know: D-13 locks 30KB per-file. SPEC out-of-scope §11 mentions a rejected 100KB total-bundle cap.
   - What's unclear: at 6 paths × 30KB = 180KB worst-case bundle — does this hit context-window pressure?
   - Recommendation: ship 30KB per-file with no total cap. Monitor in benchmark + dogfood. Planner may add a total cap later if context-window pressure surfaces.

## Environment Availability

T2 is code/config-only. No external CLI tools, services, or runtimes beyond what the project already runs on. The benchmark uses `asyncio.sleep` stubs — no live disk timing required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python ≥3.11 | All PAR-* (asyncio + dataclasses + pydantic) | ✓ | locked in `pyproject.toml` | — |
| pytest ≥8.0 | PAR-01..06 test fixtures | ✓ | pinned dev dep | — |
| pytest-asyncio ≥0.23 | All async test fixtures | ✓ | pinned dev dep | — |
| Textual (for DiffModal interactive tests) | PAR-03 modal integration test | ✓ | pinned via M9 phase | If unavailable, mock the renderer's `show_diff_modal` (Code Example 6 pattern). |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23+ (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (lines around `testpaths = ["tests"]`) |
| Quick run command | `uv run pytest tests/harness/ -k "step_loop or fs_edit_many or fs_read_many or telemetry_batches or agent_config" -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAR-01 | Partition `[read_A, write_B, read_C, read_D]` → 3 batches in order; gather concurrent dispatch | unit (async) | `uv run pytest tests/harness/test_step_loop_partition.py -x` | ❌ Wave 0 |
| PAR-02 | Synthetic mutating-in-batch raises `BatchInvariantError`; per-step `PermissionGate.check` still fires | unit | `uv run pytest tests/harness/test_step_loop_partition.py::test_mutation_in_batch_raises -x` | ❌ Wave 0 |
| PAR-03 | 4 acceptance fixtures: 3 valid edits, non-unique, not-found, modal-reject | unit (async) | `uv run pytest tests/harness/test_fs_edit_many.py -x` | ❌ Wave 0 |
| PAR-04 | 4 acceptance fixtures: 3 readable, missing-slot, duplicate, empty list | unit (async) | `uv run pytest tests/harness/test_fs_read_many.py -x` | ❌ Wave 0 |
| PAR-05 | Cap honored; benchmark ≤60% wall-clock at default; cap=1 sanity fail | unit + perf | `uv run pytest tests/harness/test_agent_config.py tests/perf/test_parallel_read_speedup.py -x` | ❌ Wave 0 (perf dir doesn't exist) |
| PAR-06 | One `batch.start`+`batch.end` per multi-step batch; no wrappers for singletons; round-trip schema | unit | `uv run pytest tests/harness/test_telemetry_batches.py tests/harness/test_session_iterations.py -x` | ❌ Wave 0 (telemetry_batches new; session_iterations exists post-T1, extend) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/harness/ -k "<related test>" -x -q` (<5s typical).
- **Per wave merge:** `uv run pytest tests/harness/ tests/perf/ -x -q` (<30s typical for harness + 1 perf file).
- **Phase gate:** Full suite green before `/gsd:verify-work`. Includes the parity test from T1-03 + the M9-05 modal tests (regression confirms multi-hunk surfacing didn't break).

### Wave 0 Gaps

- [ ] `tests/harness/test_step_loop_partition.py` — covers PAR-01, PAR-02.
- [ ] `tests/harness/test_fs_edit_many.py` — covers PAR-03 (4 acceptance fixtures).
- [ ] `tests/harness/test_fs_read_many.py` — covers PAR-04 (4 acceptance fixtures).
- [ ] `tests/harness/test_telemetry_batches.py` — covers PAR-06.
- [ ] `tests/harness/test_agent_config.py` extension — adds `max_parallel_reads` cases (T1-04 creates this file for `max_iterations`).
- [ ] `tests/perf/` directory + `tests/perf/test_parallel_read_speedup.py` — covers PAR-05 perf gate.
- [ ] `tests/harness/test_session_iterations.py` extension — adds `IterationRecord.batches=[]` round-trip assertion (T1-01 creates this file).
- [ ] Framework install: none — `pytest`, `pytest-asyncio`, `pytest-mock` already pinned in `pyproject.toml`.

## Security Domain

T2 introduces no new network surface, no new credential handling, no new shell command execution paths, and no new external input parsing. The new tools (`fs_read_many`, `fs_edit_many`) reuse the existing `jail_path` sandbox primitive and the existing redaction surface (`telemetry.redact_tool_args`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | T2 has no auth surface; provider OAuth lives in T1's `providers.py`, untouched. |
| V3 Session Management | no | Sessions are local files; no new fields. |
| V4 Access Control | **yes** | `PermissionGate.check` continues to fire per-step. Partition-time invariant (`BatchInvariantError`) is an additional access-control gate that prevents mutating tools from running concurrently. |
| V5 Input Validation | **yes** | `fs_read_many` validates each path via `jail_path` independently (D-14); `fs_edit_many` validates each `old` uniquely matches before any disk write. |
| V6 Cryptography | no | No crypto operations introduced. |
| V12 Files & Resources | **yes** | `jail_path` enforces cwd containment; `fs_edit_many` validates-then-writes atomically (no partial files on failure). |
| V14 Configuration | **yes** | `[agent] max_parallel_reads` parsed via the same regex pattern T1-04 uses for `max_iterations`; out-of-range values fall back to default with a warning (SPEC PAR-05 + Constraint 6). |

### Known Threat Patterns for {Voss harness + asyncio}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `fs_read_many` slot | Information Disclosure | `jail_path(cwd, path)` per slot; `SandboxError` → `<error: path outside cwd: {path}>` inline (D-14). |
| Concurrent writes corrupting a file (`fs_edit_many` race) | Tampering | Single tool call writes once after all edits validate; no inter-tool race because mutations stay serial (SPEC PAR-01 Constraint: "no parallel mutation"). |
| Resource exhaustion via huge `paths` list | DoS | Per-file 30KB cap (D-13) bounds bundle width per slot. **No total-bundle cap** — flagged in Open Question #5 as something to monitor in dogfood. |
| Tool classification bypass | Elevation of Privilege | `is_mutating` is data at registration (M1 D-06), not name-pattern. `BatchInvariantError` defends against misclassification slipping into a parallel batch (PAR-02). |
| Sensitive args leaking into telemetry | Information Disclosure | `redact_tool_args` already redacts `old`, `new`, `content` (from `telemetry.py:30`); applies unchanged to per-step events inside batches. |
| `CancelledError` interpretation confusion | DoS (partial work loss) | Cancel discipline locked in D-06/D-07: outer cancel propagates; in-flight reads cancel; recorder finalizes within ≤100ms (T1 SPEC criterion 3). |

## Sources

### Primary (HIGH confidence — in-tree code)
- `voss/harness/agent.py:507–598` — current `_run_step_loop` serial body [VERIFIED: read in this session]
- `voss/harness/agent.py:601–604` — `_substitute_placeholders` (T1 deletes) [VERIFIED]
- `voss/harness/tools.py:14–207` — `ToolEntry` + `make_toolset` + all current tool bodies [VERIFIED]
- `voss/harness/permissions.py:144–229` — `PermissionGate` mode/check/diff-preview flow [VERIFIED]
- `voss/harness/tui/widgets/diff_modal.py:21–123` — `Hunk`, `DiffDecision`, `DiffModal.action_*` keys [VERIFIED]
- `voss/harness/tui/renderer.py:306–323` — `show_diff_modal(hunks, timeout_s)` signature [VERIFIED]
- `voss/harness/session.py:70–87` — `RunRecord` dataclass; T1-01 extends with `iterations` + `exit_reason` [VERIFIED]
- `voss/harness/recorder.py:27–119` — `RunRecorder`; T1-01 extends with `begin_iteration/end_iteration` [VERIFIED]
- `voss/harness/config.py:1–59` — current regex-based loader (T1-04 extends with `[agent]` section) [VERIFIED]
- `voss/harness/telemetry.py:80–183` — `note_turn`, `emit`, `redact_tool_args` [VERIFIED]
- `voss/harness/sandbox.py:25–29` — `SandboxError` + `jail_path` [VERIFIED]
- `voss_runtime/agent.py:109` — codebase precedent for `asyncio.gather(*pending, return_exceptions=True)` [VERIFIED]
- `pyproject.toml` — Python ≥3.11; `pytest>=8.0`; `pytest-asyncio>=0.23`; `asyncio_mode = "auto"` [VERIFIED]
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md` — locked T1 contract [VERIFIED]
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md` — locked T1 cancel-point discipline [VERIFIED]
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-01-PLAN.md` — `IterationRecord` + `RunRecorder.begin_iteration/end_iteration` substrate [VERIFIED]
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md` — `[agent]` section loader + `RuntimeConfig.max_iterations` substrate [VERIFIED]
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-05-PLAN.md` — `_run_turn_exec` rewrite consuming `_run_step_loop` [VERIFIED]
- `.planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md` — 6 locked requirements, 22 acceptance criteria [VERIFIED]
- `.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md` — 19 locked decisions [VERIFIED]

### Secondary (HIGH confidence — official Python docs)
- [asyncio.gather](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather) — `return_exceptions=True` semantics; outer cancel propagation; ordering preservation [CITED]
- [asyncio.Semaphore](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore) — canonical `async with sem:` bounded-concurrency pattern [CITED]
- [asyncio.CancelledError](https://docs.python.org/3/library/asyncio-exceptions.html#asyncio.CancelledError) — `BaseException` subclass; propagation rules [CITED]
- [asyncio.TaskGroup](https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup) — considered as alternative; rejected per D-04 [CITED]

### Tertiary (LOW confidence — none flagged)
None. All claims in this research are either VERIFIED in-tree or CITED to official Python docs.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — stdlib + already-pinned dev deps; codebase precedent for `asyncio.gather(return_exceptions=True)` in `voss_runtime/agent.py:109`.
- Architecture: **HIGH** — 19 decisions in CONTEXT.md + 6 locked requirements with 22 acceptance criteria leave almost no exploratory surface. The partition algorithm is single-pass left-to-right (`O(n)`), straightforward.
- Pitfalls: **HIGH** — `asyncio` cancel semantics + `return_exceptions=True` behavior verified against Python docs; in-tree precedents for path jailing, redaction, error envelopes, truncation markers all confirmed.
- Tests: **HIGH** — `asyncio_mode = "auto"` is already configured; existing recorder/session test patterns (e.g., `tests/harness/test_recorder.py`) directly transfer.
- Open question on `"skip"` decision (Pitfall A6) is the only meaningful research-time ambiguity and is flagged in the Assumptions Log.

**Research date:** 2026-05-15
**Valid until:** 2026-06-14 (30 days — stack is stable in-tree; only the SPEC/CONTEXT lock could shift, in which case re-baseline).

## RESEARCH COMPLETE

6 PAR requirements mapped to 8 patterns, 10 pitfalls, 7 assumptions; 4 waves recommended; zero new third-party deps; all anchors VERIFIED in-tree.
