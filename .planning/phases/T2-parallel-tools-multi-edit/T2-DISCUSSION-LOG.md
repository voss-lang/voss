# Phase T2: Parallel Tools + Multi-Edit Primitive - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-15
**Phase:** T2-parallel-tools-multi-edit
**Areas discussed:** DiffModal wiring, Gather error semantics, BatchRecord home, harness.toml section, fs_edit fate, fs_read_many size cap, Mid-batch cancel, Batch event names

---

## DiffModal wiring for `fs_edit_many`

| Option | Description | Selected |
|--------|-------------|----------|
| Inside the tool function | `fs_edit_many` builds `list[Hunk]` and calls `renderer.show_diff_modal(hunks)`. PermissionGate stays single-edit. Tool owns its UX surface. | ✓ |
| Inside PermissionGate._render_diff_preview | Extend preview path to recognize `fs_edit_many` args. Single chokepoint for all mutating tools. | |
| New helper module: voss/harness/diff_hunks.py | Thin `hunks_from_edits(path, edits)` helper. Both fs_edit and fs_edit_many route through it. | |

**User's choice:** Inside the tool function
**Notes:** Keeps PermissionGate narrow; tool-shaped UX lives next to the tool. Gate still fires per-step before the modal call.

---

## Read-batch gather error semantics

| Option | Description | Selected |
|--------|-------------|----------|
| return_exceptions=True; per-step error strings | One step's failure does not cancel siblings. Exceptions stringified into `<error: ...>` slots in results list. Loop continues. | ✓ |
| Fail-fast; cancel sibling reads | First exception cancels remaining read coros. Loop ends turn with partial results + error. | |
| return_exceptions=True; first error halts subsequent batches | Gather completes current batch, records all results, then loop stops dispatching further batches. | |

**User's choice:** return_exceptions=True; per-step error strings
**Notes:** Matches the existing per-step try/except pattern in `_run_step_loop`. Read errors visible but non-fatal.

---

## `BatchRecord` schema home

| Option | Description | Selected |
|--------|-------------|----------|
| Nested inside T1's IterationRecord | `IterationRecord.batches: list[BatchRecord] = []`. Iteration-scoped capture. | ✓ |
| Top-level RunRecord.batches (parallel to iterations) | Sibling field to `iterations`. Each BatchRecord carries `iteration_index` for cross-reference. | |
| Telemetry-only — no RunRecord field | Batches emit JSONL events only. RunRecord schema unchanged. | |

**User's choice:** Nested inside T1's IterationRecord
**Notes:** Mirrors T1's iteration-scoped capture pattern. Pre-T2 records still round-trip via additive-Optional invariant.

---

## `harness.toml` section for `max_parallel_reads`

| Option | Description | Selected |
|--------|-------------|----------|
| [agent] section — carry forward, lock it | `[agent] max_parallel_reads = 8` co-locates with T1's `max_iterations = 8`. T2 pins T1's discretion item. | ✓ |
| [tools] section | Tool-shaped knobs under `[tools]`. Separates agent loop controls from tool-policy. | |
| Defer — planner picks during T2 plan-phase | Leave under Claude's Discretion like T1 did. | |

**User's choice:** [agent] section — carry forward, lock it
**Notes:** T1 + T2 ship coherent config. Loader extension lands once (T2 owns it per wave order).

---

## Fate of `fs_edit` after `fs_edit_many` ships

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both — fs_edit stays for single, fs_edit_many for multi | Two registered tools. Zero migration risk. | ✓ |
| Delete fs_edit — fs_edit_many handles N≥1 | One tool shape. Mirrors T1's hard-delete of `_substitute_placeholders`. | |
| Alias: fs_edit becomes a wrapper around fs_edit_many | Public name `fs_edit` survives; implementation delegates to fs_edit_many. | |

**User's choice:** Keep both
**Notes:** fs_edit is model-facing; hard-deletion forces agent-prompt churn for marginal surface reduction. `_substitute_placeholders` was internal plumbing — different bar.

---

## `fs_read_many` per-file size handling

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file cap 30KB, truncate with marker | Each section truncates at 30KB with `<truncated, total N bytes>` (mirrors shell_run). | ✓ |
| No cap — read full file like fs_read does | Bundle arbitrarily large. Matches fs_read semantics. | |
| Total-bundle cap 100KB, truncate from end | Bundle assembly stops at cumulative 100KB. | |

**User's choice:** Per-file cap 30KB, truncate with marker
**Notes:** 7.5× shell_run's 4KB. Predictable bundle size; protects context window. Re-tunable after benchmark.

---

## Interrupt mid-`asyncio.gather`

| Option | Description | Selected |
|--------|-------------|----------|
| Cancel siblings; record partial; finalize as 'interrupt' | CancelledError propagates into gather; in-flight reads cancel. Recorder captures completed steps. T1's exit_reason="interrupt" fires. | ✓ |
| Let batch finish, then check cancel at batch boundary | Gather runs to completion; check CancelledError after. Higher interrupt latency. | |
| Cancel siblings; discard batch results entirely | Cancel propagates, partial results dropped, RunRecord shows batch as not-attempted. | |

**User's choice:** Cancel siblings; record partial; finalize as 'interrupt'
**Notes:** Adds the gather as T2's third cancel-aware point (extending T1's two). Some batched steps (git_status / shell-shaped reads) are not free — running to completion violates T1's 100ms finalize criterion.

---

## Telemetry event names for batch wrappers

| Option | Description | Selected |
|--------|-------------|----------|
| `batch.start` / `batch.end` | Symmetric with T1's `iteration.start` / `iteration.end`. | ✓ |
| `tool.batch.start` / `tool.batch.end` | Nest under existing `tool.*` namespace. | |
| Defer to planner discretion | Constraint: must be `*.start` + `*.end` paired with monotonic batch_index. | |

**User's choice:** `batch.start` / `batch.end`
**Notes:** Predictable namespace: `{scope}.start` / `{scope}.end`. JSONL consumers learn one pattern.

---

## Claude's Discretion

- `DiffDecision.batch_mode` collapse mechanism (D-03 fork: per-hunk verdict inspection vs. modal-layer batch_mode flag).
- Exception → result-string formatter (`repr(exc)` vs `str(exc)` vs custom stringifier).
- `BatchRecord` exact pydantic field set + timestamp granularity (`started_at` / `ended_at` vs `wall_clock_ms` only).
- Whether per-step `tool.call` events inside a batch carry a `batch_index` annotation.
- Agent-prompt prose teaching batch semantics in T1's `PLAN_LOOP_SYSTEM`.
- Config loader refactor shape (generic section parser vs. per-section function).
- `fs_edit_many` return-string format on success and failure-index naming.
- `BatchInvariantError` class hierarchy (single class vs domain hierarchy).

## Deferred Ideas

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
- Cap value re-tuning (30KB per-file, 100KB total-bundle).
