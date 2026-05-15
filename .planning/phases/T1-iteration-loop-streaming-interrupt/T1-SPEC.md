# Phase T1: Iteration Loop + Streaming + Interrupt — Specification

**Created:** 2026-05-15
**Ambiguity score:** 0.19 (gate: ≤ 0.20)
**Requirements:** 6 locked

## Goal

Replace the single-shot plan→execute→done flow in `_run_turn_exec` with a real agent loop that re-plans on tool results (max 8 iterations, configurable), streams provider tokens to TurnView as they arrive, and cancels cleanly on user interrupt — across both Anthropic and OpenAI providers.

## Background

Today `voss/harness/agent.py:305 _run_turn_exec` is single-shot:

1. One `provider.complete(... response_format=Plan)` call produces a Plan.
2. Confidence gate checks plan.confidence pre-execute (line 426) — low confidence returns a `/clarify` and exits.
3. `_run_step_loop` (agent.py:507) executes all plan.steps sequentially.
4. `_substitute_placeholders` (agent.py:601) wires step results into `plan.final_when_done` via `{step_N}` template tokens.
5. RunRecorder finalizes one record per turn. Returns `TurnResult`.

Provider surface (`voss/harness/providers.py:144`) is `complete()` only. `body["stream"] = False` is hardcoded at line 307. No `stream()` method exists for either Anthropic OAuth or OpenAI provider.

`tui/app.py:79 action_interrupt` is a placeholder `pass` — keystroke wired but unhandled.

Telemetry (`turn.start`, `provider.response`, `plan.parsed`, `note_turn`) emits at turn granularity. No iteration count, no per-iteration cost, no exit-reason field.

The gap: this is a "fancy autocomplete" loop. The agent can't react to tool results within a single turn. Long-horizon tasks (M5 golden #2 "rename-symbol") require the user to re-prompt repeatedly. Streaming first-token latency is bounded by full-completion time. Interrupt does nothing. This phase is the breaking behavior change that justifies v0.2.

## Requirements

1. **ITER-01 — Iteration loop**: `_run_turn_exec` becomes a while-loop.
   - Current: Single `provider.complete` call, single `_run_step_loop` execution, single return.
   - Target: while-loop iterates plan→execute→re-plan. Exits on (a) plan emits `done` sentinel, (b) iteration count reaches `harness.toml` `max_iterations` (default 8), or (c) `ContextScope` reports budget exhausted. Each iteration is a sub-record under the same `RunRecord` (preserves M2 schema for `voss resume`).
   - Acceptance: M5 golden task #2 (`rename-symbol`) completes in one `voss do` invocation without user re-prompting; pytest covers all three exit conditions with structured assertions on `RunRecord.iterations` and `RunRecord.exit_reason`.

2. **ITER-02 — Tool results feed back**: Prior iteration outputs flow into the next iteration's model context.
   - Current: `_substitute_placeholders` substitutes step results into a final string template at turn end; no result-aware re-planning.
   - Target: Each iteration's `provider.complete` (or `stream`) call receives prior iteration's plan + tool results in `messages`. `_substitute_placeholders` is deleted from the codebase (hard removal — no deprecated shim). Final string is built from the loop's exit-iteration plan, not from template substitution.
   - Acceptance: grep of `voss/` returns zero matches for `_substitute_placeholders`; pytest verifies iteration N+1 receives iteration N's tool_results in its messages payload.

3. **ITER-03 — Streaming for both providers**: Provider switches from `complete` to `stream` for the iteration loop; TurnView renders incremental deltas.
   - Current: `ModelProvider.complete` is the only method. `body["stream"] = False` hardcoded in `_payload`. TurnView renders only on full response.
   - Target: Both `AnthropicOAuthProvider` and `OpenAIProvider` gain an `async def stream(...) -> AsyncIterator[ProviderStreamEvent]` method. Anthropic uses SSE `messages` streaming; OpenAI uses chat-completions streaming. TurnView subscribes to stream events and renders text deltas live (cumulative buffer). `_run_turn_exec` calls `stream()` for iterations.
   - Acceptance: First visible token in TurnView appears ≤ 500ms after provider HTTP 200 (measured via injected `time.monotonic` mock in test); both providers pass a parity test against a recorded fixture stream; structured `Plan` extraction works on the final stream event.

4. **ITER-04 — Interrupt cancels turn**: `action_interrupt` cancels the in-flight asyncio task and produces a closed recorder entry.
   - Current: `tui/app.py:79 action_interrupt` is `pass`.
   - Target: TUI tracks the active turn's `asyncio.Task`; `action_interrupt` calls `task.cancel()`. The `_run_turn_exec` coroutine catches `CancelledError`, marks `RunRecorder` exit_reason = `"interrupt"`, finalizes the record, and surfaces `"interrupted"` text in the TurnView. Permission gate per-iter behavior unchanged — each tool call still goes through `PermissionGate` fresh on every iteration (no session-cached approvals).
   - Acceptance: Test triggers `action_interrupt` mid-stream; `RunRecord.exit_reason == "interrupt"` and recorder is finalized within 100ms of the interrupt call; no asyncio task leak after the cancel.

5. **ITER-05 — Confidence gate moves to loop-exit**: Mid-loop low confidence triggers another iteration, not `/clarify`.
   - Current: Confidence gate (`agent.py:426`) checks `plan.confidence < threshold` once, before any execution, and returns a clarify question.
   - Target: Confidence gate fires only on the loop's terminating iteration (the one that emits `done`). If a non-terminating iteration's plan has `confidence < threshold`, the loop continues to the next iteration — the agent is allowed to be tentative mid-loop. The terminating iteration's confidence below threshold still produces a clarify outcome.
   - Acceptance: Test fixture with three iterations where iter 1 and iter 2 have `confidence=0.40`, iter 3 (terminating) has `confidence=0.80` — outcome is `complete`, not `clarify`; second fixture where iter 3 has `confidence=0.30` — outcome is `clarify`.

6. **ITER-06 — Telemetry per-iteration**: Recorder captures iteration count, per-iteration cost, and exit reason.
   - Current: `telemetry.note_turn` records turn-level `cost_usd`, `outcome`, `step_count`, `tool_calls`, `total_tokens`. No iteration field.
   - Target: Telemetry emits one `iteration.start` and one `iteration.end` event per loop iteration with `iteration_index`, `cost_usd`, `prompt_tokens`, `completion_tokens`. `note_turn` gains `iteration_count` and `exit_reason` (one of `"done"`, `"max-iter"`, `"budget"`, `"interrupt"`). `RunRecord` persists the same fields.
   - Acceptance: pytest parses telemetry JSONL after a 3-iteration turn and asserts exactly 3 `iteration.end` events with monotonic `iteration_index`; `note_turn` payload includes `iteration_count=3` and `exit_reason="done"`; all four exit_reason values reachable via dedicated fixtures.

## Boundaries

**In scope:**
- `_run_turn_exec` while-loop with three exit conditions (done / max-iter / budget).
- Hard deletion of `_substitute_placeholders` and all call sites.
- `stream()` method on both `AnthropicOAuthProvider` and `OpenAIProvider`.
- TurnView incremental-delta rendering.
- `action_interrupt` cancellation wired to in-flight asyncio task with recorder finalization.
- Confidence gate semantics moved from per-turn to per-loop-exit.
- Per-iteration telemetry + `exit_reason` on `note_turn` and `RunRecord`.
- `harness.toml` knob: `agent.max_iterations` (default 8).
- pytest coverage for all 6 ITER requirements + exit-reason matrix.

**Out of scope:**
- Parallel tool execution within a single iteration — T2 territory (`PAR-01..04` partitions `_run_step_loop`).
- Prompt caching (`cache_control: ephemeral`) — T4 (`CACHE-01..04`); ITER-03 stream payload format must remain cache-compatible but does NOT add `cache_control` markers in this phase.
- Session-cached permission approvals — explicitly rejected; per-iter fresh permission check stays.
- New telemetry sinks / dashboards — only the JSONL event stream gains fields.
- Cost surface changes (`/cost --by-model`) — T4 (CACHE-03) owns.
- `record_run` LLM-judged summary call frequency — stays once per turn at loop exit (not per iteration); ITER-06 telemetry is separate from `record_run`'s semantics.
- MultiPlan / branching execution — single linear iteration chain only.
- Stream backpressure / token rate limiting in TurnView — render every delta, no throttling.

## Constraints

- Each loop iteration is a sub-record under one `RunRecord` (not N `RunRecord`s). `voss resume` compatibility with M2 `RunRecord` schema is non-negotiable; schema additions (iteration_count, exit_reason) are additive only.
- `_substitute_placeholders` is fully deleted — grep gate in CI rejects re-introduction.
- `max_iterations` default = 8. Hit-cap produces a structured "halted: max-iter" `final` string, not a `RuntimeError`.
- Stream events must surface the structured `Plan` parse on the terminating event (Anthropic `tool_use` for `submit_response`; OpenAI tool_call delta accumulation) — parser cannot regress.
- TurnView delta render must be additive-only (cumulative append) — no in-place edits, no scroll jumps.
- Interrupt must close `RunRecorder` even if the cancel arrives between iterations.
- Permission gate runs per tool call per iteration (no caching) — no behavior change here, just an explicit invariant.

## Acceptance Criteria

- [ ] `_run_turn_exec` is a while-loop that exits on `done`, `max-iter`, or `budget`.
- [ ] Iteration N+1 receives iteration N's plan + tool_results in its `messages` payload (verified via pytest).
- [ ] `grep -r _substitute_placeholders voss/` returns zero matches.
- [ ] `AnthropicOAuthProvider.stream()` and `OpenAIProvider.stream()` both exist and pass a recorded-fixture parity test.
- [ ] First TurnView token visible ≤ 500ms after provider HTTP 200 in a measured test.
- [ ] `action_interrupt` cancels the active task, sets `RunRecord.exit_reason = "interrupt"`, finalizes recorder within 100ms.
- [ ] Confidence < threshold on a non-terminating iteration does NOT trigger clarify; on the terminating iteration it DOES.
- [ ] Telemetry JSONL contains one `iteration.end` event per loop iteration, with monotonic `iteration_index`.
- [ ] `note_turn` and `RunRecord` carry `iteration_count` and `exit_reason ∈ {"done","max-iter","budget","interrupt"}`.
- [ ] `harness.toml` `agent.max_iterations` defaults to 8 and is honored at runtime.
- [ ] M5 golden task #2 (`rename-symbol`) completes in one `voss do` without user re-prompt.
- [ ] Max-iter cap produces a final string containing `"halted: max-iter"` — not a `RuntimeError`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                |
|--------------------|-------|------|--------|------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Streaming scope + provider scope locked              |
| Boundary Clarity   | 0.72  | 0.70 | ✓      | Out-of-scope vs T2/T4 explicit; perm scope locked    |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Hard removal + schema additive-only locked           |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 12 pass/fail checkboxes + 4 quantitative thresholds  |
| **Ambiguity**      | 0.19  | ≤0.20| ✓      | Gate passes after round 1                            |

## Interview Log

| Round | Perspective    | Question summary                       | Decision locked                                                       |
|-------|----------------|----------------------------------------|-----------------------------------------------------------------------|
| 0     | (Scout)        | What exists today vs T1 goal?          | Single-shot loop; no stream(); action_interrupt is `pass` stub        |
| 1     | Researcher     | Stream provider scope                  | Both Anthropic + OpenAI gain stream() in T1                           |
| 1     | Boundary Keeper| `_substitute_placeholders` removal     | Hard removal; grep-gate in CI                                         |
| 1     | Boundary Keeper| Per-iter permission gate semantics     | Per-iter fresh permission check; no session-cached approvals          |

---

*Phase: T1-iteration-loop-streaming-interrupt*
*Spec created: 2026-05-15*
*Next step: /gsd:discuss-phase T1 — implementation decisions (stream event shape, TurnView buffer, interrupt-task tracking strategy)*
