# Phase T2: Parallel Tools + Multi-Edit Primitive — Specification

**Created:** 2026-05-15
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 6 locked

## Goal

Replace the strictly-sequential `_run_step_loop` with an order-preserving partition scheduler that runs read-only step batches in parallel (capped at 8) and keeps mutating steps serialized, plus ship two batch primitives — `fs_read_many(paths=[...])` returning per-path results and `fs_edit_many(path, edits=[...])` applying single-file atomic multi-edit through the M9-05 diff modal — measured by a micro-benchmark that proves ≥40% wall-clock drop on a 6-file read step.

## Background

Today `_run_step_loop` (`voss/harness/agent.py:507`) is an async-for that awaits each `ToolCall` one at a time, even when adjacent steps are read-only and independent. A 6-file read plan-step takes 6× single-read latency. There is no parallelism primitive in the harness.

`ToolEntry` (`voss/harness/tools.py:14`) already carries `is_mutating: bool` at registration — read-only tools (`fs_read`, `fs_glob`, `fs_grep`, `git_status`, `git_diff`, `voss_check`) and mutating tools (`fs_write`, `fs_edit`, `shell_run`, `record_run`) are pre-classified. The classification is unused for scheduling; only `PermissionGate.check` consumes the bit (`agent.py:535`).

`PermissionGate.check` (`permissions.py:169`) fires once per step inside the for-loop. There is no partition-time enforcement that a parallel batch contains only read-only tools — today there are no batches.

The batch tool surface is missing:
- `fs_read` (`tools.py:52`) reads one path per call.
- `fs_edit` (`tools.py:114`) replaces a single uniquely-matching `old` substring per call; multi-edit requires N tool calls.

M9-05 already ships the right modal surface: `DiffModal` (`voss/harness/tui/widgets/diff_modal.py:34`) takes `hunks: list[Hunk]` and walks per-hunk approval — multi-edit can decompose into N hunks at the modal layer without new UI.

T1 hands T2 a loop that re-iterates on tool results (`_run_turn_exec` while-loop). T1's SPEC explicitly carves parallel tool execution within an iteration out of T1 and into this phase (`PAR-01..04`). M5 golden fixtures don't exist yet — so the "40% latency drop on M5 task #5" success criterion in the roadmap cannot be measured against an external baseline; T2 ships its own micro-benchmark instead.

## Requirements

1. **PAR-01 — Partition scheduler**: `_run_step_loop` partitions plan steps into read-only batches + mutating singletons and runs each batch with bounded concurrency.
   - Current: `_run_step_loop` is a strictly serial `async for step in plan_steps`. No partitioning, no `asyncio.gather`.
   - Target: Scheduler walks `plan.steps` in author order. Consecutive read-only steps (those whose `ToolEntry.is_mutating` is False) collect into a batch; a mutating step flushes the current batch and runs alone. Batches dispatch via `asyncio.gather` bounded by an `asyncio.Semaphore(harness.agent.max_parallel_reads)` (default 8). Author ordering is preserved: a read step never executes before a write that precedes it in `plan.steps`; reads after a write run in the next batch, not hoisted ahead.
   - Acceptance: pytest fixture with steps `[read_A, write_B, read_C, read_D]` produces three batches in order — `[A]`, `[B]`, `[C, D]` — verified by mock-tool ordering hooks; gather-based dispatch on the third batch observed via concurrent invocation timestamps.

2. **PAR-02 — Mutation-in-batch gate**: `PermissionGate` enforces "no mutation in parallel batch" at partition classification, not just at per-step check.
   - Current: `PermissionGate.check` is called once per step inside the serial loop. No partition-time invariant exists because no partitions exist.
   - Target: The partition scheduler asserts at batch-construction time that every step in a multi-step batch has `is_mutating == False`. Violation (e.g. an unregistered tool defaulting to mutating, or a future tool misclassified) raises `BatchInvariantError` and the loop bails out cleanly — not silently degrading to serial. Per-step `PermissionGate.check` still fires for every step (preserves prompt + diff-preview flow); the partition assertion is an additional invariant, not a replacement.
   - Acceptance: pytest plants a synthetic plan with a mutating step inside a multi-step batch (bypassing the partitioner) and asserts `BatchInvariantError` raised; second test verifies normal flow still calls `PermissionGate.check` once per step.

3. **PAR-03 — `fs_edit_many` single-file atomic batch**: New tool `fs_edit_many(path, edits=[{old, new}, ...])` applies N edits to one file atomically.
   - Current: No `fs_edit_many` tool. Multi-edit requires N `fs_edit` calls, each writing the file, each going through a separate diff modal.
   - Target: New tool registered with `is_mutating=True`. Signature: `fs_edit_many(path: str, edits: list[dict]) -> str` where each `edits` entry is `{"old": str, "new": str}`. Semantics:
     - Read file once into a snapshot string.
     - For each edit in `edits` (left-to-right list order), verify `old` matches uniquely (count == 1) in the **current working buffer**. Apply in place. If any `old` matches zero times or more than one time, **reject the entire batch** — no partial write, no file mutation, return `<error: batch rejected at index {i}: {reason}>`.
     - On all-edits-pass, write the buffer back to disk once.
     - `PermissionGate.check` fires once for the whole call. `DiffModal` receives N `Hunk` objects (one per edit) so the user steps through with the existing M9-05 per-hunk UI. **Reject-any in the modal cancels the whole batch** (atomicity invariant survives UX); the tool returns `<denied: hunk N rejected>` and writes nothing.
   - Acceptance: pytest fixtures cover (a) 3 edits all match uniquely → file written with all 3 applied + return reports `(+N -M lines)`; (b) edit #2's `old` matches twice → batch rejected, file byte-for-byte unchanged on disk; (c) edit #3's `old` not found → batch rejected, error names index 2; (d) modal rejects hunk #2 → batch denied, file unchanged.

4. **PAR-04 — `fs_read_many` bundled response**: New tool `fs_read_many(paths=[...])` returns one bundle covering all requested paths.
   - Current: No batched read tool. Reading N files requires N `fs_read` calls.
   - Target: New tool registered with `is_mutating=False`. Signature: `fs_read_many(paths: list[str]) -> str`. Returns a deterministic formatted bundle: for each requested path, one labeled section. Each section is either the file contents OR an error string (matching `fs_read`'s existing conventions: `<error: not found: ...>`, `<error: is a directory: ...>`, `<error: binary file: ...>`). **The call itself never errors as a whole** — partial-result semantics; the agent sees per-slot errors inline. Format is stable so downstream tooling can parse it:
     ```
     === {path} ===
     {content or error string}

     === {path} ===
     {content or error string}
     ```
   - Acceptance: pytest fixtures cover (a) 3 readable paths → bundle contains 3 sections in request order with correct contents; (b) 1 missing + 2 readable → bundle still has 3 sections, missing path's section is `<error: not found: ...>`, other two readable; (c) duplicate path in list → both slots filled (no dedup); (d) empty `paths=[]` → returns `<no paths requested>` sentinel.

5. **PAR-05 — Concurrency cap + perf gate**: `harness.toml` knob `agent.max_parallel_reads` bounds batch concurrency; a self-contained micro-benchmark proves ≥40% wall-clock drop.
   - Current: No concurrency cap (no parallelism), no perf benchmark. Roadmap referenced M5 task #5 as baseline but `eval/` is empty.
   - Target: `harness.toml` gains `agent.max_parallel_reads` (int, default 8, range 1–32). Scheduler reads this at run start; semaphore bounds `asyncio.gather` width inside one batch. New benchmark `tests/perf/test_parallel_read_speedup.py` constructs a 6-file `fs_read_many` plan-step against fixture files (using a stub tool that sleeps a fixed duration to make the perf claim deterministic and CI-friendly), measures wall-clock for serial baseline vs. parallel batch via `time.monotonic` deltas, and asserts parallel time ≤ 60% of serial baseline. **No live-disk or live-network timing in the benchmark** — that would be flaky on CI.
   - Acceptance: `agent.max_parallel_reads = 2` in test config caps the gather to 2 concurrent slots even when batch has 6 reads (verified via semaphore-observer hook counting peak in-flight); benchmark passes with default cap (8) at ≤60% wall-clock; benchmark explicitly fails when cap is forced to 1 (sanity).

6. **PAR-06 — Batch telemetry events**: Recorder emits per-step `tool.call`/`tool.result` events unchanged AND wraps parallel batches with `batch.start`/`batch.end` events.
   - Current: `telemetry.emit("tool.call", ...)` and `tool.result` fire once per step in the serial loop (`agent.py:554`, `:585`). No batch concept in telemetry.
   - Target: Per-step events unchanged — preserves M2 `RunRecord` schema and `voss resume` semantics. Additionally, each multi-step batch emits one `batch.start` event before dispatch with `{batch_index, step_indices: [i, j, ...], parallel_count}` and one `batch.end` event after gather completion with `{batch_index, wall_clock_ms, ok_count, err_count}`. Mutating singletons do NOT emit batch wrappers (single-step batches are degenerate; only multi-step parallel batches get wrappers). `RunRecord` gains an additive `batches: list[BatchRecord]` field (Optional, default `[]`) capturing the same shape — schema is additive-only, M2-compatible.
   - Acceptance: pytest parses telemetry JSONL after a turn with a single 4-read parallel batch and asserts exactly one `batch.start` + one `batch.end` event, four `tool.call` events nested between them (by timestamp), `parallel_count == 4`, monotonic `batch_index` across multiple batches; second fixture confirms a mutating singleton emits NO `batch.start`/`batch.end`; `RunRecord.batches` round-trips through serialize→deserialize without loss.

## Boundaries

**In scope:**
- `_run_step_loop` partition scheduler (read batches + mutating singletons, preserve order, split at writes).
- `BatchInvariantError` raised when a multi-step batch contains a mutating step.
- New tool `fs_edit_many(path, edits=[{old,new},...])` — single-file atomic batch, registered `is_mutating=True`.
- New tool `fs_read_many(paths=[...])` — partial-result bundle, registered `is_mutating=False`.
- `harness.toml` knob `agent.max_parallel_reads` (default 8, range 1–32).
- `asyncio.Semaphore`-bounded `asyncio.gather` for each multi-step batch.
- `fs_edit_many` → `DiffModal` integration: one gate call, N hunks displayed via M9-05 per-hunk approval, reject-any → batch denied.
- Self-contained micro-benchmark in `tests/perf/test_parallel_read_speedup.py` asserting ≥40% wall-clock drop on stub-timed 6-file batch.
- Telemetry: per-step events preserved + new `batch.start`/`batch.end` wrappers for multi-step batches.
- `RunRecord.batches: list[BatchRecord]` additive field — M2 schema-compatible.
- pytest coverage for all 6 PAR requirements.

**Out of scope:**
- `fs_grep_many` / `fs_glob_many` batch primitives — deferred. `fs_grep` and `fs_glob` remain singletons; they still parallelize inside read batches via PAR-01 (singletons-in-batch is fine).
- Dependency analysis between reads — partitioner does NOT inspect `step_C.args` to detect references to `step_A`'s output. Reads are partitioned purely by `is_mutating` + author order. Plan author owns ordering correctness.
- Parallel mutation — mutations remain strictly serial in T2 even when paths obviously don't conflict (e.g. writing to `a.txt` and `b.txt`). No write-write parallelism, no read-during-write. Future phase if measured benefit emerges.
- Streaming tool results into the model mid-batch — a batch's results are delivered as one block to the next T1 iteration. T1's `stream()` text-delta render does NOT interleave with mid-batch tool results. Keeps T1/T2 layering clean.
- Multi-file `fs_edit_many` — explicitly single-file per call. `fs_edit_many(edits=[{path, old, new}, ...])` cross-file shape is rejected here; multi-file atomic edits, if needed, are a separate future tool.
- Mid-batch partial-rollback for `fs_edit_many` — all-or-nothing at the snapshot level (validate all, then write once); no surgical rollback of individual edits.
- M5 golden eval task #5 — roadmap referenced this as the perf baseline but `eval/` is empty. T2 ships its own micro-benchmark; M5 may adopt it later but is not a dependency.
- New telemetry sinks / dashboards — only the JSONL event stream gains the new event types and `RunRecord.batches` field.
- Cost surface changes (`/cost --by-batch`) — out. Cost still aggregates per-iteration via T1's existing mechanism.

## Constraints

- Author order is non-negotiable: a read step authored after a mutating step never executes before that mutation. The partitioner is a one-pass left-to-right grouping algorithm — no reordering, no dependency graph.
- `RunRecord` schema additions (`batches`) are additive-only. M2 `voss resume` must round-trip pre-T2 records unchanged.
- `fs_edit_many` atomicity is per call, single-file: validate all edits against an in-memory snapshot, then write the file exactly once. No mid-batch disk writes. No file mutation if any edit's `old` fails the uniqueness check.
- `fs_edit_many` modal flow: one `PermissionGate.check` call; `DiffModal.hunks` receives one Hunk per edit. Rejecting any hunk cancels the whole batch (atomic invariant trumps per-hunk granularity — the modal returns batch-level reject when any hunk is rejected, even though it walks per-hunk for inspection).
- `fs_read_many` partial-result schema is the stable surface: agent prompt must instruct the model that per-slot errors are normal and self-contained. `<error: ...>` strings inside a section are inline data, not call failures.
- Concurrency cap is bounded: `agent.max_parallel_reads` accepts integer 1–32 inclusive. Out-of-range values fall back to default 8 with a config warning. Zero or negative rejected at load time.
- Benchmark must use stub-timed tools (deterministic `asyncio.sleep`) — no live disk/network timing — to keep CI stable. The benchmark asserts wall-clock ratio, not absolute milliseconds.
- `BatchInvariantError` is a hard error, not a warning. The agent surface should treat it as a planner bug (a misclassified tool slipping into a parallel batch) — finalize the recorder with `exit_reason = "batch-invariant"` (additive enum value on T1's exit_reason set).
- No tool-name pattern matching for classification — partitioning reads `ToolEntry.is_mutating` only. Classification stays at registration (consistent with M1 D-06).
- Permission flow per step inside a batch is unchanged: `PermissionGate.check` fires for every step including those inside a parallel batch. The partition-time invariant (PAR-02) is in addition to, not in replacement of, the per-step check.

## Acceptance Criteria

- [ ] `_run_step_loop` partitions `[read_A, write_B, read_C, read_D]` into batches `[A]`, `[B]`, `[C, D]` in that order, verified via mock-tool ordering hook.
- [ ] Third batch's reads dispatch via `asyncio.gather` (concurrent timestamps observed).
- [ ] `agent.max_parallel_reads = 2` caps peak in-flight reads to 2 even for a 6-read batch.
- [ ] `harness.toml` `agent.max_parallel_reads` default is 8 and is honored at runtime; out-of-range values fall back to default with a warning.
- [ ] `BatchInvariantError` raised when a multi-step batch contains a mutating step (synthetic test).
- [ ] `PermissionGate.check` still fires once per step including steps inside parallel batches.
- [ ] `fs_edit_many` registered with `is_mutating=True`; appears in `make_toolset` output.
- [ ] `fs_edit_many` with 3 valid edits writes the file once with all 3 applied; return string reports total line delta.
- [ ] `fs_edit_many` rejects the entire batch when any `old` fails uniqueness; file byte-for-byte unchanged on disk after rejection.
- [ ] `fs_edit_many` error message names the offending edit index.
- [ ] `fs_edit_many` integration with `DiffModal` displays N hunks (M9-05 per-hunk walk); rejecting any hunk denies the whole batch.
- [ ] `fs_read_many` registered with `is_mutating=False`.
- [ ] `fs_read_many(paths=[a, b, c])` returns a bundle with 3 labeled sections in request order.
- [ ] `fs_read_many` returns `<error: not found: ...>` in the missing path's slot without failing the whole call.
- [ ] `fs_read_many(paths=[])` returns `<no paths requested>`.
- [ ] Telemetry: multi-step parallel batch emits exactly one `batch.start` and one `batch.end` with monotonic `batch_index`.
- [ ] Telemetry: per-step `tool.call` / `tool.result` events still fire inside batches (schema unchanged).
- [ ] Telemetry: mutating singletons emit NO `batch.start` / `batch.end` events.
- [ ] `RunRecord.batches` round-trips through serialize→deserialize; pre-T2 records load unchanged.
- [ ] Benchmark `tests/perf/test_parallel_read_speedup.py` passes at default cap (parallel ≤ 60% of serial wall-clock).
- [ ] Benchmark explicitly fails when cap is forced to 1 (sanity check).

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                       |
|--------------------|-------|------|--------|-------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Partition algorithm + tool signatures + perf gate locked    |
| Boundary Clarity   | 0.92  | 0.70 | ✓      | 4 explicit out-of-scope items beyond the in-scope list      |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Atomicity scope + concurrency cap + telemetry shape locked  |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 22 pass/fail checkboxes; deterministic benchmark            |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      | Gate passes after round 3                                   |

## Interview Log

| Round | Perspective     | Question summary                              | Decision locked                                                            |
|-------|-----------------|-----------------------------------------------|----------------------------------------------------------------------------|
| 0     | (Scout)         | What exists vs T2 goal?                       | Serial loop; `is_mutating` already classified; M9-05 hunks API ready       |
| 1     | Researcher      | Perf baseline (M5 task #5 missing)            | Own micro-benchmark in `tests/perf/`; ≤60% wall-clock vs serial            |
| 1     | Boundary Keeper | `fs_edit_many` atomicity scope                | Single-file per call; validate-then-write; reject-batch on any failure     |
| 1     | Boundary Keeper | Mixed read/write ordering                     | Preserve author order; split at writes; no read-hoisting                   |
| 2     | Boundary Keeper | `fs_read_many` failure semantics              | Partial result with per-slot error markers; call never fails as a whole    |
| 2     | Failure Analyst | Concurrency cap shape                         | `agent.max_parallel_reads` default 8, configurable, range 1–32             |
| 2     | Failure Analyst | Multi-edit gate + modal flow                  | One gate call; N hunks via M9-05; reject-any → batch denied                |
| 3     | Boundary Keeper | Telemetry granularity                         | Per-step events preserved + `batch.start`/`batch.end` wrappers added       |
| 3     | Seed Closer     | Explicit out-of-scope                         | grep/glob_many, dep analysis, parallel mutation, mid-batch result stream   |

---

*Phase: T2-parallel-tools-multi-edit*
*Spec created: 2026-05-15*
*Next step: /gsd:discuss-phase T2 — implementation decisions (BatchRecord shape, semaphore placement, error-propagation for gather failures, fs_edit_many DiffModal wiring)*
