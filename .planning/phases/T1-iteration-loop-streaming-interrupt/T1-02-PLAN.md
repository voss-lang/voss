---
phase: T1-iteration-loop-streaming-interrupt
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/providers.py
autonomous: true
requirements: [ITER-03]
must_haves:
  truths:
    - "ProviderStreamEvent is a discriminated union with six variants: TextDelta, ToolUseStart, ToolUseDelta, ToolUseEnd, Usage, Done"
    - "ModelProvider protocol (or harness analog) exposes async def stream(...) -> AsyncIterator[ProviderStreamEvent]"
    - "The stream() signature matches complete() argument-for-argument (messages, model, response_format, tools, temperature, max_tokens, timeout)"
    - "Existing complete() methods on both AnthropicOAuthProvider and OpenAIOAuthProvider are unchanged"
  artifacts:
    - path: "voss/harness/providers.py"
      provides: "ProviderStreamEvent union + ParsedPlan terminal event + stream() abstract method on a harness-level Protocol"
      contains: "class ParsedPlan\\|class TextDelta\\|class ToolUseStart\\|class ToolUseDelta\\|class ToolUseEnd\\|class Usage\\|class Done"
  key_links:
    - from: "voss/harness/providers.py"
      to: "voss_runtime.providers.base.ProviderResponse"
      via: "import — ProviderResponse stays the complete() return type; ProviderStreamEvent is new and parallel"
      pattern: "from voss_runtime.providers.base"
---

<objective>
Define the typed-event contract that both provider stream() implementations
will emit and the agent iteration loop will consume. No provider behavior
yet — this plan ships only the shapes + a Protocol/ABC the agent loop and
T1-03's implementations can pin against.

Purpose: CONTEXT.md locks "Normalized typed events — Define a
ProviderStreamEvent union in voss/harness/providers.py. Both Anthropic SSE
and OpenAI Responses-API streaming adapt to this. TurnView + agent loop
consume one shape; provider branching stays inside provider classes." This
plan is that contract. T1-03 fills in the SSE/streaming bodies against
this shape.

Output: ProviderStreamEvent union + ParsedPlan terminal event +
StreamingProvider Protocol (or ABC) in voss/harness/providers.py, with a
unit test asserting shape, discriminator, and import surface.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md
@voss/harness/providers.py
</context>

<interfaces>
Existing `ProviderResponse` is imported from
`voss_runtime.providers.base` — used as the return of `complete()`. T1-02
keeps that import and adds parallel types alongside it.

Existing provider shape (paraphrased from voss/harness/providers.py):
```
class AnthropicOAuthProvider:
    async def complete(*, messages, model, response_format=None, tools=None,
                       temperature=1.0, max_tokens=None, timeout=None) -> ProviderResponse
class OpenAIOAuthProvider:
    async def complete(*, messages, model, response_format=None,
                       temperature=1.0, max_tokens=None, timeout=None) -> ProviderResponse
```

Note: OpenAIOAuthProvider.complete does NOT accept a `tools` kwarg today
(see line 328-338). To keep the stream() signature symmetric across both
providers and match CONTEXT.md's signature ("messages, model,
response_format, tools, temperature, max_tokens, timeout"), the new
`stream()` method on OpenAIOAuthProvider accepts tools as a kwarg but
ignores it for now (no OpenAI tool-use streaming in T1 scope — submit
forced via `text.format` structured-output schema).

CONTEXT.md "Claude's Discretion": "whether providers emit a synthetic
terminal ProviderStreamEvent.ParsedPlan(plan) event or return the parsed
Plan from the stream() coroutine post-iteration. Both work; both providers
must agree." This plan PICKS: ParsedPlan(plan) terminal event. Rationale:
(a) keeps the return type AsyncIterator[ProviderStreamEvent] uniform;
(b) lets the agent loop write a single `async for event in stream(...):
if isinstance(event, ParsedPlan): plan = event.plan` branch instead of
needing both an iterator and a return-value gate. T1-03 implements this
on both providers.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Define ProviderStreamEvent union + StreamingProvider protocol</name>
  <files>voss/harness/providers.py, tests/harness/test_provider_stream_types.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-03 acceptance criteria)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Stream event shape section, ~lines 29-35)
    - voss/harness/providers.py (entire file — imports, both provider classes, _payload methods)
    - voss_runtime/providers/base.py (ProviderResponse + ModelProvider protocol if defined)
  </read_first>
  <behavior>
    - TextDelta(text="hello").text == "hello"
    - ToolUseStart(id="tu_1", name="submit_response").id == "tu_1" and .name == "submit_response"
    - ToolUseDelta(id="tu_1", partial_json='{"rationale":"').partial_json == '{"rationale":"'
    - ToolUseEnd(id="tu_1").id == "tu_1"
    - Usage(prompt_tokens=120, completion_tokens=50, cost_usd=0.0).cost_usd == 0.0
    - Done(stop_reason="end_turn").stop_reason == "end_turn"
    - ParsedPlan(plan=&lt;Plan instance&gt;).plan is the same instance
    - isinstance(TextDelta("x"), ProviderStreamEvent) is True for all seven variants
    - typing.get_args(ProviderStreamEvent) returns exactly seven types (TextDelta, ToolUseStart, ToolUseDelta, ToolUseEnd, Usage, Done, ParsedPlan) — assert by name
    - StreamingProvider protocol declares `async def stream(self, *, messages, model, response_format=None, tools=None, temperature=1.0, max_tokens=None, timeout=None) -> AsyncIterator[ProviderStreamEvent]`
    - AnthropicOAuthProvider and OpenAIOAuthProvider satisfy the StreamingProvider protocol structurally (hasattr check + signature inspection) — actual impl in T1-03 but a placeholder raising NotImplementedError counts for this plan
  </behavior>
  <action>
    Add the following types to `voss/harness/providers.py` after the
    imports block and before the AnthropicOAuthProvider class.

    Use frozen `@dataclass(frozen=True, slots=True)` (slots OK for py3.10+;
    project pins py3.12 per voss_runtime/_config.py heuristics — verify via
    `grep python_requires pyproject.toml` if uncertain). Seven dataclasses:
    - TextDelta: text: str
    - ToolUseStart: id: str, name: str
    - ToolUseDelta: id: str, partial_json: str
    - ToolUseEnd: id: str
    - Usage: prompt_tokens: int, completion_tokens: int, cost_usd: float
    - Done: stop_reason: str
    - ParsedPlan: plan: Any (don't import Plan from agent — avoid circular)

    Define `ProviderStreamEvent` as a typing.Union of those seven (use
    `from typing import Union, Any, AsyncIterator, Protocol,
    runtime_checkable`). Export `__all__` additions if a module __all__
    exists today (`grep -n "^__all__" voss/harness/providers.py`); if not,
    skip.

    Define a `@runtime_checkable class StreamingProvider(Protocol)` with
    one method: `async def stream(self, *, messages: list[dict], model: str,
    response_format: Optional[type] = None, tools: Optional[list[dict]] =
    None, temperature: float = 1.0, max_tokens: Optional[int] = None,
    timeout: Optional[float] = None) -> AsyncIterator[ProviderStreamEvent]:
    ...`

    On BOTH AnthropicOAuthProvider AND OpenAIOAuthProvider, add an
    `async def stream(self, *, messages, model, response_format=None,
    tools=None, temperature=1.0, max_tokens=None, timeout=None) ->
    AsyncIterator[ProviderStreamEvent]:` method body containing:
    `raise NotImplementedError("stream() body lands in T1-03")` followed by
    a yield in an unreachable branch (e.g. `if False: yield TextDelta("")`)
    so the method is a valid async generator that satisfies the Protocol's
    AsyncIterator return type. T1-03 replaces both bodies.

    Do NOT modify _payload, complete(), _headers, _maybe_refresh, or any
    other existing method. Do NOT change OpenAI's `stream: False`
    hardcoded line in _payload (T1-03 owns that change — that line is for
    the Responses-API non-stream path).

    Write `tests/harness/test_provider_stream_types.py` covering all 11
    behavior bullets above. The "AnthropicOAuthProvider and
    OpenAIOAuthProvider satisfy StreamingProvider" assertion uses
    `isinstance(instance, StreamingProvider)` thanks to
    @runtime_checkable. Use a minimal stub `creds` for both providers
    (look at how existing tests instantiate them: probably
    tests/harness/test_providers*.py — read those for the fixture
    pattern).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_provider_stream_types.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -c "^@dataclass" voss/harness/providers.py` increases by at least 7 (the seven event variants)
    - source assertion: `grep -n "class StreamingProvider\|ProviderStreamEvent =\s*Union\[" voss/harness/providers.py` returns 2 matches
    - source assertion: `grep -n "async def stream" voss/harness/providers.py` returns exactly 2 matches (one per provider)
    - source assertion: `grep -n "raise NotImplementedError" voss/harness/providers.py` returns at least 2 matches (placeholder bodies for T1-03)
    - behavior assertion: pytest passes all behaviors; the typing.get_args(ProviderStreamEvent) test confirms exactly 7 variants
    - regression assertion: existing provider tests still pass — `uv run pytest tests/harness/ -k provider -x -q`
    - test command: `uv run pytest tests/harness/test_provider_stream_types.py -x -q && uv run pytest tests/harness/ -k provider -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>ProviderStreamEvent union exists with seven variants including ParsedPlan terminal; StreamingProvider Protocol declares the stream() signature; both provider classes structurally satisfy StreamingProvider with NotImplementedError placeholder bodies; all existing provider tests still pass.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/test_provider_stream_types.py -x -q` passes
- `uv run pytest tests/harness/ -k provider -x -q` passes (existing complete() tests unaffected)
- Both provider classes pass `isinstance(p, StreamingProvider)` runtime check
- T1-03 can subclass / replace the placeholder bodies with concrete SSE/streaming logic without touching the Union, ParsedPlan, or StreamingProvider declarations
</verification>

<success_criteria>
- voss/harness/providers.py exports ProviderStreamEvent (Union of 7 typed events) + StreamingProvider Protocol + ParsedPlan terminal event
- ParsedPlan is the locked mechanism for surfacing the structured Plan parse (resolves the CONTEXT.md "Claude's Discretion" item for both providers)
- AnthropicOAuthProvider.stream() and OpenAIOAuthProvider.stream() exist with the locked signature but raise NotImplementedError (T1-03 fills the bodies)
- No regression in existing complete() codepath
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-02-SUMMARY.md` when done with: the seven event dataclass signatures, the StreamingProvider protocol signature, and confirmation that ParsedPlan is the chosen Plan-surface mechanism (vs return value).
</output>
