# Phase T1: Iteration Loop + Streaming + Interrupt — Discussion Log

**Discussed:** 2026-05-15
**Mode:** /gsd:discuss-phase (default, batched 3 questions per area)
**Areas covered:** 4 / 4 (all selected by user)

This log is for human reference (audits, retrospectives). Downstream agents read SPEC.md + CONTEXT.md, not this file.

---

## Area selection

**Question:** Phase T1: requirements locked by SPEC.md — discussing implementation only. Which gray areas to dig in on?

**Options presented:**
- Stream event shape
- Done signal mechanism
- Iteration sub-record schema
- Interrupt + mid-iter cleanup

**Selected:** All 4.

---

## Area 1 — Stream event shape

| Question | Options | Selection |
|---|---|---|
| Stream event type — normalized across providers or raw passthrough? | Normalized typed events / Raw chunks / Hybrid (raw + parsed) | **Normalized typed events** |
| When does structured `Plan` parse fire during a stream? | On terminating event / Incremental field-by-field / Two-phase (plan call then exec) | **On terminating event** |
| Stream method signature on ModelProvider? | `async def stream(...) -> AsyncIterator[Event]` / Callback-based | **AsyncIterator[Event]** |

**Notes:** Provider-agnostic event shape (`ProviderStreamEvent` union) keeps agent loop simple. Plan parses from accumulated `ToolUseDelta` chunks at stream end — mid-stream partial-JSON parsing rejected as brittle.

---

## Area 2 — Done signal mechanism

| Question | Options | Selection |
|---|---|---|
| How does agent signal loop-exit — what does `done` look like in Plan? | Empty steps + final_when_done set / New `Plan.is_terminal: bool` / Distinct `FinalAnswer` model | **Empty steps + final_when_done set** |
| System prompt for done semantics — how loud about iteration? | Explicit iteration prompt / Minimal change / Per-iter dynamic context | **Explicit iteration prompt** |
| M5 eval / existing-fixture compatibility — pre-T1 plans that always had steps? | Hard break — update fixtures / Compat layer / Out of T1 scope | **Hard break — update fixtures** |

**Notes:** Reuse existing `Plan` schema — no new field, no migration. New `PLAN_LOOP_SYSTEM` block teaches the model the iteration semantics. M5 golden fixtures re-recorded in a follow-up commit; v0.2 minor bump justifies the break.

---

## Area 3 — Iteration sub-record schema

| Question | Options | Selection |
|---|---|---|
| RunRecord schema shape for per-iteration data? | `iterations: list[IterationRecord]` field / Flatten + iteration-tagged events / Sub-record file per iter | **`iterations: list[IterationRecord]` field** |
| Schema versioning approach — RunRecord pydantic model has version field? | Additive Optional only / Bump `schema_version` field / Defer to existing migration path | **Additive Optional only** |
| `voss resume` behavior on T1 records? | Replay exit-plan only / Replay all iterations as context / Replay last N iterations | **Replay exit-plan only** |

**Notes:** New nested list captures per-iter detail; top-level RunRecord fields stay for the exit-plan (preserves M2 voss-resume schema). Additive Optional drift risk mitigated by a single CI test on old-fixture round-trip.

---

## Area 4 — Interrupt + mid-iter cleanup

| Question | Options | Selection |
|---|---|---|
| Where TUI tracks the active turn `asyncio.Task`? | App-level `self.active_turn_task` / Per-screen registry / Workers + Textual `worker.cancel` | **App-level `self.active_turn_task`** |
| Mid-iter tool-call state on cancel — partial fs_edit / shell already mid-flight? | Tools are atomic — no cleanup needed / Best-effort cleanup hook / Hard cancel + recorder warning | **Tools are atomic — no cleanup needed** |
| Stream cancellation — graceful HTTP close or hard cancel? | Graceful httpx aclose() / Hard task cancel | **Graceful httpx aclose()** |

**Notes:** Cancel-points have exactly two: iteration boundary + before each tool dispatch. Tools atomic by design (fs_edit_many T2, shell_run, fs_edit single-occurrence). Graceful aclose adds 10-50ms but stays under SPEC's 100ms interrupt criterion.

---

## Deferred ideas captured

- Mid-stream incremental Plan-field rendering (post-T1 polish).
- Tool finalize/cleanup callbacks (T5 background shell territory).
- Per-iter `record_run` summaries (signal-driven; reconsider after dogfood).
- `cache_control: ephemeral` markers on PLAN_LOOP_SYSTEM (T4).
- `voss resume --replay-iters` flag (future polish).
- Session-cached permission approvals (rejected for T1; may resurface separately).
- Configurable cancel-point granularity (not needed yet).
- M5 golden-fixture re-record (M5 follow-up commit).

## Claude's discretion items handed to planner

- Exact `Plan` parse delivery mechanism (synthetic terminal event vs. coroutine return).
- Anthropic SSE parser implementation (raw httpx decode vs. anthropic SDK helper).
- OpenAI streaming API choice (Responses vs. Chat Completions).
- `harness.toml` section name for `max_iterations` (`[agent]` vs. `[loop]`).
- Telemetry event names (`iteration.start` / `iteration.end` proposed).
- Confidence-gate placement inside the loop body.
- `PLAN_LOOP_SYSTEM` exact prose.
- Test fixture strategy for stream tests (recorded vs. stubbed).

---

*Phase: T1-iteration-loop-streaming-interrupt*
*Discussion: 2026-05-15*
