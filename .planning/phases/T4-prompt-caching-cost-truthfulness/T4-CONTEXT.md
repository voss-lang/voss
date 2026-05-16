# Phase T4: Prompt Caching + Cost Truthfulness — Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**SPEC:** `T4-SPEC.md` — 7 requirements locked (CACHE-01..CACHE-07), ambiguity 0.13

<domain>
## Phase Boundary

Restructure the system prompt in `voss/harness/agent.py` as a list of content blocks with one trailing `cache_control: {type: "ephemeral"}` marker on the static prefix (VOSS.md + cognition + prior_context + loop_system), so the Anthropic API caches it for 5 minutes and bills cache_creation on the first turn and cache_read on subsequent turns. Capture both Anthropic and OpenAI cache token counts on the streaming Usage event AND the non-streaming ProviderResponse symmetrically. Continue trusting LiteLLM's pre-computed `response_cost` — no Voss-owned pricing table. Prove cache HIT end-to-end via one vcrpy cassette in `tests/harness/fixtures/cassettes/`. Verify `/cost --by-model` to 4-decimal accuracy. Defer `/cost --by-tool` to T6 SLASH-07. Requirements (WHAT) are locked by SPEC.md. This document captures HOW.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**7 requirements are locked.** See `T4-SPEC.md` for full requirements (CACHE-01..CACHE-07), boundaries, constraints, and 8 acceptance criteria.

Downstream agents MUST read `T4-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Multi-block system prompt restructure with one trailing `cache_control: ephemeral` marker on the static prefix.
- Cache-token capture in `ProviderResponse` (Anthropic + OpenAI extraction).
- Trusted LiteLLM `response_cost` extraction — no Voss-owned pricing table.
- Verification of `/cost --by-model` to 4 decimals.
- vcrpy-recorded Anthropic cassette integration test for end-to-end cache HIT proof.
- Cache invalidation unit tests for four locked drift triggers.
- First-turn cache-write invariant.
- `provider.response` telemetry event gains two cache-token fields additively.

**Out of scope (from SPEC.md):**
- Caching `tools[]` schema array.
- Caching per-iteration replay history.
- Adaptive cache TTL or 1-hour extended-cache beta.
- Per-tool cost attribution / `/cost --by-tool` (T6 territory).
- Cost dashboards / historical persistence beyond `SessionRecord.total_cost_usd`.
- Dedicated `AnthropicProvider` subclass.
- Explicit model-swap cache-miss test.
- Hard-coded pricing multipliers / `[cost]` config block.

</spec_lock>

<decisions>
## Implementation Decisions

### Data shape extension (Usage + ProviderResponse symmetric)

- **D-01:** Additive fields `cache_creation_input_tokens: int = 0` and `cache_read_input_tokens: int = 0` land on BOTH the T1 streaming variant `ProviderStreamEvent.Usage(prompt_tokens, completion_tokens, cost_usd)` AND the non-streaming `ProviderResponse` dataclass at `voss_runtime/providers/base.py`. Symmetric — same field names, same defaults, same extractor. Agent.py's stream consumer at line 596 reads them off the `Usage` event at stream-end without branching streaming vs non-streaming. RunRecord round-trip preserves them additively (pre-T4 fixtures still deserialize because defaults=0). Mirrors T2 D-additive-IterationRecord pattern.

### LiteLLM passthrough mechanism (RESEARCHER blocker)

- **D-02:** Open question for `gsd-phase-researcher` to pin before plans land: when LiteLLMProvider.complete (and the streaming path) sends `messages = [{"role": "system", "content": [{"type": "text", "text": "..."}, {"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}]}, ...]`, does LiteLLM v1.50+ pass that block-list shape through to the Anthropic Messages API verbatim, OR does it require an additional kwarg (e.g., `extra_body={"system": [...]}` or beta-header flag) to bypass LiteLLM's message-massaging pipeline? Researcher: (a) inspect `litellm.llms.anthropic` source for the system-message transform; (b) confirm Anthropic's `prompt-caching` is now GA (no beta header required); (c) record a live `litellm.acompletion` call against `claude-sonnet-4-6` and inspect the outbound HTTPX request body to verify markers are present; (d) document the exact required kwarg if any. Blocks Wave 1 of the plan.

### Cache-token extraction (universal probe, no model detection)

- **D-03:** Pure function `extract_cache_tokens(usage_obj) -> tuple[int, int]` returns `(creation, read)`. Behavior: try `getattr(usage_obj, "cache_creation_input_tokens", 0)` and `getattr(usage_obj, "cache_read_input_tokens", 0)` for the Anthropic shape; for OpenAI's shape, descend through `getattr(usage_obj, "prompt_tokens_details", None)` and read `.cached_tokens` if present, treating it as the `cache_read` count (OpenAI has no client-visible creation count, so creation stays 0). Missing fields default to 0. NO `model.startswith(...)` branching — both shapes probed universally. Stub provider's usage returns `(0, 0)` naturally. Future Gemini works without code change.

### Extractor module location

- **D-04:** The pure function lives at `voss_runtime/providers/_cache_tokens.py` (new private module). Imports: stdlib only. Both `LiteLLMProvider.complete` (line 42 area) and the streaming Usage emission path import it. Tests at `tests/harness/test_cache_tokens.py` assert all three shapes: Anthropic SimpleNamespace, OpenAI nested `prompt_tokens_details.cached_tokens`, missing fields → (0, 0). Mirrors the `redact_url` placement convention from T3 D-15 (pure pure-Python function in a peer module alongside the provider it serves).

### Telemetry event shape (flat, additive)

- **D-05:** The existing `provider.response` telemetry event's `data` dict gains two new keys at the SAME nesting depth as existing fields: `cache_creation_input_tokens: int` and `cache_read_input_tokens: int`. NO nested `cache: {...}` sub-object — flat shape matches the existing convention in `cognition.snapshot` (`architecture_tokens`, `constraints_count`) and other harness events. Pre-T4 events round-trip with absent keys treated as 0 by consumers; RunRecord deserializer is tolerant. No new event type (`provider.cache` was considered in SPEC R3 and explicitly rejected — reuses `provider.response`).

### Pricing posture (trust LiteLLM exclusively)

- **D-06:** `cost_usd` continues to flow from `resp._hidden_params.response_cost`. NO Voss-owned pricing module, NO hard-coded multipliers, NO `[cost]` config block. CACHE-03 acceptance test asserts LiteLLM's cost is cache-aware by comparing two fixture responses (one with `cache_creation_input_tokens > 0`, one with both cache fields 0) and confirming the first has strictly higher cost. `pyproject.toml` requires `litellm >= 1.50.0` (exact pin set at plan time after researcher's protocol verification in D-02).

### vcrpy cassette location + protocol

- **D-07:** Cassettes live at `tests/harness/fixtures/cassettes/` (co-located with the harness test suite, mirrors `tests/harness/fixtures/` convention). vcrpy is added to `[project.optional-dependencies] dev` or `[tool.pytest]` (researcher confirms exact location during plan). Recording protocol: `VOSS_RECORD=1 pytest tests/harness/test_cache_integration.py` makes live Anthropic calls and writes/overwrites cassettes; absence of `VOSS_RECORD` means replay-only. CI runs without the env var → pure replay. vcrpy config: `filter_headers=['x-api-key', 'authorization', 'anthropic-api-key', 'cookie']`, `record_mode='none'` by default (raises if cassette missing), `record_mode='new_episodes'` when `VOSS_RECORD=1`. Cassettes committed as YAML (vcrpy default; human-readable diffs). Cassette filename = test function name + `.yaml`.

### Cache invalidation triggers (CACHE-06 — locked four)

- **D-08:** Four drift triggers that MUST invalidate the cacheable prefix between turns (each gets a parametrized unit test in `tests/harness/test_cache_invalidation.py`):
  - VOSS.md text changes
  - Project cognition (architecture text OR constraints rules list) changes
  - `[agent] max_iterations` config value changes (changes `_compose_loop_system` output)
  - `prior_context` block content changes (M8 project memory feeds this)
  Model swap mid-session ALSO misses the cache but that is inherent to Anthropic's per-model keying — documented in CONTEXT but NOT covered by a Voss-side test. Each drift test perturbs ONE source between two simulated turns and asserts the rendered block-list content differs by ≥1 byte, forcing a cache miss.

### CLI placeholder update

- **D-09:** `voss/harness/cli.py:545-551` currently prints `"/cost --by-tool: per-tool cost tracking lands with T4 (prompt caching). Recorder doesn't yet attribute provider cost to individual tool calls."`. Update the message string to reference T6 SLASH-07 instead of T4 (no other code change to `--by-tool`). Single-line edit.

### Claude's Discretion

These were not explicitly asked but are implementation-natural; downstream agents may pick reasonable shapes:

- Exact name of the agent.py helper that builds the block list (suggest: `_compose_system_blocks(...) -> list[dict]`).
- Whether to keep `_compose_loop_system(max_iterations)` as a string-returning helper and have `_compose_system_blocks` consume its output, or to refactor it to return a block dict directly. Recommend the former — less surface area.
- Exact cassette redaction logic for response bodies (no API keys in responses, but safety belt against future fields).
- Whether `extract_cache_tokens` returns `(creation, read)` tuple or a small dataclass `CacheTokens(creation, read)` — recommend tuple for simplicity.
- Whether to add a `harness.toml` `[cache]` diagnostic block exposing the 5-minute TTL as a read-only field, or just document the TTL in a code comment. Recommend code comment until a real need for runtime introspection emerges.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase artifacts (locked)

- `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-SPEC.md` — **Locked requirements (CACHE-01..CACHE-07) — MUST read before planning. 8 pass/fail acceptance criteria.**
- `.planning/ROADMAP.md` §"Phase T4 — Prompt Caching + Cost Truthfulness" — phase goal + cross-cutting constraints (cache key stability, 5-min TTL).
- `.planning/REQUIREMENTS.md` — no CACHE-* requirements at the project level; CACHE-* are phase-scoped via SPEC.md.

### Codebase anchors (read before touching)

- `voss/harness/agent.py:272-307` — `_compose_loop_system` + `_build_iter_rider` separation (T1 deliberately split for T4 caching).
- `voss/harness/agent.py:486-503` — current `sys_prompt = "\n\n".join(...)` composition (the joined string to be replaced by a block list).
- `voss/harness/agent.py:556-560` — `messages` list construction; current `{"role": "system", "content": sys_prompt}` shape. Replace `content` with a block list for the static prefix; rider stays a separate `{"role": "system", "content": rider}` entry.
- `voss/harness/agent.py:584-600` — `provider.stream(...)` loop; `event is Usage` branch at line 596 reads cache fields after D-01.
- `voss_runtime/providers/base.py:7-19` — `ProviderResponse` dataclass; CACHE-02 adds two additive int fields.
- `voss_runtime/providers/litellm_provider.py:42-60` — `usage = resp.usage` site; calls D-03 extractor and populates new fields.
- `voss/harness/providers.py` — `ProviderStreamEvent.Usage` variant location (T1 union); CACHE-02 extends additively.
- `voss/harness/cli.py:542-580` — `/cost` slash command; verify `--by-model` math; update `--by-tool` placeholder string (D-09).
- `voss/harness/session.py:80-140` — `RunRecord` / `IterationRecord` / `SessionRecord` schema; ensure cache fields round-trip if they end up on per-turn records (planner decides; SPEC mandates telemetry event but not recorder fields).
- `voss/harness/recorder.py:25-160` — `RunRecorder` shape; consult for whether to add cache aggregates.
- `voss/harness/telemetry.py` — `emit` site for `provider.response` event; D-05 extends event payload.
- `pyproject.toml` — `litellm` version pin floor for D-06 (≥1.50.0).

### Cross-phase context

- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md` — established `ProviderStreamEvent.Usage` variant and PLAN_LOOP_SYSTEM/rider split specifically reserving T4 caching territory.
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md` — `[agent] max_iterations` TOML loader pattern (relevant for D-08 invalidation test).
- `.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md` — additive-dataclass-extension pattern; LiteLLM trust posture for cost.
- `.planning/phases/T3-network-surface/T3-CONTEXT.md` D-15 — `redact_url` pure-function placement (D-04 mirrors this).

### External protocol

- Anthropic prompt-caching API reference — researcher pins the exact URL + GA status (no beta header required as of 2025-Q4, but verify). Specifically the `cache_control: {"type": "ephemeral"}` block shape on `system` content array and the `usage.cache_creation_input_tokens` / `usage.cache_read_input_tokens` response fields.
- OpenAI prompt caching docs — automatic for prompts > 1024 tokens; reports `usage.prompt_tokens_details.cached_tokens`. Pin URL.
- LiteLLM v1.50+ Anthropic provider source (`litellm.llms.anthropic.chat`) — researcher inspects for the system-message transform path to answer D-02.
- vcrpy docs — `filter_headers`, `record_mode`, default YAML serializer.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_compose_loop_system(max_iterations)`** at `agent.py:272-274` — current `str.replace` placeholder filler. Output flows into the cacheable prefix; refactor is a one-line wrapper or leave as-is and have `_compose_system_blocks` consume its string output.
- **`_build_iter_rider`** at `agent.py:277-307` — already separate from the cacheable prefix. No change needed.
- **`telemetry.emit("provider.response", ...)`** call site (existing) — D-05 adds two flat keys to the `data` dict; no new event type.
- **`ProviderResponse`** dataclass at `base.py:7-19` — additive extension only; existing `prompt_tokens`/`completion_tokens`/`cost_usd` untouched.
- **LiteLLM `resp._hidden_params.response_cost`** at `litellm_provider.py:43` — continues to be the sole cost source.

### Established Patterns

- **Additive dataclass extension** — T1/T2 set the precedent; backward-compatible defaults (`= 0`) keep pre-T4 fixtures and the stub provider working.
- **Pure helper functions in peer modules** — T3 D-15 placed `redact_url` in `telemetry.py` as a peer to the consumer; D-04 places `extract_cache_tokens` in `_cache_tokens.py` peer to `litellm_provider.py`.
- **Flat telemetry data dicts** — `cognition.snapshot` and other events use flat keys; D-05 follows.
- **String returns for static composition** — `_compose_loop_system` returns a string; the new `_compose_system_blocks` returns `list[dict]` (the shape Anthropic + LiteLLM expect).
- **`<error: ...>` envelopes are unchanged** — caching has no failure mode that propagates to tool result envelopes (cache misses are silent; provider errors surface as before).

### Integration Points

- **`agent.py` system-message composition** — primary change site for CACHE-01.
- **`LiteLLMProvider.complete`** — calls `extract_cache_tokens(resp.usage)` and populates new `ProviderResponse` fields (CACHE-02).
- **Streaming Usage event emission** — provider's stream emitter calls `extract_cache_tokens` and includes the values on the emitted `Usage` event (CACHE-02 streaming half).
- **`provider.response` telemetry event** — emit site already exists; D-05 adds two keys to `data`.
- **`/cost --by-model`** — verify accuracy; no code change unless the test fails.
- **`/cost --by-tool` placeholder string** — single-line update to reference T6 SLASH-07 instead of T4 (D-09).
- **`pyproject.toml`** — `litellm >= 1.50.0` pin (D-06).
- **`tests/harness/fixtures/cassettes/`** — new directory for vcrpy YAML files (D-07).

</code_context>

<specifics>
## Specific Ideas

- **The PLAN_LOOP_SYSTEM/rider split at `agent.py:272-307` already anticipates T4** — the in-code comment at lines 287-289 explicitly cites "future T4 caching" as the reason. CACHE-01 finishes that work by materializing the cache_control marker on the static prefix.
- **Trust LiteLLM, don't reinvent pricing** (Round 2 decision) — Voss owns cache-aware ACCOUNTING (capture token counts) and cache-aware OBSERVABILITY (telemetry + /cost surfaces); pricing math stays with LiteLLM. Symmetric to T2's "trust asyncio.gather" posture.
- **Universal probe over provider detection** (Round 1 Q3) — both Anthropic and OpenAI shapes attempted on every response; missing fields default to 0. Future Gemini works without code change; stub provider works without special-casing. Avoids `model.startswith(...)` brittleness.
- **`VOSS_RECORD=1` env var as the recording gate** — CI without the var → pure replay; local dev with the var → re-record. Catches "forgot to commit cassette" via record_mode='none' default raising on missing fixtures.
- **First-turn invariant is the falsifiability anchor** (SPEC CACHE-07) — without it, a degenerate implementation could pass the two-turn cache_read test by always reporting reads without ever writing. Test asserts cache_creation > 0 AND cache_read == 0 on the very first turn.

</specifics>

<deferred>
## Deferred Ideas

- **Caching the `tools[]` schema array** — Anthropic supports cache_control on tools too. Tool registry is more volatile than system text; burns the 4-marker budget on something that invalidates often. Revisit when v0.3+ adds more stable agent-specific tool sets.
- **Caching per-iteration replay history** — `agent.py:561-564` appends prior-iter messages that mutate every iter; caching is incoherent.
- **1-hour extended cache (Anthropic beta)** — T4 uses 5-minute default only. Revisit when latency-vs-cost analysis on real workloads shows the longer-TTV premium pays off.
- **Per-tool cost attribution** — T6 SLASH-07 territory. Needs `Recorder.tool_result` to gain `cost_usd` field; out of T4 scope.
- **Token-cost dashboards / historical cost store** — `SessionRecord.total_cost_usd` is the only persistence surface in v0.2. Revisit if a real reporting need surfaces.
- **`AnthropicProvider` subclass** — Round 1 decision rejected this. Provider-agnostic block-list format keeps LiteLLM as the single provider with no subclass tree.
- **Model-swap cache-miss test** — Per-model keying is inherent to Anthropic; documented but not separately asserted by Voss.
- **`[cost]` config block / hard-coded pricing multipliers** — D-06 rejected this; Voss trusts LiteLLM's `response_cost` exclusively.
- **`/cost --by-cache` breakdown** — Splitting cost into "uncached input / cache create / cache read / output" lines. Not in SPEC; nice-to-have for cost truthfulness deep-dive. v0.3+ candidate phase.
- **Cache-hit telemetry summary at session exit** — Roll-up of cache reads / writes / cost savings across the session. Not in SPEC; deferred.

</deferred>

---

*Phase: T4-prompt-caching-cost-truthfulness*
*Context gathered: 2026-05-16 via /gsd:discuss-phase T4*
*Next step: /gsd:plan-phase T4 — research and plan*
