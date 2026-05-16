# Phase T4: Prompt Caching + Cost Truthfulness — Specification

**Created:** 2026-05-16
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

Stop rebuilding and re-sending the static system-prompt prefix every turn by marking it
`cache_control: ephemeral` (Anthropic) and reading `cache_creation_input_tokens` +
`cache_read_input_tokens` (Anthropic) and `usage.prompt_tokens_details.cached_tokens` (OpenAI)
back into Voss's cost accounting so reported `cost_usd` matches what providers actually
billed, including cache writes and cache reads.

## Background

- Current system prompt is composed in `voss/harness/agent.py:494-503` as a single
  newline-joined string and sent as one `{"role": "system", "content": sys_prompt}` block
  at `agent.py:557`. There are no `cache_control` markers anywhere in the codebase.
- The static prefix has four candidate slices: `voss_md_block`, `cognition_text`,
  `prior_context_text`, `_compose_loop_system(max_iterations)`. The per-iter rider is
  intentionally separate at `agent.py:558` — the comment at `agent.py:287-289` explicitly
  calls out "future T4 caching" as the reason for that split.
- The single provider abstraction is `voss_runtime/providers/litellm_provider.py`.
  `ProviderResponse` (`base.py:8-15`) has `prompt_tokens`, `completion_tokens`, `cost_usd` —
  no cache token fields. Cost flows from `resp._hidden_params.response_cost` (LiteLLM
  pre-computes including cache rates for v1.50+).
- `/cost --by-model` works today (`cli.py:552-570`). `/cost --by-tool` currently prints
  "lands with T4" placeholder (`cli.py:545-551`) but per-tool attribution is deferred
  to T6 SLASH-07; T4 ships `--by-model` only.
- Session cost lives in `session.SessionRecord.total_cost_usd` (`session.py:132`); no cache
  breakdown is exposed.

## Requirements

1. **CACHE-01: Multi-block system prompt with single cache breakpoint**:
   Restructure `agent.py` to send the system prompt as a LIST of content blocks instead
   of one joined string. Append one `cache_control: {type: "ephemeral"}` marker at the
   end of the static prefix `[voss_md_block, cognition_text, prior_context_text, loop_system]`.
   The per-iter rider remains a separate uncached system message. Provider-agnostic
   format — LiteLLM passes the block list through to the Anthropic API unchanged.
   - Current: `sys_prompt = "\n\n".join(...)` produces a single string; `messages` list contains one system entry.
   - Target: The static prefix is sent as a list of `{"type": "text", "text": ...}` blocks with the trailing block carrying `"cache_control": {"type": "ephemeral"}`. Rider stays separate and uncached.
   - Acceptance: `tests/harness/test_agent_caching.py::test_system_blocks_have_single_marker` asserts the outbound `messages[0]["content"]` is a list of ≥1 block, exactly one block carries `cache_control: {type: "ephemeral"}`, and that block is the last static-prefix block (not the rider).

2. **CACHE-02: Cache-token capture in ProviderResponse**:
   Extend `ProviderResponse` with additive fields `cache_creation_input_tokens: int = 0`
   and `cache_read_input_tokens: int = 0`. `LiteLLMProvider.complete` populates these
   from `resp.usage` for Anthropic models (`usage.cache_creation_input_tokens` /
   `usage.cache_read_input_tokens`) and from `resp.usage.prompt_tokens_details.cached_tokens`
   for OpenAI models (cache reads only — OpenAI has no client-visible cache-create count).
   - Current: `ProviderResponse` has `prompt_tokens`, `completion_tokens`, `cost_usd` only.
   - Target: Two additional integer fields default-zero, populated when the provider response includes them; backward-compatible with the stub provider (still returns 0).
   - Acceptance: `tests/harness/test_provider_response.py::test_anthropic_usage_extraction` asserts both cache fields are read; `tests/harness/test_provider_response.py::test_openai_cached_tokens_extraction` asserts `cache_read_input_tokens` is populated from `prompt_tokens_details.cached_tokens` while `cache_creation_input_tokens` stays 0; pre-T4 fixtures still deserialize (additive field guarantee).

3. **CACHE-03: Trust LiteLLM's response_cost for cache-inclusive pricing**:
   `cost_usd` continues to flow from `resp._hidden_params.response_cost`. No new pricing
   module, no hard-coded rate multipliers, no `[cost]` config block. T4 relies on
   LiteLLM v1.50+ already pricing cache_creation at 1.25× and cache_read at 0.10× of the
   Anthropic input rate, and OpenAI cached at 0.50× of the OpenAI input rate. Voss's
   responsibility is verification, not pricing.
   - Current: `cost_usd` extracted from LiteLLM hidden params with no cache awareness on Voss's side.
   - Target: Same extraction path; no Voss-owned pricing constants. `pyproject.toml` pins `litellm >= 1.50.0` (current floor) — exact version pin set at planning time after verification against the live API.
   - Acceptance: `tests/harness/test_cost_accounting.py::test_litellm_cost_includes_cache_rates` asserts a recorded fixture with non-zero `cache_creation_input_tokens` produces a `cost_usd` strictly greater than the same response with `cache_creation_input_tokens = 0` (pricing is non-zero); `pyproject.toml` grep shows `litellm` with a `>=1.50.0` floor or higher.

4. **CACHE-04: `/cost --by-model` produces per-model cost breakdown to 4-decimal precision**:
   Existing `cli.py:_cost` `--by-model` flag is verified to sum per-run `cost_usd` per
   model and match `sum(per-turn cost_usd) by model` to 4 decimal places. No code change
   in `cli.py` if the existing impl already matches; otherwise tighten the implementation.
   `--by-tool` continues to print the "lands with T6" placeholder (no behavior change).
   - Current: `--by-model` exists at `cli.py:552-570` and aggregates by `record.model` per run; `--by-tool` returns the placeholder string.
   - Target: `--by-model` semantics confirmed correct via test; `--by-tool` placeholder text updated to reference T6 SLASH-07 instead of T4.
   - Acceptance: `tests/harness/test_cost_slash.py::test_by_model_matches_per_run_sum` constructs a SessionRecord with 3 runs across 2 models (mixed cache hits/misses), invokes `/cost --by-model`, and asserts each printed line matches `sum(run.cost_usd for run in record.runs if run.model == m)` to 4 decimal places; placeholder string for `--by-tool` contains "T6 SLASH-07".

5. **CACHE-05: Recorded-fixture integration test proves cache HIT across turns**:
   Add `tests/harness/test_cache_integration.py` using vcrpy-recorded HTTPX cassettes
   against real `claude-sonnet-4-6` (or current Anthropic model). The test runs two
   consecutive turns in a single `voss chat` session, replays the recorded cassette,
   and asserts the first turn shows `cache_creation_input_tokens > 0` AND
   `cache_read_input_tokens == 0`, while the second turn shows
   `cache_read_input_tokens > 0`. Cassettes live under `tests/fixtures/cassettes/`
   and are re-recorded manually (not in CI) when the prompt structure changes.
   - Current: No integration test for caching behavior; no recorded cassettes for provider responses.
   - Target: One pytest file with one cassette covering two turns; CI runs replay-only mode (no live network calls).
   - Acceptance: `pytest tests/harness/test_cache_integration.py -x` exits 0 in CI against the recorded cassette; the cassette file exists at the expected path; both turn-level assertions on cache_creation and cache_read tokens fire and pass.

6. **CACHE-06: Cache invalidation triggers documented and verified**:
   The cacheable static prefix invalidates (next turn shows `cache_creation_input_tokens > 0`
   again, not `cache_read_input_tokens`) when ANY of the following drift events occur
   between turns: (a) VOSS.md text changes, (b) project cognition (architecture text or
   constraints rules list) changes, (c) `[agent] max_iterations` config value changes,
   (d) `prior_context` block content changes. Model swap mid-session also misses the
   cache but that is inherent to Anthropic's per-model cache keying — documented but
   not separately tested by Voss.
   - Current: No code expresses these drift contracts; the cache hasn't existed.
   - Target: Each of (a)–(d) is asserted by a unit test that perturbs the corresponding source between two simulated turns and confirms the outbound `messages` block content differs by ≥1 byte, forcing a cache miss.
   - Acceptance: `tests/harness/test_cache_invalidation.py::test_{voss_md,cognition,max_iterations,prior_context}_drift_changes_prefix` — four parametrized cases, each constructs the system prefix with versions A and B differing only in the targeted slice, asserts the rendered block content differs.

7. **CACHE-07: First-turn invariant + telemetry**:
   On the very first turn of a `voss chat` session against a cache-eligible model
   (Anthropic), `cache_creation_input_tokens > 0` AND `cache_read_input_tokens == 0`.
   This is the falsifiability anchor that prevents a degenerate implementation passing
   the two-turn test by always reporting cache reads. Capture the cache token counts on
   the existing `provider.response` telemetry event payload (`data` dict gains
   `cache_creation_input_tokens` and `cache_read_input_tokens` keys, default 0 when
   absent). No new event type is introduced.
   - Current: First turn shows zero cache activity because no marker is sent; telemetry has no cache fields.
   - Target: First turn writes cache; telemetry data carries cache counts so RunRecord round-trip can be asserted.
   - Acceptance: `tests/harness/test_cache_integration.py::test_first_turn_writes_cache` (uses the same cassette as CACHE-05) asserts the first turn has `cache_creation_input_tokens > 0 AND cache_read_input_tokens == 0`; `tests/harness/test_telemetry_cache_fields.py::test_provider_response_event_carries_cache_tokens` asserts the `provider.response` event data dict contains both keys with correct values; RunRecord deserialize round-trip preserves them.

## Boundaries

**In scope:**
- Multi-block system prompt restructure in `agent.py` with one trailing `cache_control: ephemeral` marker on the static prefix.
- Cache-token capture in `ProviderResponse` (Anthropic + OpenAI extraction logic).
- Trusted LiteLLM `response_cost` extraction — no Voss-owned pricing table.
- Verification of `/cost --by-model` accuracy to 4 decimals.
- vcrpy-recorded Anthropic cassette integration test for end-to-end cache HIT proof.
- Cache invalidation unit tests for the four locked drift triggers (VOSS.md, cognition, max_iterations, prior_context).
- First-turn cache-write invariant.
- `provider.response` telemetry event additively gains two cache-token fields.

**Out of scope:**
- Caching the `tools[]` schema array — burns a marker budget slot; tool registry is more volatile than system text. Defer to a later phase.
- Caching per-iteration replay history (prior assistant/user messages appended at `agent.py:561-564`) — mutates every iter, caching is incoherent.
- Adaptive cache TTL or 1-hour extended-cache beta — T4 uses Anthropic's 5-minute default only.
- Per-tool cost attribution and `/cost --by-tool` semantics — T6 SLASH-07 territory; T4 only verifies `--by-model` and updates the placeholder string.
- Token-cost dashboards / historical persistence beyond `SessionRecord.total_cost_usd` — no new cost store.
- A dedicated `AnthropicProvider` subclass — the multi-block format is provider-agnostic; LiteLLM passes through.
- Explicit testing of model-swap cache miss — inherent to Anthropic's per-model keying; documented but not asserted.
- Hard-coded pricing multipliers in a Voss-owned `cost.py` module or `[cost]` config block — T4 trusts LiteLLM exclusively.

## Constraints

- **Cache key stability:** The cacheable prefix is a function of (VOSS.md, cognition text, constraints rules list, prior_context, `_compose_loop_system(max_iterations)`). Drift in any input invalidates — acceptable per ROADMAP cross-cutting constraint.
- **Cache TTL:** 5 minutes (Anthropic default). Documented in `harness.toml` `[cache]` block as a read-only diagnostic field; no runtime configuration of TTL in T4.
- **LiteLLM floor:** `pyproject.toml` requires `litellm >= 1.50.0` for cache-aware cost computation. Exact pin set at planning time after verification.
- **Provider scope:** Caching applies when model is Anthropic Claude family (cache_control marker) or OpenAI (auto-cache for prompts > 1024 tokens). Other providers (stub, future Gemini) treat cache fields as zero and report unmodified cost.
- **Backward compatibility:** `ProviderResponse` field additions are additive defaults (= 0); existing fixtures and stub provider responses deserialize without change.
- **No new external dependencies:** vcrpy is the one new test-only dep added under `[tool.pytest]` dev-deps. No new runtime deps.

## Acceptance Criteria

- [ ] `pytest tests/harness/test_agent_caching.py -x` passes (CACHE-01 marker shape and position).
- [ ] `pytest tests/harness/test_provider_response.py -x` passes (CACHE-02 cache-token extraction for both Anthropic and OpenAI usage shapes).
- [ ] `pytest tests/harness/test_cost_accounting.py::test_litellm_cost_includes_cache_rates -x` passes AND `grep "litellm" pyproject.toml` shows `>=1.50.0` or higher floor (CACHE-03).
- [ ] `pytest tests/harness/test_cost_slash.py -x` passes (CACHE-04 `--by-model` matches 4-decimal sum; `--by-tool` placeholder cites T6 SLASH-07).
- [ ] `pytest tests/harness/test_cache_integration.py -x` passes against the committed vcrpy cassette without making live network calls (CACHE-05 + CACHE-07 first-turn invariant).
- [ ] `pytest tests/harness/test_cache_invalidation.py -x` passes — all four drift triggers (VOSS.md, cognition, max_iterations, prior_context) produce a different rendered prefix (CACHE-06).
- [ ] `pytest tests/harness/test_telemetry_cache_fields.py -x` passes — `provider.response` event payload carries both cache-token fields; RunRecord round-trip preserves them (CACHE-07).
- [ ] `voss chat` session against a real Anthropic model shows turn 2+ with non-zero `cache_read_input_tokens` in the recorded RunRecord (manual smoke test; not gating CI).

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                 |
|--------------------|-------|------|--------|-----------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Single-breakpoint cache slice + multi-block restructure pinned        |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | 8 out-of-scope items locked; CACHE-03/04 phase boundaries explicit    |
| Constraint Clarity | 0.85  | 0.65 | ✓      | LiteLLM trust, TTL=5min, additive ProviderResponse fields documented  |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 8 pass/fail checkboxes including first-turn falsifiability anchor      |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      | Gate passed after 3 rounds                                            |

## Interview Notes

- **Round 1 (Researcher):** Confirmed there's no dedicated AnthropicProvider — provider-agnostic multi-block format chosen over a subclass to avoid restructuring the provider hierarchy. CACHE-03 split: `--by-model` lands in T4, `--by-tool` stays T6. CACHE-04 expanded to cover OpenAI's auto-caching path with full cached-token extraction + Anthropic pricing parity via LiteLLM.
- **Round 2 (Researcher + Simplifier):** Single cache breakpoint chosen over 2- or 4-marker variants — simpler invalidation, matches roadmap intent literally, leaves marker budget room. LiteLLM `response_cost` trusted exclusively — no Voss-owned pricing constants. Integration test via recorded HTTPX cassettes for deterministic CI.
- **Round 3 (Boundary Keeper):** Four invalidation triggers locked (VOSS.md, cognition, max_iterations, prior_context). Model swap NOT explicitly tested — inherent to Anthropic's per-model keying, documented but not asserted. First-turn invariant added as falsifiability anchor against degenerate implementations that fake cache reads.

---

*Phase: T4-prompt-caching-cost-truthfulness*
*Spec written: 2026-05-16 via /gsd:spec-phase T4*
*Next step: /gsd:discuss-phase T4 — implementation decisions (HOW)*
