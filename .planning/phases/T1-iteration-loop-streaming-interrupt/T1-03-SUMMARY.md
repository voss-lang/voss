---
phase: T1-iteration-loop-streaming-interrupt
plan: 03
status: complete
completed_at: 2026-05-15
commits:
  - 6132c75 — feat(T1-03): implement Anthropic + OpenAI stream() bodies with SSE decode
---

# T1-03 Summary — Provider streaming bodies

## Files changed

- `voss/harness/providers.py` — replaced both T1-02 placeholder `stream()` bodies with concrete SSE-decode implementations.
- `tests/harness/test_anthropic_stream.py` — 4 tests (sequence + refresh-on-401 + 2 cancel paths).
- `tests/harness/test_openai_stream.py` — 3 tests (sequence + refresh + cancel).
- `tests/harness/test_provider_stream_parity.py` — 1 cross-provider parity test.
- `tests/harness/test_provider_stream_types.py` — removed obsolete T1-02 `TestPlaceholderBodiesRaise` (bodies are no longer placeholders).
- `tests/harness/fixtures/anthropic_stream_plan.sse` — base Anthropic SSE fixture.
- `tests/harness/fixtures/anthropic_stream_parity.sse` — parity fixture with locked Plan values.
- `tests/harness/fixtures/openai_stream_plan.sse` — base OpenAI Responses-API fixture.
- `tests/harness/fixtures/openai_stream_parity.sse` — parity fixture with locked Plan values.

## Body line counts

- AnthropicOAuthProvider.stream() — ~130 lines (incl. docstring, two async-with for refresh path).
- OpenAIOAuthProvider.stream() — ~104 lines (incl. docstring, two async-with for refresh path).

## SSE event-type → ProviderStreamEvent mapping

### Anthropic (Messages API stream=true)

| Anthropic `type`           | Branch                                                         | Emitted event(s)                              |
|----------------------------|----------------------------------------------------------------|-----------------------------------------------|
| `message_start`            | state only                                                     | —                                             |
| `content_block_start`      | block.type == "tool_use"                                       | `ToolUseStart(id, name)`                      |
| `content_block_delta`      | delta.type == "text_delta"                                     | `TextDelta(text)`                             |
| `content_block_delta`      | delta.type == "input_json_delta" (accumulate per `tu_id`)      | `ToolUseDelta(id, partial_json)`              |
| `content_block_stop`       | (only when a tool_use is open)                                 | `ToolUseEnd(id)`                              |
| `message_delta`            | capture `stop_reason` + `usage`                                | —                                             |
| `message_stop`             | emit Usage if captured; parse accumulated `submit_response` JSON | `Usage`, `ParsedPlan(plan)`, `Done(stop_reason)` |

### OpenAI (Responses API stream=true)

| OpenAI `type`                    | Branch                                                        | Emitted event(s)                                       |
|----------------------------------|---------------------------------------------------------------|--------------------------------------------------------|
| `response.created`               | ignored                                                       | —                                                      |
| `response.in_progress` / other   | ignored                                                       | —                                                      |
| `response.output_text.delta`     | accumulate, emit                                              | `TextDelta(text)`                                      |
| `response.completed`             | parse full `output_text` (or joined chunks) via Plan          | `Usage`, `ParsedPlan(plan)`, `Done(stop_reason=status)`|

## Provider asymmetry encountered

- **Anthropic** emits the full seven-variant sequence: `TextDelta*`, `ToolUseStart`, `ToolUseDelta*`, `ToolUseEnd`, `Usage`, `ParsedPlan`, `Done`. ParsedPlan comes from accumulated `input_json_delta` chunks under the forced `submit_response` tool_use.
- **OpenAI** does **not** emit any ToolUse* events in T1. The Plan parse rides on `text.format` json_schema structured output — every chunk is text. Final ParsedPlan comes from `response.completed.response.output_text` (with fallback to the accumulated `text_acc` list if the terminal event omits the full string).
- The parity test (`test_provider_stream_parity.py`) explicitly tolerates this asymmetry: both streams emit `>=1 TextDelta`, exactly one `ParsedPlan` carrying the same locked Plan values (rationale="parity rationale", confidence=0.85, final_when_done="parity"), and exactly one terminal `Done`; ToolUse* events are an Anthropic-only addition.

## Cancellation path

Both stream() methods wrap the response in `async with client.stream(...) as resp:`. When the caller cancels (via `gen.aclose()` or task cancellation propagating CancelledError into the generator frame), Python invokes `__aexit__` on the async-with which closes the underlying httpx response. Verified by `CountingStream.aclose` counter in both `test_*_stream.py::test_stream_cancel_closes_connection` (and the additional `test_stream_cancel_via_task_does_not_leak` on the Anthropic side).

## Deviations from plan

- **`grep -c "async def stream"` returns 3, not 2.** Same T1-02 inconsistency: the `StreamingProvider` Protocol declaration uses the same method name. Two impls + one Protocol declaration is correct.
- No other deviations. `complete()` codepath untouched; existing OAuth provider tests (`test_oauth_provider.py`, `test_openai_oauth.py`) still pass.

## Verification

```
uv run pytest tests/harness/test_anthropic_stream.py \
              tests/harness/test_openai_stream.py \
              tests/harness/test_provider_stream_parity.py -x -q   # 8 passed
uv run pytest tests/harness/ -k "openai or provider or anthropic" -x -q  # 45 passed
```
