---
phase: T4-prompt-caching-cost-truthfulness
plan: 04
type: execute
wave: 4
depends_on: ["T4-01", "T4-02", "T4-03"]
files_modified:
  - voss/harness/providers.py
  - voss/harness/agent.py
  - voss/harness/session.py
  - voss/harness/recorder.py
  - tests/harness/test_streaming_usage_cache.py
  - tests/harness/test_telemetry_cache_fields.py
autonomous: true
requirements: [CACHE-02, CACHE-07]

must_haves:
  truths:
    - "ProviderStreamEvent.Usage carries cache_creation_input_tokens: int = 0 and cache_read_input_tokens: int = 0 (additive, mirrors ProviderResponse — D-01 symmetric)."
    - "agent.py Usage consumer reads both new fields off the event via the same `if this_iter_usage else 0` guard pattern as prompt_tokens/completion_tokens."
    - "The provider.response telemetry event's data dict gains two flat keys: cache_creation_input_tokens, cache_read_input_tokens (D-05 flat shape, NO nested cache:{} sub-object)."
    - "IterationRecord gains two additive int=0 cache fields adjacent to prompt_tokens/completion_tokens (Pitfall 8 / Open Question 3)."
    - "RunRecorder.end_iteration accepts two new keyword-only int kwargs (default 0) and writes them onto the IterationRecord."
    - "Pre-T4 IterationRecord JSON fixtures (no cache fields) hydrate cleanly with both fields defaulting to 0."
    - "Round-trip: dataclasses.asdict(IterationRecord(... cache_creation_input_tokens=1500, cache_read_input_tokens=200)) then IterationRecord(**d) preserves both values."
  artifacts:
    - path: "voss/harness/providers.py"
      provides: "Usage dataclass with two additive cache fields."
      contains: "cache_creation_input_tokens"
    - path: "voss/harness/agent.py"
      provides: "Usage consumer extension + provider.response telemetry payload extension."
      contains: "iter_cache_creation"
    - path: "voss/harness/session.py"
      provides: "IterationRecord with two additive cache fields."
      contains: "cache_creation_input_tokens"
    - path: "voss/harness/recorder.py"
      provides: "end_iteration accepts cache kwargs and writes to the target record."
      contains: "cache_creation_input_tokens"
    - path: "tests/harness/test_streaming_usage_cache.py"
      provides: "CACHE-02 streaming-half green test."
    - path: "tests/harness/test_telemetry_cache_fields.py"
      provides: "CACHE-07 telemetry + round-trip green test."
  key_links:
    - from: "voss/harness/agent.py"
      to: "voss/harness/providers.py::Usage"
      via: "stream event consumer reads new fields"
      pattern: "this_iter_usage\\.cache_creation_input_tokens"
    - from: "voss/harness/agent.py"
      to: "voss/harness/recorder.py::end_iteration"
      via: "kwarg pass-through (if existing call site touched; else write directly on iter_rec)"
      pattern: "cache_creation_input_tokens="
    - from: "voss/harness/session.py::IterationRecord"
      to: "json serialization via dataclasses.asdict"
      via: "round-trip preserves defaults"
      pattern: "cache_creation_input_tokens: int = 0"
---

<objective>
Close the streaming half of CACHE-02 and all of CACHE-07: extend `ProviderStreamEvent.Usage` with two additive cache fields, propagate them through the agent.py Usage consumer into the existing `provider.response` telemetry event, add matching additive fields to `IterationRecord`, extend `RunRecorder.end_iteration` to accept them, and turn the two remaining T4-01 red stubs (streaming + telemetry/round-trip) green.

Purpose: Symmetry — non-streaming half landed in T4-02; this is the matching streaming + recorder/telemetry path. RunRecord round-trip becomes assertable (Pitfall 8). The flat-dict telemetry shape (D-05) is preserved.
Output: Four small additive dataclass / function extensions in voss/harness/ + two green tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-SPEC.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-CONTEXT.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-RESEARCH.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-PATTERNS.md
@voss/harness/providers.py
@voss/harness/agent.py
@voss/harness/session.py
@voss/harness/recorder.py
@voss/harness/telemetry.py

<interfaces>
<!-- Current shapes to extend additively. -->

Today's streaming Usage variant (voss/harness/providers.py:52-57):
```python
@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
```

Today's IterationRecord (voss/harness/session.py:96-109): has `prompt_tokens: int = 0`, `completion_tokens: int = 0`; adjacent placement for the new fields.

Today's RunRecorder.end_iteration (voss/harness/recorder.py:116-150): accepts kwargs `plan, tool_results, cost_usd, prompt_tokens, completion_tokens, exit_reason`. Writes them onto the most recent open iteration.

Today's agent.py Usage consumer (voss/harness/agent.py:609-622): `if isinstance(event, Usage): this_iter_usage = event` then reads `prompt_tokens`/`completion_tokens` with the `if this_iter_usage else 0` guard at lines 617-621.

Today's agent.py telemetry emit (voss/harness/agent.py:645-658): flat `data={...}` dict on `provider.response`. NO nested sub-objects.

OAuth-provider emission sites (providers.py:400-404 and 701-704) construct `Usage` with three positional kwargs only — the new int=0 defaults mean those sites stay valid without modification (cache fields default to 0 for OAuth path per Pitfall 3 deferral).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend Usage dataclass + agent.py consumer + telemetry payload + turn streaming + telemetry tests green</name>
  <files>voss/harness/providers.py, voss/harness/agent.py, tests/harness/test_streaming_usage_cache.py, tests/harness/test_telemetry_cache_fields.py</files>
  <behavior>
    - `Usage(prompt_tokens=1, completion_tokens=1, cost_usd=0.0)` constructs cleanly; both new cache fields default to 0.
    - `Usage(prompt_tokens=100, completion_tokens=50, cost_usd=0.01, cache_creation_input_tokens=1500, cache_read_input_tokens=0)` constructs cleanly.
    - When the agent.py stream consumer receives a Usage event with cache fields populated, the next telemetry.emit("provider.response", ...) call's `data` dict contains those two values as flat keys (NO nested cache:{...}).
    - When `this_iter_usage is None`, both `iter_cache_creation` and `iter_cache_read` default to 0 (mirrors existing token-field guard).
  </behavior>
  <action>
    (1) Extend `voss/harness/providers.py::Usage` (frozen-slots dataclass at lines 52-57) with two additive int=0 fields after `cost_usd`. Per T4-PATTERNS.md "voss/harness/providers.py" section. Add a comment cite `# T4 CACHE-02 (D-01): streaming half — symmetric with ProviderResponse on the non-streaming path; OAuth-path emission sites pass through defaults (Pitfall 3 deferral).`

       Do NOT modify the OAuth-provider emission sites at providers.py:400-404 and 701-704 — they remain three-kwarg `Usage(...)` constructions; the new defaults keep them valid. The OAuth path's `message_start` cache-token capture is explicitly deferred per RESEARCH.md Pitfall 6 / Open Question 1.

    (2) Extend the agent.py Usage consumer + telemetry emit per T4-PATTERNS.md "Streaming Usage consumer" + "Telemetry emit-site":

       After the existing `iter_completion_tokens = ...` block (agent.py:620-622), add two analogous extraction blocks for `iter_cache_creation` and `iter_cache_read` using the same `if this_iter_usage else 0` guard pattern.

       In the existing `telemetry.emit("provider.response", "info", data={...})` block (agent.py:645-658), add the two new flat keys `cache_creation_input_tokens: iter_cache_creation` and `cache_read_input_tokens: iter_cache_read` AFTER `stop_reason`. Order within the dict: existing keys unchanged, the two new keys land at the end (matches T4-PATTERNS.md insertion point — `# T4 CACHE-07: flat additive keys, NO nested cache: {...} sub-object`).

       Do NOT introduce a `cache: {}` sub-object. D-05 lock.

    (3) Turn the T4-01 streaming stub `tests/harness/test_streaming_usage_cache.py::test_stream_usage_event_carries_cache_tokens` GREEN. Recommended approach (the simpler of two options): a UNIT test that constructs a `Usage(prompt_tokens=100, completion_tokens=50, cost_usd=0.01, cache_creation_input_tokens=1500, cache_read_input_tokens=0)` directly and asserts both new fields. This proves the dataclass-shape extension is wired correctly without spinning up the full SSE-fixture harness. The cassette integration test in T4-06 covers the end-to-end streaming surface; this unit test covers the data-shape contract per VALIDATION.md test map row "CACHE-02 (stream)".

       Add a second test in the same file: `test_usage_defaults_to_zero_cache_fields` constructs `Usage(prompt_tokens=1, completion_tokens=1, cost_usd=0.0)` (pre-T4 three-kwarg shape) and asserts both new fields == 0. This proves the additive-defaults contract for the OAuth emission sites that don't pass cache kwargs.

    (4) Turn the T4-01 telemetry stub `tests/harness/test_telemetry_cache_fields.py::test_provider_response_event_carries_cache_tokens` GREEN. Use the analog at `tests/harness/test_telemetry.py::test_emit_writes_ndjson_file` (lines 46-69) per T4-PATTERNS.md:

       Set `VOSS_LOG=1` + `VOSS_LOG_PATH=<tmp>` via monkeypatch, reset/begin a turn, directly `telemetry.emit("provider.response", "info", data={"model": "claude-sonnet-4-5", "cost_usd": 0.012, "cache_creation_input_tokens": 1500, "cache_read_input_tokens": 0})`, finalize, then read the NDJSON file and assert the readback event's `data["cache_creation_input_tokens"] == 1500` and `data["cache_read_input_tokens"] == 0`. This tests the telemetry payload shape; the agent.py emit-site is covered by integration in T4-06.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_streaming_usage_cache.py tests/harness/test_telemetry_cache_fields.py::test_provider_response_event_carries_cache_tokens tests/harness/test_oauth_provider.py tests/harness/test_anthropic_stream.py tests/harness/test_openai_stream.py -x -q</automated>
  </verify>
  <done>
    Streaming + telemetry tests green. The OAuth stream tests still pass (proves the additive defaults don't break the existing three-kwarg `Usage(...)` construction sites at providers.py:400-404 and 701-704). No nested `cache: {...}` sub-object introduced anywhere.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend IterationRecord + RunRecorder.end_iteration + turn round-trip tests green</name>
  <files>voss/harness/session.py, voss/harness/recorder.py, voss/harness/agent.py, tests/harness/test_telemetry_cache_fields.py</files>
  <behavior>
    - `IterationRecord(index=0)` constructs with both new cache fields defaulting to 0.
    - Old-fixture dict (no cache keys) round-trips through `IterationRecord(**old_iter)` with both fields defaulting to 0.
    - `dataclasses.asdict(IterationRecord(index=0, cache_creation_input_tokens=1500, cache_read_input_tokens=200))` then `IterationRecord(**d)` preserves both values.
    - `RunRecorder.end_iteration(... cache_creation_input_tokens=1500, cache_read_input_tokens=200, ...)` writes those values onto the target IterationRecord.
    - agent.py's existing `rec.end_iteration(... prompt_tokens=..., completion_tokens=..., ...)` call site passes the two new kwargs alongside the existing token kwargs.
  </behavior>
  <action>
    (1) Extend `voss/harness/session.py::IterationRecord` (lines 96-109) with two additive int=0 fields placed IMMEDIATELY AFTER `completion_tokens: int = 0` (line 105) and BEFORE `started_at: str = ""` (line 106). Field order: index, plan, tool_results, cost_usd, prompt_tokens, completion_tokens, **cache_creation_input_tokens: int = 0**, **cache_read_input_tokens: int = 0**, started_at, ended_at, exit_reason, batches. Add comment `# T4 CACHE-07 (Pitfall 8 / Open Question 3): additive defaults preserve pre-T4 session JSON round-trip.` above the two new fields.

       Do NOT modify BatchRecord, RunRecord, SessionRecord, EXIT_REASONS, or `_hydrate`. Pre-T4 sessions hydrate via `_hydrate` (line 184-188) which filters unknown keys — additive new fields default to 0 when old JSON lacks them.

    (2) Extend `voss/harness/recorder.py::RunRecorder.end_iteration` (lines 116-150) per T4-PATTERNS.md: add two new keyword-only parameters `cache_creation_input_tokens: int = 0` and `cache_read_input_tokens: int = 0` to the signature (place them adjacent to `prompt_tokens` and `completion_tokens`). In the body, after the existing `target.completion_tokens = completion_tokens` line (148), add the two mirror assignments. Do NOT modify `begin_iteration`, `begin_batch`, `end_batch`, or `finalize`.

       Optional: extend `finalize` to sum cache totals onto RunRecord — but RunRecord does NOT carry cache totals today per SPEC scope (CACHE-07 specifies IterationRecord round-trip only, not RunRecord aggregates). Skip this. If a future plan wants RunRecord cache totals, it's additive.

    (3) Locate the agent.py call site of `rec.end_iteration(...)` (search agent.py for `end_iteration(`) and add the two new kwargs alongside `prompt_tokens=iter_prompt_tokens, completion_tokens=iter_completion_tokens,`. Pass `cache_creation_input_tokens=iter_cache_creation, cache_read_input_tokens=iter_cache_read,`. This is purely additive — pre-T4 signature compatibility preserved by the defaults.

    (4) Turn the two T4-01 round-trip stubs in `tests/harness/test_telemetry_cache_fields.py` GREEN per T4-PATTERNS.md:
       - `test_iteration_record_cache_fields_default_zero_for_old_fixtures`: construct an old-shape dict (no cache keys) and unpack into `IterationRecord(**old_iter)`; assert both fields == 0.
       - `test_iteration_record_cache_fields_round_trip`: construct an IterationRecord with both cache fields populated, `dataclasses.asdict()` then unpack back; assert both values preserved.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_telemetry_cache_fields.py tests/harness/test_session_iterations.py tests/harness/test_agent_loop.py tests/harness/test_agent_integration.py -x -q</automated>
  </verify>
  <done>
    Round-trip tests green. Existing IterationRecord / session round-trip tests (test_session_iterations.py) still pass — proves additive defaults preserve pre-T4 fixtures. The agent.py `end_iteration` call site passes the two new kwargs without breaking existing agent-loop tests.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| stream→harness | LiteLLM streaming aggregates cache tokens onto the final Usage chunk; OAuth path defers (Pitfall 3). |
| recorder→disk | IterationRecord serializes via dataclasses.asdict → JSON. Additive defaults preserve pre-T4 session files. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T4-04-01 | Repudiation | provider.response telemetry | mitigate | Flat-dict cache fields preserved through NDJSON serialization; CACHE-07 readback test asserts they round-trip. Falsifiability anchor against silent payload drift. |
| T-T4-04-02 | Tampering | IterationRecord round-trip | mitigate | Additive int=0 defaults; `_hydrate` filter (session.py:184-188) drops unknown keys from old JSON, new keys absent → default to 0. test_iteration_record_cache_fields_default_zero_for_old_fixtures is the contract test. |
| T-T4-04-03 | Information Disclosure | NDJSON telemetry | accept | Telemetry payload contains model name + token counts + cost; no API keys, no user content. Existing redact_tool_args pattern still applies to tool args; cache token counts are non-sensitive. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_streaming_usage_cache.py tests/harness/test_telemetry_cache_fields.py -x -q` exits 0.
- `python3 -m pytest tests/harness/test_session_iterations.py tests/harness/test_oauth_provider.py tests/harness/test_anthropic_stream.py tests/harness/test_openai_stream.py tests/harness/test_agent_loop.py tests/harness/test_agent_integration.py -x -q` exits 0 (no regression).
- `grep -nE 'cache_creation_input_tokens|cache_read_input_tokens' voss/harness/providers.py voss/harness/session.py voss/harness/recorder.py voss/harness/agent.py | wc -l` returns ≥10 (2 Usage field defs + 2 IterationRecord field defs + 2 end_iteration signature params + 2 end_iteration body assignments + 2 agent.py consumer extractions + 2 telemetry data dict keys + 2 agent.py end_iteration call-site kwargs).
- `grep -c '"cache":\s*{' voss/harness/agent.py` returns 0 (D-05 flat-shape lock — no nested sub-object).
</verification>

<success_criteria>
- `ProviderStreamEvent.Usage` carries two additive int=0 cache fields; OAuth-provider emission sites still construct with three positional kwargs and the new defaults preserve correctness for the deferred OAuth-cache path.
- `agent.py` Usage consumer + telemetry emit propagate the values through with NO nested `cache: {}` sub-object.
- `IterationRecord` round-trips both old (no cache keys) and new (with cache values) fixtures.
- `RunRecorder.end_iteration` accepts two new keyword-only int kwargs, defaulted; the agent.py call site passes them.
- All four T4-01 stubs for CACHE-02-stream + CACHE-07 (telemetry + round-trip × 2) are GREEN.
- No regression in existing OAuth provider, stream, agent-loop, or session-iteration tests.
- OAuth-path cache-token capture remains explicitly deferred per RESEARCH.md Pitfall 3 / Pitfall 6.
</success_criteria>

<output>
Create `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-04-SUMMARY.md` when done. Note the OAuth-path Usage emission sites at providers.py:400-404 and 701-704 are intentionally untouched (additive defaults handle them).
</output>
