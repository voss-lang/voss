---
phase: T1-iteration-loop-streaming-interrupt
plan: 03
type: execute
wave: 2
depends_on: [T1-02]
files_modified:
  - voss/harness/providers.py
autonomous: true
requirements: [ITER-03]
must_haves:
  truths:
    - "AnthropicOAuthProvider.stream() emits TextDelta events as Anthropic SSE 'content_block_delta' events arrive"
    - "OpenAIOAuthProvider.stream() emits TextDelta events as OpenAI Responses-API streaming chunks arrive"
    - "Both providers accumulate tool_use submit_response chunks across the stream and emit ParsedPlan(plan=<Plan instance>) immediately before Done(stop_reason=...)"
    - "Anthropic OAuth refresh-on-401 path is preserved for stream() (refresh + reopen)"
    - "On asyncio.CancelledError during stream consumption, the underlying httpx connection is closed via async-context exit (no leaked sockets)"
    - "Both stream() bodies replace the T1-02 NotImplementedError placeholders and conform to the StreamingProvider protocol"
    - "complete() codepath is unchanged — non-streaming callers still work"
  artifacts:
    - path: "voss/harness/providers.py"
      provides: "Concrete async-generator bodies for AnthropicOAuthProvider.stream and OpenAIOAuthProvider.stream"
      contains: "async def stream"
  key_links:
    - from: "voss/harness/providers.py:AnthropicOAuthProvider.stream"
      to: "https://api.anthropic.com/v1/messages with stream=true"
      via: "httpx.AsyncClient.stream() context manager + SSE line decode"
      pattern: "async with .*\\.stream\\(.*\"POST\""
    - from: "voss/harness/providers.py:OpenAIOAuthProvider.stream"
      to: "/v1/responses or /responses with stream=true"
      via: "httpx.AsyncClient.stream() context manager + SSE / chunked JSON decode"
      pattern: "body\\[\"stream\"\\]\\s*=\\s*True"
---

<objective>
Implement concrete SSE/streaming bodies for both providers, both adapting
their native event shape to the ProviderStreamEvent union. Preserve OAuth
refresh, preserve structured-output Plan parsing, ship a recorded-fixture
parity test that exercises both providers end-to-end.

Purpose: SPEC ITER-03 mandates both AnthropicOAuthProvider.stream() and
OpenAIOAuthProvider.stream() exist and pass a recorded-fixture parity
test. CONTEXT.md locks ParsedPlan terminal event mechanism (resolved in
T1-02) and the AsyncIterator[ProviderStreamEvent] return contract.
"Graceful httpx aclose() on stream cancel" is non-negotiable.

Output: Two concrete stream() implementations replacing T1-02's
NotImplementedError placeholders + a parity test asserting both
providers emit the same logical event sequence against recorded SSE
fixtures.
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
After T1-02:
- ProviderStreamEvent = Union[TextDelta, ToolUseStart, ToolUseDelta,
  ToolUseEnd, Usage, Done, ParsedPlan]
- StreamingProvider Protocol with `async def stream(...) ->
  AsyncIterator[ProviderStreamEvent]`
- Both provider classes have stream() methods that currently raise
  NotImplementedError after a sentinel `if False: yield TextDelta("")`.
  THIS PLAN REPLACES BOTH BODIES.

Anthropic streaming wire format (Anthropic Messages API, stream=true):
SSE events. Relevant event types we map:
- `message_start` -> capture model + initial usage
- `content_block_start` with content_block.type=="text" -> nothing emitted yet
- `content_block_start` with content_block.type=="tool_use" -> emit ToolUseStart(id=block.id, name=block.name)
- `content_block_delta` with delta.type=="text_delta" -> emit TextDelta(delta.text)
- `content_block_delta` with delta.type=="input_json_delta" -> emit ToolUseDelta(id=current_block_id, partial_json=delta.partial_json)
- `content_block_stop` for a tool_use block -> emit ToolUseEnd(id=block_id), accumulate the partial_json into a complete JSON string for that block
- `message_delta` with delta.stop_reason -> capture stop_reason
- `message_delta` with usage -> emit Usage(prompt_tokens=usage.input_tokens, completion_tokens=usage.output_tokens, cost_usd=0.0)
- `message_stop` -> if there is an accumulated submit_response tool_use, parse via response_format.model_validate_json(json_str), emit ParsedPlan(plan=parsed) then Done(stop_reason=captured_stop_reason)

OpenAI Responses-API streaming (chatgpt.com/backend-api/codex/responses or
api.openai.com/v1/responses with stream=true): emits SSE-style events
with `event: response.output_text.delta` carrying `{"delta":"..."}` and
terminal `event: response.completed` with the full payload. Since the
existing _payload uses `text.format: {type: "json_schema", strict: true,
schema: ...}`, structured-output text accumulates as output_text deltas
and the terminal event carries `output_text` (full string). Map:
- `response.output_text.delta` -> emit TextDelta(text=chunk["delta"])
- `response.completed` -> parse accumulated text via
  response_format.model_validate_json(full_text), emit ParsedPlan +
  Usage (from event.response.usage) + Done(stop_reason=event.response.status)

The OpenAI provider does NOT have native tool_use streaming in the
text.format Plan-extraction path, so it does not emit ToolUseStart/
ToolUseDelta/ToolUseEnd. The parity test must accept this provider
asymmetry: assert that BOTH streams produce >=1 TextDelta and exactly
one ParsedPlan followed by one Done. Anthropic additionally emits
ToolUseStart/Delta/End triplet.

Existing http client:
- AnthropicOAuthProvider._http() returns httpx.AsyncClient (timeout=120s)
- OpenAIOAuthProvider._http() ditto
- Both have _maybe_refresh / refresh on 401 (Anthropic) or 401-with-
  refresh-token (OpenAI). The stream() impl must preserve this.

Pattern for graceful cancel (locked in CONTEXT.md):
```
async with self._http().stream("POST", url, json=body, headers=...,
                                timeout=timeout) as resp:
    if resp.status_code == 401:
        # refresh + reopen — see Action below
    async for line in resp.aiter_lines():
        # parse SSE, yield events
```
The `async with` ensures asyncio.CancelledError propagation closes the
connection cleanly.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement AnthropicOAuthProvider.stream() with OAuth refresh + SSE decode</name>
  <files>voss/harness/providers.py, tests/harness/test_anthropic_stream.py, tests/harness/fixtures/anthropic_stream_plan.sse</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-03 acceptance criteria + 500ms first-token threshold)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Stream event shape + Graceful httpx aclose section, ~lines 71-74)
    - voss/harness/providers.py (lines 45-211 — AnthropicOAuthProvider class entirety, esp. _payload, complete, _maybe_refresh)
    - voss/harness/auth.py (refresh_anthropic + ANTHROPIC_OAUTH_BETA — confirm existing refresh pathway)
    - Any existing tests under tests/harness/ that exercise AnthropicOAuthProvider (probably test_providers.py / test_anthropic_provider.py — `grep -ln Anthropic tests/harness/`)
  </read_first>
  <behavior>
    - Given a recorded SSE fixture containing message_start +
      content_block_start(text) + 3x content_block_delta(text_delta) +
      content_block_stop + content_block_start(tool_use submit_response) +
      2x content_block_delta(input_json_delta forming a Plan) +
      content_block_stop + message_delta(stop_reason="end_turn",
      usage{input_tokens:100,output_tokens:50}) + message_stop,
      iterating `async for event in provider.stream(messages=[...],
      model="claude-sonnet-4-5", response_format=Plan)` yields events in
      this order:
        TextDelta * 3, ToolUseStart, ToolUseDelta * 2, ToolUseEnd,
        Usage(100, 50, 0.0), ParsedPlan(plan=&lt;Plan&gt;), Done(stop_reason="end_turn")
    - The ParsedPlan.plan is a validated Plan instance whose fields match
      the JSON encoded across the two input_json_delta chunks
    - Given a 401 response on the initial stream open, the provider
      calls auth.refresh_anthropic(self.creds), reopens the stream, and
      consumes from the second connection
    - Calling provider.stream() inside an asyncio.CancelledError-raising
      task (cancel the consumer task mid-iteration) does not leak the
      httpx.AsyncClient connection — verifiable via a custom transport
      stub that counts `aclose` calls on the underlying response context
    - Anthropic OAuth headers including `anthropic-beta: oauth-2025-04-20`
      are sent on the streaming request
    - The request body contains `"stream": true` and the same
      _payload(...)-built structure as complete() (system blocks, forced
      submit_response tool, tool_choice=tool/submit_response)
  </behavior>
  <action>
    Replace the AnthropicOAuthProvider.stream() body. Reuse `_payload()`
    with the existing args plus set `body["stream"] = True` before sending.
    Call `self._maybe_refresh()` first.

    Structure:
    1. Build body via self._payload(...), set body["stream"] = True.
    2. url = f"{self.base_url}/v1/messages"
    3. Open a helper `async def _open():` that yields the stream context:
       `client = self._http()`; return `client.stream("POST", url,
       json=body, headers=self._headers(), timeout=timeout)`.
    4. async with _open() as resp:
         if resp.status_code == 401:
             self.creds = auth.refresh_anthropic(self.creds)
             # IMPORTANT: cannot reopen inside the same `async with`. Pattern:
             #   break out, then re-enter with refreshed creds.
       Implement as: try once with current creds, catch on first non-200,
       check 401, refresh, then run the stream in a second async-with
       block. Concretely two near-identical async-with blocks guarded by
       a `refreshed: bool = False` flag.
    5. State across SSE events:
       current_text_block_id: Optional[str] = None
       current_tool_use_id: Optional[str] = None
       current_tool_use_name: Optional[str] = None
       tool_use_json: dict[str, list[str]] = {}  # id -> list of partial_json chunks
       captured_stop_reason: str = "end_turn"  # default
       captured_usage: Optional[Usage] = None
    6. Decode SSE: `async for line in resp.aiter_lines():`; skip empty
       lines and lines starting with `event:` (Anthropic SSE uses
       `data: {json}` lines for the payload; the `event: NAME` line
       precedes each data line but Anthropic also includes a `type`
       field inside the data JSON so we can parse from data alone).
       Parse each `data: {...}` line via json.loads. Switch on data["type"]:
         - "message_start": grab data["message"]["usage"] if present
         - "content_block_start":
             cb = data["content_block"]
             if cb["type"] == "tool_use":
                 current_tool_use_id = cb["id"]
                 current_tool_use_name = cb["name"]
                 tool_use_json[cb["id"]] = []
                 yield ToolUseStart(id=cb["id"], name=cb["name"])
         - "content_block_delta":
             d = data["delta"]
             if d["type"] == "text_delta":
                 yield TextDelta(text=d["text"])
             elif d["type"] == "input_json_delta" and current_tool_use_id:
                 tool_use_json[current_tool_use_id].append(d["partial_json"])
                 yield ToolUseDelta(id=current_tool_use_id, partial_json=d["partial_json"])
         - "content_block_stop":
             if current_tool_use_id is not None:
                 yield ToolUseEnd(id=current_tool_use_id)
                 # do NOT reset current_tool_use_id here — message_stop
                 # uses it to find which block was submit_response
         - "message_delta":
             d = data.get("delta", {})
             if "stop_reason" in d:
                 captured_stop_reason = d["stop_reason"] or "end_turn"
             usage = data.get("usage")
             if usage:
                 captured_usage = Usage(
                     prompt_tokens=int(usage.get("input_tokens", 0)),
                     completion_tokens=int(usage.get("output_tokens", 0)),
                     cost_usd=0.0,
                 )
         - "message_stop":
             if captured_usage is not None:
                 yield captured_usage
             # Resolve ParsedPlan from accumulated submit_response tool_use
             if response_format is not None and current_tool_use_id is not None:
                 full_json = "".join(tool_use_json.get(current_tool_use_id, []))
                 try:
                     plan_obj = response_format.model_validate_json(full_json)
                     yield ParsedPlan(plan=plan_obj)
                 except Exception:
                     # parser failure — surface Done without ParsedPlan; loop
                     # handles missing-plan case
                     pass
             yield Done(stop_reason=captured_stop_reason)
             return
    7. If the stream ends without `message_stop` (server hangup), emit a
       Done(stop_reason="incomplete") then return — do NOT raise inside
       the generator (callers catch CancelledError separately).

    Create the recorded fixture `tests/harness/fixtures/anthropic_stream_plan.sse`
    as a literal SSE byte stream covering the event sequence in the
    behavior bullet. Use a Plan JSON with fields: rationale="test
    rationale", steps=[], confidence=0.92, final_when_done="done". Encode
    this Plan as 2 input_json_delta chunks: first chunk is the first half
    of the JSON, second chunk is the second half (split arbitrarily
    mid-key — exercises the accumulator). Each SSE event is two lines:
    `event: <name>\n` + `data: {"type": "<name>", ...}\n\n`.

    Write `tests/harness/test_anthropic_stream.py` with a fixture-based
    test that builds an AnthropicOAuthProvider whose `_http()` returns a
    fake httpx.AsyncClient backed by httpx.MockTransport replaying the
    .sse file as the response body for a streaming POST. Assert event
    sequence, ParsedPlan.plan fields, Usage values, Done.stop_reason.

    Add a second test `test_anthropic_stream_refreshes_on_401` using
    MockTransport that returns 401 on first request and the SSE body on
    second request; assert auth.refresh_anthropic was called exactly once
    (monkeypatch it) and final event sequence is correct.

    Add a third test `test_anthropic_stream_cancel_closes_connection`
    using a controllable MockTransport that records `aclose` calls on
    the response stream; cancel the consumer task mid-iteration and
    assert the response was closed (or the connection-counter shows
    zero leaks).

    Do NOT remove or modify the existing `complete()` method.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_anthropic_stream.py -x -q 2>&amp;1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "async def stream" voss/harness/providers.py | head -1` points into AnthropicOAuthProvider
    - source assertion: `grep -n "body\[\"stream\"\] = True\|raise NotImplementedError" voss/harness/providers.py` — first match present, NotImplementedError for AnthropicOAuthProvider removed
    - source assertion: `grep -n "auth.refresh_anthropic" voss/harness/providers.py` >= 2 (existing complete + new stream)
    - source assertion: `grep -n "async with .*\\.stream(" voss/harness/providers.py` >= 1
    - behavior assertion: all three pytest tests pass — event sequence, refresh-on-401, cancel-closes-connection
    - fixture assertion: `wc -l tests/harness/fixtures/anthropic_stream_plan.sse` > 10
    - regression assertion: `uv run pytest tests/harness/ -k anthropic -x -q` passes
    - test command: `uv run pytest tests/harness/test_anthropic_stream.py -x -q && uv run pytest tests/harness/ -k anthropic -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>AnthropicOAuthProvider.stream() yields the documented seven-event sequence including ParsedPlan; OAuth refresh-on-401 is preserved; cancel closes the connection cleanly; recorded SSE fixture replays deterministically.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement OpenAIOAuthProvider.stream() + cross-provider parity test</name>
  <files>voss/harness/providers.py, tests/harness/test_openai_stream.py, tests/harness/test_provider_stream_parity.py, tests/harness/fixtures/openai_stream_plan.sse</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-03 — "both providers pass a parity test against a recorded fixture stream")
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (OpenAI streaming format constraint: "must work with structured-output `text.format` schema (currently used in `_payload`)", lines 85)
    - voss/harness/providers.py (lines 221-402 — OpenAIOAuthProvider class entirety)
    - voss/harness/auth.py (refresh_codex + CHATGPT_BACKEND_BASE + ANTHROPIC_OAUTH_BETA constants)
    - tests/harness/test_anthropic_stream.py (just-written sibling; copy the MockTransport pattern)
  </read_first>
  <behavior>
    - Given a recorded SSE fixture containing
      response.created -> response.output_text.delta * 4 (chunks summing
      to a complete Plan JSON) -> response.completed (carrying usage
      {"input_tokens":120,"output_tokens":60} and status "completed"),
      iterating provider.stream(messages=[...], model="gpt-5",
      response_format=Plan) yields:
        TextDelta * 4, Usage(120, 60, 0.0), ParsedPlan(plan=&lt;Plan&gt;),
        Done(stop_reason="completed")
    - The request body has `body["stream"] = True` and preserves the
      existing text.format json_schema structured-output block
    - 401 with refresh_token triggers auth.refresh_codex(self.creds) and
      one reopen (matches existing complete() refresh behavior)
    - Cancel mid-iteration closes the httpx response (same assertion
      pattern as Anthropic Task 1)
    - chatgpt-account-id header is sent when self.creds.account_id is set
    - Parity test (test_provider_stream_parity.py): given two recorded
      fixtures (Anthropic + OpenAI) that encode the SAME logical Plan
      (rationale="parity rationale", steps=[], confidence=0.85,
      final_when_done="parity"), both providers' stream() yields a
      ParsedPlan whose plan.rationale == "parity rationale" AND
      plan.confidence == pytest.approx(0.85) AND plan.final_when_done ==
      "parity". Both provider streams emit exactly ONE ParsedPlan event
      followed by exactly ONE Done event. Both emit >=1 TextDelta.
      Anthropic additionally emits ToolUseStart/Delta/End; OpenAI does
      not (and the parity test EXPLICITLY tolerates this asymmetry —
      assertions are structured around "intersection of guaranteed
      events", not "identical sequences").
  </behavior>
  <action>
    Replace the OpenAIOAuthProvider.stream() placeholder body. The
    existing _payload(messages, model, response_format, temperature,
    max_tokens) builds a body with `stream: False`. For streaming, build
    the body the same way then OVERWRITE `body["stream"] = True`. Call
    self._maybe_refresh() first (current impl is a no-op but keep the
    call so future expiry logic Just Works).

    URL resolution mirrors complete():
    `url = f"{self.base_url}/responses" if self.base_url.endswith("/codex")
    else f"{self.base_url}/v1/responses"`

    Open the stream via `async with self._http().stream("POST", url,
    json=body, headers=self._headers(), timeout=timeout) as resp:`.
    On 401 with self.creds.refresh_token present, run
    `self.creds = auth.refresh_codex(self.creds)` and reopen in a second
    async-with (same `refreshed: bool = False` flag pattern as Anthropic).

    SSE decoding: OpenAI Responses-API streaming uses lines like:
        event: response.output_text.delta
        data: {"type":"response.output_text.delta","delta":"hello"}

        event: response.completed
        data: {"type":"response.completed","response":{"usage":{...},"status":"completed","output_text":"..."}}

    Decode each `data: {...}` line. Maintain `text_acc: list[str] = []`.
    Switch on data.get("type"):
      - "response.output_text.delta":
          chunk = data.get("delta", "")
          text_acc.append(chunk)
          yield TextDelta(text=chunk)
      - "response.completed":
          usage = data.get("response", {}).get("usage", {}) or {}
          yield Usage(prompt_tokens=int(usage.get("input_tokens", 0)),
                      completion_tokens=int(usage.get("output_tokens", 0)),
                      cost_usd=0.0)
          if response_format is not None:
              full_text = data.get("response", {}).get("output_text") or "".join(text_acc)
              try:
                  plan_obj = response_format.model_validate_json(full_text)
                  yield ParsedPlan(plan=plan_obj)
              except Exception:
                  pass
          stop = data.get("response", {}).get("status", "completed")
          yield Done(stop_reason=stop)
          return
      - other event types ("response.created", "response.in_progress",
        "response.output_item.added", etc): ignore.

    On stream end without `response.completed`: yield Done(stop_reason="incomplete").

    Build `tests/harness/fixtures/openai_stream_plan.sse` with 4
    output_text.delta chunks (split a Plan JSON
    {"rationale":"test rationale","steps":[],"confidence":0.92,
    "final_when_done":"done"} into four pieces) + one response.completed
    event carrying usage{input_tokens:120,output_tokens:60} and status
    "completed".

    Write `tests/harness/test_openai_stream.py` with three tests
    mirroring the Anthropic test file: sequence, refresh-on-401,
    cancel-closes-connection. Reuse the MockTransport fixture pattern
    from Task 1's test file.

    Write `tests/harness/test_provider_stream_parity.py` with ONE test
    that:
      1. Builds two new recorded fixtures (or reuses the existing ones
         re-encoded with the SAME Plan JSON content) — locked plan
         values: rationale="parity rationale", steps=[], confidence=0.85,
         final_when_done="parity".
      2. Runs each provider's stream() against its respective fixture
         via MockTransport.
      3. Collects events into two lists.
      4. Asserts both lists contain exactly one ParsedPlan whose
         plan.rationale == "parity rationale", plan.confidence ==
         pytest.approx(0.85), plan.final_when_done == "parity".
      5. Asserts both lists end with exactly one Done event.
      6. Asserts both lists contain >=1 TextDelta.
      7. Asserts Anthropic's list additionally contains exactly one
         ToolUseStart with name=="submit_response" and at least one
         ToolUseDelta and exactly one ToolUseEnd. (OpenAI's list has
         zero of these — that's the documented asymmetry.)

    Do NOT modify _payload, _to_responses_input, complete, _headers, or
    _maybe_refresh.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_openai_stream.py tests/harness/test_provider_stream_parity.py tests/harness/test_anthropic_stream.py -x -q 2>&amp;1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -c "async def stream" voss/harness/providers.py` == 2
    - source assertion: `grep -c "raise NotImplementedError" voss/harness/providers.py` == 0 (both placeholder bodies replaced)
    - source assertion: `grep -n "auth.refresh_codex" voss/harness/providers.py` >= 2
    - source assertion: `grep -n "response.output_text.delta\|response.completed" voss/harness/providers.py` >= 2
    - behavior assertion: all three OpenAI tests pass + parity test passes
    - parity assertion: both ParsedPlan.plan.rationale strings equal "parity rationale" in the parity test
    - regression assertion: `uv run pytest tests/harness/ -k "openai or provider or anthropic" -x -q` passes
    - test command: `uv run pytest tests/harness/test_openai_stream.py tests/harness/test_anthropic_stream.py tests/harness/test_provider_stream_parity.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>OpenAIOAuthProvider.stream() yields the documented six-event sequence; refresh-on-401 + cancel-closes-connection both preserved; parity test confirms both providers expose the same logical Plan via ParsedPlan; complete() codepath unchanged.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/test_anthropic_stream.py tests/harness/test_openai_stream.py tests/harness/test_provider_stream_parity.py -x -q` passes
- `grep -c "raise NotImplementedError" voss/harness/providers.py` returns 0
- `grep -c "async def stream" voss/harness/providers.py` returns 2
- `uv run pytest tests/harness/ -k "provider" -x -q` (existing tests + new) passes
- isinstance(AnthropicOAuthProvider(...), StreamingProvider) is True
- isinstance(OpenAIOAuthProvider(...), StreamingProvider) is True
</verification>

<success_criteria>
- Both providers expose a working stream() that yields ProviderStreamEvent variants in deterministic order
- Anthropic stream emits the full seven-variant sequence (TextDelta, ToolUseStart/Delta/End, Usage, ParsedPlan, Done)
- OpenAI stream emits the structured-output sequence (TextDelta * N, Usage, ParsedPlan, Done)
- Both ParsedPlan events carry a fully-validated Plan whose fields match the encoded JSON
- OAuth refresh + graceful httpx aclose are both verified in tests, not just asserted in docs
- Recorded SSE fixtures live under tests/harness/fixtures/ so the agent loop in T1-04 can replay them too
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-03-SUMMARY.md` when done with: line counts of both stream() bodies, the chosen SSE event-type mapping table for each provider, fixture file paths, and any provider asymmetry encountered (e.g., did OpenAI emit any tool-use deltas? — expected: no in T1).
</output>
