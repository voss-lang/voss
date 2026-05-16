---
phase: T4-prompt-caching-cost-truthfulness
plan: 02
type: execute
wave: 2
depends_on: ["T4-01"]
files_modified:
  - voss_runtime/providers/_cache_tokens.py
  - voss_runtime/providers/base.py
  - voss_runtime/providers/litellm_provider.py
  - tests/harness/test_cache_tokens.py
  - tests/harness/test_provider_response.py
autonomous: true
requirements: [CACHE-02]

must_haves:
  truths:
    - "extract_cache_tokens(usage) returns (creation, read) for Anthropic, OpenAI, missing, and None usage shapes."
    - "ProviderResponse carries cache_creation_input_tokens and cache_read_input_tokens (additive int=0)."
    - "LiteLLMProvider.complete populates both new fields from resp.usage via extract_cache_tokens."
    - "Pre-T4 ProviderResponse construction (5 positional args, no cache kwargs) still works — backward-compatible defaults preserved."
  artifacts:
    - path: "voss_runtime/providers/_cache_tokens.py"
      provides: "Pure stdlib extractor — D-04 location."
      exports: ["extract_cache_tokens"]
    - path: "voss_runtime/providers/base.py"
      provides: "ProviderResponse with two additive int=0 cache fields."
      contains: "cache_creation_input_tokens"
    - path: "voss_runtime/providers/litellm_provider.py"
      provides: "Cache-aware ProviderResponse construction."
      contains: "extract_cache_tokens(usage)"
  key_links:
    - from: "voss_runtime/providers/litellm_provider.py"
      to: "voss_runtime/providers/_cache_tokens.py"
      via: "relative import from ._cache_tokens"
      pattern: "from \\._cache_tokens import extract_cache_tokens"
    - from: "voss_runtime/providers/litellm_provider.py"
      to: "voss_runtime/providers/base.py::ProviderResponse"
      via: "kwarg passing"
      pattern: "cache_creation_input_tokens="
---

<objective>
Land the pure cache-token extractor (D-04), extend `ProviderResponse` with two additive int=0 cache fields, and wire `LiteLLMProvider.complete` to populate them. Turn the two T4-01 red stubs for CACHE-02 non-streaming + `_cache_tokens` extractor green.

Purpose: Unblocks every downstream plan. The extractor is the single probe used by both non-streaming (here) and streaming (T4-04) provider paths. The additive ProviderResponse fields are the symmetric data-shape extension D-01 requires.
Output: One new module + two surgical dataclass / function extensions + 2 green test files.
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
@voss_runtime/providers/base.py
@voss_runtime/providers/litellm_provider.py
@voss/harness/telemetry.py

<interfaces>
<!-- Existing — extending additively per D-01 / D-04. -->

Today's ProviderResponse (voss_runtime/providers/base.py:7-19):
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
```

Today's LiteLLM extraction (voss_runtime/providers/litellm_provider.py:40-60): Constructs ProviderResponse from `choice.content`, `usage.prompt_tokens`, `usage.completion_tokens`, and `resp._hidden_params.response_cost`. The extension adds one call to `extract_cache_tokens(usage)` and two kwargs on the return.

LiteLLM `Usage` shape (verified in RESEARCH.md §Sources via local probe of litellm 1.74.7):
- Anthropic models: `usage.cache_creation_input_tokens: int`, `usage.cache_read_input_tokens: int` (top-level attrs).
- OpenAI models: `usage.prompt_tokens_details.cached_tokens: int` (nested); top-level cache fields absent.
- Stub / missing: both shapes return zeros.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement extract_cache_tokens (pure stdlib helper)</name>
  <files>voss_runtime/providers/_cache_tokens.py, tests/harness/test_cache_tokens.py</files>
  <behavior>
    - `extract_cache_tokens(SimpleNamespace(cache_creation_input_tokens=120, cache_read_input_tokens=480))` returns `(120, 480)`.
    - `extract_cache_tokens(SimpleNamespace(prompt_tokens_details=SimpleNamespace(cached_tokens=300)))` returns `(0, 300)`.
    - `extract_cache_tokens(SimpleNamespace())` returns `(0, 0)`.
    - `extract_cache_tokens(None)` returns `(0, 0)`.
  </behavior>
  <action>
    Create `voss_runtime/providers/_cache_tokens.py` per CONTEXT D-04 and RESEARCH.md Pattern 2. Module must use `from __future__ import annotations` and stdlib only — NO `litellm`, `anthropic`, or `openai` imports.

    Function signature: `def extract_cache_tokens(usage_obj) -> tuple[int, int]:` returning `(creation, read)`. Use defensive duck-typing:
    1. If `usage_obj is None` → return `(0, 0)`.
    2. Read `cache_creation_input_tokens` and `cache_read_input_tokens` via `int(getattr(obj, name, 0) or 0)`.
    3. If `read == 0` (Anthropic top-level absent), descend into `prompt_tokens_details` (OpenAI shape) and read `cached_tokens` via the same `int(getattr(...) or 0)` pattern.
    4. Return `(creation, read)`.

    Module docstring cites D-04 and explains the universal-probe rationale (no `model.startswith` branching — handles Anthropic, OpenAI, stub, and future Gemini uniformly).

    Convert the four T4-01 red stubs in `tests/harness/test_cache_tokens.py` to GREEN assertions per the behavior table above. Use `types.SimpleNamespace` (project convention — see RESEARCH.md / PATTERNS.md). Import `from voss_runtime.providers._cache_tokens import extract_cache_tokens` at module top.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_cache_tokens.py -x -q</automated>
  </verify>
  <done>All four tests in test_cache_tokens.py pass. The new module is importable, stdlib-only (`python3 -c "import voss_runtime.providers._cache_tokens"` exits 0), and the function returns the documented tuple for the four canonical shapes.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add additive cache fields to ProviderResponse and wire LiteLLMProvider</name>
  <files>voss_runtime/providers/base.py, voss_runtime/providers/litellm_provider.py, tests/harness/test_provider_response.py</files>
  <behavior>
    - `ProviderResponse(text="x", model="m", prompt_tokens=1, completion_tokens=1, cost_usd=0.0)` constructs cleanly and reports `cache_creation_input_tokens == 0` and `cache_read_input_tokens == 0` (additive defaults).
    - For an Anthropic-shape usage object (`cache_creation_input_tokens=1500, cache_read_input_tokens=0`), `extract_cache_tokens(usage) == (1500, 0)` — the LiteLLMProvider passes the values forward.
    - For an OpenAI-shape usage object (`prompt_tokens_details.cached_tokens=1200`), the response's `cache_creation_input_tokens == 0` and `cache_read_input_tokens == 1200`.
  </behavior>
  <action>
    Extend `voss_runtime/providers/base.py` per T4-PATTERNS.md (analog: T1 IterationRecord additive ints). Insert two new fields between `cost_usd` and `raw`:
    ```
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    ```
    Field ordering rule: defaults must be contiguous from the right. `cost_usd: float` is non-default; `raw` already has `field(default_factory=dict)`. The two new int-default fields land between them. Add an inline comment `# T4 CACHE-02 (D-01): symmetric with ProviderStreamEvent.Usage; additive defaults preserve pre-T4 fixtures` above the new fields.

    Do NOT touch the `total_tokens` property or the `ModelProvider` Protocol. Do NOT widen the existing fields' types.

    Extend `voss_runtime/providers/litellm_provider.py` per T4-PATTERNS.md (self-extension on lines 42-60). Two changes only:
    1. At the existing import block (line 6, `from .base import ProviderResponse`), add a sibling import line `from ._cache_tokens import extract_cache_tokens`.
    2. Between the existing `cost = float(...)` line (43) and the `parsed = None` line (45), add `cache_create, cache_read = extract_cache_tokens(usage)`.
    3. In the `return ProviderResponse(...)` block (lines 52-60), add two kwargs `cache_creation_input_tokens=cache_create,` and `cache_read_input_tokens=cache_read,` between `cost_usd=cost,` and `raw=...`.

    Do not modify error-handling, response_format parsing, or count_tokens.

    Turn the three T4-01 red stubs in `tests/harness/test_provider_response.py` GREEN:
    - `test_provider_response_defaults_cache_fields_to_zero`: construct ProviderResponse without cache kwargs, assert both default to 0.
    - `test_anthropic_usage_extraction`: feed a `SimpleNamespace(prompt_tokens=600, completion_tokens=100, cache_creation_input_tokens=1500, cache_read_input_tokens=0)` to `extract_cache_tokens`, assert `(1500, 0)`. (This test is logically about the extractor in the LiteLLM context — keep it focused on the extractor's behavior with an Anthropic-shaped object; CACHE-02 spec acceptance allows extractor-level assertion since LiteLLMProvider would only forward those values.)
    - `test_openai_cached_tokens_extraction`: feed an OpenAI-shape SimpleNamespace, assert `(0, 1200)`.

    All three tests stay close to the dataclass + extractor surfaces and do NOT make real LiteLLM HTTP calls.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_provider_response.py tests/harness/test_cache_tokens.py -x -q</automated>
  </verify>
  <done>
    Both test files green. `python3 -c "from voss_runtime.providers.base import ProviderResponse; r = ProviderResponse(text='', model='m', prompt_tokens=0, completion_tokens=0, cost_usd=0.0); assert r.cache_creation_input_tokens == 0 and r.cache_read_input_tokens == 0"` exits 0. Pre-T4 ProviderResponse construction (no cache kwargs) still works.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| provider→Voss | LiteLLM-normalized `usage` object is consumed defensively via getattr; non-int values fall back to 0. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T4-02-01 | Tampering | extract_cache_tokens input | mitigate | All field reads go through `int(getattr(obj, name, 0) or 0)` — `None`, missing attrs, and non-int values resolve to 0 without raising (ASVS V5). |
| T-T4-02-02 | Repudiation | LiteLLM cache pricing | accept | Voss does not own cache pricing math (D-06). LiteLLM `_hidden_params.response_cost` is the contractual source; CACHE-03 (in T4-05) is the falsifiability anchor. |
| T-T4-02-SC | Tampering | litellm install | mitigate | litellm pin raised to `>=1.74.0` in T4-01 (PR #9838 + #25517 fixes); already in Package Legitimacy Audit as Approved. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_provider_response.py -x -q` exits 0.
- `python3 -m pytest tests/harness/ -x -q --ignore=tests/harness/test_cache_integration.py` shows the rest of the suite still green (no regression in pre-T4 callers of ProviderResponse).
- `grep -n "extract_cache_tokens" voss_runtime/providers/litellm_provider.py` returns exactly the import and one call site.
- `grep -n "cache_creation_input_tokens\|cache_read_input_tokens" voss_runtime/providers/base.py` returns exactly the two field-definition lines.
</verification>

<success_criteria>
- `extract_cache_tokens` lives at `voss_runtime/providers/_cache_tokens.py`, is stdlib-only, and handles the four canonical shapes.
- `ProviderResponse` carries two additive int=0 cache fields; old call sites unchanged.
- `LiteLLMProvider.complete` populates both fields via the extractor.
- Two T4-01 test stubs (test_cache_tokens, test_provider_response) are GREEN; no other tests regress.
- No `model.startswith(...)` branching introduced anywhere.
- No new external runtime dependency added (D-04 stdlib-only).
</success_criteria>

<output>
Create `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-02-SUMMARY.md` when done.
</output>
