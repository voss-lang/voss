# Phase T4: Prompt Caching + Cost Truthfulness — Research

**Researched:** 2026-05-16
**Domain:** LLM prompt caching (Anthropic ephemeral + OpenAI auto), provider response usage extraction, vcrpy cassette integration for httpx
**Confidence:** HIGH (D-02 mechanism verified against installed LiteLLM 1.74.7 source; OpenAI/Anthropic shapes confirmed in vendor docs + local probe of LiteLLM `Usage` constructor)

## Summary

T4's most-feared unknown — D-02, the LiteLLM passthrough mechanism — resolves cleanly. **LiteLLM 1.74.7 (installed locally) calls `translate_system_message` over each `{"role": "system", "content": [...]}` entry and propagates `cache_control` markers verbatim into the Anthropic Messages API `system` array** ([source](/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/litellm/llms/anthropic/chat/transformation.py):545-596, line 580 reads `cache_control` from each content block when the system content is a list). No `extra_body`, no `extra_headers`, no beta flag is needed. The single requirement is that **system content be a list of typed text blocks** (not a joined string).

The token-shape probe (D-03) also lands cleanly. LiteLLM normalizes Anthropic cache fields onto the `Usage` object so **both** `getattr(usage, "cache_creation_input_tokens")` AND `getattr(usage, "cache_read_input_tokens")` are present as integers after the `for k, v in params.items(): setattr(self, k, v)` loop in `Usage.__init__` ([source](/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/litellm/types/utils.py):995-996). For OpenAI shape, only `usage.prompt_tokens_details.cached_tokens` is populated and the top-level fields stay `MISSING` — exactly the asymmetric shape D-03 anticipates.

Cost truthfulness (D-06) survives one historical scare. Two real bugs existed in LiteLLM's cache cost calculation: **#9812/#9838 (April 2025, double-counting cache_creation_input_tokens) and #11789/#10240/#25517 (Bedrock/streaming usage aggregation, fixed through 2025-2026)**. The streaming Bedrock fix #25517 only merged on April 10, 2026 — but the relevant code path for Voss is **direct LiteLLM acompletion against Anthropic** (not Bedrock), which uses a different streaming aggregator. The 1.74.7 floor used locally is past both fixes for the direct-Anthropic path. Recommended pin: **`litellm >= 1.74.0`** (raises D-06's `1.50.0` floor to clear the streaming-cache-cost bug class definitively).

vcrpy 8.1.1 patches `httpcore` (which httpx uses under the hood) via `vcr/stubs/httpcore_stubs.py`. Record modes are exactly `{all, any, new_episodes, none, once}` — D-07's `none` and `new_episodes` choices map 1:1. YAML default serializer. `filter_headers` accepts a list of header names.

**Primary recommendation:** Implement D-01..D-09 as written. Raise the LiteLLM pin from `>=1.50.0` to `>=1.74.0`. Add vcrpy 8 (not earlier) to dev deps. Build the cassette via `VOSS_RECORD=1` against `claude-sonnet-4-5` (the existing default alias) over the OAuth-bypass path — see Sharp Edges §1 for why OAuth-bypass cassettes are riskier and the LiteLLM-direct path is preferred for the test fixture.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| System-prompt block-list composition | Harness (`voss/harness/agent.py`) | — | Single composition site at agent.py:506-516 today; cache marker placement is a harness concern. |
| Cache-marker insertion | Harness (`voss/harness/agent.py`) | — | The marker is a Voss-side decision (which prefix to cache); providers just pass it through. |
| Cache-control passthrough to wire format | LiteLLM (`litellm.llms.anthropic.chat.transformation`) | — | Vendor-owned transform; Voss must not duplicate. |
| Cache-token extraction from `resp.usage` | Provider adapter (`voss_runtime/providers/litellm_provider.py` + new `_cache_tokens.py`) | — | Adapter boundary — Voss reads what LiteLLM normalized. |
| Cache-token extraction from streaming `Usage` event | Stream consumer (`voss/harness/agent.py:609-622`) | Provider stream emitters (`voss/harness/providers.py`) | Symmetric to non-streaming; lives at the event boundary. |
| Cost computation (cache-aware) | LiteLLM (`cost_calculator.py`) | — | Voss trusts pre-computed `_hidden_params.response_cost`. |
| Cost surfacing (`/cost --by-model`) | CLI (`voss/harness/cli.py:562-595`) | — | Already implemented; T4 verifies + tightens placeholder text. |
| Telemetry event extension | `voss/harness/telemetry.py` consumer (`agent.py:645-658` emit site) | — | Additive flat-dict keys on existing `provider.response` event. |
| Cache-invalidation drift detection | Test fixtures (`tests/harness/test_cache_invalidation.py`) | — | Pure unit tests; no production code. |
| HTTPX request/response replay | vcrpy (`tests/harness/test_cache_integration.py` + cassettes) | — | Test infrastructure. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `litellm` | `>=1.74.0` [VERIFIED: installed 1.74.7 + GitHub issue history] | Cache-aware Messages API translation + `response_cost` | Only provider abstraction in Voss; CONTEXT D-02/D-06 lock the trust posture. The pre-1.74 floor of `>=1.50.0` is below the cache double-count fixes from PRs #9838 (April 2025) and #25517 (April 2026 — Bedrock streaming). Direct-Anthropic streaming via the `anthropic/chat` transformation path was patched earlier; `>=1.74.0` clears all known cache-cost bugs in the direct (non-Bedrock-pass-through) provider for both streaming and non-streaming. |
| `vcrpy` | `>=8.0.0,<9` [VERIFIED: installed 8.1.1] | Record/replay HTTPX requests for cache integration test (CACHE-05) | v8.0.0 rewrote httpx support to patch `httpcore` instead of `httpx` directly — more durable across httpx releases. Earlier (4.1.x–7.x) variants patched httpx and broke on each httpx minor bump. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | already pinned | Test runner | All CACHE-01..CACHE-07 tests. |
| `httpx` | already pinned | Existing provider HTTP layer (oauth providers) | Indirect — vcrpy intercepts the underlying `httpcore` transport. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| vcrpy | `pytest-recording` (vcrpy wrapper) | Adds another dep + a different fixture API. vcrpy directly via `vcr.use_cassette(...)` context manager is one fewer indirection; matches T3's tooling minimalism. |
| vcrpy | `respx` (httpx-only mock library) | `respx` requires hand-authoring response bodies; vcrpy records once, replays forever. CACHE-05 is fundamentally a record-then-replay scenario. |
| LiteLLM `response_cost` | Voss-owned pricing table from `model_prices_and_context_window.json` | Decisively rejected by CONTEXT D-06. Cache pricing math is in LiteLLM's `cost_calculator.py` and tracks JSON updates we'd otherwise have to mirror. |
| Single-block system content | Multi-block with internal newline joining | The block list IS the multi-block format. Single-block-with-newlines defeats the cache-marker placement requirement. |

**Installation:**
```bash
python3 -m pip install 'litellm>=1.74.0' 'vcrpy>=8.0.0,<9'
```

**Version verification:**
```bash
python3 -c "from importlib.metadata import version; print(version('litellm'), version('vcrpy'))"
# Already on machine: litellm 1.74.7, vcrpy 8.1.1
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| litellm | PyPI | ~3 yr | ~80M/mo | github.com/BerriAI/litellm | not run (existing dep) | Approved (already pinned at `>=1.50.0`; T4 raises floor only) |
| vcrpy | PyPI | ~12 yr | ~9M/mo | github.com/kevin1024/vcrpy | not run (well-established, locally importable; verified Python module structure) | Approved |
| wrapt | PyPI | ~14 yr | ~150M/mo | github.com/GrahamDumpleton/wrapt | (transitive of vcrpy) | Approved |

slopcheck was not available in the environment; both new dependencies are major, long-lived projects with verifiable GitHub presence, importable Python modules, and substantial downloads. No new packages are speculative.

## Architecture Patterns

### System Architecture Diagram

```
                          ┌─────────────────────────────────────┐
                          │ harness.toml [agent] max_iterations │
                          │ VOSS.md, cognition, prior_context   │
                          └────────────────┬────────────────────┘
                                           │
                                           ▼
        _compose_system_blocks(...) ─────▶ list[dict] (block list)
                                           │
                                           │  trailing block carries
                                           │  cache_control:{type:"ephemeral"}
                                           ▼
        messages = [{"role":"system", "content":[blocks]},     ◄── CACHED prefix
                    {"role":"system", "content": rider},        ◄── uncached
                    {"role":"user",   "content": user_prompt},
                    ...prior replay messages...]
                                           │
                                           ▼
                  ┌────────────────────────────────────────┐
                  │ provider.stream(messages, ...)         │
                  │ (LiteLLMProvider via litellm.acompletion │
                  │  OR AnthropicOAuthProvider via httpx)  │
                  └─────┬──────────────────────────────────┘
                        │
                        │   LiteLLM path:                       OAuth path:
                        │   translate_system_message()          _payload() builds system_blocks
                        │   reads cache_control on each         (already a list — but does NOT
                        │   block (transformation.py:580)       pass cache_control through today;
                        │                                       see Sharp Edges §2)
                        ▼
                  ┌──────────────────────────────────────┐
                  │ Anthropic Messages API               │
                  │   system: [{type,text,cache_control}] │
                  │   first turn → cache_creation > 0    │
                  │   subsequent → cache_read > 0        │
                  └─────┬────────────────────────────────┘
                        │
                        ▼
                  resp.usage:
                    cache_creation_input_tokens (int)
                    cache_read_input_tokens (int)
                    prompt_tokens_details.cached_tokens (mirror of cache_read)
                  resp._hidden_params.response_cost (cache-aware float)
                        │
                        ▼
              extract_cache_tokens(usage_obj) → (creation, read)
                        │
                        ▼
        ProviderResponse(... cache_creation_input_tokens, cache_read_input_tokens)
        ProviderStreamEvent.Usage(... cache_creation_input_tokens, cache_read_input_tokens)
                        │
                        ▼
              telemetry.emit("provider.response", data={
                  cache_creation_input_tokens: int,
                  cache_read_input_tokens: int,
                  cost_usd: float, ...
              })
                        │
                        ▼
              RunRecord (via IterationRecord) — fields stay zero by default;
              cassette test asserts they round-trip when present
```

### Recommended Project Structure

```
voss/harness/
├── agent.py                    # CACHE-01 — new _compose_system_blocks helper
├── providers.py                # CACHE-02 streaming half — Usage variant gains 2 fields
├── cli.py                      # CACHE-04 — verify --by-model; update --by-tool string
├── telemetry.py                # unchanged; emit-site adds 2 keys
voss_runtime/providers/
├── base.py                     # CACHE-02 — ProviderResponse +2 fields
├── litellm_provider.py         # CACHE-02 — call extract_cache_tokens(resp.usage)
└── _cache_tokens.py            # NEW (D-04) — pure extractor, stdlib only
tests/harness/
├── test_agent_caching.py       # CACHE-01 marker shape/position
├── test_provider_response.py   # CACHE-02 Anthropic + OpenAI extraction (existing file extended)
├── test_cost_accounting.py     # CACHE-03 cache-aware cost differential
├── test_cost_slash.py          # CACHE-04 4-decimal sum + placeholder string
├── test_cache_integration.py   # CACHE-05 + CACHE-07 via cassette
├── test_cache_invalidation.py  # CACHE-06 four parametrized drift triggers
├── test_telemetry_cache_fields.py  # CACHE-07 provider.response payload + RunRecord round-trip
├── test_cache_tokens.py        # D-04 extractor unit tests (all three usage shapes)
└── fixtures/cassettes/
    └── test_cache_integration.yaml   # vcrpy YAML cassette, redacted keys
```

### Pattern 1: Anthropic-style multi-block system content with cache_control

**What:** Send `{"role": "system", "content": [<list of typed text blocks>]}` where the trailing block carries `"cache_control": {"type": "ephemeral"}`. LiteLLM's `AnthropicConfig.translate_system_message` (transformation.py:545-596) reads each `_content["cache_control"]` field and propagates it to the Anthropic `system` array.

**When to use:** Whenever a stable prefix of ≥ ~1024 tokens (Sonnet 4.5) or ≥ ~4096 tokens (Opus 4.7, Haiku 4.5) exists and you want the 90% input-cost discount on cache reads.

**Example:**
```python
# Source: pinned by inspection of litellm 1.74.7 transformation.py:545-596
# Voss path: voss/harness/agent.py — replace lines 506-516 + 569-573

def _compose_system_blocks(
    *,
    voss_md_block: str,
    cognition_text: str,
    prior_context_text: str,
    loop_system: str,
) -> list[dict]:
    """Return Anthropic-format system block list with one trailing cache_control marker.

    LiteLLM's AnthropicConfig.translate_system_message reads the cache_control
    field off each content block and forwards it verbatim to the Messages API
    system[] array. No extra_body kwarg, no anthropic-beta header — caching is
    GA as of 2024-Q4.
    """
    blocks: list[dict] = []
    for text in (voss_md_block, cognition_text, prior_context_text, loop_system):
        if text:
            blocks.append({"type": "text", "text": text})
    if blocks:
        # Mark ONLY the trailing block — single breakpoint per CONTEXT D-01.
        blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
    return blocks


# At the messages-list build site (agent.py:569-573):
sys_blocks = _compose_system_blocks(
    voss_md_block=voss_md_block,
    cognition_text=cognition_text,
    prior_context_text=prior_context_text,
    loop_system=_compose_loop_system(max_iterations),
)
messages: list[dict] = [
    {"role": "system", "content": sys_blocks},   # CACHED static prefix
    {"role": "system", "content": rider},        # uncached per-iter rider
    {"role": "user", "content": user_prompt},
]
```

### Pattern 2: Universal cache-token probe across provider shapes

**What:** A single pure function that inspects `usage` for both Anthropic shape (`cache_creation_input_tokens`/`cache_read_input_tokens` as top-level attrs) and OpenAI shape (`prompt_tokens_details.cached_tokens`) without branching on `model.startswith(...)`.

**When to use:** Inside `LiteLLMProvider.complete` after `usage = resp.usage` (litellm_provider.py:42) AND inside whichever stream emitter constructs the `Usage` event from a provider response.

**Example:**
```python
# Source: pinned by local probe of litellm 1.74.7 Usage.__init__ behavior
# Voss path: voss_runtime/providers/_cache_tokens.py (NEW per D-04)

def extract_cache_tokens(usage_obj) -> tuple[int, int]:
    """Return (cache_creation, cache_read) probed across known usage shapes.

    Anthropic shape (LiteLLM normalized):
        usage.cache_creation_input_tokens: int
        usage.cache_read_input_tokens: int
    OpenAI shape:
        usage.prompt_tokens_details.cached_tokens: int  (cache_read equivalent)
        No client-visible creation count (cache_create returns 0).
    Stub / missing fields → (0, 0).
    """
    if usage_obj is None:
        return (0, 0)
    creation = int(getattr(usage_obj, "cache_creation_input_tokens", 0) or 0)
    read = int(getattr(usage_obj, "cache_read_input_tokens", 0) or 0)
    if read == 0:
        details = getattr(usage_obj, "prompt_tokens_details", None)
        if details is not None:
            read = int(getattr(details, "cached_tokens", 0) or 0)
    return (creation, read)
```

### Pattern 3: vcrpy cassette gated by VOSS_RECORD env var

**What:** Use `vcr.use_cassette(...)` with `record_mode='none'` by default (raises on missing cassette / new requests) and switch to `'new_episodes'` when `VOSS_RECORD=1` is set. Redact API auth headers.

**When to use:** CACHE-05 integration test only. Unit tests should NOT use vcrpy — they mock at the `usage` object level.

**Example:**
```python
# Source: vcrpy 8.1.1 API confirmed locally; record_mode enum has {all, any, new_episodes, none, once}
# Voss path: tests/harness/test_cache_integration.py (NEW)
import os
import vcr
import pytest

_CASSETTE_DIR = "tests/harness/fixtures/cassettes"

def _cassette(name: str):
    record_mode = "new_episodes" if os.environ.get("VOSS_RECORD") == "1" else "none"
    return vcr.use_cassette(
        f"{_CASSETTE_DIR}/{name}.yaml",
        record_mode=record_mode,
        filter_headers=[
            "x-api-key",
            "authorization",
            "anthropic-api-key",
            "cookie",
            "set-cookie",
        ],
        # YAML is the default serializer; left implicit.
    )

@pytest.mark.asyncio
async def test_first_turn_writes_cache():
    with _cassette("test_first_turn_writes_cache"):
        # ...run a voss harness turn against claude-sonnet-4-5...
        # assert first turn run.cache_creation_input_tokens > 0
        # assert first turn run.cache_read_input_tokens == 0
        ...
```

### Anti-Patterns to Avoid

- **Joining the system blocks with `"\n\n".join(...)` then attaching `cache_control` to the resulting string:** Anthropic's `cache_control` is a per-block attribute; on a single joined string LiteLLM still propagates it (transformation.py:559-571), but you've collapsed your four invalidation surfaces (D-08) into one. Multi-block is the contract that gives D-08 a meaningful per-source byte-diff.
- **Adding the `anthropic-beta: prompt-caching-2024-07-31` header:** Prompt caching is GA. Adding the legacy beta header was harmless historically but [the cookbook README has been corrected](https://github.com/anthropics/claude-cookbooks/issues/175) and the header may eventually be rejected as unknown.
- **Detecting provider by `model.startswith("claude")` or `"gpt"`:** D-03 explicitly rejects this. The universal probe falls back through both shapes; stub providers and future Gemini work without code change.
- **Caching the per-iter rider:** Rider includes `Iteration N of M`, tokens used, and prior-iter summaries — changes every iteration. A `cache_control` marker on the rider produces a guaranteed cache miss every turn AND burns a marker slot (Anthropic allows 4 total).
- **Caching the `tools[]` schema:** Explicitly deferred (SPEC out-of-scope, CONTEXT deferred). The tool registry mutates on T3 MCP attachment, T6 work, etc. Caching it now means re-creating the entry every release.
- **Recomputing `cost_usd` in Voss when cache tokens are non-zero:** D-06 lock. LiteLLM's `cost_calculator.py:712-713` reads `cache_creation_input_tokens` and `cache_read_input_tokens` off the usage dict and folds them into `_hidden_params.response_cost`. Voss arithmetic would either duplicate or contradict that.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Anthropic cache_control wire format | A new `AnthropicProvider` subclass that crafts the body directly | LiteLLM's existing `translate_system_message` — pass a block list as `content` | Code already exists at litellm/llms/anthropic/chat/transformation.py:545-596 and is the upstream-blessed path. A subclass duplicates this and drifts on every Anthropic API revision. |
| Cache-aware pricing math | A `voss/harness/cost.py` with rate constants (1.25x, 0.10x, 0.50x) | LiteLLM's `_hidden_params.response_cost` | Rates change. `model_prices_and_context_window.json` updates every release. Voss-owned constants go stale silently. |
| HTTPX recording for integration tests | Hand-rolled `httpx.MockTransport` fixtures | vcrpy 8 patching httpcore | MockTransport requires you to author response bodies; vcrpy captures real Anthropic SSE byte-for-byte, including the precise `cache_creation_input_tokens` and `cache_read_input_tokens` values that prove the contract. |
| Cache-token field mapping | Different field shapes for Anthropic vs OpenAI in `ProviderResponse` | Symmetric two fields (`cache_creation_input_tokens`, `cache_read_input_tokens`) where OpenAI's `cache_create` is always 0 | Single recorder schema. Telemetry consumers don't branch. T4 SPEC CACHE-02 mandates this symmetry. |
| `/cost --by-model` aggregator | Reimplement | The existing `cli.py:562-595` impl iterates `ctx.record.runs` and sums `cost_usd` per model | Already passes shape check (4-decimal floats). T4 verifies only — no rewrite. |

**Key insight:** Voss owns *placement of the cache marker* and *accounting fidelity* (token count capture + telemetry emission). It does NOT own the wire format, pricing math, or HTTP replay infrastructure. Each of these has a mature upstream implementation that is correct as of the pinned versions.

## Common Pitfalls

### Pitfall 1: LiteLLM streaming + cache double-counting (HISTORICAL)

**What goes wrong:** Pre-fix LiteLLM versions summed `uncached + cache_creation + cache_read` into `input_tokens`, then `calculate_usage` added cache fields *again*, doubling the cost report. Caused 2x cost inflation.

**Why it happens:** Two independent aggregators in the streaming path each wanted to be the canonical sum.

**How to avoid:** Pin `litellm >= 1.74.0`. PR #9838 (April 2025) fixed non-streaming + the direct-Anthropic streaming path; PR #25517 (April 2026) fixed Bedrock pass-through streaming. Voss uses direct-Anthropic, so 1.74.7 is past the relevant fix. Verify by inspecting `cost_calculator.py:652-720` which now takes cache tokens as explicit kwargs and computes the discounted cost once.

**Warning signs:** A unit test fixture with `cache_read_input_tokens=10000, prompt_tokens=100` whose `cost_usd` looks suspiciously close to the cost of 10100 *uncached* input tokens at full rate. CACHE-03 acceptance test catches this by comparing two fixtures where the only difference is cache token presence.

### Pitfall 2: Joined-string system message destroys cache-marker placement

**What goes wrong:** Today's `sys_prompt = "\n\n".join(...)` at agent.py:507-516 produces a SINGLE string. Putting `cache_control` on it works (LiteLLM transformation.py:559-571 handles the string branch), but D-08's four drift triggers all collapse onto the same monolith — you cannot byte-diff "only VOSS.md changed" vs "only cognition changed" because there are no boundaries.

**Why it happens:** Premature concatenation hides the prefix's structure from later passes.

**How to avoid:** Keep the four prefix slices as separate blocks all the way to the wire. The new `_compose_system_blocks` returns a `list[dict]`, never joins. D-08 invalidation tests can then assert `blocks_A[i]["text"] != blocks_B[i]["text"]` for exactly one `i`.

**Warning signs:** Any test that compares prefixes via single string equality. CACHE-06 should compare the rendered block-list as `json.dumps(blocks, sort_keys=True)` byte-for-byte; the test assertion shape forces the structure to stay multi-block.

### Pitfall 3: OAuth provider path silently drops cache markers

**What goes wrong:** The `AnthropicOAuthProvider` in `voss/harness/providers.py` builds its own system block list at lines 195-221. It splits incoming system messages and reconstructs `[{"type":"text","text":chunk}]` — **the reconstruction at line 212-213 drops any `cache_control` marker** because `chunk` is `m.get("content", "")` (a string, never a dict).

**Why it happens:** The OAuth provider predates T4. Its splitter assumes string content. When agent.py starts passing a `content: list[dict]` system message, `m.get("content", "")` returns the list, and the `if chunk:` filter at line 212 either passes the entire list as a single text body (bug) or rebuilds without the marker.

**How to avoid:** Either (a) update `AnthropicOAuthProvider._payload` to handle list-typed `content` and preserve `cache_control`, or (b) run CACHE-05's cassette test against the LiteLLM path only and document that OAuth-bypass mode loses caching until a follow-up. The SPEC CACHE-01 acceptance test asserts marker SHAPE on `messages[0]["content"]` — which is correct as the **input** to the provider; the **output** to Anthropic is a different surface and only LiteLLM is contractually tested.

**Recommended planner decision:** Treat OAuth-path cache marker preservation as a Wave-2-or-later follow-up (additive to providers.py) and run CACHE-05 against LiteLLM. The SPEC does not require OAuth caching to ship in T4. (See Open Questions §1.)

**Warning signs:** Cassette test passes on LiteLLM, but a real `voss chat` session with `VOSS_USE_OAUTH=1` (or however the OAuth path is selected) shows no `cache_read_input_tokens` after turn 1.

### Pitfall 4: vcrpy v7 vs v8 httpx patching semantics differ

**What goes wrong:** vcrpy 4.1.0 through 7.x patched httpx directly. vcrpy 8.0.0 rewrote httpx support to patch `httpcore` (the lower transport layer). A `tests/conftest.py` written against v7 examples may install hooks that v8 doesn't recognize.

**Why it happens:** Documentation churn — most StackOverflow answers reference the v7 API.

**How to avoid:** Pin `vcrpy >= 8.0.0,<9` and use the v8 `vcr.use_cassette(...)` context manager. Do NOT use `vcr.stubs.httpx_stubs` references — that module no longer exists in v8 (confirmed locally: stubs dir contains `httpcore_stubs.py`, not `httpx_stubs.py`).

**Warning signs:** Import error `cannot import name 'httpx_stubs' from 'vcr.stubs'` — fix by switching to high-level `vcr.use_cassette`.

### Pitfall 5: `record_mode='none'` raises on cassette ABSENCE, not just on new requests

**What goes wrong:** Run `pytest tests/harness/test_cache_integration.py` in a fresh checkout that hasn't committed the cassette → vcrpy raises `CannotOverwriteExistingCassetteException` or `FileNotFoundError`. Looks like a flaky test, is actually a "you forgot to commit the cassette" signal.

**Why it happens:** That's the intentional design — `'none'` is replay-only.

**How to avoid:** Document the workflow in the test docstring: missing cassette → run `VOSS_RECORD=1 pytest -x` with live Anthropic creds, commit the resulting YAML.

**Warning signs:** CI red on a clean checkout with "cassette not found".

### Pitfall 6: Anthropic streaming surfaces cache tokens on `message_start`, not `message_delta` or `message_stop`

**What goes wrong:** The existing `AnthropicOAuthProvider.stream` at providers.py:394-404 reads `usage` from the `message_delta` SSE event. Per [Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), `cache_read_input_tokens` and `cache_creation_input_tokens` appear in the **`message_start`** SSE event's `message.usage` field, NOT on the final `message_delta`. If a provider reads only the final usage, it misses the cache counts.

**Why it happens:** Anthropic SSE splits initial input-token reporting (sent eagerly at message_start) from output-token aggregation (sent in message_delta as the stream progresses). Cache tokens are an input concern → message_start.

**How to avoid:** When extending streaming Usage capture, read cache fields from `message_start` and merge them with output tokens captured at `message_delta`. The LiteLLM path through `litellm.acompletion` already handles this aggregation internally (see `litellm/llms/anthropic/chat/transformation.py:813-855` for the streamed-usage promotion logic), so the LiteLLM path is the safer integration surface. If the OAuth path is extended in a follow-up, the SSE event handler needs an explicit `message_start` branch.

**Warning signs:** Cassette test asserts `cache_read_input_tokens > 0` on turn 2 but the assertion fails on the OAuth path despite a verified server-side cache hit.

### Pitfall 7: Anthropic per-model cache keying interacts with the model alias map

**What goes wrong:** `voss/harness/providers.py:121-126` aliases `claude-sonnet-4-7` → `claude-sonnet-4-5`. If a user switches `default_model` mid-session from one alias that maps to one underlying model to another, cache invalidates inherently. This is documented in D-08 as "not Voss-tested", but the planner should be aware that the alias map is the actual cache key namespace.

**Why it happens:** Anthropic caches per concrete model ID. The alias resolution happens after composition, so the same harness state can produce a cache miss because of an alias change that's invisible to D-08's drift detectors.

**How to avoid:** Document in a code comment near `_MODEL_ALIASES`. Do not add a Voss-side cache-clear hook — Anthropic handles it.

### Pitfall 8: ProviderResponse round-trip via `asdict` plus old recorded sessions

**What goes wrong:** Pre-T4 session JSON files don't have the two new cache fields. Voss `_hydrate` filters unknown keys (session.py:184-188) but ProviderResponse → IterationRecord serialization needs to handle both directions. The IterationRecord dataclass at session.py:97-109 does not currently carry cache fields — and SPEC explicitly says CACHE-07 requires the telemetry event but not necessarily the recorder.

**Why it happens:** The session.py recorder isolates ProviderResponse from RunRecord intentionally; cost flows through but not raw usage.

**How to avoid:** Plan-time decision: does IterationRecord gain `cache_creation_input_tokens: int = 0` and `cache_read_input_tokens: int = 0`? **Recommendation: yes, additive default-zero, mirrors `prompt_tokens` and `completion_tokens` fields already on IterationRecord (session.py:104-105).** This makes the recorder round-trip test (CACHE-07 third assertion) straightforward and gives the SDK a stable shape. See Open Questions §3.

**Warning signs:** `RunRecord` round-trip test in CACHE-07 fails because the cache fields are dropped between save and load.

## Runtime State Inventory

> T4 is a code/config change phase — no databases, OS-registered state, or live services to update.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by grep for `cache_creation`/`cache_read` across `.voss/`, `tests/fixtures/`, session JSON snapshots | None |
| Live service config | None — no external services consume system-prompt structure | None |
| OS-registered state | None — no schedulers, daemons, or installed CLIs reference these constants | None |
| Secrets/env vars | New env var `VOSS_RECORD=1` (test-only) gates cassette recording mode. Does NOT carry secrets — it's an empty/`1` toggle. ANTHROPIC_API_KEY (already in scope for live recording) is the only secret involved, and is redacted from cassettes via `filter_headers` | Document in test docstring; no .env updates |
| Build artifacts | `.voss-cache/harness/` may contain stale compiled `.voss` artifacts that reference the old `_compose_loop_system` shape (the function signature stays the same, but if any compiled artifact inlined the joined-string path, it goes stale). M4 already enforces sha-keyed cache invalidation via `_manifest.json` — should self-heal | Bump compiled-harness cache invariant if `_compose_loop_system` signature changes (it does not in this plan) |

**Verification grep:**
```bash
grep -rn "cache_creation_input_tokens\|cache_read_input_tokens" .voss/ tests/fixtures/ 2>/dev/null
# expected: 0 matches before T4 lands
```

## Common Pitfalls (additional cross-references)

See Common Pitfalls section above. Pitfall 3 and Pitfall 6 are the highest-priority items for the planner — they bound CACHE-05's testable surface to the LiteLLM path and explain why OAuth-path caching is a follow-up.

## Code Examples

### Cache-aware ProviderResponse (CACHE-02 non-streaming half)

```python
# Source: synthesized from voss_runtime/providers/litellm_provider.py:42-60 + D-04
# Voss path: voss_runtime/providers/litellm_provider.py

from ._cache_tokens import extract_cache_tokens

# ...inside complete()...
choice = resp.choices[0].message
text = choice.content or ""
usage = resp.usage
cost = float(getattr(resp, "_hidden_params", {}).get("response_cost", 0.0) or 0.0)
cache_create, cache_read = extract_cache_tokens(usage)

return ProviderResponse(
    text=text,
    model=model,
    prompt_tokens=usage.prompt_tokens,
    completion_tokens=usage.completion_tokens,
    cost_usd=cost,
    cache_creation_input_tokens=cache_create,   # NEW (additive, default 0)
    cache_read_input_tokens=cache_read,         # NEW (additive, default 0)
    raw=resp.model_dump() if hasattr(resp, "model_dump") else dict(resp),
    parsed=parsed,
)
```

### Cache-aware streaming Usage event (CACHE-02 streaming half)

```python
# Source: synthesized from voss/harness/providers.py:52-57 + D-01
# Voss path: voss/harness/providers.py (Usage dataclass) + each stream() emitter

@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    cache_creation_input_tokens: int = 0   # NEW (additive)
    cache_read_input_tokens: int = 0       # NEW (additive)
```

When the AnthropicOAuthProvider streamer (providers.py:394-404) builds `captured_usage`, it currently reads from the `message_delta` SSE chunk. Per Pitfall 6, cache tokens arrive on `message_start`; the emitter needs to capture them earlier and merge at message_stop. **However**, since CACHE-05 is gated to the LiteLLM path (Pitfall 3 / Open Question §1), the OAuth provider streaming usage augmentation is a separate (smaller) plan: thread `_cache_tokens_seen_in_message_start` through the SSE loop. The LiteLLM stream path is consumed via `litellm.acompletion(..., stream=True)` whose final accumulated chunk's `.usage` is already cache-aware.

### Telemetry event extension (CACHE-07)

```python
# Source: voss/harness/agent.py:645-658
# Diff: two additive keys on the existing data dict, flat shape per D-05

telemetry.emit(
    "provider.response",
    "info",
    data={
        "phase": "plan",
        "model": model,
        "iteration_index": iteration_index,
        "latency_ms": int((time.monotonic() - iter_t0) * 1000),
        "prompt_tokens": iter_prompt_tokens,
        "completion_tokens": iter_completion_tokens,
        "cost_usd": iter_cost,
        "stop_reason": this_iter_stop,
        # NEW: D-05 flat additive keys
        "cache_creation_input_tokens": iter_cache_creation,
        "cache_read_input_tokens": iter_cache_read,
    },
)
```

`iter_cache_creation` and `iter_cache_read` are populated from `this_iter_usage` if set (mirrors `iter_prompt_tokens = this_iter_usage.prompt_tokens if this_iter_usage else 0` on line 617-619).

### Cache-invalidation test scaffold (CACHE-06)

```python
# Voss path: tests/harness/test_cache_invalidation.py (NEW)
import json
import pytest
from voss.harness.agent import _compose_system_blocks, _compose_loop_system


def _render(*, voss_md, cognition, prior_ctx, max_iters):
    return _compose_system_blocks(
        voss_md_block=f"# VOSS.md\n{voss_md}" if voss_md else "",
        cognition_text=cognition,
        prior_context_text=prior_ctx,
        loop_system=_compose_loop_system(max_iters),
    )


@pytest.mark.parametrize("drift_field,a,b", [
    ("voss_md",     {"voss_md": "A", "cognition": "X", "prior_ctx": "Y", "max_iters": 12}, {"voss_md": "B", "cognition": "X", "prior_ctx": "Y", "max_iters": 12}),
    ("cognition",   {"voss_md": "A", "cognition": "X", "prior_ctx": "Y", "max_iters": 12}, {"voss_md": "A", "cognition": "Z", "prior_ctx": "Y", "max_iters": 12}),
    ("prior_ctx",   {"voss_md": "A", "cognition": "X", "prior_ctx": "Y", "max_iters": 12}, {"voss_md": "A", "cognition": "X", "prior_ctx": "W", "max_iters": 12}),
    ("max_iters",   {"voss_md": "A", "cognition": "X", "prior_ctx": "Y", "max_iters": 12}, {"voss_md": "A", "cognition": "X", "prior_ctx": "Y", "max_iters": 24}),
])
def test_drift_changes_rendered_prefix(drift_field, a, b):
    blocks_a = _render(**a)
    blocks_b = _render(**b)
    a_bytes = json.dumps(blocks_a, sort_keys=True).encode()
    b_bytes = json.dumps(blocks_b, sort_keys=True).encode()
    assert a_bytes != b_bytes, f"{drift_field} drift did not change rendered prefix"
```

The `json.dumps(..., sort_keys=True)` byte-diff strategy answers researcher question #7: it's the cleanest comparison because (a) `cache_control` marker positioning is preserved, (b) any one-character change in any block fires the assertion, (c) the comparison is deterministic across runs.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `anthropic-beta: prompt-caching-2024-07-31` header required | No beta header — `cache_control` directly in messages | ~2024-Q4 (GA) | Skip the header; Voss SDK doesn't need to add it. |
| LiteLLM cache tokens absent from streaming usage | LiteLLM aggregates cache tokens from `message_start` + `message_delta` SSE chunks into final usage | PR #9838 (April 2025), PR #25517 Bedrock (April 2026) | Direct-Anthropic streaming path is correct as of ~1.65+; raise pin to 1.74+ for definitiveness. |
| vcrpy patches httpx directly | vcrpy 8.0.0+ patches httpcore | vcrpy 8.0.0 | Use `vcr.use_cassette(...)` high-level API; do NOT import `vcr.stubs.httpx_stubs` (no longer exists). |
| Single-string system prompts | Anthropic accepts list-of-block system content | Always (cache_control requires this) | Migration is a one-shot at the message-build site. |
| 5-minute TTL only | Optional `"ttl": "1h"` extended cache at 2x base rate | Anthropic 2025 update | T4 deferred per CONTEXT. |

**Deprecated/outdated:**
- `anthropic-beta: prompt-caching-2024-07-31` — GA'd, removed; do not add.
- vcrpy 7.x and earlier `httpx_stubs` — replaced by httpcore patching in v8.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CACHE-01 | Multi-block system prompt with single cache breakpoint | Pattern 1 (block-list shape verified against LiteLLM 1.74.7 transformation.py:545-596); Pitfall 2 (do not collapse to joined string); Code Examples §_compose_system_blocks |
| CACHE-02 | Cache-token capture in ProviderResponse + streaming Usage | Pattern 2 (`extract_cache_tokens` universal probe verified by local probe of LiteLLM `Usage` constructor + `prompt_tokens_details` mirror); Pitfall 6 (Anthropic streaming SSE event mapping — LiteLLM aggregates correctly internally); Code Examples §non-streaming + §streaming |
| CACHE-03 | Trust LiteLLM's response_cost for cache-inclusive pricing | Pitfall 1 (historical double-counting bugs fixed in PRs #9838 and #25517; pin floor `>=1.74.0`); LiteLLM `cost_calculator.py:712-720` confirmed to take cache tokens as explicit inputs |
| CACHE-04 | `/cost --by-model` 4-decimal accuracy + `--by-tool` placeholder string update | Inspection of cli.py:562-595 confirms existing per-run sum is already 4-decimal; D-09 single-line placeholder text change |
| CACHE-05 | Recorded-fixture integration test proves cache HIT across turns | Pattern 3 (vcrpy 8.1.1 cassette gated by VOSS_RECORD); Pitfall 3 (OAuth path drops markers — test against LiteLLM path); Pitfall 5 (`record_mode='none'` raises on missing cassette) |
| CACHE-06 | Cache invalidation triggers documented and verified | Code Examples §test scaffold (4 parametrized drift cases with byte-diff assertion); answer to researcher Q7 — `json.dumps(blocks, sort_keys=True)` is the comparison strategy |
| CACHE-07 | First-turn invariant + telemetry | Telemetry event extension (Code Examples §provider.response); Pitfall 8 (IterationRecord gains additive cache fields for RunRecord round-trip) |

## Project Constraints (from CLAUDE.md)

Voss repo root has no top-level `./CLAUDE.md` (verified via `ls`). User-level global CLAUDE.md governing principles relevant to this phase:

- **Surgical changes** — touch only what T4 requires. Don't reformat agent.py, providers.py, or cli.py beyond the lines this phase requires.
- **Simplicity first** — D-01..D-09 lock the shape; the plan should follow them, not invent new abstractions.
- **Goal-driven execution** — eight acceptance criteria in SPEC are the success contract; tests come before/with code.

Voss-specific constraints from `.planning/`:

- **No new runtime deps** (SPEC Constraints): vcrpy lands under `[tool.pytest]` or `[project.optional-dependencies] dev` only.
- **Additive ProviderResponse extension** (SPEC + CONTEXT D-01): backward-compatible defaults; pre-T4 fixtures must still deserialize. Verified via the dataclass shape — `int = 0` defaults satisfy this.
- **No Voss-owned pricing table** (CONTEXT D-06): research confirms this is viable; LiteLLM 1.74.7's `cost_calculator.py` is cache-aware.
- **Telemetry stays flat-dict** (CONTEXT D-05): research confirms event payloads in agent.py:528-535 (`cognition.snapshot`) and 645-658 (`provider.response`) follow flat shape.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LiteLLM 1.74.7's `translate_system_message` is representative of versions `>=1.65` for the direct-Anthropic path (i.e., 1.65 also works) | Standard Stack / Pitfall 1 | If wrong, pin to 1.74.0+ exactly. Easy mitigation; just raises minimum more. Already accepted in research recommendation. [ASSUMED — only 1.74.7 directly inspected] |
| A2 | LiteLLM normalizes `cache_creation_input_tokens` onto `usage` for streaming (not just non-streaming) | Code Examples / CACHE-02 streaming | If wrong, CACHE-05's streaming assertion fails. Mitigation: read from `_hidden_params["additional_headers"]` or fall back to direct SSE inspection. [ASSUMED for LiteLLM streaming path — verified for non-streaming via local probe; streaming aggregation logic in transformation.py:813-855 is consistent but not end-to-end exercised here] |
| A3 | OAuth providers' SSE streaming need a follow-up plan for cache token capture | Pitfall 3, 6 | If wrong (i.e., OAuth path "just works"), the planner skips a Wave. Mitigation: include a quick OAuth-path smoke test in CACHE-05 as a secondary assertion; if it passes, no follow-up needed. [ASSUMED based on code inspection — providers.py:212-213 reconstructs system content as `{"type":"text","text":chunk}` which loses cache_control when chunk is a string; needs end-to-end verification] |
| A4 | LiteLLM 1.74.7's cache cost calculation for the direct-Anthropic path is correct (post-PR #9838) | CACHE-03 | If wrong, CACHE-03 acceptance test fails. Mitigation: file upstream + temporarily patch via `cost_usd = compute_cache_aware_cost(...)`. Acceptance test is a falsifiability anchor — easily detected. [ASSUMED — verified that PRs landed pre-1.74; not exercised here against live API] |
| A5 | vcrpy 8.1.1 successfully replays Anthropic SSE streams (not just unary responses) | CACHE-05 | If wrong, the cassette test cannot prove cache HIT end-to-end. Mitigation: switch to `httpx.MockTransport` with hand-crafted SSE bytes (more brittle). [ASSUMED — vcrpy's httpcore stub supports both, but SSE streaming response replay across multiple read() calls has historically had edge cases; needs live verification at record time] |
| A6 | `cache_control` markers DO survive `litellm.acompletion(stream=True)` (not just non-streaming) | Pattern 1 | If wrong, LiteLLM streaming path silently drops markers. Mitigation: switch to non-streaming for the cassette test. [ASSUMED — transformation.translate_system_message runs on the request before streaming begins, so markers should pass through; not directly verified via stream() call here] |
| A7 | Anthropic Claude Sonnet 4.5/4.6 honors cache markers at the existing `default_model` alias | CACHE-05 | Live API call at record time would surface mismatch. Mitigation: planner picks model alias at record time, not plan time. [ASSUMED based on Anthropic doc list of cache-eligible models] |

**Risk-weighted recommendation:** A2, A3, A5 are the highest-impact assumptions. The planner should sequence Wave 1 such that the LiteLLM path is the first integration target; if it works, A2/A5 are confirmed and A3 becomes a smaller follow-up plan.

## Open Questions

1. **OAuth provider cache-marker preservation — in T4 or follow-up?**
   - What we know: `AnthropicOAuthProvider._payload` at providers.py:195-221 reconstructs system content as `[{"type":"text","text":chunk}]` and silently drops `cache_control` markers from list-typed `content`. Same provider's stream() reads usage from `message_delta`, not `message_start`, so it would also miss cache token surfacing even after marker preservation.
   - What's unclear: Whether SPEC CACHE-01 acceptance test (which asserts marker shape on `messages[0]["content"]`) is satisfied by the *input* to provider.stream (which would pass) or requires the *outbound HTTP body* to carry the marker (which requires OAuth path fix).
   - Recommendation: **Planner choice.** Reading SPEC CACHE-01 strictly — "the outbound `messages[0]["content"]` is a list of ≥1 block, exactly one block carries `cache_control: {type: "ephemeral"}`" — this is satisfied by the agent.py composition output. CACHE-05 (the integration test) is run against the LiteLLM path. OAuth path cache support becomes a v0.2 follow-up. **Recommend: scope OAuth-path caching out of T4 and add a tracking item.**

2. **Pin LiteLLM to `>=1.50.0` (CONTEXT D-06 current) or raise to `>=1.74.0`?**
   - What we know: The streaming-cache double-count bug was fixed in PR #9838 (April 2025). The Bedrock-pass-through variant was fixed in PR #25517 (April 2026). Voss uses direct LiteLLM (not Bedrock pass-through), so 1.65+ should work. Local probe was 1.74.7.
   - What's unclear: Whether the direct-Anthropic streaming path was 100% fixed by 1.65 or still had edge cases until 1.74.
   - Recommendation: **Raise the pin to `>=1.74.0`.** Cost is trivial (no API breakage in that range), benefit is removing a class of bugs from the trust posture. CONTEXT D-06 explicitly says "exact pin set at plan time after researcher's protocol verification" — this is the protocol verification.

3. **Should IterationRecord gain cache fields (additive default-zero)?**
   - What we know: SPEC CACHE-07 acceptance: "RunRecord deserialize round-trip preserves them." IterationRecord (session.py:97-109) currently has `prompt_tokens` and `completion_tokens` and `cost_usd` but not the new cache fields.
   - What's unclear: Whether "RunRecord round-trip" means the on-disk session JSON or the in-memory dataclass. The session.py uses `asdict()` for serialization (line 208) — if cache fields aren't on the dataclass, they're not on disk.
   - Recommendation: **Add two additive default-zero fields to IterationRecord** (`cache_creation_input_tokens: int = 0`, `cache_read_input_tokens: int = 0`). Mirrors the existing token fields. Pre-T4 sessions hydrate cleanly because `_hydrate` filters unknown keys (already documented at session.py:184-188) — but additive new fields default to 0 when old JSON lacks them.

4. **vcrpy `before_record_response` callback for response body redaction?**
   - What we know: `filter_headers` redacts request and response headers. Anthropic response bodies do NOT contain API keys (the bearer header is the only secret). Cassette content is mostly token usage and assistant text — both already in the user's session anyway.
   - What's unclear: Future-proofing against Anthropic adding new response fields.
   - Recommendation: **Skip the callback for T4.** Keep the cassette minimal and human-readable. If a future Anthropic API revision surfaces something sensitive, add the callback then. The `filter_headers` list (`x-api-key`, `authorization`, `anthropic-api-key`, `cookie`, `set-cookie`) is sufficient.

5. **Cassette filename convention — test function name or test class+function?**
   - What we know: CONTEXT D-07 says "Cassette filename = test function name + `.yaml`".
   - What's unclear: If multiple tests share a cassette (the same two-turn HTTP trace can satisfy CACHE-05 and CACHE-07).
   - Recommendation: **One cassette per fixture trace, not per test function.** Name it descriptively, e.g., `cache_two_turn_session.yaml`. Multiple tests load the same cassette. This avoids re-recording identical HTTP traces.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | Tests + harness | ✓ | 3.13 | — |
| litellm | LiteLLM provider | ✓ | 1.74.7 (above proposed 1.74.0 floor) | — |
| vcrpy | CACHE-05 cassette test | ✓ | 8.1.1 (above proposed 8.0.0 floor) | — |
| httpx | Existing provider HTTP layer | ✓ (already pinned in pyproject) | — | — |
| pytest | Test runner | ✓ (already in dev deps) | — | — |
| ANTHROPIC_API_KEY | One-time cassette recording (`VOSS_RECORD=1`) | ✓ user-provided at record time | — | Skip live recording → manual smoke test from `voss chat` |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

> `workflow.nyquist_validation: true` confirmed in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py -x` |
| Full suite command | `python3 -m pytest tests/harness/ -x` |
| Per-cassette run | `python3 -m pytest tests/harness/test_cache_integration.py -x` |
| Cassette re-record | `VOSS_RECORD=1 ANTHROPIC_API_KEY=... python3 -m pytest tests/harness/test_cache_integration.py -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CACHE-01 | `messages[0]["content"]` is a list of ≥1 block; exactly one block (the last static-prefix block) carries `cache_control: ephemeral` | unit | `python3 -m pytest tests/harness/test_agent_caching.py::test_system_blocks_have_single_marker -x` | ❌ Wave 0 |
| CACHE-02 (non-stream) | `LiteLLMProvider.complete` populates two cache fields on `ProviderResponse` for both Anthropic-shape and OpenAI-shape usage | unit | `python3 -m pytest tests/harness/test_provider_response.py::test_anthropic_usage_extraction tests/harness/test_provider_response.py::test_openai_cached_tokens_extraction -x` | ❌ Wave 0 (file may exist; extend) |
| CACHE-02 (stream) | `ProviderStreamEvent.Usage` carries two cache fields, populated by stream emitters | unit (with mocked stream) | `python3 -m pytest tests/harness/test_streaming_usage_cache.py -x` | ❌ Wave 0 |
| CACHE-03 | `cost_usd` from LiteLLM is strictly greater with `cache_creation_input_tokens > 0` than with 0 (cache pricing is non-zero) | unit (fixture-based) | `python3 -m pytest tests/harness/test_cost_accounting.py::test_litellm_cost_includes_cache_rates -x` | ❌ Wave 0 |
| CACHE-04 | `/cost --by-model` sums per-run `cost_usd` per model to 4 decimals; `--by-tool` placeholder cites T6 SLASH-07 | unit | `python3 -m pytest tests/harness/test_cost_slash.py::test_by_model_matches_per_run_sum tests/harness/test_cost_slash.py::test_by_tool_placeholder_cites_t6 -x` | ❌ Wave 0 |
| CACHE-05 | Two-turn voss chat session against recorded cassette shows turn 1 cache_creation > 0 AND turn 2 cache_read > 0 | integration (cassette) | `python3 -m pytest tests/harness/test_cache_integration.py -x` | ❌ Wave 0 (+ cassette in fixtures/cassettes/) |
| CACHE-06 | Each of 4 drift triggers (VOSS.md, cognition, max_iterations, prior_context) produces a different rendered block-list | unit (parametrized) | `python3 -m pytest tests/harness/test_cache_invalidation.py -x` | ❌ Wave 0 |
| CACHE-07 (invariant) | Turn 1 of cassette: cache_creation > 0 AND cache_read == 0 | integration (same cassette as CACHE-05) | `python3 -m pytest tests/harness/test_cache_integration.py::test_first_turn_writes_cache -x` | ❌ Wave 0 |
| CACHE-07 (telemetry) | `provider.response` event data dict carries cache fields; RunRecord round-trip preserves them | unit | `python3 -m pytest tests/harness/test_telemetry_cache_fields.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py -x` (~all unit tests except integration cassette — fast feedback)
- **Per wave merge:** `python3 -m pytest tests/harness/ -x` (full suite including cassette)
- **Phase gate:** Full suite green + manual smoke test from `voss chat` against real Anthropic showing turn 2 cache_read > 0 in RunRecord (per SPEC final acceptance bullet)

### Wave 0 Gaps

- [ ] `tests/harness/test_cache_tokens.py` — covers D-04 extractor (Anthropic shape, OpenAI shape, missing fields)
- [ ] `tests/harness/test_agent_caching.py` — covers CACHE-01 marker shape/position
- [ ] `tests/harness/test_cache_invalidation.py` — covers CACHE-06 four drift triggers
- [ ] `tests/harness/test_cache_integration.py` — covers CACHE-05 + CACHE-07 first-turn (uses cassette)
- [ ] `tests/harness/test_cost_accounting.py` — covers CACHE-03 (file may exist; extend)
- [ ] `tests/harness/test_cost_slash.py` — covers CACHE-04 (file likely exists; extend)
- [ ] `tests/harness/test_streaming_usage_cache.py` — covers CACHE-02 streaming half
- [ ] `tests/harness/test_telemetry_cache_fields.py` — covers CACHE-07 telemetry shape
- [ ] `tests/harness/test_provider_response.py` — covers CACHE-02 non-streaming half (file may exist; extend)
- [ ] `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` — vcrpy cassette (recorded once, committed)
- [ ] `tests/harness/fixtures/cassettes/.gitignore` or README — document the VOSS_RECORD=1 workflow

## Security Domain

`security_enforcement` is not explicitly set in `.planning/config.json` — defaults to enabled. Applicable per phase scope:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Anthropic API keys handled via env var; cassette `filter_headers` blocks them from disk |
| V3 Session Management | no | No browser sessions or cookies in scope |
| V4 Access Control | no | No new permission gates in T4 |
| V5 Input Validation | yes | `extract_cache_tokens` uses `int(getattr(...) or 0)` — handles `None`, missing attrs, non-int → 0 fallback |
| V6 Cryptography | no | No new crypto |
| V7 Error Handling | yes | Cache-miss is silent (not an error); ProviderError still raised for HTTP failures |
| V9 Communication | yes | HTTPX is already pinned; no new TLS surface |
| V10 Malicious Code | yes | vcrpy and litellm slopcheck assessment in Package Legitimacy Audit |

### Known Threat Patterns for python harness + Anthropic + vcrpy

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage via committed cassette | Information Disclosure | `filter_headers=['x-api-key', 'authorization', 'anthropic-api-key', 'cookie', 'set-cookie']`; cassette gitignore review |
| Cache key reuse cross-user (theoretical) | Tampering / Info Disclosure | Anthropic per-org cache isolation is upstream; Voss is single-tenant per process — out of scope |
| Stale cassette replay masking real API regressions | Tampering | `record_mode='none'` raises on signature drift; `VOSS_RECORD=1` workflow re-records on prompt structure change |
| Cache-control marker injection via user input | Tampering | Markers are placed by Voss-controlled `_compose_system_blocks`, never by user input — user prompt is in a separate `{"role":"user"}` message and not marked |
| Prompt-prefix injection via VOSS.md edits | Tampering | VOSS.md is a user-authored project file; trust is delegated to the user. D-08 invalidation test verifies the cache invalidates on VOSS.md drift, preventing cross-version cache poisoning |
| Cost-reporting bypass via faked cache reads | Repudiation | CACHE-07 first-turn invariant test (`cache_creation > 0 AND cache_read == 0`) prevents a degenerate impl from always reporting reads |

## Sources

### Primary (HIGH confidence)

- Local LiteLLM 1.74.7 source: `/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/litellm/llms/anthropic/chat/transformation.py:545-596` — `translate_system_message` cache_control passthrough
- Local LiteLLM 1.74.7 source: `/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/litellm/types/utils.py:881-1000` — `Usage` constructor's Anthropic + DeepSeek mapping; confirms both `cache_creation_input_tokens`/`cache_read_input_tokens` setattr AND `prompt_tokens_details.cached_tokens` mirror
- Local LiteLLM 1.74.7 source: `/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/litellm/cost_calculator.py:142, 186, 652, 712-720, 918` — cache token kwargs into pricing math
- Local vcrpy 8.1.1: `vcr/stubs/httpcore_stubs.py` (presence) + `vcr.record_mode.RecordMode` enum (values: all, any, new_episodes, none, once)
- Anthropic prompt-caching docs: https://platform.claude.com/docs/en/build-with-claude/prompt-caching — GA status, message shape, usage field names, 5-min TTL, model-eligibility table
- OpenAI prompt-caching docs: https://developers.openai.com/api/docs/guides/prompt-caching — `prompt_tokens_details.cached_tokens` shape, automatic at >1024 tokens
- LiteLLM prompt-caching docs: https://docs.litellm.ai/docs/completion/prompt_caching

### Secondary (MEDIUM confidence)

- LiteLLM GitHub PR #9838 (merged April 2025): https://github.com/BerriAI/litellm/pull/9838 — fixed Anthropic prompt-caching cost double-counting
- LiteLLM GitHub PR #25517 (merged April 2026): https://github.com/BerriAI/litellm/pull/25517 — fixed Bedrock-pass-through streaming cache double-counting
- LiteLLM GitHub Issue #11789: https://github.com/BerriAI/litellm/issues/11789 — Bedrock streaming + cache cost regression (closed)
- LiteLLM GitHub Issue #11364: https://github.com/BerriAI/litellm/issues/11364 — Anthropic cost calc wrong with caching (closed)
- vcrpy 8.0.0 changelog: https://vcrpy.readthedocs.io/en/latest/changelog.html — "rewrote httpx support to patch httpcore instead of httpx"
- Anthropic cookbook README correction: https://github.com/anthropics/claude-cookbooks/issues/175 — beta header no longer required

### Tertiary (LOW confidence — confirmed via cross-source)

- OpenAI Responses API streaming surface for `cached_tokens`: cross-referenced with LiteLLM Issue #22192 (Responses API bridge drops prompt_tokens_details on stream) — noted as edge case; Voss uses Chat Completions path via LiteLLM for the cached scenario.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — LiteLLM 1.74.7 inspected directly, vcrpy 8.1.1 imported and probed; both behave as documented.
- Architecture: HIGH — D-01..D-09 are coherent against the codebase anchors; the only sharp edge (OAuth provider cache marker drop) is detected and routed to a follow-up.
- Pitfalls: HIGH — historical LiteLLM cache cost bugs traced to specific PRs with merge dates; Anthropic SSE event mapping verified against vendor docs; vcrpy v7→v8 migration confirmed via local stub directory listing.
- Test design: HIGH — every requirement maps to at least one automated command runnable in <30s except the cassette test (which needs the cassette pre-recorded). Wave 0 file list is exhaustive.

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (30 days — LiteLLM and Anthropic prompt-caching are stable surfaces; vcrpy 8.x is mature)

---

*Phase: T4-prompt-caching-cost-truthfulness*
*Research completed: 2026-05-16 via /gsd-research-phase T4*
*Next step: /gsd:plan-phase T4 — synthesize plans from CONTEXT.md + SPEC.md + RESEARCH.md*
