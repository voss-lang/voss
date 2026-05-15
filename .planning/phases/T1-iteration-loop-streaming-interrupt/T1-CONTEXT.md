# Phase T1: Iteration Loop + Streaming + Interrupt — Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**SPEC:** `T1-SPEC.md` — 6 requirements locked (ITER-01..06), ambiguity 0.19

<domain>
## Phase Boundary

Convert `_run_turn_exec` from single-shot plan→exec→done into a real agent loop that re-plans on tool results (max 8 iters, configurable), streams provider tokens to TurnView live, and cancels cleanly on user interrupt — across both Anthropic and OpenAI providers. This is the breaking behavior change that justifies v0.2. Requirements (WHAT) are locked by SPEC.md. This document captures HOW.
</domain>

<spec_lock>
## Locked Requirements (from SPEC.md)

Requirements ITER-01..06, Boundaries (in/out of scope), Constraints, and Acceptance Criteria are locked in `T1-SPEC.md`. Downstream agents MUST read SPEC.md before planning. This CONTEXT.md captures only implementation decisions — it does not duplicate or override SPEC.md.

Out-of-scope reminders that frequently leak in:
- Parallel tool execution within an iteration → T2 (`PAR-01..04`).
- `cache_control: ephemeral` markers on system prompt → T4 (`CACHE-01..04`).
- Session-cached permission approvals → explicitly rejected; per-iter fresh check stays.
- `/cost --by-model` surface → T4 (CACHE-03).
- Mid-iter partial-tool-state rollback → not built; tools stay atomic.
</spec_lock>

<decisions>
## Implementation Decisions

### Stream event shape

- **Normalized typed events** — Define a `ProviderStreamEvent` union in `voss/harness/providers.py`. Variants: `TextDelta(text)`, `ToolUseStart(name, id)`, `ToolUseDelta(id, partial_json)`, `ToolUseEnd(id)`, `Usage(prompt_tokens, completion_tokens, cost_usd)`, `Done(stop_reason)`. Both Anthropic SSE and OpenAI Responses-API streaming adapt to this. TurnView + agent loop consume one shape; provider branching stays inside provider classes.
- **Stream method signature:** `async def stream(self, *, messages, model, response_format, tools, temperature, max_tokens, timeout) -> AsyncIterator[ProviderStreamEvent]`. Caller uses `async for event in provider.stream(...)`. Composes natively with `asyncio.CancelledError` (graceful httpx `aclose()` on exit).
- **Structured `Plan` parse fires on the terminating event.** Provider accumulates `ToolUseDelta(submit_response, partial_json)` chunks during the stream. On `Done`, the accumulated JSON is parsed into a `Plan` instance and surfaced via a final synthetic event or return value (planner picks exact mechanism; both providers must agree). Mid-stream incremental field parsing is rejected — too complex, partial JSON brittle.
- **TurnView render** — Append-only via `RichLog.write` on every `TextDelta`. Reuses M9's existing `TurnView` (`voss/harness/tui/widgets/turn_view.py:18`). No in-place edits, no scroll jumps. Cumulative buffer kept in agent loop for plan-text accumulation; TurnView gets deltas.

### Done signal mechanism

- **Reuse existing `Plan` schema — no new field.** Loop exit condition: `plan.steps == [] AND plan.final_when_done is set`. The agent emits a "done" by returning an empty step list with the final answer populated. Keeps Plan pydantic model unchanged; no schema migration.
- **New `PLAN_LOOP_SYSTEM` system-prompt block** — Replaces the static `PLAN_SYSTEM` for iteration calls. Explicit text covers:
  - "You are in iteration N of max M. Prior iterations' plans + tool results are in messages."
  - "Emit `done` by returning a Plan with `steps: []` and a populated `final_when_done`."
  - "If you need more tool calls, return a non-empty `steps` list — the loop will execute them and call you again."
- **Per-iter dynamic context** — Iteration index, remaining budget, and prior-iter summaries injected as a system rider message per call (separate from the static `PLAN_LOOP_SYSTEM` block above). This keeps the cacheable prefix stable for future T4 caching.
- **M5 fixture compatibility = hard break.** Pre-T1 single-shot fixtures get re-recorded in M5 after T1 ships. Re-record is justified by v0.2 minor bump. No compat shim in T1.

### Iteration sub-record schema

- **`RunRecord` gains `iterations: list[IterationRecord]` field** (Optional, default empty list). `IterationRecord` shape:
  ```
  IterationRecord {
    index: int                      # 0-based
    plan: dict                      # serialized Plan
    tool_results: list[ToolResult]  # results from this iter's steps
    cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    started_at: datetime
    ended_at: datetime
    exit_reason: str | None         # only set on terminating iter; one of "done"|"max-iter"|"budget"|"interrupt"
  }
  ```
- **Top-level RunRecord fields stay** for the exit-plan (`plan`, `final`, `decisions`, `cost_usd` aggregated) — preserves M2 `voss resume` schema. Per-iter detail lives in `iterations[]`; aggregate stays at top level.
- **Additive Optional only — no `schema_version` bump.** New `iterations` field defaults to `[]`. Old records (pre-T1) round-trip cleanly through pydantic. Drift risk acknowledged; mitigated by a single CI test asserting `RunRecord(**old_fixture)` parses successfully.
- **`voss resume` behavior unchanged from v0.1** — replays exit-plan only (not the per-iteration chain). `iterations[]` is captured for inspection / telemetry / future surfaces but is not used for context restoration. Matches v0.1 mental model (one record → one resume context).

### Interrupt + mid-iter cleanup

- **App-level `self.active_turn_task: Optional[asyncio.Task]` on `VossApp`** (`voss/harness/tui/app.py`). Set when a turn starts; cleared on completion or cancel. `action_interrupt` does:
  ```python
  if self.active_turn_task and not self.active_turn_task.done():
      self.active_turn_task.cancel()
  ```
- **Tools are atomic — no cleanup hooks.** Cancel points only at iteration boundaries and immediately before each tool dispatch in `_run_step_loop`. Tools in-flight at cancel time run to completion or raise; partial state is not unwound. Justification: `fs_edit_many` is already all-or-nothing in T2 scope; `shell_run` completes-or-fails atomically; current `fs_edit` single-occurrence is already atomic. Loop checks `asyncio.current_task().cancelled()` (or relies on natural `CancelledError` propagation) at the two boundary points only.
- **Graceful httpx `aclose()` on stream cancel.** `provider.stream()` wraps the SSE/streaming body in `async with` so `CancelledError` triggers httpx context exit. Drops half-decoded SSE bytes cleanly. Accepts ~10-50ms extra latency before recorder finalize; still well within SPEC's 100ms criterion (target measured from `action_interrupt` invocation to `RunRecord.exit_reason = "interrupt"` being persisted).
- **Recorder finalization on cancel** — `_run_turn_exec` wraps its loop in `try/except asyncio.CancelledError` that:
  1. Sets the current iteration's `exit_reason = "interrupt"`.
  2. Calls `RunRecorder.finalize(...)` with the partial `iterations[]`.
  3. Surfaces `"interrupted"` text in the TurnView.
  4. Re-raises `CancelledError` so asyncio task state ends as cancelled (not swallowed).

### Claude's Discretion (planner picks; constraints noted)

- **Exact `Plan` parse delivery mechanism** — whether providers emit a synthetic terminal `ProviderStreamEvent.ParsedPlan(plan)` event or return the parsed `Plan` from the `stream()` coroutine post-iteration. Both work; both providers must agree. Constraint: the agent loop must NOT have to branch on provider.
- **Anthropic SSE parser implementation** — direct SSE byte stream decode vs. `anthropic` SDK's helper. Constraint: keep OAuth path working (`AnthropicOAuthProvider` uses raw httpx + OAuth refresh on 401; SDK adoption must not regress refresh).
- **OpenAI streaming format choice** — Responses API streaming vs. Chat Completions streaming. Constraint: must work with structured-output `text.format` schema (currently used in `_payload`).
- **`harness.toml` schema location** — `[agent]` section vs. `[loop]` section for `max_iterations = 8`. Constraint: must be discoverable via `voss config` and documented in M0/M1 docs.
- **Telemetry event names** — `iteration.start` / `iteration.end` are the proposed names; planner picks final names. Constraint: monotonic `iteration_index`, four exit reasons reachable per SPEC.
- **Confidence-gate placement in the loop body** — exact line in `_run_turn_exec` where the per-loop-exit gate fires. Constraint: only fires on the terminating iter (one with `steps: []`); never on non-terminating iters.
- **`PLAN_LOOP_SYSTEM` exact prose** — planner writes it. Constraint: explicit about iteration index, max cap, and the `steps:[] + final_when_done` done convention.
- **Test fixture strategy for stream tests** — recorded fixtures (replay SSE bytes) vs. fake provider stubs. Constraint: parity test must cover both providers against the same logical plan output.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract

- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md` — **Locked requirements** (ITER-01..06), boundaries, constraints, 12 acceptance criteria. MUST read before planning.
- `.planning/ROADMAP.md` (Phase T1 section, lines 685–719) — Goal, requirements, success criteria, cross-cutting constraints.
- `.planning/notes/daily-driver-punch-list.md` (T1 section + sequencing rationale, lines 66–115, 381–427) — Why this phase exists, sequencing relative to T2/T4, v0.2 ship lock rationale.

### Inherited prior-phase context

- `.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md` — TUI architecture this builds on. `TurnView` (M9-02), `action_interrupt` slot (M9-03), permission/diff modals (M9-05) are M9 deliverables T1 plugs into.

### Runtime + harness code to modify

- `voss/harness/agent.py` — `_run_turn_exec` (line 305), `_run_step_loop` (line 507), `_substitute_placeholders` (line 601 — **delete entirely**), `Plan` (line 153), `TurnResult` (line 220), `PLAN_SYSTEM` constant. This is the file the iteration loop lives in.
- `voss/harness/providers.py` — `ModelProvider` ABC, `AnthropicOAuthProvider.complete` (line 144), `OpenAIProvider.complete` (line 328), `_payload` `stream: False` hardcoded (line 307). Add `stream()` method + `ProviderStreamEvent` union here.
- `voss/harness/tui/app.py` — `action_interrupt` stub (line 79 — wire to `self.active_turn_task.cancel()`). Add `self.active_turn_task: Optional[asyncio.Task]` attribute.
- `voss/harness/tui/widgets/turn_view.py` — `TurnView` (line 18, `RichLog` subclass). Add a delta-write entry point if one doesn't already exist; otherwise call `write()` directly.
- `voss/harness/recorder.py` — `RunRecorder` (line 28). Grow per-iteration capture API (`begin_iteration` / `end_iteration`) and persist into `RunRecord.iterations`.
- `voss/harness/session.py` — `RunRecord` (line 71). Add `iterations: list[IterationRecord] = Field(default_factory=list)`. Define `IterationRecord` pydantic model.

### Config

- `voss/harness/config.py` (read during planning) — `harness.toml` config loader. Add `[agent] max_iterations = 8` default + getter.

### Tests / fixtures

- Existing tests touching `_run_turn_exec`, `_run_step_loop`, `_substitute_placeholders` — all need updates. `_substitute_placeholders` tests get deleted (grep-gate guards re-introduction).
- M5 golden fixtures (re-record post-T1 in a follow-up commit; not in T1 scope per "hard break" decision).

</canonical_refs>

<code_context>
## Reusable Assets

- **`TurnView` (M9-02)** is already a `RichLog` — append-only by design. Streaming text deltas drop straight into `write()`. No render rewrite needed.
- **`RunRecorder` (M2)** already brackets a turn; per-iteration substep API is an additive extension, not a redesign.
- **`PermissionGate`** stays unchanged. Per-iter fresh permission check (no session caching) means existing gate code is reused as-is from the `_run_step_loop` call site, just inside the new while-loop.
- **`ContextScope`** (around `provider.complete` in `_run_turn_exec`, line 384) — wraps token budget tracking. Move inside the while-loop body so each iter shares the same scope (accumulating budget across iters); budget exhaustion raises and triggers the `exit_reason="budget"` path.
- **OAuth refresh on 401** (`providers.py:172`) — the `stream()` method must preserve this behavior. Pattern: open stream, on 401 in the first event, refresh creds and reopen.

## Integration points

- M9 `action_interrupt` is wired (keystroke → method) but the method is `pass`. T1 only fills the method body + adds `self.active_turn_task` tracking.
- M9 `TurnView` exists; T1 adds a streaming-text consumer hook (or just calls `write()` directly from the agent loop with TUI access plumbed via existing renderer abstraction).
- M2 `RunRecord` voss-resume path stays. T1 adds inert per-iter detail that resume ignores.
</code_context>

<specifics>
## Specific Ideas

- **Cancel-point discipline** — Loop has exactly two cancel-aware points: (a) at iteration boundary (before next `provider.stream()` call), (b) immediately before each tool dispatch inside `_run_step_loop`. Anywhere else, cancellation is best-effort via natural `CancelledError` propagation. Documented invariant — planner enforces in tests.
- **Iteration index in telemetry is 0-based.** Matches Python convention; pytest assertions read more naturally. `iteration.end` events emit `iteration_index: 0` for the first iter.
- **"halted: max-iter" final string format** — exact string `"halted: max-iter"` (lowercase, hyphenated). Used by SPEC's acceptance criterion and the recorder's final-string surface. No other format permitted (planner can add prefix/suffix but the substring must match).
- **Exit reason precedence** — if cancel arrives during a stream that is already past `max_iterations` exhaustion semantically (rare race), exit_reason is `"interrupt"`, not `"max-iter"`. User-visible cancel wins over silent cap.

</specifics>

<deferred>
## Deferred Ideas

- **Mid-stream incremental Plan-field rendering** — Streaming `rationale` text and step labels as they parse. Worth ~UX win but partial-JSON parsing is brittle; revisit after T1 ships with terminal-event parse working.
- **Tool finalize/cleanup callbacks for non-atomic tools** — Useful when T5 ships background shell and long-running file ops. Not needed in T1.
- **Per-iter `record_run` LLM-judged summaries** — Currently `record_run` fires once per turn at loop exit. Per-iter summaries would aid debugging long loops; reconsider after telemetry signal from real usage.
- **Cache `cache_control: ephemeral` markers on PLAN_LOOP_SYSTEM + per-iter rider** — T4 territory. T1 keeps prompt structure cache-compatible (stable prefix) but does not add markers.
- **Replay-iterations-as-context mode for `voss resume`** — Could be a `voss resume --replay-iters` flag in a future polish phase. Out of T1.
- **Session-cached permission approvals to reduce mid-loop prompts** — Explicitly rejected for T1. May resurface as a separate phase if dogfood shows prompt fatigue.
- **Configurable cancel-point granularity** — Cancel between tool calls within a single iter's `_run_step_loop`. T1 cancels only at iter boundaries + before each tool dispatch; finer granularity not needed yet.
- **M5 golden-fixture re-record** — Lands in M5 follow-up commit, not in T1.

</deferred>

---

*Phase: T1-iteration-loop-streaming-interrupt*
*Context gathered: 2026-05-15 via /gsd:discuss-phase (4 areas, 12 questions)*
*Next step: /gsd:plan-phase T1*
