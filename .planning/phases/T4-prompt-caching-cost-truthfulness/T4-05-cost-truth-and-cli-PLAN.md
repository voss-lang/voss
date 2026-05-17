---
phase: T4-prompt-caching-cost-truthfulness
plan: 05
type: execute
wave: 4
depends_on: ["T4-01", "T4-02"]
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_cost_accounting.py
  - tests/harness/test_cost_slash.py
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [CACHE-03, CACHE-04]

must_haves:
  truths:
    - "CACHE-03 asserts cache pricing is non-zero: a ProviderResponse with cache_creation_input_tokens > 0 produces strictly greater cost_usd than the same response with both cache fields == 0, when cost_usd is sourced from LiteLLM's cost_per_token computation."
    - "CACHE-04 asserts /cost --by-model sums per-run cost_usd per model to 4-decimal precision."
    - "CACHE-04 asserts /cost --by-tool placeholder cites T6 SLASH-07 (not T4)."
    - "The pre-existing test_cost_by_tool_is_honest_stub in test_repl_slash.py — which today asserts 'T4' in out — is updated to assert 'T6' in out (per CONTEXT D-09 and PATTERNS.md)."
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "/cost --by-tool placeholder text references T6 SLASH-07 (D-09 single-line edit)."
      contains: "T6 SLASH-07"
    - path: "tests/harness/test_cost_accounting.py"
      provides: "CACHE-03 cache-aware cost differential test (green)."
    - path: "tests/harness/test_cost_slash.py"
      provides: "CACHE-04 4-decimal /cost --by-model + T6 placeholder tests (green)."
  key_links:
    - from: "tests/harness/test_repl_slash.py::test_cost_by_tool_is_honest_stub"
      to: "voss/harness/cli.py:565-571 placeholder string"
      via: "string assertion against captured stdout"
      pattern: "T6"
---

<objective>
Land the cost-truth verification layer: prove LiteLLM's `cost_usd` is cache-aware by fixture differential (CACHE-03), prove `/cost --by-model` matches the per-run sum to 4-decimal precision (CACHE-04), and execute the D-09 single-line CLI placeholder edit (T4 → T6 SLASH-07). Update the existing `test_cost_by_tool_is_honest_stub` assertion in lockstep so the build does not break.

Purpose: CACHE-03 is the falsifiability anchor for D-06 (trust LiteLLM exclusively); CACHE-04 verifies the existing `/cost --by-model` math without re-implementing it; D-09 retires the stale T4 reference now that T4 is actually shipping. This plan touches only cli.py + tests — no overlap with T4-04's agent.py / providers.py / session.py / recorder.py work, so they run in parallel.
Output: One single-line cli.py edit + 2 green new test files + 1 assertion update in an existing test file.
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
@voss/harness/cli.py
@tests/harness/test_repl_slash.py

<interfaces>
<!-- Existing /cost handler and its T6 test surface. -->

From voss/harness/cli.py:562-590 — the `_cost` slash handler. The `--by-tool` placeholder lives at lines 565-571 (today references T4). The `--by-model` aggregation lives at 572-590 and is mathematically correct as-is (per RESEARCH.md and PATTERNS.md — verified by inspection); CACHE-04 only verifies it, no code change.

From tests/harness/test_repl_slash.py:128-231 — `TestT6Behaviors` class with `fake_ctx` fixture (lines 133-169). `test_cost_by_tool_is_honest_stub` at lines 225-231 currently asserts `"T4" in out`.

Cost-from-LiteLLM contract (D-06, RESEARCH.md §Standard Stack): `cost_usd` flows from `resp._hidden_params.response_cost` in voss_runtime/providers/litellm_provider.py:43. LiteLLM's `cost_calculator.py:712-720` takes `cache_creation_input_tokens` and `cache_read_input_tokens` as explicit kwargs (verified in RESEARCH.md §Sources).

For CACHE-03, the simplest fixture source per T4-PATTERNS.md "test_cost_accounting.py" Option (a) is two stub `ProviderResponse` instances whose `cost_usd` is hand-set from a `litellm.cost_per_token(...)` probe — decouples the test from cassette state and from network availability.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: D-09 placeholder string update (cli.py + test_repl_slash.py assertion)</name>
  <files>voss/harness/cli.py, tests/harness/test_repl_slash.py</files>
  <action>
    Two surgical edits.

    (1) In `voss/harness/cli.py`, locate the `--by-tool` branch at lines 565-571 and replace the click.echo string body. Per CONTEXT D-09 and T4-PATTERNS.md (cli.py section), change:
    ```
    "  /cost --by-tool: per-tool cost tracking lands with T4 "
    "(prompt caching). Recorder doesn't yet attribute provider "
    "cost to individual tool calls."
    ```
    To:
    ```
    "  /cost --by-tool: per-tool cost tracking lands with T6 SLASH-07. "
    "Recorder doesn't yet attribute provider cost to individual tool calls."
    ```
    Preserve the leading two-space indent and click.echo call structure exactly. The `return` immediately after is unchanged. The `--by-model` block (lines 572-590) is untouched.

    (2) In `tests/harness/test_repl_slash.py`, locate `test_cost_by_tool_is_honest_stub` at lines 225-231 and update the assertion from `assert "T4" in out` to `assert "T6" in out  # T6 SLASH-07 — per-tool cost tracking destination (post-T4 update)`. Do not touch any other test in that file.

    These two edits MUST land in the same commit so the suite never sees a transitional state where cli.py says T6 but test_repl_slash.py asserts T4. The agent should make both file edits before re-running the affected test.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_repl_slash.py::TestT6Behaviors -x -q && grep -F 'T6 SLASH-07' voss/harness/cli.py</automated>
  </verify>
  <done>
    test_repl_slash.py::TestT6Behaviors all green (including the updated `test_cost_by_tool_is_honest_stub`). The `grep -F 'T6 SLASH-07' voss/harness/cli.py` matches the new placeholder string. No other tests regress.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: CACHE-04 — /cost --by-model 4-decimal + placeholder citation tests</name>
  <files>tests/harness/test_cost_slash.py</files>
  <behavior>
    - `test_by_model_matches_per_run_sum_to_4_decimals`: a fake ReplContext with runs `[{"cost_usd": 0.0123, ...}, {"cost_usd": 0.0456, ...}]` invoked via `_build_slash_registry().lookup("/cost").handler(fake_ctx, ["--by-model"], "/cost --by-model")` prints a line containing `$0.0579` (4-decimal sum). The captured stdout must NOT contain only `$0.06` rounding.
    - `test_by_tool_placeholder_cites_t6`: invoking `/cost --by-tool` against any fake_ctx prints output containing both `"T6"` and `"SLASH-07"`, and does NOT contain a standalone `"T4"` token. (Test against the placeholder text only; a substring `"T6 SLASH-07"` in the output proves both citations.)
  </behavior>
  <action>
    Convert the two T4-01 red stubs in `tests/harness/test_cost_slash.py` to GREEN tests per T4-PATTERNS.md "test_cost_slash.py" section. Use the analog fixture pattern from `tests/harness/test_repl_slash.py::TestT6Behaviors::fake_ctx` (lines 133-169):

    - Inline a minimal `fake_ctx` fixture (copy the SimpleNamespace structure from test_repl_slash.py:133-169). Do NOT import the fixture across files; project convention is per-file fixtures.
    - For `test_by_model_matches_per_run_sum_to_4_decimals`, set `record.runs = [{"cost_usd": 0.0123, "changed": []}, {"cost_usd": 0.0456, "changed": []}]`, set `record.model = "claude-sonnet-4-7"`, set `total_cost = 0.0579`. Invoke `_build_slash_registry().lookup("/cost").handler(fake_ctx, ["--by-model"], "/cost --by-model")` and capture stdout via `capsys`. Assert `"$0.0579" in out` AND `"claude-sonnet-4-7" in out`.
    - For `test_by_tool_placeholder_cites_t6`, invoke `_build_slash_registry().lookup("/cost").handler(fake_ctx, ["--by-tool"], "/cost --by-tool")` and capture stdout. Assert `"T6 SLASH-07" in out`. Do NOT assert `"T4" not in out` — overly strict; the substring assertion is sufficient.

    These two tests both touch the same `_cost` handler — keep them in one file. CACHE-04 acceptance criterion is satisfied.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_cost_slash.py -x -q</automated>
  </verify>
  <done>Both tests in test_cost_slash.py pass. The 4-decimal assertion proves cli.py:582-589 `${c:.4f}` format string works as designed; the T6 assertion confirms D-09 landed in Task 1.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: CACHE-03 — LiteLLM cost is cache-aware (fixture differential)</name>
  <files>tests/harness/test_cost_accounting.py</files>
  <behavior>
    - Two ProviderResponse fixtures with the same `prompt_tokens` and `completion_tokens` but different cache token counts produce different `cost_usd` values, with the cache-creation fixture strictly more expensive than the no-cache fixture.
    - Cost values come from `litellm.cost_per_token(model="claude-sonnet-4-5", prompt_tokens=..., completion_tokens=..., cache_creation_input_tokens=..., cache_read_input_tokens=...)` — Voss does not own pricing math (D-06 lock).
  </behavior>
  <action>
    Convert the T4-01 red `test_litellm_cost_includes_cache_rates` stub to a GREEN test per T4-PATTERNS.md "test_cost_accounting.py" Option (a) (decoupled from cassette state).

    Imports: `pytest`, `litellm`, `from voss_runtime.providers.base import ProviderResponse`.

    Two fixtures (constructed in-test, no external state):
    ```
    pricing_kwargs = dict(
        model="claude-sonnet-4-5",
        prompt_tokens=1000,
        completion_tokens=200,
    )

    cost_with_cache_creation = sum(litellm.cost_per_token(
        **pricing_kwargs,
        cache_creation_input_tokens=2000,
        cache_read_input_tokens=0,
    ))

    cost_without_cache = sum(litellm.cost_per_token(
        **pricing_kwargs,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    ))
    ```
    (Note: `litellm.cost_per_token` returns a (prompt_cost, completion_cost) tuple — sum it.)

    Assertions:
    - `cost_with_cache_creation > cost_without_cache` — strict inequality. This proves LiteLLM's pricing for `cache_creation_input_tokens` is non-zero. If this assertion fails, LiteLLM regressed (Pitfall 1 fix reverted) and Voss must investigate — that's the falsifiability anchor RESEARCH.md §Common Pitfalls 1 describes.
    - Also assert `cost_without_cache > 0` to guard against `cost_per_token` returning 0 for a typo'd model name.

    Add a docstring at module level: `"""CACHE-03: LiteLLM's cost_per_token charges for cache_creation_input_tokens — Voss trusts this entirely (D-06). No Voss-owned pricing table."""`

    Edge case: if `litellm.cost_per_token` raises (e.g., model not in the pricing JSON for the local litellm version), wrap in `try/except` and `pytest.skip(f"litellm cost_per_token unavailable for claude-sonnet-4-5: {e}")` — but ONLY for ImportError or KeyError, not generic Exception. Document this as A4 in the test docstring.

    Do NOT make any network call. Do NOT touch cassettes. This test runs offline against installed litellm 1.74+.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_cost_accounting.py -x -q</automated>
  </verify>
  <done>test_litellm_cost_includes_cache_rates passes (asserts strict cost differential when cache tokens are non-zero). The test uses litellm.cost_per_token directly — no Voss pricing math added.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| harness→LiteLLM pricing | Voss reads `_hidden_params.response_cost` from LiteLLM and never overrides it. CACHE-03 is the falsifiability anchor against silent LiteLLM cache-pricing regressions. |
| CLI→user | `/cost` slash command output crosses to the user via stdout; cost values come from RunRecord/ProviderResponse. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T4-05-01 | Repudiation | LiteLLM cache pricing regression | mitigate | CACHE-03 fixture differential is the contract test; if LiteLLM cost_per_token stops charging for cache_creation_input_tokens (Pitfall 1 regression), the test fails loudly. |
| T-T4-05-02 | Tampering | Voss-owned pricing | mitigate | D-06 lock — no Voss pricing module is added by this plan or any T4 plan. CACHE-03 enforces this by asserting LiteLLM's pricing is non-zero rather than asserting a specific Voss-computed number. |
| T-T4-05-03 | Information Disclosure | `/cost` stdout | accept | Cost summaries are part of the existing harness UX; no new disclosure surface. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_cost_accounting.py tests/harness/test_cost_slash.py tests/harness/test_repl_slash.py -x -q` exits 0.
- `grep -F 'T6 SLASH-07' voss/harness/cli.py` matches exactly one line.
- `grep -cE '"T4"' voss/harness/cli.py` returns 0 (no stale T4 reference in the placeholder).
- `grep -nE '"T4"' tests/harness/test_repl_slash.py` shows no remaining `"T4"` assertion in `test_cost_by_tool_is_honest_stub`.
- No Voss-owned pricing module, constants, or `[cost]` config block introduced (D-06 lock). Verify via `grep -rE 'cache_creation_rate|cache_read_rate|cost_multiplier' voss voss_runtime` returning 0 matches.
</verification>

<success_criteria>
- D-09 single-line placeholder edit lands in cli.py with the matching assertion update in test_repl_slash.py.
- CACHE-03 passes — LiteLLM's cost_per_token charges for cache_creation_input_tokens; no Voss pricing math added.
- CACHE-04 passes — `/cost --by-model` prints 4-decimal accurate per-model sums; `/cost --by-tool` placeholder cites T6 SLASH-07.
- All three T4-01 stubs (test_cost_accounting, test_cost_slash × 2) are GREEN.
- No agent.py / providers.py / session.py / recorder.py touched — this plan is fully orthogonal to T4-04 and they share Wave 4.
</success_criteria>

<output>
Create `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-05-SUMMARY.md` when done.
</output>
