---
phase: M5
plan: 02
type: execute
wave: 1
depends_on:
  - M5-01
files_modified:
  - voss/eval/judge.py
  - voss/harness/auth.py
  - tests/eval/test_judge_verdict.py
  - tests/eval/test_judge_skipped.py
  - tests/harness/test_auth.py
autonomous: true
requirements:
  - EVAL-02
must_haves:
  truths:
    - "`from voss.eval.judge import Verdict, judge_run` works."
    - "Verdict pydantic model validates `{verdict: 'pass'|'fail', confidence: 0..1, rationale: str}` JSON."
    - "`judge_run` returns the Verdict on valid JSON; returns `(None, 'skipped')` on ParseError."
    - "`voss.harness.auth.resolve` accepts an optional `role` kwarg; in v0.1 the kwarg is ignored (pass-through)."
  artifacts:
    - path: "voss/eval/judge.py"
      provides: "Verdict pydantic model + judge_run async function"
      exports: ["Verdict", "judge_run", "JUDGE_SYSTEM"]
      contains: "class Verdict(BaseModel):"
    - path: "voss/harness/auth.py"
      provides: "resolve(preference, role=None) pass-through extension"
      contains: "role: str | None = None"
    - path: "tests/eval/test_judge_verdict.py"
      provides: "FakeJudgeProvider tests for Verdict happy-path + ParseError-skipped fallback"
    - path: "tests/eval/test_judge_skipped.py"
      provides: "Test: when provider raises, judge_run returns (None, 'skipped')"
    - path: "tests/harness/test_auth.py"
      provides: "Pinned regression: resolve(role='judge') == resolve() for v0.1 pass-through"
  key_links:
    - from: "voss/eval/judge.py"
      to: "voss_runtime.providers.litellm_provider.ParseError"
      via: "judge_run catches ParseError and returns (None, 'skipped')"
      pattern: "except ParseError"
    - from: "voss/eval/judge.py"
      to: "voss_runtime.providers.base.ModelProvider"
      via: "judge_run is provider-agnostic (typed against the base protocol)"
      pattern: "ModelProvider"
---

<objective>
Land the judge surface and the minimal `auth.resolve(role=...)` pass-through. The Wave 2 runner will call `judge_run(...)` after each agent run completes; this plan provides that callable, the `Verdict` pydantic model used as `response_format`, and a regression-pinned 1-LOC extension of `auth.resolve` so the runner can request a (logical) judge provider in v0.1 without a second resolver path.

Purpose: EVAL-02 requires per-run pass/fail verdicts from an LLM judge. The runner pulls this through `response_format=Verdict` so judge calls ride the same litellm_provider.py:32-50 JSON-mode contract as `Plan` does. When the model returns unparseable JSON, the row is recorded with `judge_verdict: "skipped"`, `success: null` — the same "skipped" path that the runner uses on agent crash.

Output: New `voss/eval/judge.py` module, a 1-LOC signature change in `voss/harness/auth.py`, and three pytest files pinning the contracts.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md
@.planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md
@.planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md
@.planning/phases/M5-eval-and-distribution-prep/M5-01-PLAN.md
@voss/harness/agent.py
@voss/harness/auth.py
@voss_runtime/providers/litellm_provider.py
@voss_runtime/providers/base.py

<interfaces>
<!-- litellm_provider response_format machinery — voss_runtime/providers/litellm_provider.py:32-50 -->
# if response_format is not None:
#     kwargs["response_format"] = response_format
# try:
#     resp = await litellm.acompletion(**kwargs)
# except Exception as e:
#     raise ProviderError(...) from e
# parsed = None
# if response_format is not None and text:
#     try:
#         parsed = response_format.model_validate_json(text)
#     except Exception as e:
#         raise ParseError(f"Failed to parse {response_format.__name__}: {e}") from e

<!-- ProviderResponse (returned by .complete) -->
# Has fields: text, model, prompt_tokens, completion_tokens, cost_usd, raw, parsed

<!-- Existing auth.resolve signature — voss/harness/auth.py:332 -->
# def resolve(preference: str = "auto") -> Resolution:
#     """Decide which auth path to use.
#     preference: auto | claude | codex | api | none
#     """
#     if preference == "none":
#         return Resolution(source="none", detail="forced none")
#     ...
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Verdict model + judge_run + auth.resolve role kwarg</name>
  <files>voss/eval/judge.py, voss/harness/auth.py</files>
  <read_first>
    - voss/harness/agent.py:43-58 — Plan BaseModel + Field(ge=, le=) constraints (analog for Verdict)
    - voss_runtime/providers/litellm_provider.py:32-50 — response_format=Pydantic JSON-mode machinery + ParseError raise site
    - voss_runtime/providers/base.py — ModelProvider protocol and ProviderResponse dataclass (judge_run must remain provider-agnostic)
    - voss/harness/auth.py:330-360 — existing resolve() signature and body (extension point)
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"voss/eval/judge.py" (lines 160-251) — exact target shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"voss/harness/auth.py:resolve (MODIFY +1 LOC)" (lines 255-291) — extension shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-08, D-09 — judge contract (LLM-as-judge only, Verdict JSON via pydantic)
  </read_first>
  <behavior>
    - `from voss.eval.judge import Verdict, judge_run, JUDGE_SYSTEM` works.
    - `Verdict(verdict="pass", confidence=0.9, rationale="ok")` validates. `verdict` is Literal["pass","fail"]; `confidence` is float in [0,1].
    - `judge_run(provider=fake, model="m", task_prompt="t", final="f", file_diff="", rubric="r")` (when fake returns ProviderResponse with .parsed = Verdict(...)) returns the Verdict and its verdict string.
    - When the provider raises `ParseError`, `judge_run` returns `(None, "skipped")` and does NOT propagate the exception.
    - `voss.harness.auth.resolve(preference="auto")` continues to work unchanged for all existing callers.
    - `voss.harness.auth.resolve(preference="auto", role="judge")` returns the same Resolution as `resolve(preference="auto")` — `role` is accepted and silently ignored (v0.1 pass-through per CONTEXT D-10 + RESEARCH Assumption A1).
  </behavior>
  <action>
    Create `voss/eval/judge.py` per M5-PATTERNS.md lines 187-243:
    - Module docstring `"""LLM-as-judge scorer (M5 D-08, D-09)."""`.
    - Imports: `from __future__ import annotations`; `from typing import Literal`; `from pydantic import BaseModel, ConfigDict, Field`; `from voss_runtime.providers.base import ModelProvider`; `from voss_runtime.providers.litellm_provider import ParseError`.
    - Class `Verdict(BaseModel)` with `model_config = ConfigDict(extra="ignore")` (lenient — judge model may include extra fields), fields: `verdict: Literal["pass", "fail"]`, `confidence: float = Field(ge=0.0, le=1.0)`, `rationale: str`.
    - Module constant `JUDGE_SYSTEM` (multi-line string) per M5-PATTERNS.md lines 206-210: instructs the model to return ONLY a JSON object matching the schema.
    - Async function `judge_run(*, provider: ModelProvider, model: str, task_prompt: str, final: str, file_diff: str, rubric: str) -> tuple[Verdict | None, str]` per M5-PATTERNS.md lines 213-243:
      - Builds a user message containing four labeled sections: "## Task prompt", "## Agent final", "## File diff", "## Rubric".
      - Calls `await provider.complete(messages=[{role:system, content:JUDGE_SYSTEM}, {role:user, content:user_msg}], model=model, response_format=Verdict, temperature=0.0)`.
      - Wraps the call in `try/except ParseError`; on ParseError returns `(None, "skipped")`.
      - If `resp.parsed is None`, returns `(None, "skipped")`.
      - Otherwise returns `(resp.parsed, resp.parsed.verdict)`.
    - `temperature=0.0` for reproducibility (judge must not vary on identical inputs per M5-PATTERNS.md line 249).

    Modify `voss/harness/auth.py:resolve`:
    - Add a `role: str | None = None` keyword argument after `preference`. Update the docstring with the new line: `role: optional logical role (e.g. "judge"); v0.1 pass-through, future versions may resolve a separate creds bucket per role. Today ignored.` per M5-PATTERNS.md lines 273-283.
    - Do NOT branch on `role` anywhere in the function body — RESEARCH Assumption A1 confirms it is a no-op pass-through in v0.1.
    - No other call sites change; `role` defaults to None so all existing `resolve()` / `resolve(preference="auto")` invocations remain compatible.

    Do NOT modify `voss_runtime/providers/*` — the response_format=Pydantic contract is already in place at litellm_provider.py:32-50.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "from voss.eval.judge import Verdict, judge_run, JUDGE_SYSTEM; v = Verdict(verdict='pass', confidence=0.9, rationale='ok'); print(v.verdict, v.confidence); import asyncio; from voss.harness.auth import resolve; r1 = resolve(); r2 = resolve(role='judge'); assert r1.source == r2.source; print('OK')"</automated>
  </verify>
  <done>
    `voss/eval/judge.py` exists with Verdict + judge_run + JUDGE_SYSTEM. `voss/harness/auth.py:resolve` accepts `role` kwarg. No external dependencies added (uses existing pydantic + voss_runtime base/litellm_provider).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Pytest coverage — judge Verdict happy path, ParseError skipped, auth role kwarg</name>
  <files>tests/eval/test_judge_verdict.py, tests/eval/test_judge_skipped.py, tests/harness/test_auth.py</files>
  <read_first>
    - tests/harness/test_agent_integration.py:21-50 — FakeProvider pattern (canned ProviderResponse with .parsed already populated)
    - voss_runtime/providers/base.py — ProviderResponse dataclass fields (text, model, prompt_tokens, completion_tokens, cost_usd, raw, parsed)
    - voss_runtime/providers/litellm_provider.py:50 — ParseError raise site (canonical import path)
    - tests/harness/test_auth.py — existing Resolution test cases (location for the new role test)
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/test_judge_verdict.py" (lines 863-921) — FakeJudgeProvider shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/harness/test_auth.py (MODIFY)" (lines 294-319) — two role tests
    - .planning/phases/M5-eval-and-distribution-prep/M5-VALIDATION.md rows `verdict-model`, `judge-skipped-on-crash`, `auth-resolve-role`
  </read_first>
  <behavior>
    - `pytest tests/eval/test_judge_verdict.py -q` passes 2 tests: happy-path returns the Verdict; ParseError path returns (None, "skipped").
    - `pytest tests/eval/test_judge_skipped.py -q` passes 1 test: when the underlying provider's .complete raises a non-ParseError exception (e.g. RuntimeError simulating an agent crash) AND the test invokes judge_run directly, the runner-side "crashed" semantics are NOT exercised here — instead the test asserts that judge_run does NOT swallow non-ParseError exceptions (they propagate; the runner is responsible for the crashed branch, per RESEARCH §Common Pitfalls). Note: VALIDATION's `judge-skipped-on-crash` is satisfied at the runner layer (Plan 03); this test pins the judge-layer contract that ONLY ParseError → skipped.
    - `pytest tests/harness/test_auth.py -q -k role` passes 2 tests: resolve(role="judge") same Resolution as resolve(); resolve(preference="none", role="judge") returns Resolution(source="none").
  </behavior>
  <action>
    Create `tests/eval/test_judge_verdict.py` per M5-PATTERNS.md lines 867-920:
    - Define a `FakeJudgeProvider` class with `__init__(self, verdict: Verdict | None)`, an `async complete(self, *, messages, model, response_format=None, **kw)` that returns a `ProviderResponse(text=self.verdict.model_dump_json() if self.verdict else "{}", model=model, prompt_tokens=1, completion_tokens=1, cost_usd=0.0, raw={}, parsed=self.verdict)`, and a stub `count_tokens(self, *, text, model) -> int: return 1`.
    - `test_judge_returns_verdict`: instantiate FakeJudgeProvider with Verdict(verdict="pass", confidence=0.9, rationale="ok"), call `asyncio.run(judge_run(provider=fp, model="m", task_prompt="t", final="f", file_diff="", rubric="r"))`, assert returned verdict_str == "pass" and verdict.confidence == 0.9.
    - `test_judge_parse_error_returns_skipped`: define an inline `RaisingProvider` whose `complete` raises `ParseError("bad json")`; call judge_run; assert returned tuple is `(None, "skipped")`.
    - Import `Verdict`, `judge_run` from `voss.eval.judge`; `ProviderResponse` from `voss_runtime.providers.base`; `ParseError` from `voss_runtime.providers.litellm_provider`.

    Create `tests/eval/test_judge_skipped.py`:
    - This file pins the contract that judge_run only catches ParseError — non-ParseError exceptions from the provider propagate. (VALIDATION's `judge-skipped-on-crash` row is finally satisfied at the runner layer in Plan 03 / Wave 2; this test pins the judge-layer half.)
    - `test_runtime_error_propagates`: define an inline `CrashingProvider` whose `complete` raises `RuntimeError("simulated provider crash")`; call `asyncio.run(judge_run(provider=cp, model="m", task_prompt="t", final="f", file_diff="", rubric="r"))` inside `pytest.raises(RuntimeError)` to confirm the exception escapes the judge_run try/except (which catches ParseError only).
    - Add a module docstring explicitly noting: "Runner-layer crash semantics (`judge_verdict='skipped'`, `success=False`) live in `voss/eval/runner.py` (Plan 03)."

    Modify `tests/harness/test_auth.py` — append (do not edit existing tests) per M5-PATTERNS.md lines 300-315:
    - `test_resolve_accepts_role_kwarg(monkeypatch)`: set ANTHROPIC_API_KEY via monkeypatch.setenv to a test value; import resolve; call once with default args and once with role="judge"; assert .source and .detail are identical.
    - `test_resolve_role_with_none_preference()`: call `resolve(preference="none", role="judge")` and assert `.source == "none"`.
    Use `from voss.harness.auth import resolve` inside each test function (matches existing pattern in test_auth.py).
    Keyword `role` in both function names so `pytest -k role` picks them up (VALIDATION pin).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest -q -m "not slow and not live" tests/eval/test_judge_verdict.py tests/eval/test_judge_skipped.py tests/harness/test_auth.py -k "judge or role"</automated>
  </verify>
  <done>
    All three test files green. Tests assert: Verdict happy path; ParseError → ("skipped"); non-ParseError exception propagates; resolve(role="judge") is pass-through; resolve(preference="none", role="judge") returns source="none".
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent output → Judge prompt | The agent's `final` and the file diff are placed into the judge user-message; both may contain attacker-influenced content if the agent is compromised |
| Judge response text → Verdict pydantic | Untrusted JSON crosses into the type system; `response_format=Verdict` enforces shape |
| auth.resolve(role=...) → callers | Role kwarg is currently ignored; future versions may introduce real branching |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M5-02-judge-prompt-injection | T (Tampering) | judge_run user-message construction | mitigate | Rubric is authored in the fixture (trusted), NOT by the agent. The agent's final and file_diff are clearly labeled ("## Agent final", "## File diff") in the user-message; the judge's system prompt instructs it to return only Verdict JSON. response_format=Verdict + pydantic strict typing (`Literal["pass","fail"]`, float bounds) makes prompt-injection-driven verdicts structurally bounded — an attacker cannot inject a non-pass/non-fail verdict label. |
| T-M5-02-verdict-parse | I (Info Disclosure) / T (Tampering) | response_format=Verdict | mitigate | LiteLLMProvider raises ParseError on invalid JSON; judge_run catches and returns ("skipped"). No partial data flows into JSONL. |
| T-M5-02-auth-role-future-drift | T (Tampering) | auth.resolve | accept | role is ignored in v0.1 by design; documented in docstring. Regression test pins the pass-through; if a future change differs the resolution per role, the failing test forces an explicit decision. |
| T-M5-02-judge-raises-non-parse | T (Tampering) | judge_run | mitigate | judge_run only swallows ParseError; all other exceptions (network, auth, provider internal) propagate so the runner can mark the run crashed (judge_verdict="skipped", success=False). Pinned by `test_runtime_error_propagates`. |
</threat_model>

<verification>
- `pytest -q -m "not slow and not live" tests/eval/test_judge_verdict.py tests/eval/test_judge_skipped.py` passes.
- `pytest -q tests/harness/test_auth.py -k role` passes.
- `python -c "from voss.eval.judge import Verdict, judge_run, JUDGE_SYSTEM; from voss.harness.auth import resolve; resolve(role='judge')"` exits 0.
- No new top-level dependencies added (only stdlib + pydantic + voss_runtime).
</verification>

<success_criteria>
1. `voss/eval/judge.py` defines `Verdict`, `JUDGE_SYSTEM`, and `judge_run`.
2. Verdict pydantic model has the exact field set: `verdict: Literal["pass","fail"]`, `confidence: float ∈ [0,1]`, `rationale: str`.
3. judge_run catches ParseError only — all other exceptions propagate.
4. `auth.resolve(preference, role=None)` accepts the new kwarg without changing behavior for existing callers.
5. All five tests across the three files pass on a clean checkout.
</success_criteria>

<output>
After completion, create `.planning/phases/M5-eval-and-distribution-prep/M5-02-SUMMARY.md` summarizing: judge_run signature (kwarg-only), the ParseError-only catch contract, the auth.resolve role pass-through, and which threats are mitigated vs accepted.
</output>
