---
phase: T1-iteration-loop-streaming-interrupt
plan: 02
status: complete
completed_at: 2026-05-15
commits:
  - b9afaa4 — feat(T1-02): ProviderStreamEvent union + StreamingProvider Protocol
---

# T1-02 Summary — Streaming event contract

## Files changed

- `voss/harness/providers.py` — added seven frozen+slots dataclass event variants, `ProviderStreamEvent` Union alias, `StreamingProvider` runtime-checkable Protocol, placeholder `stream()` async-generator method on both providers.
- `tests/harness/test_provider_stream_types.py` — 14 tests covering variant shapes, Union arity, isinstance dispatch, Protocol satisfaction, signature parity, placeholder body raising.

## Seven event dataclasses

All `@dataclass(frozen=True, slots=True)`:

```python
TextDelta(text: str)
ToolUseStart(id: str, name: str)
ToolUseDelta(id: str, partial_json: str)
ToolUseEnd(id: str)
Usage(prompt_tokens: int, completion_tokens: int, cost_usd: float)
Done(stop_reason: str)
ParsedPlan(plan: Any)
```

`ProviderStreamEvent = Union[TextDelta, ToolUseStart, ToolUseDelta, ToolUseEnd, Usage, Done, ParsedPlan]`

## ParsedPlan vs. return value — locked

ParsedPlan terminal event is the chosen mechanism for surfacing the structured Plan parse (resolves the CONTEXT.md "Claude's Discretion" item). Rationale captured in plan: keeps `AsyncIterator[ProviderStreamEvent]` uniform; agent loop branches on a single shape. `plan: Any` keeps the variant import-free vs. `voss.harness.agent.Plan` to avoid a circular import; T1-03 / T1-05 pin the concrete type at the call site.

## StreamingProvider Protocol signature

```python
@runtime_checkable
class StreamingProvider(Protocol):
    async def stream(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[ProviderStreamEvent]: ...
```

Both `AnthropicOAuthProvider` and `OpenAIOAuthProvider` structurally satisfy it (verified by `isinstance(p, StreamingProvider)` runtime check at test time). Placeholder bodies raise `NotImplementedError("stream() body lands in T1-03")` and include an unreachable `if False: yield TextDelta("")` so they remain valid async generators (required for the `AsyncIterator` return type).

## Deviations from plan

- **`grep -n "async def stream"` count is 3, not 2.** The plan's acceptance assertion says "exactly 2 matches (one per provider)" but the same plan also requires a `StreamingProvider` Protocol method also named `async def stream(...)`. Internal inconsistency in the plan — Protocol method legitimately matches. Behavior (two impls + one Protocol declaration) is correct.
- No other deviations. Existing `complete()` codepath untouched. Existing provider tests pass without modification.

## Verification

```
uv run pytest tests/harness/test_provider_stream_types.py -x -q       # 14 passed
uv run pytest tests/harness/ -k provider -x -q                         # 26 passed
uv run pytest tests/harness/test_oauth_provider.py \
              tests/harness/test_openai_oauth.py -x -q                 # green
```
