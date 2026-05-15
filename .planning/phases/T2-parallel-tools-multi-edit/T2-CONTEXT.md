# Phase T2: Parallel Tools + Multi-Edit Primitive — Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**SPEC:** `T2-SPEC.md` — 6 requirements locked (PAR-01..06), ambiguity 0.13

<domain>
## Phase Boundary

Replace strictly-serial `_run_step_loop` with an order-preserving partition scheduler that runs read-only step batches in parallel (semaphore-capped) and keeps mutating singletons serialized; ship two new batch primitives — `fs_read_many` (partial-result bundle) and `fs_edit_many` (single-file atomic multi-edit through M9-05 DiffModal); prove a ≥40% wall-clock drop on a stub-timed 6-read micro-benchmark. Requirements (WHAT) are locked by SPEC.md. This document captures HOW.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**6 requirements are locked.** See `T2-SPEC.md` for full requirements (PAR-01..06), boundaries, constraints, and 22 acceptance criteria.

Downstream agents MUST read `T2-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- `_run_step_loop` partition scheduler (read batches + mutating singletons, preserve order, split at writes).
- `BatchInvariantError` when a multi-step batch contains a mutating step.
- New tool `fs_edit_many(path, edits=[{old,new},...])` — single-file atomic batch; `is_mutating=True`.
- New tool `fs_read_many(paths=[...])` — partial-result bundle; `is_mutating=False`.
- `harness.toml` knob `agent.max_parallel_reads` (default 8, range 1–32).
- `asyncio.Semaphore`-bounded `asyncio.gather` for each multi-step batch.
- `fs_edit_many` → `DiffModal` integration via M9-05 per-hunk approval; reject-any → batch denied.
- Self-contained micro-benchmark in `tests/perf/test_parallel_read_speedup.py`.
- Telemetry: per-step events preserved + `batch.start` / `batch.end` wrappers for multi-step batches.
- `RunRecord` schema additive: batches captured via `IterationRecord.batches: list[BatchRecord]`.

**Out of scope (from SPEC.md):**
- `fs_grep_many` / `fs_glob_many` batch primitives — deferred.
- Dependency analysis between reads — partitioner uses `is_mutating` + author order only.
- Parallel mutation — all writes strictly serial.
- Streaming tool results into the model mid-batch — batches deliver as one block.
- Multi-file `fs_edit_many` shape — single-file only.
- Mid-batch partial-rollback for `fs_edit_many` — validate-then-write, all-or-nothing.
- M5 golden eval task #5 — T2 ships own micro-benchmark.
- New telemetry sinks / dashboards / `/cost --by-batch` surface.
</spec_lock>

<decisions>
## Implementation Decisions

### Diff modal wiring for `fs_edit_many`

- **D-01:** `fs_edit_many` builds `list[Hunk]` itself and calls `renderer.show_diff_modal(hunks)` (M9-05 surface at `voss/harness/tui/renderer.py:306`). The tool function owns its UX surface. `PermissionGate._render_diff_preview` (`permissions.py`) stays single-edit and is NOT extended to recognize `fs_edit_many` args. Rationale: tool-shaped UX lives next to the tool; permission layer stays narrow. `fs_edit_many` still routes through `PermissionGate.check` once (per SPEC PAR-03) for the mode/scope/auto-yes flow — the modal call sits between the gate's `True` return and the actual disk write.
- **D-02:** Hunk-build sequence inside the tool:
  1. Read file once into snapshot buffer.
  2. Walk `edits` left-to-right validating each `old` matches uniquely in the *current working buffer*. On any failure, abort before any modal call → return error string, no UI surfaced.
  3. After all edits validate, construct `list[Hunk]` (one Hunk per edit, file = path, before/after lines from the in-memory diff).
  4. Call `renderer.show_diff_modal(hunks, timeout_s=…)`. Block on `DiffDecision`.
  5. If decision is whole-batch accept → write buffer once. If any hunk rejected → return `<denied: hunk N rejected>`, no disk write.
- **D-03:** Modal reject semantics: M9-05's `DiffModal` walks per-hunk (existing per-hunk approval UI), but T2 treats "any hunk rejected" as "batch rejected" to preserve atomicity. The modal still affords per-hunk *inspection* during the walk; the final return state collapses to all-accept-or-batch-reject. Planner decides whether to (a) read M9-05's existing `DiffDecision` shape to confirm it surfaces per-hunk verdicts, or (b) introduce a `DiffDecision.batch_mode` flag forcing all-or-nothing collapse at the modal layer. Both work for SPEC; D-03 picks (a) if M9-05 already returns granular state, else (b).

### Read-batch gather semantics

- **D-04:** `asyncio.gather(*coros, return_exceptions=True)` for read batches. Exceptions converted to `<error: {exc}>` strings and slotted into the same `results: list[str]` position the serial loop produces. Matches the existing per-step `try/except Exception` pattern in `_run_step_loop` (`agent.py:567`). Loop continues to next batch on any error; recorder captures per-step `ok=False` for the failed slot. This means **read errors are visible but non-fatal** — agent sees the error string in its next-iteration messages and can react.
- **D-05:** Telemetry inside a batch: each step still emits its own `tool.call` / `tool.result` (PAR-06 preserves M2 schema). The `batch.end` wrapper carries `ok_count` and `err_count` totals so JSONL consumers can spot partial batches without scanning every nested event.

### Interrupt + cancel-point discipline (extends T1)

- **D-06:** T1 defined two cancel-aware points (iteration boundary + before each tool dispatch). T2 adds a **third**: inside `asyncio.gather`. When `CancelledError` propagates into the gather, in-flight sibling read coros cancel (httpx-equivalent cleanup falls to tool implementations; `fs_read` is local-disk so cancel is near-instant). The loop's existing `except asyncio.CancelledError` (T1 D-Interrupt path in `_run_turn_exec`) finalizes the recorder with `exit_reason = "interrupt"`. Partial batch results captured in the `IterationRecord` for the canceled iteration.
- **D-07:** "Cancel siblings" is preferred over "let batch finish" because batches may include `fs_grep` / `voss_check` / `shell_run`-equivalent shell-shaped reads (e.g., `git_status`, `git_diff`) that are NOT cheap — letting them run after user-visible interrupt violates T1's "cancel must finalize ≤100ms" criterion.

### `BatchRecord` schema location

- **D-08:** `BatchRecord` nests inside T1's `IterationRecord.batches: list[BatchRecord]`. Each batch belongs to the iteration that produced it. Mirrors T1's iteration-scoped capture pattern. `RunRecord` top-level shape unchanged (no new top-level field), preserving M2 `voss resume` round-trip behavior verified by T1's "old fixture parses" CI test (same test absorbs T2 with an additional empty-batches assertion).
- **D-09:** Minimum `BatchRecord` fields (planner picks final shape): `batch_index: int` (monotonic within iteration), `step_indices: list[int]` (Plan.steps positions), `parallel_count: int`, `wall_clock_ms: int`, `ok_count: int`, `err_count: int`. Mutating singletons do NOT produce a `BatchRecord` (per SPEC PAR-06: "Mutating singletons emit NO `batch.start` / `batch.end`"). `batches` defaults to `[]`; serializes empty for pre-T2 records.

### Tool surface migration

- **D-10:** Keep both `fs_edit` and `fs_edit_many` registered. Two registered tools in `make_toolset`. `fs_edit` (single old/new) stays unchanged for one-shot edits; `fs_edit_many` is the multi-edit primitive. Zero migration risk. **Rationale (versus T1's hard-delete of `_substitute_placeholders`):** `_substitute_placeholders` was internal plumbing; `fs_edit` is a model-facing tool whose existence the LLM already learned. Hard-deletion would require agent-prompt churn for marginal surface reduction. Two tools = one extra registry entry.
- **D-11:** Agent prompt / `PLAN_LOOP_SYSTEM` (introduced by T1) gets a short paragraph teaching: (a) read-only steps may run in parallel; (b) `fs_read_many` returns one bundle for N paths; (c) `fs_edit_many` is atomic single-file multi-edit. Planner writes the exact prose. Constraint: must not change Plan schema (no new fields on `ToolCall`).

### `fs_read_many` bundle shape

- **D-12:** Bundle format is the SPEC-locked `=== {path} ===\n{section}\n\n` per section.
- **D-13:** Per-file size cap: **30KB**, truncate with `<truncated, total {N} bytes>` suffix. Mirrors `shell_run`'s 4KB cap pattern but tuned 7.5x larger because read-many is the read-many primitive and bundling 6 files at 4KB each is too tight. Planner picks final cap if 30KB proves wrong in benchmark.
- **D-14:** Path validation: each path runs through `jail_path(cwd, path)` independently before bundle assembly. A path that escapes the jail becomes `<error: path outside cwd: {path}>` in its slot — does NOT abort the whole call. Consistent with partial-result semantics (D-12 / SPEC PAR-04).

### Concurrency cap + config

- **D-15:** `harness.toml` `[agent]` section is **locked** here for T1 + T2: `[agent] max_iterations = 8` (T1) co-locates with `[agent] max_parallel_reads = 8` (T2). T1's CONTEXT marked this as Claude's Discretion — T2 pins it. Planner extends `voss/harness/config.py` to parse `[agent]` block with int values (loader is currently `[harness]`-only with string values — see `_HARNESS_BLOCK` and `_KV` regex).
- **D-16:** Loader extension shape (planner picks): new function `load_agent_config() -> dict[str, int]` parallel to `load_harness_config()` OR refactor into a generic section parser. Constraint: must not break the existing `[harness] preferred_model` consumer.
- **D-17:** Semaphore scope: **per-batch**. Each multi-step batch creates `asyncio.Semaphore(cap)` at batch entry; semaphore is GC'd after gather completes. No process-wide semaphore (would require cross-turn coordination not needed for current scope).

### `BatchInvariantError` placement

- **D-18:** New exception class lives in `voss/harness/agent.py` alongside `_run_step_loop` (the only raise site). Planner picks whether to subclass `Exception` directly or to introduce a domain hierarchy (e.g., `HarnessError → BatchInvariantError`). Constraint: error must surface in `RunRecord.exit_reason = "batch-invariant"` — T1's exit_reason enum gains this fifth value (additive to T1's `done|max-iter|budget|interrupt`).

### Perf benchmark fixture

- **D-19:** Stub tools sleep deterministically. Suggested: 6 stub-tools each `await asyncio.sleep(0.1)` (100ms). Serial baseline ≈ 600ms; parallel batch ≈ 100ms (one round-trip width). Asserts parallel ≤ 60% × serial. Planner picks exact sleep duration; constraint is ratio not milliseconds. Runs in `tests/perf/` so it's segregable from unit suite (CI may run a subset).

### Claude's Discretion (planner picks; constraints noted)

- **`DiffDecision.batch_mode` collapse mechanism** — D-03 forks: read M9-05's current `DiffDecision` shape (`voss/harness/tui/widgets/diff_modal.py`) and either reuse per-hunk verdicts (collapse in tool function) or add `batch_mode` flag at modal layer. Constraint: any hunk rejected → batch denied. M9-05's existing tests must still pass.
- **Exception → result-string formatting in gather** — D-04 says `<error: {exc}>`. Planner picks whether to use `repr(exc)`, `str(exc)`, or a custom stringifier. Constraint: must be redacted via `telemetry.redact_tool_args` equivalent for sensitive paths.
- **`BatchRecord` exact pydantic field set + timestamps** — D-09 lists minimum fields. Planner decides whether to add `started_at` / `ended_at` (datetime) versus just `wall_clock_ms` (int). Constraint: schema-additive, pre-T2 records round-trip.
- **`tool.call` event `batch_index` annotation** — Whether per-step `tool.call` events inside a batch carry a `batch_index` field for JSONL grouping. Trade-off: simpler downstream parsing vs. mutating an existing event schema. Planner picks; constraint: M2 RunRecord ledger unchanged.
- **Agent-prompt prose for batch semantics** — D-11 prose. Planner writes. Constraint: must NOT change `Plan` / `ToolCall` schema.
- **Config loader refactor shape** — D-16 fork. Generic section parser vs. per-section function. Constraint: `[harness] preferred_model` consumer still works.
- **`fs_edit_many` return-string format** — SPEC requires it report line delta and name offending index on failure. Exact prose (e.g., `"edited {path} ({sign}{delta} lines, {n} hunks)"` versus alternatives) is planner discretion.
- **Migration of existing `_run_step_loop` callers** — `_run_step_loop` is called at `agent.py:444` from `_run_turn_exec`. T1 already restructures that caller into a while-loop body. T2 changes `_run_step_loop`'s signature/semantics. Sequencing decision (T2 depends on T1-built loop) lives in plan-phase wave ordering, not here.
- **`BatchInvariantError` exception hierarchy** — D-18 fork. Planner picks single-class versus hierarchy.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract

- `.planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md` — **Locked requirements** (PAR-01..06), boundaries, constraints, 22 acceptance criteria. MUST read before planning.
- `.planning/ROADMAP.md` (Phase T2 section, lines 752–779) — Goal, requirements, success criteria, cross-cutting constraints.
- `.planning/notes/daily-driver-punch-list.md` (T2 section + sequencing rationale) — Why this phase exists, T1→T2 sequencing, P0 gap categorization.

### Inherited prior-phase context (MUST read)

- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md` — T1 carves parallel tools out into T2 and locks the iteration loop T2 plugs into. Cancel-point discipline, RunRecord/IterationRecord schema, exit_reason enum all extend from T1.
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md` — T1's implementation decisions, especially: while-loop body for `_run_turn_exec`, `IterationRecord` shape, cancel discipline, `harness.toml [agent]` slot (T2 pins this).
- `.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md` (lines covering M9-05) — `DiffModal`, `Hunk`, `DiffDecision` API. T2's `fs_edit_many` plugs into the existing M9-05 modal.
- `.planning/phases/M2-project-cognition/M2-CONTEXT.md` — `RunRecord` schema, `voss resume` semantics, ledger format. T2 additions must round-trip pre-T2 records.
- `.planning/phases/M1-harness-happy-path/M1-CONTEXT.md` (D-06 tool classification) — `ToolEntry.is_mutating` is data at registration, not name-pattern. T2 partitioner relies on this invariant.

### Runtime + harness code to modify

- `voss/harness/agent.py` — `_run_step_loop` (line 507) gets partition rewrite. `BatchInvariantError` class added here. Existing per-step `try/except` (line 567) becomes the inner body of the gather coros.
- `voss/harness/tools.py` — `make_toolset` (line 44) gains `fs_edit_many` and `fs_read_many` registrations. Both new tools defined inline. `ToolEntry` (line 14) unchanged. Existing `fs_edit` (line 114) + `fs_read` (line 52) preserved.
- `voss/harness/permissions.py` — `PermissionGate.check` (line 169) unchanged; per-step gate fires for every step including batched. `_render_diff_preview` (line 209) stays single-edit-only (D-01).
- `voss/harness/tui/widgets/diff_modal.py` — `DiffModal` (line 34), `Hunk`, `DiffDecision` consumed by `fs_edit_many`. Verify whether `DiffDecision` returns per-hunk verdicts or whole-batch verdict (drives D-03 fork).
- `voss/harness/tui/renderer.py` — `Renderer.show_diff_modal` (line 306) is the call site for `fs_edit_many`'s N-hunk dispatch.
- `voss/harness/session.py` — `RunRecord` and T1's `IterationRecord` (added in T1). Adds `IterationRecord.batches: list[BatchRecord] = []` + new `BatchRecord` pydantic class.
- `voss/harness/recorder.py` — `RunRecorder` (line 28). Adds `begin_batch` / `end_batch` capture API parallel to T1's `begin_iteration` / `end_iteration`. `observe` (line 53) per-step path unchanged.
- `voss/harness/config.py` — `load_harness_config` (line 32) currently `[harness]`-only. Add `load_agent_config()` or generic section parser for `[agent]` (D-15, D-16). T1 already needs this for `max_iterations`; T2 piggybacks for `max_parallel_reads`.
- `voss/harness/telemetry.py` — emits `batch.start` / `batch.end` events. Reuses existing `emit(...)` machinery; no schema changes to the emit function itself.

### Tests / fixtures

- `tests/harness/test_step_loop.py` (or equivalent) — partition fixtures: `[read_A, write_B, read_C, read_D]` → 3 batches in order. Synthetic mutating-in-batch test for `BatchInvariantError`.
- `tests/harness/test_fs_edit_many.py` — new file. 4 fixtures per SPEC PAR-03 acceptance criteria (all-pass / non-unique / not-found / modal-reject).
- `tests/harness/test_fs_read_many.py` — new file. 4 fixtures per SPEC PAR-04 (all-readable / missing / duplicate / empty).
- `tests/harness/test_telemetry_batches.py` — `batch.start` / `batch.end` event assertions, monotonic batch_index, mutating-singleton emits no wrapper.
- `tests/perf/test_parallel_read_speedup.py` — new directory + file. Stub-timed 6-read benchmark. Default cap = ≤60% serial; cap=1 forces fail (sanity).
- `tests/harness/test_session_roundtrip.py` (T1 fixture from CI gate) — extends with empty-batches assertion for pre-T2 record loading.

### Config

- `~/.config/voss/config.toml` — `[agent]` section with `max_parallel_reads = 8` and (T1) `max_iterations = 8`. Range validation 1–32 inclusive; out-of-range falls back to default with warning (config-load-time log, not runtime warn).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ToolEntry.is_mutating`** (`tools.py:14`) — already classifies every registered tool at registration. Partitioner reads this directly; zero new classification machinery needed.
- **`asyncio.gather` + `asyncio.Semaphore`** — stdlib primitives. Idiomatic Python; no third-party dep.
- **`DiffModal` + `Hunk` + `DiffDecision`** (`voss/harness/tui/widgets/diff_modal.py:34`) — M9-05 ships per-hunk approval UI. `Renderer.show_diff_modal(hunks, timeout_s=300.0)` (`renderer.py:306`) is the call surface `fs_edit_many` invokes.
- **`jail_path(cwd, path)`** (`voss/harness/sandbox.py`) — same path-jail used by `fs_read` / `fs_edit` / `fs_write`. `fs_read_many` and `fs_edit_many` reuse it per-path.
- **Per-step `<error: {exc}>` string convention** (`agent.py:567`) — existing pattern for tool-call exception capture. `asyncio.gather(return_exceptions=True)` results fold into this shape.
- **`telemetry.emit(event, level, data=...)`** — existing event emitter. `batch.start` / `batch.end` plug in with no helper changes.
- **`RunRecorder.observe(name, args, result, ok=...)`** — per-step capture API (`recorder.py:53`). Batched steps still call `observe` per step; new `begin_batch` / `end_batch` wrap a batch in the same recorder.

### Established Patterns

- **Classification at registration, not by name** (M1 D-06) — `is_mutating` is a data field on `ToolEntry`, never inferred from tool name. T2 partitioner depends on this invariant.
- **Atomic tools** (T1 D-Interrupt) — Tools complete-or-fail-atomically. `fs_edit_many`'s "validate all, write once" matches this. No mid-tool rollback mechanism required.
- **Additive-only schema migrations** (M2 + T1) — `RunRecord` additions are Optional + default; pre-version records round-trip via pydantic. T2 adds `IterationRecord.batches` under the same constraint.
- **Per-step recorder observation** (`agent.py:597`) — every successful or failed step emits `recorder.observe(...)`. Batched steps preserve this (gather doesn't collapse observation).
- **Truncation marker convention** (`shell_run` at `tools.py:96`) — `<truncated, total {N} bytes>` is the existing format. `fs_read_many` per-file cap reuses this string.

### Integration Points

- **T1's while-loop body** wraps T2's partitioned `_run_step_loop`. T2 ships AFTER T1 in the wave order (planner enforces).
- **T1's `IterationRecord.tool_results`** captures per-step results regardless of batched vs singleton. T2's `IterationRecord.batches` is additional structural metadata, not a replacement.
- **T1's cancel discipline** extends: T2 adds the `asyncio.gather` as a third cancel-aware point.
- **M9-05's `DiffModal.hunks: list[Hunk]`** is already a list parameter — multi-hunk is the existing API, not a new one. `fs_edit_many` is the first tool to populate >1 hunk.
- **`harness.toml [agent]` section** — T1 needs `max_iterations`, T2 needs `max_parallel_reads`. Loader extension lands once (T2 owns it per the wave dependency).

</code_context>

<specifics>
## Specific Ideas

- **Bundle separator format** — `=== {path} ===\n{section}\n\n` (locked in SPEC PAR-04 and D-12). Exact equals signs and double-newline trailer matter for deterministic parsing.
- **Truncation marker** — `<truncated, total {N} bytes>` reused from `shell_run` (D-13). Don't invent a new marker string.
- **Cap value 30KB** — D-13. Picked 7.5× `shell_run`'s 4KB. Justification: read-many is the bulk-read primitive; 6 files × 5KB average is realistic. Planner may re-tune after benchmark.
- **`exit_reason = "batch-invariant"`** — fifth value joining T1's `done|max-iter|budget|interrupt`. Hyphenated, lowercase (matches T1 convention).
- **Semaphore creation site** — at the start of each multi-step batch, inside the partition scheduler. Not module-global, not session-scoped (D-17).
- **Mutating-singleton no-wrapper invariant** — single-step batches (whether read or write) emit NO `batch.start` / `batch.end`. Telemetry consumers detect singleton vs batch by event presence, not by `parallel_count=1` inspection.

</specifics>

<deferred>
## Deferred Ideas

- **`fs_grep_many` / `fs_glob_many` batch primitives** — Captured during SPEC out-of-scope discussion. Worth doing if real plans show grep/glob fan-out; revisit after T2 ships and dogfood shows the pattern.
- **Dependency-graph partitioner** — Hoisting independent reads ahead of writes by inspecting `step_C.args` for references to `step_A`'s output. Big payoff, big complexity. Future phase if plan-author ordering proves consistently suboptimal.
- **Parallel write to disjoint paths** — Two writes to obviously non-conflicting paths. Future phase if measured benefit (likely small — writes are rare in plans).
- **Multi-file `fs_edit_many`** — `fs_edit_many(edits=[{path, old, new}])` cross-file shape. Future tool if real plans show coordinated multi-file edits as a common pattern.
- **Mid-batch incremental result streaming into T1's iteration messages** — Batch results currently delivered as one block to next iteration. Streaming could shave latency on slow batches; revisit after T1 streaming UX stabilizes.
- **`fs_edit_many` mid-batch partial rollback** — Surgical undo of individual edits within a batch. Rejected in favor of snapshot-then-write-once atomicity (simpler, sufficient for current scope).
- **Process-wide / session-wide parallel-read semaphore** — Cross-turn coordination of in-flight reads. Not needed at current scale; revisit if dogfood shows disk/network contention.
- **`/cost --by-batch` surface** — Batch-level cost aggregation in the cost slash command. Out for T2; T4 owns cost surface evolution.
- **BatchRecord persisted in `voss resume` replay context** — Currently `voss resume` ignores `batches` like it ignores T1's per-iter detail. Could be opt-in via `voss resume --replay-batches` in a future polish phase.
- **`harness.toml [agent]` discoverability via `voss config` slash** — Pinning the section here pre-empts T1's discretion item but doesn't auto-wire `voss config` enumeration; that lives in a polish phase.
- **Cap value re-tuning** — 30KB per-file cap (D-13) and 100KB total-bundle cap (rejected option) both worth re-evaluating after the benchmark fixture lands and real plans exercise the bundle width.

</deferred>

---

*Phase: T2-parallel-tools-multi-edit*
*Context gathered: 2026-05-15 via /gsd:discuss-phase (2 rounds, 8 questions)*
*Next step: /gsd:plan-phase T2*
