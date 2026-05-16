# Phase T4: Prompt Caching + Cost Truthfulness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** T4-prompt-caching-cost-truthfulness
**Areas discussed:** Streaming Usage event extension, LiteLLM block-list passthrough, Cache-token extraction, vcrpy cassette location + protocol, Extractor module location, Telemetry event shape

---

## Streaming Usage event extension

| Option | Description | Selected |
|--------|-------------|----------|
| Extend Usage variant additively + ProviderResponse symmetrically | Same cache fields on T1's `ProviderStreamEvent.Usage` AND on `ProviderResponse`. Single extractor; agent.py reads cache values off the streamed Usage event without branching. | ✓ |
| Non-streaming ProviderResponse only | Literal SPEC CACHE-02 text. Streaming path stays unchanged. Means telemetry never sees cache numbers in practice because agent.py uses streaming. | |
| New separate ProviderStreamEvent variant `CacheUsage(creation, read)` | New union variant emitted at stream end. Cleaner separation, more surface area. | |

**User's choice:** Extend Usage + ProviderResponse symmetrically
**Notes:** Symmetric extension is the natural fit since agent.py:596 already consumes `Usage` events; capturing cache fields on the streaming event keeps telemetry and RunRecord consistent.

---

## LiteLLM block-list passthrough verification

| Option | Description | Selected |
|--------|-------------|----------|
| Researcher pins the exact LiteLLM passthrough mechanism | Block Wave 1 on researcher: inspect `litellm.llms.anthropic` source, verify GA status of prompt-caching (no beta header), record a live call to confirm markers reach the wire. Document required kwarg if any. | ✓ |
| Assume passthrough works — verify only via integration test | Skip protocol research; trust cassette behavior. Risk: silently-stripped markers + writes-only test passes but reads never fire. | |
| Send Anthropic-native kwarg explicitly in LiteLLMProvider | Always emit `extra_body={"system": [...]}` for Claude models. Bypasses LiteLLM's transform. Heaviest option, provider-detection coupling. | |

**User's choice:** Researcher pins the exact LiteLLM passthrough mechanism
**Notes:** D-02 in CONTEXT becomes a research-blocker for Wave 1.

---

## Cache-token extraction strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Probe both shapes universally (no model detection) | Try Anthropic `usage.cache_creation_input_tokens`/`cache_read_input_tokens` AND OpenAI `usage.prompt_tokens_details.cached_tokens` on every response. Missing fields default to 0. Stub + future Gemini work without code change. | ✓ |
| Branch on model.startswith('claude') vs 'gpt' | Explicit string match; brittle to model renames. | |
| Inspect `_hidden_params.custom_llm_provider` | LiteLLM tags provider on each response. Provider-accurate but couples to LiteLLM internals. | |

**User's choice:** Probe both shapes universally
**Notes:** Single source of truth in `extract_cache_tokens()`. Avoids `model.startswith(...)` strings everywhere.

---

## vcrpy cassette location + record protocol

| Option | Description | Selected |
|--------|-------------|----------|
| `tests/harness/fixtures/cassettes/` + `VOSS_RECORD=1` env var | Co-located. Replay by default; record on env var. `filter_headers` for API keys. YAML cassettes committed to git. CI replay-only. | ✓ |
| `tests/fixtures/cassettes/` + standalone `scripts/record_cassettes.py` | Centralized fixtures dir; dedicated record script. More setup. | |
| `tests/cassettes/` + auto-record-if-missing, fail-in-CI-if-missing | Smallest surface; catches forgotten-commit cases. | |

**User's choice:** `tests/harness/fixtures/cassettes/` + `VOSS_RECORD=1` env var
**Notes:** Matches existing `tests/harness/fixtures/` convention. vcrpy `record_mode='none'` raises on missing cassette in CI.

---

## Cache-token extractor module location

| Option | Description | Selected |
|--------|-------------|----------|
| `voss_runtime/providers/_cache_tokens.py` (new shared util) | Pure function `extract_cache_tokens(usage_obj) -> (int, int)`. Both streaming and non-streaming providers import it. Mirrors T3 D-15 `redact_url` placement. | ✓ |
| Inline in `LiteLLMProvider.complete` + duplicate in stream path | Two call sites, two inline blocks. Drift risk if cache schemas evolve. | |
| Method on `ProviderResponse` / `Usage` dataclass | Classmethod constructor-style. Couples dataclass to LiteLLM-shape input; doesn't fit frozen union variants. | |

**User's choice:** New shared util at `voss_runtime/providers/_cache_tokens.py`
**Notes:** Mirrors T3 `redact_url` pattern (pure function in a peer module).

---

## Telemetry event data dict shape

| Option | Description | Selected |
|--------|-------------|----------|
| Flat keys: `cache_creation_input_tokens` + `cache_read_input_tokens` | Mirrors Anthropic API field names. Matches existing flat data dict convention (`cognition.snapshot` uses `architecture_tokens`, `constraints_count`). | ✓ |
| Nested `cache: {creation: N, read: M}` sub-object | Logically grouped; adds one dict-deref layer. Breaks flat convention. | |

**User's choice:** Flat keys
**Notes:** Reuses existing `provider.response` event (no new event type).

---

## Claude's Discretion

- Exact name of the agent.py helper that builds the block list (suggest: `_compose_system_blocks`).
- Whether `_compose_loop_system` is refactored to return a block dict or stays string-returning and is consumed by `_compose_system_blocks`. Recommend the latter.
- Cassette response-body redaction details beyond header filtering.
- Tuple vs small dataclass return for `extract_cache_tokens` (recommend tuple).
- Whether `harness.toml` `[cache]` diagnostic block exposes the 5-min TTL as a read-only field (recommend code comment until needed).

## Deferred Ideas

- Caching `tools[]` schema array (v0.3+ candidate).
- Caching per-iteration replay history (incoherent — mutates every iter).
- 1-hour extended cache (Anthropic beta).
- Per-tool cost attribution (T6 SLASH-07).
- Token-cost dashboards / historical persistence.
- `AnthropicProvider` subclass.
- Model-swap cache-miss test (inherent, documented only).
- `[cost]` config block / hard-coded pricing.
- `/cost --by-cache` breakdown (uncached/create/read/output).
- Cache-hit session-exit summary roll-up.
