---
phase: T4-prompt-caching-cost-truthfulness
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - tests/harness/test_cache_tokens.py
  - tests/harness/test_agent_caching.py
  - tests/harness/test_cache_invalidation.py
  - tests/harness/test_streaming_usage_cache.py
  - tests/harness/test_provider_response.py
  - tests/harness/test_cost_accounting.py
  - tests/harness/test_cost_slash.py
  - tests/harness/test_telemetry_cache_fields.py
  - tests/harness/test_cache_integration.py
  - tests/harness/fixtures/cassettes/README.md
autonomous: true
requirements: [CACHE-01, CACHE-02, CACHE-03, CACHE-04, CACHE-05, CACHE-06, CACHE-07]

must_haves:
  truths:
    - "Every CACHE-NN requirement has at least one failing test stub in tests/harness/."
    - "pyproject.toml pins litellm>=1.74.0 and vcrpy>=8.0.0,<9 (vcrpy under dev)."
    - "The cassette fixture directory exists with a README documenting VOSS_RECORD=1."
  artifacts:
    - path: "tests/harness/test_cache_tokens.py"
      provides: "D-04 extractor unit-test stubs (Anthropic / OpenAI / missing / None shapes)."
    - path: "tests/harness/test_agent_caching.py"
      provides: "CACHE-01 marker-shape stub."
    - path: "tests/harness/test_cache_invalidation.py"
      provides: "CACHE-06 four-drift parametrized stub."
    - path: "tests/harness/test_streaming_usage_cache.py"
      provides: "CACHE-02 streaming-half stub."
    - path: "tests/harness/test_provider_response.py"
      provides: "CACHE-02 non-streaming-half stub."
    - path: "tests/harness/test_cost_accounting.py"
      provides: "CACHE-03 cache-aware cost differential stub."
    - path: "tests/harness/test_cost_slash.py"
      provides: "CACHE-04 /cost --by-model 4-decimal + --by-tool placeholder stub."
    - path: "tests/harness/test_telemetry_cache_fields.py"
      provides: "CACHE-07 telemetry payload + RunRecord round-trip stub."
    - path: "tests/harness/test_cache_integration.py"
      provides: "CACHE-05 / CACHE-07-invariant vcrpy cassette stub."
    - path: "tests/harness/fixtures/cassettes/README.md"
      provides: "Cassette re-record workflow doc."
    - path: "pyproject.toml"
      provides: "litellm>=1.74.0 floor + vcrpy>=8.0.0,<9 dev dep."
  key_links:
    - from: "tests/harness/test_*.py"
      to: "pyproject.toml dev deps"
      via: "vcrpy import in test_cache_integration.py"
      pattern: "import vcr"
---

<objective>
Land the Wave 0 test scaffold for phase T4 in one pass: every CACHE-NN requirement gets a failing pytest stub, the cassette fixture directory exists with workflow docs, and pyproject.toml pins are raised. Subsequent plans turn red stubs into green tests.

Purpose: Give every downstream plan a fail-then-pass arc and enforce per-task `<automated>` coverage. Mirrors the established Wave 0 pattern from T1/T2.
Output: 9 new test files, 1 README, 1 modified pyproject.toml — no production code touched.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-SPEC.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-CONTEXT.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-RESEARCH.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-PATTERNS.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-VALIDATION.md
@pyproject.toml
@tests/harness/test_telemetry.py
@tests/harness/test_repl_slash.py
@tests/harness/test_session_iterations.py
@tests/harness/test_anthropic_stream.py
@tests/harness/test_provider_stream_types.py

<interfaces>
<!-- Imports the stubs will need. Targets are created by downstream plans. -->

From voss_runtime/providers/base.py (existing today; T4-02 extends additively):
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

Symbols that will exist after later plans (stubs may reference via `pytest.importorskip` or `try/except ImportError: pytest.skip(...)` so this plan stays green on the additive-fields-not-yet-added paths):
- `voss_runtime.providers._cache_tokens.extract_cache_tokens` — created by T4-02.
- `voss.harness.agent._compose_system_blocks` — created by T4-03.

Stub strategy: each test file imports its target inside the test (or at module top with a `pytest.importorskip` guard) so the WHOLE FILE runs and FAILS cleanly per test, instead of collection-erroring on import.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bump pyproject pins (litellm, vcrpy)</name>
  <files>pyproject.toml</files>
  <action>
    Edit pyproject.toml per RESEARCH.md §Standard Stack and CONTEXT D-06 / D-07:
    (1) On the `dependencies = [...]` block (lines 10-23), change `"litellm>=1.50.0"` to `"litellm>=1.74.0"` and add an end-of-line comment `# T4 CACHE-03: cache-cost double-count fix (PR #9838, PR #25517)`.
    (2) On the `dev = [...]` block (lines 35-44), add `"vcrpy>=8.0.0,<9",  # T4 CACHE-05: cassette replay; v8 patches httpcore` after the `"respx>=0.21",` entry.
    Do NOT touch the `search` block or any other dependency. Do NOT reflow surrounding lines.
  </action>
  <verify>
    <automated>grep -E '"litellm>=1\.74\.0"' pyproject.toml && grep -E '"vcrpy>=8\.0\.0,<9"' pyproject.toml</automated>
  </verify>
  <done>Both grep commands match exactly one line. No other lines in pyproject.toml are modified.</done>
</task>

<task type="auto">
  <name>Task 2: Create failing test stubs for all 9 CACHE-NN test files</name>
  <files>
    tests/harness/test_cache_tokens.py,
    tests/harness/test_agent_caching.py,
    tests/harness/test_cache_invalidation.py,
    tests/harness/test_streaming_usage_cache.py,
    tests/harness/test_provider_response.py,
    tests/harness/test_cost_accounting.py,
    tests/harness/test_cost_slash.py,
    tests/harness/test_telemetry_cache_fields.py,
    tests/harness/test_cache_integration.py
  </files>
  <action>
    Create nine new pytest files following the per-file specs below. Every test is a stub that FAILS LOUDLY today with `pytest.fail("not yet implemented: <plan that lands this>")` or `pytest.xfail(...)` — the executor must use `pytest.fail` (HARD red), not skip. Each test file's module docstring cites the requirement and the plan that will turn it green.

    Use existing analog patterns per T4-PATTERNS.md:
    - `tests/harness/test_cache_tokens.py` — analog `test_telemetry.py::test_redact_*`. Four functions: `test_anthropic_shape_returns_both_counts`, `test_openai_shape_returns_read_only`, `test_missing_fields_default_to_zero`, `test_none_usage_returns_zero`. Each builds a `types.SimpleNamespace` mock (or `None`) and asserts the expected `(creation, read)` tuple. Bodies all start with `pytest.fail("T4-02 lands extract_cache_tokens")` so they're red today.
    - `tests/harness/test_agent_caching.py` — analog `test_provider_stream_types.py::TestEventShapes`. Two functions: `test_system_blocks_have_single_marker`, `test_empty_inputs_produce_empty_block_list`. Bodies fail with `pytest.fail("T4-03 lands _compose_system_blocks")`.
    - `tests/harness/test_cache_invalidation.py` — analog `test_session_iterations.py::TestPreT1FixtureRoundTrip`. One parametrized function `test_drift_changes_rendered_prefix` with four parametrize IDs (`voss_md`, `cognition`, `prior_ctx`, `max_iters`) per VALIDATION.md table. Body fails with `pytest.fail("T4-03 lands cache invalidation")`.
    - `tests/harness/test_streaming_usage_cache.py` — analog `test_anthropic_stream.py::test_stream_emits_documented_event_sequence`. One function `test_stream_usage_event_carries_cache_tokens`. Body fails with `pytest.fail("T4-04 lands streaming Usage cache fields")`.
    - `tests/harness/test_provider_response.py` — analog `test_session_iterations.py::TestIterationRecord::test_constructs_with_all_defaults_except_index`. Three functions: `test_provider_response_defaults_cache_fields_to_zero`, `test_anthropic_usage_extraction`, `test_openai_cached_tokens_extraction`. Bodies fail with `pytest.fail("T4-02 lands ProviderResponse cache fields")`.
    - `tests/harness/test_cost_accounting.py` — analog `test_session_iterations.py::TestPreT1FixtureRoundTrip` for fixture shape. One function `test_litellm_cost_includes_cache_rates`. Body fails with `pytest.fail("T4-05 lands cache-aware cost differential")`.
    - `tests/harness/test_cost_slash.py` — analog `test_repl_slash.py::TestT6Behaviors`. Two functions: `test_by_model_matches_per_run_sum_to_4_decimals`, `test_by_tool_placeholder_cites_t6`. Reuse the `fake_ctx` SimpleNamespace fixture pattern from test_repl_slash.py:133-169 (inline a minimal copy — do NOT import the fixture across files). Bodies fail with `pytest.fail("T4-05 lands /cost --by-model verification and D-09 update")`.
    - `tests/harness/test_telemetry_cache_fields.py` — analog `test_telemetry.py::test_emit_writes_ndjson_file` + `test_session_iterations.py::TestPreT1FixtureRoundTrip`. Three functions: `test_provider_response_event_carries_cache_tokens`, `test_iteration_record_cache_fields_default_zero_for_old_fixtures`, `test_iteration_record_cache_fields_round_trip`. Bodies fail with `pytest.fail("T4-04 lands telemetry + IterationRecord additive fields")`.
    - `tests/harness/test_cache_integration.py` — analog `test_anthropic_stream.py`, replacing MockTransport with `vcr.use_cassette`. Two functions: `test_first_turn_writes_cache`, `test_second_turn_reads_cache`. Add `import pytest`, attempt `import vcr` inside `pytest.importorskip("vcr")` so the file collects even before the cassette/recording ships. Bodies fail with `pytest.fail("T4-06 lands cassette integration")`.

    Every stub file MUST include a module docstring identifying the requirement (e.g., `"""CACHE-01: agent.py emits multi-block system content with one cache_control marker."""`) and the landing plan ID. Do not add ANY imports beyond what each stub needs — keep red stubs minimal so the executor can extend cleanly.

    CRITICAL: tests must FAIL, not skip. `pytest.fail("...")` only. Reason: VALIDATION.md sampling gate requires red→green arc visibility per task.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py tests/harness/test_streaming_usage_cache.py tests/harness/test_provider_response.py tests/harness/test_cost_accounting.py tests/harness/test_cost_slash.py tests/harness/test_telemetry_cache_fields.py tests/harness/test_cache_integration.py --collect-only -q 2>&1 | grep -c "::test_" | xargs -I{} test {} -ge 14</automated>
  </verify>
  <done>All 9 test files collect (at least 14 test items across them) and each test fails with a `pytest.fail("...T4-NN...")` message naming its landing plan.</done>
</task>

<task type="auto">
  <name>Task 3: Create cassette directory + workflow README</name>
  <files>tests/harness/fixtures/cassettes/README.md</files>
  <action>
    Create directory `tests/harness/fixtures/cassettes/` (parent already exists) by writing the README.md inside it. Content per T4-PATTERNS.md "Cache integration cassettes" block — minimal Markdown documenting: (a) what the directory holds (vcrpy YAML cassettes for test_cache_integration.py), (b) the `VOSS_RECORD=1 ANTHROPIC_API_KEY=... python3 -m pytest tests/harness/test_cache_integration.py -x` re-record workflow, (c) the `filter_headers` redaction list (x-api-key, authorization, anthropic-api-key, cookie, set-cookie), (d) the CI replay-only posture (record_mode='none' raises on missing cassette by design — that's the signal to re-record). Do NOT add a `.gitignore`; cassettes are committed per CONTEXT D-07.
  </action>
  <verify>
    <automated>test -f tests/harness/fixtures/cassettes/README.md && grep -q "VOSS_RECORD=1" tests/harness/fixtures/cassettes/README.md && grep -q "filter_headers" tests/harness/fixtures/cassettes/README.md</automated>
  </verify>
  <done>README exists, mentions VOSS_RECORD=1 workflow and filter_headers redaction list.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo→committed YAML cassette | Future cassettes (T4-06) will contain Anthropic SSE responses; this plan creates the directory + README that establishes the redaction contract. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T4-01-01 | Information Disclosure | tests/harness/fixtures/cassettes/* | mitigate | README codifies the `filter_headers` list (x-api-key, authorization, anthropic-api-key, cookie, set-cookie). Cassette author follows it. |
| T-T4-01-SC | Tampering | vcrpy install | mitigate | vcrpy is listed in Package Legitimacy Audit (RESEARCH.md §Package Legitimacy Audit) as Approved. wrapt is a known transitive (Approved). No [ASSUMED] / [SUS] packages introduced; no blocking human-verify gate needed for this plan. |
</threat_model>

<verification>
- `grep '"litellm>=1.74.0"' pyproject.toml` exits 0.
- `grep '"vcrpy>=8.0.0,<9"' pyproject.toml` exits 0.
- `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py tests/harness/test_streaming_usage_cache.py tests/harness/test_provider_response.py tests/harness/test_cost_accounting.py tests/harness/test_cost_slash.py tests/harness/test_telemetry_cache_fields.py tests/harness/test_cache_integration.py --collect-only -q` collects ≥14 items.
- All collected tests FAIL (not skip) when invoked: `python3 -m pytest tests/harness/test_cache_tokens.py ... -x` exits non-zero with `pytest.fail` messages referencing T4-02/03/04/05/06.
- `tests/harness/fixtures/cassettes/README.md` exists.
</verification>

<success_criteria>
- 9 new test files exist with failing stubs that name their landing plan.
- pyproject.toml pins are raised per CONTEXT D-06 and RESEARCH.md §Standard Stack.
- Cassette directory + README documents the VOSS_RECORD=1 workflow.
- No production code in voss/ or voss_runtime/ is modified.
- Wave 1 quick command (`python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py -x`) returns RED with `pytest.fail` messages — establishing the fail→pass arc for all downstream plans.
</success_criteria>

<output>
Create `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-01-SUMMARY.md` when done.
</output>
