---
phase: T1-iteration-loop-streaming-interrupt
plan: 05
status: complete
completed_at: 2026-05-15
commits:
  - 3163173 — feat(T1-05): implement iteration loop system and serialization for replay (helpers + tests)
  - 45f89da — feat(T1-05): implement iteration loop with streaming and plan management (rewrite + renderers + test updates)
---

# T1-05 Summary — Iteration loop + renderer streaming

## Files changed

- `voss/harness/agent.py` — added PLAN_LOOP_SYSTEM + helpers + `HALTED_*` constants; rewrote `_run_turn_exec` as a while-loop over `provider.stream()`; deleted `_substitute_placeholders` (~1054 lines total).
- `voss/harness/render.py` — added `stream_delta` + `finalize_stream` to Renderer Protocol and to TtyRenderer / PlainRenderer / JsonRenderer (~429 lines total).
- `voss/harness/tui/renderer.py` — added `stream_delta` + `finalize_stream` forwarding to TurnView via `_safe` + `_post` (~387 lines total).
- `voss/harness/agent/loop.voss` + `voss/harness/agent/reviewer.voss` — removed `_substitute_placeholders` imports + use; `review()` passes `final_when_done` through verbatim (matches the iteration loop's "model produces realized final" contract).
- `tests/harness/test_agent_loop_helpers.py` — 13 helper tests (constants, `_compose_loop_system`, `_build_iter_rider`, `_serialize_iter_for_replay`, `_is_done_plan`).
- `tests/harness/test_agent_loop.py` — 10 iteration-loop tests covering all 3 non-interrupt exit_reasons, replay-into-next-iter messages, confidence gate timing, telemetry emissions, and `_substitute_placeholders` hard-removal assertion.
- `tests/harness/test_renderer_streaming.py` — 10 renderer + telemetry-passthrough tests.
- `tests/harness/test_agent_integration.py` — FakeProvider extended with `stream()`; placeholder-substitution assertions retargeted to `tool_results` + `run.iterations[0].tool_results`.
- `tests/harness/test_voss_loop_parity.py` — FakeProvider extended with `stream()`; `test_python_and_compiled_backends_agree` xfail-marked (v0.2 break documented).
- `tests/harness/test_voss_md_injection.py` + `tests/harness/test_cognition.py` + `tests/harness/test_extensions.py` — providers gained `stream()` so existing fixtures continue exercising the new loop.
- `tests/harness/tui/baseline/plain_baseline.txt` — regenerated via `VOSS_CAPTURE_BASELINE=1` (T1-05 stream rendering is the new baseline).
- `tests/harness/tui/test_plain_parity.py` — CANNED_PLAN gained `final_when_done` so `_is_done_plan` recognizes the terminating iter.

## Removed call sites of `_substitute_placeholders`

Exactly one in-function call: `voss/harness/agent.py` line ~468 of the pre-T1 `_run_turn_exec` body. The function definition itself (pre-T1 line 601) is deleted alongside.

`grep -rn "_substitute_placeholders" voss/` returns ZERO matches. CI grep gate satisfied.

## PLAN_LOOP_SYSTEM exact text

```
You are Voss, a coding agent running in a terminal. You operate in an
iterative plan-then-execute-then-re-plan loop.

You receive a task and a list of tools. On each iteration:
- Review prior iterations' plans and tool results (in messages above).
- Produce a Plan: rationale, sequential tool calls for THIS iteration,
  self-rated confidence (0.0-1.0), and the final answer ONCE you are
  done.

To signal "done", return a Plan with:
  - steps: []  (empty list)
  - final_when_done: <the user-facing answer, fully realized, NO
    placeholders like {{step_0}}>

If you still need tool calls, return a non-empty `steps` list and the
loop will execute them and call you again on the next iteration.

You have at most {max_iterations} iterations. Use them frugally.

Confidence rubric:
- 0.95+: trivial, deterministic, single-step
- 0.80-0.94: clear path, normal risk
- 0.60-0.79: ambiguity present; consider asking — but ONLY on the done
  iteration. Mid-loop low confidence is fine; just keep iterating.
- below 0.60 on the done iteration: populate open_question and leave
  steps empty.

Only call tools from the provided list.
```

`{max_iterations}` is filled via `str.replace`, not f-string, so the cacheable prefix stays stable for future T4 prompt caching.

## Messages-replay format

One (assistant, user) pair per prior iteration:

- **Assistant**: JSON-serialized prior plan with keys `rationale`, `steps`, `final_when_done`.
- **User**: `"Tool results for iteration {i}:\n- {name}({redacted_args}) -> {result_truncated_400}\n..."` — args redacted via `telemetry.redact_tool_args` so secrets do not leak into the replay chain.

The per-iter rider message (separate system message) is rebuilt every iter; the static `PLAN_LOOP_SYSTEM`-derived sys_prompt stays cacheable.

## telemetry.note_turn — zero source diff

`note_turn(**fields)` already accepts arbitrary kwargs (telemetry.py:80). T1-05 calls add `iteration_count` + `exit_reason` to the meta dict without any signature change. Test `test_note_turn_accepts_iteration_count_and_exit_reason` in `test_renderer_streaming.py` pins this passthrough.

## Exit-reason coverage

| Path        | Trigger                                                          | Final string                  |
|-------------|------------------------------------------------------------------|-------------------------------|
| `done`      | `_is_done_plan(plan)` AND `plan.confidence >= threshold`         | `plan.final_when_done`        |
| `done` (clarify) | `_is_done_plan(plan)` AND `plan.confidence < threshold`     | `plan.open_question`          |
| `max-iter`  | `iteration_index` reaches `cfg.max_iterations`                   | `"halted: max-iter"` (exact)  |
| `budget`    | `ctx.token_budget and ctx.tokens_used >= ctx.token_budget`       | `"halted: budget"`            |
| `interrupt` | T1-06 territory — not implemented in this plan                   | —                             |

## Deviations from plan

- **Test rewrites beyond plan scope**: SPEC ITER-02 hard-removes `_substitute_placeholders`. Several existing tests (`test_agent_integration.py::test_step_placeholder_substitution`, the `{{step_N}}` assertions in adjacent tests) were written against that pre-T1 feature. Retargeted assertions onto `tool_results` + `run.iterations[0].tool_results` (the structured replacement). Renamed `test_step_placeholder_substitution` to `test_tool_results_surface_in_run_record`.
- **`test_voss_loop_parity.py::test_python_and_compiled_backends_agree` is xfail**: SPEC explicitly frames T1 as the "breaking behavior change that justifies v0.2." The compiled `.voss` harness is still single-shot; python backend is now iteration-loop. M4 parity will be re-recorded in a follow-up against the new loop semantics.
- **`plain_baseline.txt` regenerated**: stream rendering adds `…` lines and the iteration banner. Locked baseline updated via `VOSS_CAPTURE_BASELINE=1` (the test's documented refresh path).
- **`async def stream` grep returns 3** (Protocol + 2 impls) — unchanged from T1-02 / T1-03; consistently documented.

## Verification

```
uv run pytest tests/harness/                          # 677 passed, 2 skipped, 1 xfailed
grep -rn "_substitute_placeholders" voss/             # ZERO matches
grep -F 'halted: max-iter' voss/harness/agent.py      # >= 1 match
grep -nE 'exit_reason\s*=\s*"(done|max-iter|budget|interrupt)"' voss/harness/agent.py
                                                       # 3 of 4 reachable; interrupt is T1-06
```
