# Phase T4: Prompt Caching + Cost Truthfulness — Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 17 (9 new, 8 modified)
**Analogs found:** 15 / 17 (2 files have no direct analog and rely on RESEARCH.md patterns)

## File Classification

| File (new/modified) | Role | Data Flow | Closest Analog | Match Quality |
|----|----|----|----|----|
| `voss_runtime/providers/_cache_tokens.py` (NEW) | provider-adapter (pure helper) | transform (usage_obj → tuple) | `voss/harness/telemetry.py::redact_tool_args` | role-match (pure helper) |
| `tests/harness/test_cache_tokens.py` (NEW) | test-unit | request-response | `tests/harness/test_telemetry.py::test_redact_*` | role-match |
| `tests/harness/test_agent_caching.py` (NEW) | test-unit (composer) | request-response | `tests/harness/test_provider_stream_types.py::TestEventShapes` | role-match (shape assertions) |
| `tests/harness/test_cache_invalidation.py` (NEW) | test-unit (parametrized drift) | transform | `tests/harness/test_session_iterations.py::TestPreT1FixtureRoundTrip` | role-match (parametrized variants) |
| `tests/harness/test_cache_integration.py` (NEW) | test-integration (cassette) | event-driven | `tests/harness/test_anthropic_stream.py` (httpx.MockTransport SSE replay) | role-match (no vcrpy yet in repo) |
| `tests/harness/test_telemetry_cache_fields.py` (NEW) | test-unit | event-driven | `tests/harness/test_telemetry.py::test_emit_writes_ndjson_file` + `test_session_iterations.py::TestPreT1FixtureRoundTrip` | role-match (two-pattern hybrid) |
| `tests/harness/test_streaming_usage_cache.py` (NEW) | test-unit (stream events) | event-driven | `tests/harness/test_anthropic_stream.py::test_stream_emits_documented_event_sequence` | exact |
| `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` (NEW) | fixture (cassette) | replay | `tests/harness/fixtures/anthropic_stream_plan.sse` | role-match (different format) |
| `tests/harness/fixtures/cassettes/README.md` (NEW) | doc | n/a | (no analog — first cassette dir) | no-analog |
| `voss/harness/agent.py` (MODIFIED lines 285-287, 506-516, 569-573, 596, 645-658) | harness-agent | request-response | self (`_compose_loop_system` adjacent pattern at lines 285-287) | exact (self-reference) |
| `voss_runtime/providers/base.py` (MODIFIED lines 7-19) | provider-adapter (dataclass) | additive schema | `voss/harness/session.py::IterationRecord` lines 96-109 | exact (T1 additive-int pattern) |
| `voss_runtime/providers/litellm_provider.py` (MODIFIED lines 42-60) | provider-adapter | request-response | self (lines 52-60 existing return shape) | exact (self-extension) |
| `voss/harness/providers.py` (MODIFIED `Usage` dataclass + emission sites lines 52-57, 400, 701) | streaming provider | event-driven | self (lines 52-57 existing `Usage` variant) | exact (self-extension) |
| `voss/harness/cli.py` (MODIFIED lines 562-571) | CLI (slash command) | request-response | self (single-line string update) | exact (self-edit) |
| `voss/harness/session.py` (MODIFIED `IterationRecord` lines 96-109) | recorder (dataclass) | additive schema | self (T1 fields lines 130-136; T2 `batches` field line 109) | exact (third additive pass) |
| `voss/harness/telemetry.py` (MODIFIED — agent.py emit-site only; no telemetry.py code change) | telemetry consumer | event-driven | self (lines 87-100 `redact_tool_args` pure-helper pattern is the structural cousin for `_cache_tokens.py`, not a modification target) | no-op |
| `pyproject.toml` (MODIFIED lines 10-13, 35-44) | config | n/a | self (existing `dev` deps block) | exact (self-extension) |
| `tests/harness/test_provider_response.py` (NEW/extend) | test-unit | request-response | `tests/harness/test_session_iterations.py::TestIterationRecord` | role-match |
| `tests/harness/test_cost_accounting.py` (NEW/extend) | test-unit (fixture-based comparison) | request-response | `tests/harness/test_session_iterations.py::TestPreT1FixtureRoundTrip` + `test_repl_slash.py::TestT6Behaviors` SimpleNamespace fixture | role-match |
| `tests/harness/test_cost_slash.py` (NEW/extend) | test-unit (CLI slash) | request-response | `tests/harness/test_repl_slash.py::TestT6Behaviors::test_cost_by_model_groups_by_session_model` | exact |

## Pattern Assignments

### `voss_runtime/providers/_cache_tokens.py` (NEW — pure extractor, stdlib only)

**Analog:** `voss/harness/telemetry.py::redact_tool_args` (lines 87-100) — established T3 D-15 precedent for "pure peer-module helper imported by the consumer it serves." `_cache_tokens.py` mirrors this: a pure function in a peer module alongside `litellm_provider.py`, imported wherever extraction is needed.

**Imports pattern** (T3-style stdlib-only top of `telemetry.py`, lines 9-17):
```python
from __future__ import annotations

# stdlib only — no litellm import, no provider classes
```
The `_cache_tokens.py` module must not import `litellm` at module top-level (CONTEXT D-04). It probes via duck-typed `getattr`.

**Core pattern (duck-typed defensive extraction)** — analog from `redact_tool_args` (telemetry.py:87-100):
```python
def redact_tool_args(args: dict[str, Any]) -> dict[str, Any]:
    """Shallow redaction for tool argument telemetry."""
    ...
    out: dict[str, Any] = {}
    for k, v in args.items():
        lk = str(k).lower()
        if lk in _SENSITIVE_EXACT and lk != "cmd":
            out[k] = f"<{len(str(v))} chars>" if verbose else "<redacted>"
            continue
```

**Apply to `_cache_tokens.py`** (use RESEARCH.md Pattern 2 verbatim — universal probe, `getattr(... , 0) or 0`, fallback to `prompt_tokens_details.cached_tokens` for OpenAI shape; return `tuple[int, int]`).

---

### `voss_runtime/providers/base.py` (MODIFIED — additive `ProviderResponse` fields)

**Analog:** `voss/harness/session.py::IterationRecord` (lines 96-109) — same pattern: dataclass with additive default-zero int fields preserving pre-phase round-trip.

**Existing shape** (`base.py:7-19`):
```python
@dataclass
class ProviderResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    raw: dict = field(default_factory=dict)
    parsed: Optional[Any] = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
```

**Additive extension** (mirrors T2's `batches: list[BatchRecord] = field(default_factory=list)` on IterationRecord at session.py:109, and T1's int-default-zero pattern at session.py:135-136 `iteration_total_prompt_tokens: int = 0`):
```python
@dataclass
class ProviderResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    # T4: CACHE-02 additive. Defaults preserve pre-T4 ProviderResponse
    # construction (stub provider still returns 0; old fixtures rehydrate
    # because the new fields default to 0).
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    raw: dict = field(default_factory=dict)
    parsed: Optional[Any] = None
```

**Critical constraint:** New fields go BEFORE `raw` and `parsed` (which already use `field(default_factory=...)`). Python dataclasses require defaults to be contiguous from the right. The existing `cost_usd: float` has no default, so the two new int-default fields land between `cost_usd` and `raw`. (Verified by inspection — `raw` and `parsed` already have defaults.)

---

### `voss_runtime/providers/litellm_provider.py` (MODIFIED — call extractor, populate new fields)

**Analog:** Self, lines 42-60 — the existing usage-extraction + return-statement block.

**Existing pattern** (litellm_provider.py:40-60):
```python
choice = resp.choices[0].message
text = choice.content or ""
usage = resp.usage
cost = float(getattr(resp, "_hidden_params", {}).get("response_cost", 0.0) or 0.0)

parsed = None
if response_format is not None and text:
    try:
        parsed = response_format.model_validate_json(text)
    except Exception as e:
        raise ParseError(f"Failed to parse {response_format.__name__}: {e}") from e

return ProviderResponse(
    text=text,
    model=model,
    prompt_tokens=usage.prompt_tokens,
    completion_tokens=usage.completion_tokens,
    cost_usd=cost,
    raw=resp.model_dump() if hasattr(resp, "model_dump") else dict(resp),
    parsed=parsed,
)
```

**Extension** (insert one extractor call + two kwargs on the return — see RESEARCH.md Code Example "Cache-aware ProviderResponse"):
```python
from ._cache_tokens import extract_cache_tokens

# ... existing extraction ...
cache_create, cache_read = extract_cache_tokens(usage)

return ProviderResponse(
    text=text,
    model=model,
    prompt_tokens=usage.prompt_tokens,
    completion_tokens=usage.completion_tokens,
    cost_usd=cost,
    cache_creation_input_tokens=cache_create,
    cache_read_input_tokens=cache_read,
    raw=resp.model_dump() if hasattr(resp, "model_dump") else dict(resp),
    parsed=parsed,
)
```

Import path is relative — `_cache_tokens` is a peer module in the same `voss_runtime/providers/` package.

---

### `voss/harness/providers.py` (MODIFIED — `Usage` variant + emission sites)

**Analog:** Self, lines 52-57 (`Usage` dataclass declaration) — additive frozen-slots dataclass field extension.

**Existing shape** (providers.py:52-57):
```python
@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
```

**Additive extension** (T1-style — mirror the dataclass shape used by `base.ProviderResponse` for symmetry; CONTEXT D-01):
```python
@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    # T4: CACHE-02 streaming half. Additive default-zero ints mirror
    # ProviderResponse on the non-streaming path. Frozen-slots dataclass
    # tolerates trailing defaults (no inheritance, no kwonly).
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
```

**Emission-site pattern** (existing, providers.py:400-404):
```python
captured_usage = Usage(
    prompt_tokens=int(usage.get("input_tokens", 0)),
    completion_tokens=int(usage.get("output_tokens", 0)),
    cost_usd=0.0,
)
```

**Extension at OAuth emission sites** (providers.py:400 and 701) — defaults keep these uncached-by-default per RESEARCH.md Pitfall 3 (OAuth-path caching deferred). No kwargs added at those call sites in T4 — the dataclass defaults to 0 and Sharp Edges §1 documents this as a follow-up.

**For the LiteLLM streaming path** — LiteLLM's `litellm.acompletion(..., stream=True)` aggregates cache tokens onto its final `Usage` chunk. The planner decides whether the harness already routes through a LiteLLM streaming adapter (check `get_provider(model)` resolution in `voss_runtime/providers/__init__.py`). If a LiteLLM stream emission site exists, call `extract_cache_tokens` there:
```python
cache_create, cache_read = extract_cache_tokens(final_chunk_usage)
yield Usage(
    prompt_tokens=...,
    completion_tokens=...,
    cost_usd=...,
    cache_creation_input_tokens=cache_create,
    cache_read_input_tokens=cache_read,
)
```

---

### `voss/harness/agent.py` (MODIFIED — `_compose_system_blocks` + message build + Usage consumer + telemetry emit)

**Analog:** Self — `_compose_loop_system` at lines 285-287 is the existing static helper pattern; the new `_compose_system_blocks` slots in right beside it.

**Existing helper pattern** (agent.py:285-287):
```python
def _compose_loop_system(max_iterations: int) -> str:
    """Fill the PLAN_LOOP_SYSTEM placeholder via str.replace (cache-stable)."""
    return PLAN_LOOP_SYSTEM.replace("{max_iterations}", str(max_iterations))
```

**New helper** (insert after `_compose_loop_system`; see RESEARCH.md Pattern 1 verbatim):
```python
def _compose_system_blocks(
    *,
    voss_md_block: str,
    cognition_text: str,
    prior_context_text: str,
    loop_system: str,
) -> list[dict]:
    """Return Anthropic-format system block list with one trailing cache_control marker.

    The trailing block carries cache_control: {"type": "ephemeral"} so
    LiteLLM's translate_system_message propagates it to Anthropic's
    Messages API system[] array. Drift in any input block invalidates the
    cache — see CACHE-06 invalidation tests.
    """
    blocks: list[dict] = []
    for text in (voss_md_block, cognition_text, prior_context_text, loop_system):
        if text:
            blocks.append({"type": "text", "text": text})
    if blocks:
        blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
    return blocks
```

**Existing system-prompt composition (REPLACE)** (agent.py:506-516):
```python
voss_md_block = f"# VOSS.md\n{voss_md_text}" if voss_md_text else ""
sys_prompt = "\n\n".join(
    s
    for s in (
        voss_md_block,
        cognition_text,
        prior_context_text,
        _compose_loop_system(max_iterations),
    )
    if s
)
```

**Replacement** (build `sys_blocks: list[dict]` instead of joined string):
```python
voss_md_block = f"# VOSS.md\n{voss_md_text}" if voss_md_text else ""
sys_blocks = _compose_system_blocks(
    voss_md_block=voss_md_block,
    cognition_text=cognition_text,
    prior_context_text=prior_context_text,
    loop_system=_compose_loop_system(max_iterations),
)
```

**Existing messages list (MODIFY content of messages[0])** (agent.py:569-573):
```python
messages: list[dict] = [
    {"role": "system", "content": sys_prompt},
    {"role": "system", "content": rider},
    {"role": "user", "content": user_prompt},
]
```

**Replacement** (rider stays separate and uncached — CONTEXT D-01):
```python
messages: list[dict] = [
    {"role": "system", "content": sys_blocks},   # cached static prefix
    {"role": "system", "content": rider},         # uncached per-iter rider
    {"role": "user", "content": user_prompt},
]
```

**Streaming Usage consumer (EXTEND)** (agent.py:609-622):
```python
elif isinstance(event, Usage):
    this_iter_usage = event
...
iter_cost = this_iter_usage.cost_usd if this_iter_usage else 0.0
iter_prompt_tokens = (
    this_iter_usage.prompt_tokens if this_iter_usage else 0
)
iter_completion_tokens = (
    this_iter_usage.completion_tokens if this_iter_usage else 0
)
```

**Extension — add cache fields with the SAME `if this_iter_usage else 0` guard pattern** (mirrors existing token-extraction shape exactly):
```python
iter_cache_creation = (
    this_iter_usage.cache_creation_input_tokens if this_iter_usage else 0
)
iter_cache_read = (
    this_iter_usage.cache_read_input_tokens if this_iter_usage else 0
)
```

**Telemetry emit-site (EXTEND `data` dict)** (agent.py:645-658) — flat keys per CONTEXT D-05:
```python
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
        # T4 CACHE-07: flat additive keys, NO nested cache: {...} sub-object
        "cache_creation_input_tokens": iter_cache_creation,
        "cache_read_input_tokens": iter_cache_read,
    },
)
```

This shape matches the existing flat convention used in `cognition.snapshot` (agent.py:528-535) where `architecture_tokens` and `constraints_count` sit at the same nesting depth.

---

### `voss/harness/session.py` (MODIFIED — `IterationRecord` additive cache fields)

**Analog:** Self — `IterationRecord` already has the T1 additive int-default-zero pattern (`prompt_tokens: int = 0`, `completion_tokens: int = 0` at lines 104-105) and the T2 list-default pattern (`batches: list[BatchRecord] = field(default_factory=list)` at line 109).

**Existing shape** (session.py:96-109):
```python
@dataclass
class IterationRecord:
    """One iteration of the agent loop. Persisted under RunRecord.iterations."""

    index: int
    plan: dict = field(default_factory=dict)
    tool_results: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    started_at: str = ""
    ended_at: str = ""
    exit_reason: Optional[str] = None
    batches: list[BatchRecord] = field(default_factory=list)
```

**Extension** (additive int-default-zero, mirrors T1's `prompt_tokens`/`completion_tokens`; placed adjacent to those fields for cohesion — RESEARCH.md Pitfall 8 + Open Question §3):
```python
@dataclass
class IterationRecord:
    index: int
    plan: dict = field(default_factory=dict)
    tool_results: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # T4: CACHE-07 additive. Defaults preserve pre-T4 session JSON
    # round-trip (older fixtures lack these keys → reconstruct as 0).
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    started_at: str = ""
    ended_at: str = ""
    exit_reason: Optional[str] = None
    batches: list[BatchRecord] = field(default_factory=list)
```

**Recorder wiring follow-on:** `RunRecorder.end_iteration` at `recorder.py:116-150` currently accepts `prompt_tokens` and `completion_tokens` kwargs. Extend its signature with two new keyword-only ints (default 0) and write to the target IterationRecord. Mirrors the kwarg-additive pattern from T2 (`end_batch`).

---

### `voss/harness/cli.py` (MODIFIED — single-line placeholder text)

**Analog:** Self — surgical single-line edit per CONTEXT D-09.

**Existing** (cli.py:565-571):
```python
if "by-tool" in flags:
    click.echo(
        "  /cost --by-tool: per-tool cost tracking lands with T4 "
        "(prompt caching). Recorder doesn't yet attribute provider "
        "cost to individual tool calls."
    )
    return
```

**Replacement** (only the string body changes; logic and structure unchanged):
```python
if "by-tool" in flags:
    click.echo(
        "  /cost --by-tool: per-tool cost tracking lands with T6 SLASH-07. "
        "Recorder doesn't yet attribute provider cost to individual tool calls."
    )
    return
```

The existing T6-test (`test_repl_slash.py:225-231`) asserts `"T4" in out`; that assertion must be updated to `"T6" in out` as part of the CACHE-04 verification. See planner action on `test_cost_slash.py` below.

The `--by-model` block at cli.py:572-590 stays untouched per CACHE-04 (test-only verification).

---

### `pyproject.toml` (MODIFIED — raise litellm pin, add vcrpy dev dep)

**Analog:** Self — existing dependency block at lines 10-23 and dev-deps block at lines 35-44.

**Existing** (pyproject.toml:10-23):
```toml
dependencies = [
    "lark>=1.1.9",
    "litellm>=1.50.0",
    "pydantic>=2.6,<3.0",
    ...
]
```

**Modification** (RESEARCH.md §Standard Stack + §Open Question 2):
```toml
dependencies = [
    "lark>=1.1.9",
    "litellm>=1.74.0",  # T4 CACHE-03: raise floor past cache-cost double-count fix (PR #9838)
    ...
]
```

**Existing dev block** (lines 35-44):
```toml
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "respx>=0.21",
    ...
]
```

**Modification** (add vcrpy under dev — CONTEXT D-07):
```toml
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "respx>=0.21",
    "vcrpy>=8.0.0,<9",  # T4 CACHE-05: cassette replay; v8 patches httpcore (RESEARCH.md Pitfall 4)
    ...
]
```

---

### `tests/harness/test_cache_tokens.py` (NEW — extractor unit tests)

**Analog:** `tests/harness/test_telemetry.py::test_redact_tool_args_masks_content` (lines 23-36) — pattern for testing a pure helper function with simple input/output assertions, no fixtures.

**Existing pattern** (test_telemetry.py:23-28):
```python
def test_redact_tool_args_masks_content() -> None:
    telemetry = _telemetry_module()
    d = {"path": "x.py", "content": "secret body"}
    r = telemetry.redact_tool_args(d)
    assert r["path"] == "x.py"
    assert r["content"] == "<redacted>"
```

**Apply to test_cache_tokens.py** (three test cases — Anthropic, OpenAI, missing per CONTEXT D-03):
```python
from types import SimpleNamespace
from voss_runtime.providers._cache_tokens import extract_cache_tokens

def test_anthropic_shape_returns_both_counts() -> None:
    usage = SimpleNamespace(
        cache_creation_input_tokens=120,
        cache_read_input_tokens=480,
    )
    assert extract_cache_tokens(usage) == (120, 480)

def test_openai_shape_returns_read_only() -> None:
    usage = SimpleNamespace(
        prompt_tokens_details=SimpleNamespace(cached_tokens=300),
    )
    assert extract_cache_tokens(usage) == (0, 300)

def test_missing_fields_default_to_zero() -> None:
    usage = SimpleNamespace()
    assert extract_cache_tokens(usage) == (0, 0)

def test_none_usage_returns_zero() -> None:
    assert extract_cache_tokens(None) == (0, 0)
```

Use `SimpleNamespace` (already a project test convention — see `test_repl_slash.py:135` and `test_session_iterations.py` round-trip dict pattern).

---

### `tests/harness/test_agent_caching.py` (NEW — CACHE-01 marker shape)

**Analog:** `tests/harness/test_provider_stream_types.py::TestEventShapes` (lines 47-76) — pattern for asserting dataclass/dict shape directly without provider invocation.

**Existing shape-assertion pattern** (test_provider_stream_types.py:63-67):
```python
def test_usage(self) -> None:
    ev = Usage(prompt_tokens=120, completion_tokens=50, cost_usd=0.0)
    assert ev.cost_usd == 0.0
    assert ev.prompt_tokens == 120
    assert ev.completion_tokens == 50
```

**Apply to test_agent_caching.py** (CACHE-01 SPEC acceptance):
```python
from voss.harness.agent import _compose_system_blocks

def test_system_blocks_have_single_marker() -> None:
    blocks = _compose_system_blocks(
        voss_md_block="# VOSS.md\nproject voss",
        cognition_text="cognition body",
        prior_context_text="prior ctx",
        loop_system="loop system",
    )
    # Block list shape — list of dicts with type and text
    assert isinstance(blocks, list)
    assert len(blocks) >= 1
    assert all(b.get("type") == "text" for b in blocks)
    # Exactly one block carries cache_control: {"type": "ephemeral"}
    marked = [b for b in blocks if "cache_control" in b]
    assert len(marked) == 1
    assert marked[0]["cache_control"] == {"type": "ephemeral"}
    # The marker is on the LAST static-prefix block (not the rider — rider
    # is a separate messages[] entry, not part of _compose_system_blocks).
    assert blocks[-1] is marked[0]

def test_empty_inputs_produce_empty_block_list() -> None:
    blocks = _compose_system_blocks(
        voss_md_block="",
        cognition_text="",
        prior_context_text="",
        loop_system="",
    )
    assert blocks == []
```

---

### `tests/harness/test_cache_invalidation.py` (NEW — CACHE-06 parametrized drift)

**Analog:** `tests/harness/test_session_iterations.py::TestPreT1FixtureRoundTrip` for the round-trip-dict construction pattern + `pytest.mark.parametrize` for drift variants.

**Apply directly** — use the RESEARCH.md Code Examples §"Cache-invalidation test scaffold" verbatim (lines 496-523 of RESEARCH.md). The `json.dumps(blocks, sort_keys=True)` byte-diff strategy is the locked comparison shape.

```python
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
    ("voss_md",     {"voss_md":"A","cognition":"X","prior_ctx":"Y","max_iters":12},
                    {"voss_md":"B","cognition":"X","prior_ctx":"Y","max_iters":12}),
    ("cognition",   {"voss_md":"A","cognition":"X","prior_ctx":"Y","max_iters":12},
                    {"voss_md":"A","cognition":"Z","prior_ctx":"Y","max_iters":12}),
    ("prior_ctx",   {"voss_md":"A","cognition":"X","prior_ctx":"Y","max_iters":12},
                    {"voss_md":"A","cognition":"X","prior_ctx":"W","max_iters":12}),
    ("max_iters",   {"voss_md":"A","cognition":"X","prior_ctx":"Y","max_iters":12},
                    {"voss_md":"A","cognition":"X","prior_ctx":"Y","max_iters":24}),
])
def test_drift_changes_rendered_prefix(drift_field, a, b):
    a_bytes = json.dumps(_render(**a), sort_keys=True).encode()
    b_bytes = json.dumps(_render(**b), sort_keys=True).encode()
    assert a_bytes != b_bytes, f"{drift_field} drift did not change rendered prefix"
```

---

### `tests/harness/test_cache_integration.py` (NEW — CACHE-05 + CACHE-07 cassette)

**Analog:** `tests/harness/test_anthropic_stream.py` for the "fixture-driven async streaming + assertion" pattern. vcrpy replaces `httpx.MockTransport` but the test structure is identical.

**Existing fixture-driven pattern** (test_anthropic_stream.py:25-66):
```python
FIXTURE = Path(__file__).parent / "fixtures" / "anthropic_stream_plan.sse"

def _sse_response(body_bytes: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        content=body_bytes,
        headers={"content-type": "text/event-stream"},
    )

def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))

@pytest.mark.asyncio
async def test_stream_emits_documented_event_sequence() -> None:
    body = FIXTURE.read_bytes()
    def handler(req: httpx.Request) -> httpx.Response:
        return _sse_response(body)
    p = AnthropicOAuthProvider(_creds(), client=_mock_client(handler))
    events = []
    async for ev in p.stream(...):
        events.append(ev)
    ...
```

**Apply to test_cache_integration.py** — use RESEARCH.md Pattern 3 §"vcrpy cassette gated by VOSS_RECORD env var" (lines 254-292 verbatim) but route through the LiteLLM path (per RESEARCH.md Pitfall 3 — OAuth-bypass cache markers deferred):

```python
import os
import vcr
import pytest
from pathlib import Path

_CASSETTE_DIR = Path(__file__).parent / "fixtures" / "cassettes"

def _cassette(name: str):
    record_mode = "new_episodes" if os.environ.get("VOSS_RECORD") == "1" else "none"
    return vcr.use_cassette(
        str(_CASSETTE_DIR / f"{name}.yaml"),
        record_mode=record_mode,
        filter_headers=[
            "x-api-key", "authorization", "anthropic-api-key",
            "cookie", "set-cookie",
        ],
    )

@pytest.mark.asyncio
async def test_first_turn_writes_cache():
    with _cassette("cache_two_turn_session"):
        # ... run a voss harness turn via the LiteLLM path against
        # claude-sonnet-4-5; capture the IterationRecord (or
        # ProviderResponse) from turn 1.
        ...
    assert turn1.cache_creation_input_tokens > 0
    assert turn1.cache_read_input_tokens == 0

@pytest.mark.asyncio
async def test_second_turn_reads_cache():
    with _cassette("cache_two_turn_session"):
        # ... same fixture, two turns; assert turn 2 cache_read > 0
        ...
    assert turn2.cache_read_input_tokens > 0
```

Both tests share the SAME cassette name (RESEARCH.md Open Question §5 — one cassette per fixture trace, not per test function).

---

### `tests/harness/test_telemetry_cache_fields.py` (NEW — CACHE-07 telemetry + RunRecord round-trip)

**Analog (telemetry half):** `tests/harness/test_telemetry.py::test_emit_writes_ndjson_file` (lines 46-69) — pattern for emit + readback of NDJSON event.

**Existing emit + readback** (test_telemetry.py:46-69):
```python
def test_emit_writes_ndjson_file(monkeypatch, tmp_path: Path) -> None:
    telemetry = _telemetry_module()
    logf = tmp_path / "h.ndjson"
    monkeypatch.setenv("VOSS_LOG", "1")
    monkeypatch.setenv("VOSS_LOG_PATH", str(logf))
    telemetry.reset_session_sink()
    telemetry.ensure_trace_id()
    telemetry.begin_turn()
    telemetry.emit("probe", "info", data={"k": 1})
    telemetry.finalize_turn(True, None)
    telemetry.reset_session_sink()

    lines = [ln for ln in logf.read_text().splitlines() if ln.strip()]
    ...
    probe = next(json.loads(ln) for ln in lines if json.loads(ln).get("kind") == "probe")
    assert probe["data"]["k"] == 1
```

**Apply to telemetry-half** of `test_telemetry_cache_fields.py`:
```python
def test_provider_response_event_carries_cache_tokens(monkeypatch, tmp_path: Path) -> None:
    # emit a synthetic provider.response event with cache fields, read back
    monkeypatch.setenv("VOSS_LOG", "1")
    monkeypatch.setenv("VOSS_LOG_PATH", str(tmp_path / "h.ndjson"))
    telemetry.reset_session_sink()
    telemetry.ensure_trace_id()
    telemetry.begin_turn()
    telemetry.emit("provider.response", "info", data={
        "model": "claude-sonnet-4-5",
        "cost_usd": 0.012,
        "cache_creation_input_tokens": 1500,
        "cache_read_input_tokens": 0,
    })
    telemetry.finalize_turn(True, None)
    # readback assertion
    events = [json.loads(ln) for ln in (tmp_path/"h.ndjson").read_text().splitlines() if ln.strip()]
    pr = next(e for e in events if e.get("kind") == "provider.response")
    assert pr["data"]["cache_creation_input_tokens"] == 1500
    assert pr["data"]["cache_read_input_tokens"] == 0
```

**Analog (RunRecord round-trip half):** `tests/harness/test_session_iterations.py::TestPreT1FixtureRoundTrip::test_runrecord_old_fixture_roundtrip` (lines 88-109) — old-fixture-dict construction with additive new fields defaulting to 0.

**Apply** (mirror exactly — RESEARCH.md Pitfall 8):
```python
def test_iteration_record_cache_fields_default_zero_for_old_fixtures() -> None:
    old_iter = {
        "index": 0,
        "plan": {"rationale": "r", "steps": []},
        "tool_results": [],
        "cost_usd": 0.012,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "started_at": "2025-12-01T00:00:00+00:00",
        "ended_at": "2025-12-01T00:00:01+00:00",
        "exit_reason": None,
        # NO cache_creation_input_tokens / cache_read_input_tokens keys.
    }
    rec = IterationRecord(**old_iter)
    assert rec.cache_creation_input_tokens == 0
    assert rec.cache_read_input_tokens == 0

def test_iteration_record_cache_fields_round_trip() -> None:
    it = IterationRecord(
        index=0,
        cache_creation_input_tokens=1500,
        cache_read_input_tokens=200,
    )
    d = dataclasses.asdict(it)
    rebuilt = IterationRecord(**d)
    assert rebuilt.cache_creation_input_tokens == 1500
    assert rebuilt.cache_read_input_tokens == 200
```

---

### `tests/harness/test_streaming_usage_cache.py` (NEW — CACHE-02 streaming half)

**Analog:** `tests/harness/test_anthropic_stream.py::test_stream_emits_documented_event_sequence` (lines 49-100) — directly. The pattern is to drive `provider.stream(...)` via a mocked httpx transport with a hand-crafted SSE fixture, collect events, assert on the `Usage` event.

**Existing Usage-event extraction pattern** (test_anthropic_stream.py:94-96):
```python
usage = next(e for e in events if isinstance(e, Usage))
assert usage.prompt_tokens == 100
assert usage.completion_tokens == 50
```

**Apply** (add a new SSE fixture under `tests/harness/fixtures/` mirroring `anthropic_stream_plan.sse` with `message_start.usage` containing `cache_creation_input_tokens` and `cache_read_input_tokens`; assert):
```python
# fixture: anthropic_stream_cache.sse — message_start.usage has cache fields
usage = next(e for e in events if isinstance(e, Usage))
assert usage.cache_creation_input_tokens == 1500
assert usage.cache_read_input_tokens == 0
```

**Critical:** Per RESEARCH.md Pitfall 6, Anthropic's SSE puts cache fields on `message_start.usage`, NOT `message_delta`. The fixture must encode this. For T4, this test exercises the LiteLLM streaming path (assumed to aggregate correctly) — the OAuth provider streaming SSE event handler may need a separate `message_start` branch in a follow-up.

---

### `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` (NEW — vcrpy cassette)

**Analog:** `tests/harness/fixtures/anthropic_stream_plan.sse` — fixture file structure (different format: SSE plain-text vs vcrpy YAML).

**Recording protocol** (CONTEXT D-07):
```bash
VOSS_RECORD=1 ANTHROPIC_API_KEY=sk-ant-... python3 -m pytest tests/harness/test_cache_integration.py -x
```
Cassette committed as YAML, default vcrpy serializer. Headers redacted via `filter_headers` in the cassette context manager — see test_cache_integration.py pattern above. No callback needed (RESEARCH.md Open Question §4).

---

### `tests/harness/fixtures/cassettes/README.md` (NEW — workflow doc)

**No analog** in the codebase. Content (minimal — RESEARCH.md §Common Pitfalls 5 + CONTEXT D-07):
```markdown
# Cache integration cassettes

Cassettes here are replayed by `tests/harness/test_cache_integration.py`.

## Re-recording

When system-prompt structure changes (CACHE-06 drift triggers), re-record:

    VOSS_RECORD=1 ANTHROPIC_API_KEY=sk-ant-... \
      python3 -m pytest tests/harness/test_cache_integration.py -x

Commit the resulting `*.yaml` file. CI runs replay-only (no `VOSS_RECORD`),
so a missing cassette will fail with `CannotOverwriteExistingCassetteException`
or `FileNotFoundError` — that's a signal to re-record and commit.

Headers `x-api-key`, `authorization`, `anthropic-api-key`, `cookie`,
`set-cookie` are filtered from the YAML; the bearer token never lands in the
repo.
```

---

### `tests/harness/test_provider_response.py` (NEW or extend — CACHE-02 non-streaming)

**Analog:** `tests/harness/test_session_iterations.py::TestIterationRecord::test_constructs_with_all_defaults_except_index` (lines 16-26) — dataclass-construction shape assertions.

**Apply** (mirror exact construction-then-assert pattern):
```python
from types import SimpleNamespace
from voss_runtime.providers.base import ProviderResponse
from voss_runtime.providers._cache_tokens import extract_cache_tokens

def test_provider_response_defaults_cache_fields_to_zero() -> None:
    pr = ProviderResponse(
        text="hello",
        model="claude-sonnet-4-5",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.012,
    )
    assert pr.cache_creation_input_tokens == 0
    assert pr.cache_read_input_tokens == 0

def test_anthropic_usage_extraction() -> None:
    usage = SimpleNamespace(
        prompt_tokens=600,
        completion_tokens=100,
        cache_creation_input_tokens=1500,
        cache_read_input_tokens=0,
    )
    creation, read = extract_cache_tokens(usage)
    assert creation == 1500
    assert read == 0

def test_openai_cached_tokens_extraction() -> None:
    usage = SimpleNamespace(
        prompt_tokens=2000,
        completion_tokens=50,
        prompt_tokens_details=SimpleNamespace(cached_tokens=1200),
    )
    creation, read = extract_cache_tokens(usage)
    assert creation == 0
    assert read == 1200
```

---

### `tests/harness/test_cost_accounting.py` (NEW or extend — CACHE-03 differential)

**Analog:** `tests/harness/test_session_iterations.py::TestPreT1FixtureRoundTrip` (dataclass-from-dict pattern) + `tests/harness/test_repl_slash.py::TestT6Behaviors` fixture pattern.

**Pattern** — CACHE-03 is a strict-inequality fixture comparison:
```python
def test_litellm_cost_includes_cache_rates() -> None:
    # Two ProviderResponse fixtures: same prompt/completion tokens, the only
    # difference is cache_creation_input_tokens > 0 in fixture_a.
    # Assert cost_usd of fixture_a > cost_usd of fixture_b strictly.
    # Cost values come from a recorded cassette OR from a litellm
    # cost_per_token probe — planner picks the simplest fixture source.
    ...
    assert fixture_a_cost > fixture_b_cost  # cache pricing is non-zero
```

Implementation choices for the planner: (a) two stub ProviderResponse instances with cost_usd hand-set from a `litellm.cost_calculator` probe, OR (b) sub-extract from the same cassette used by `test_cache_integration.py`. Option (a) is simpler and decouples from cassette state.

---

### `tests/harness/test_cost_slash.py` (NEW or extend — CACHE-04 + D-09 placeholder)

**Analog:** `tests/harness/test_repl_slash.py::TestT6Behaviors::test_cost_by_model_groups_by_session_model` (lines 216-223) — EXACT pattern; same slash handler, same fixture.

**Existing pattern** (test_repl_slash.py:216-223):
```python
def test_cost_by_model_groups_by_session_model(self, fake_ctx, capsys):
    from voss.harness.cli import _build_slash_registry
    reg = _build_slash_registry()
    reg.lookup("/cost").handler(fake_ctx, ["--by-model"], "/cost --by-model")
    out = capsys.readouterr().out
    assert "claude-sonnet-4-7" in out
    assert "$0.0200" in out  # 0.012 + 0.008
```

**Apply** — copy fixture + handler invocation; extend with 4-decimal precision assertion and D-09 placeholder update:
```python
def test_by_model_matches_per_run_sum(self, fake_ctx, capsys):
    # fake_ctx has runs=[{"cost_usd": 0.0123, ...}, {"cost_usd": 0.0456, ...}]
    reg = _build_slash_registry()
    reg.lookup("/cost").handler(fake_ctx, ["--by-model"], "/cost --by-model")
    out = capsys.readouterr().out
    # 4-decimal precision — printed string must contain "$0.0579" not "$0.06"
    assert "$0.0579" in out

def test_by_tool_placeholder_cites_t6(self, fake_ctx, capsys):
    reg = _build_slash_registry()
    reg.lookup("/cost").handler(fake_ctx, ["--by-tool"], "/cost --by-tool")
    out = capsys.readouterr().out
    assert "T6" in out
    assert "SLASH-07" in out
    assert "T4" not in out  # no stale T4 reference
```

**Note:** The existing `test_cost_by_tool_is_honest_stub` (test_repl_slash.py:225-231) asserts `"T4" in out` — that test MUST be updated as part of the D-09 plan, or the new test will conflict.

## Shared Patterns

### Additive dataclass extension (default-zero ints)

**Source:** `voss/harness/session.py::IterationRecord` lines 96-109 (T1 baseline + T2 batches field) — and `RunRecord` lines 130-136 (T1 additive ints).

**Apply to:** `ProviderResponse` (base.py), `Usage` streaming variant (providers.py), `IterationRecord` (session.py).

**Pattern:**
```python
# Additive int-default-zero fields land BEFORE any field with field(default_factory=...)
# to preserve dataclass ordering rules (defaults must be contiguous from the right).
@dataclass
class X:
    required_a: int
    required_b: str
    # ... existing default-zero fields (T_n_baseline) ...
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # T4: CACHE-_n additive. Comment cites phase and acceptance ID.
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    # ... existing factory-default fields preserved at end ...
    raw: dict = field(default_factory=dict)
```

**Round-trip test pattern (universal):** `test_session_iterations.py::TestPreT1FixtureRoundTrip::test_runrecord_old_fixture_roundtrip` (lines 89-109) — construct dataclass from a dict missing the new keys, assert new fields default to 0, then assert pre-existing keys preserved.

### Pure peer-module helpers (stdlib-only)

**Source:** `voss/harness/telemetry.py::redact_tool_args` lines 87-100. T3 D-15 established the convention.

**Apply to:** `voss_runtime/providers/_cache_tokens.py::extract_cache_tokens`.

**Pattern:**
- Module name prefixed with `_` (private, peer to consumer)
- Imports limited to stdlib (no `litellm`, no provider classes)
- Pure function: no side effects, no I/O, no globals
- Defensive duck-typing: `getattr(obj, "field", default) or default` to handle `None`, missing attrs, and falsy values uniformly
- Unit test mirrors the pattern in `tests/harness/test_telemetry.py::test_redact_tool_args_*` — simple input/output assertions, `SimpleNamespace` for stub usage objects

### Flat telemetry data dict (no nested cache: {} sub-object)

**Source:** `voss/harness/agent.py:528-535` (`cognition.snapshot` event) and `agent.py:645-658` (`provider.response` event today).

**Apply to:** `provider.response` event extension in CACHE-07.

**Pattern:** New fields land as flat keys at the same nesting depth as existing keys. NO nested `cache: {...}` sub-object. Naming mirrors the dataclass field name (`cache_creation_input_tokens`, `cache_read_input_tokens`) — consumers (RunRecord serializer, future replay) align effortlessly.

### Fixture-driven async streaming tests

**Source:** `tests/harness/test_anthropic_stream.py` (entire file).

**Apply to:** `test_streaming_usage_cache.py` (httpx.MockTransport pattern + new SSE fixture) and conceptually to `test_cache_integration.py` (vcrpy replaces httpx.MockTransport but the test structure is the same).

**Pattern:**
1. Fixture file under `tests/harness/fixtures/` with hand-crafted SSE bytes (or vcrpy YAML cassette).
2. `_mock_client(handler)` helper or vcrpy `use_cassette` context manager.
3. `async for ev in provider.stream(...)` consumer.
4. Assertions on collected `events` list — type sequence, individual event fields.

### `SimpleNamespace` stub fixtures for slash + provider tests

**Source:** `tests/harness/test_repl_slash.py::TestT6Behaviors::fake_ctx` (lines 133-169) and `tests/harness/test_session_iterations.py` (dict-as-fixture pattern).

**Apply to:** `test_cache_tokens.py` (stub usage objects), `test_provider_response.py` (stub responses), `test_cost_slash.py` (stub ReplContext via SimpleNamespace, copied from `fake_ctx`).

## No Analog Found

Two files have no close existing analog and rely on RESEARCH.md patterns:

| File | Role | Reason |
|------|------|--------|
| `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` | fixture | No vcrpy cassette exists in the repo; format is auto-generated by `VOSS_RECORD=1`. Analog `anthropic_stream_plan.sse` is structurally distinct (SSE plain-text, not YAML). |
| `tests/harness/fixtures/cassettes/README.md` | doc | No equivalent README under `tests/` exists. Pattern is minimal — workflow note only, content drafted from RESEARCH.md §Common Pitfalls 5 + CONTEXT D-07. |

For both, the planner should reference RESEARCH.md Pattern 3 §"vcrpy cassette gated by VOSS_RECORD env var" (lines 254-292) directly.

## Metadata

**Analog search scope:**
- `/Users/benjaminmarks/Projects/Voss/voss/harness/` (agent.py, providers.py, session.py, cli.py, telemetry.py, recorder.py)
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/providers/` (base.py, litellm_provider.py)
- `/Users/benjaminmarks/Projects/Voss/tests/harness/` (full file listing, ~60 test files inspected by name; 6 read in depth)
- `/Users/benjaminmarks/Projects/Voss/tests/harness/fixtures/` (existing SSE fixtures)
- `/Users/benjaminmarks/Projects/Voss/pyproject.toml`

**Files scanned in depth:** 11 (agent.py, providers.py, session.py, cli.py, recorder.py, telemetry.py, base.py, litellm_provider.py, test_session_iterations.py, test_anthropic_stream.py, test_provider_stream_types.py, test_repl_slash.py, test_telemetry.py, pyproject.toml).

**Pattern extraction date:** 2026-05-16

## PATTERN MAPPING COMPLETE

**Phase:** T4 - Prompt Caching + Cost Truthfulness
**Files classified:** 17 (9 new, 8 modified)
**Analogs found:** 15 / 17 (88%)

### Coverage
- Files with exact analog: 11 (self-extension or T1/T2 additive-dataclass + test_repl_slash.py for slash tests)
- Files with role-match analog: 4 (cache extractor → redact_tool_args; cassette integration test → MockTransport SSE; vcrpy YAML → SSE fixture; telemetry test hybrid)
- Files with no analog: 2 (cassette YAML auto-generated; cassettes/README.md doc — both covered by RESEARCH.md patterns)

### Key Patterns Identified
- T1/T2 additive-dataclass pattern: int-default-zero fields land before factory-default fields; old fixtures round-trip via `dataclass(**old_dict_without_new_keys)` — applies to `ProviderResponse`, streaming `Usage`, and `IterationRecord` symmetrically.
- T3 D-15 pure-peer-module-helper pattern: `_cache_tokens.py` mirrors `redact_tool_args` structurally (stdlib-only, defensive duck-typing, unit-tested with `SimpleNamespace`).
- Existing flat-telemetry-data-dict convention (cognition.snapshot, provider.response) — CACHE-07 adds two flat keys, no nested `cache: {}` sub-object.
- httpx.MockTransport SSE-fixture test pattern in `test_anthropic_stream.py` is the structural analog for `test_streaming_usage_cache.py`; vcrpy `use_cassette` in `test_cache_integration.py` is the same shape with a different recording layer.
- `test_repl_slash.py::TestT6Behaviors` fixture (`fake_ctx` SimpleNamespace + `_build_slash_registry().lookup("/cost").handler(...)` invocation) is the exact analog for `test_cost_slash.py`; the existing `test_cost_by_tool_is_honest_stub` asserts `"T4" in out` and must be updated alongside the D-09 placeholder edit.

### File Created
`/Users/benjaminmarks/Projects/Voss/.planning/phases/T4-prompt-caching-cost-truthfulness/T4-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns by file:line in PLAN.md files. All extension sites have explicit code excerpts the planner can quote verbatim.
