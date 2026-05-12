---
phase: M5
plan: 02
status: complete
date: 2026-05-12
requirements-completed:
  - EVAL-02
---

# M5-02 Summary - judge surface and auth role pass-through

M5-02 added the LLM-as-judge boundary for eval runs and extended auth resolution with the future-proof `role` keyword while keeping v0.1 behavior unchanged.

## What Changed

- Added `voss/eval/judge.py` with `Verdict`, `JUDGE_SYSTEM`, and `judge_run`.
- Updated `voss/harness/auth.py:resolve(preference="auto", role=None)` so future eval code can request `role="judge"`.
- Added judge tests for successful Verdict parsing, `ParseError` skipped fallback, and non-ParseError propagation.
- Added auth tests proving `resolve(role="judge")` is currently pass-through.

## judge_run Contract

Signature:

```python
async def judge_run(
    *,
    provider: ModelProvider,
    model: str,
    task_prompt: str,
    final: str,
    file_diff: str,
    rubric: str,
) -> tuple[Verdict | None, str]
```

The function builds a labeled prompt with task prompt, agent final, file diff, and rubric. It calls `provider.complete(..., response_format=Verdict, temperature=0.0)`.

Return behavior:

- Parsed Verdict: returns `(verdict, verdict.verdict)`.
- `ParseError`: returns `(None, "skipped")`.
- `resp.parsed is None`: returns `(None, "skipped")`.
- Any other provider exception: propagates. The Wave 2 runner owns crashed-run semantics.

## Verdict Model

`Verdict` is a pydantic model with lenient extras:

- `verdict: Literal["pass", "fail"]`
- `confidence: float = Field(ge=0.0, le=1.0)`
- `rationale: str`

The `extra="ignore"` config keeps judge output structurally bounded while allowing harmless extra fields.

## Auth Role

`resolve(preference="auto", role=None)` accepts `role` for the future judge-provider resolver shape. In v0.1 the value is ignored; `resolve(role="judge")` returns the same `Resolution` as `resolve()`.

## Threat Notes

- Prompt injection is mitigated structurally by labeled sections, trusted rubrics, `response_format=Verdict`, and pydantic `Literal`/bounds validation.
- Invalid judge JSON is mitigated by the `ParseError -> skipped` path.
- Auth role drift is accepted for v0.1 and pinned by pass-through tests.
- Non-parse provider failures intentionally propagate so the runner can record a crashed run rather than hiding infrastructure errors.

## Verification

```bash
python3 -c "from voss.eval.judge import Verdict, judge_run, JUDGE_SYSTEM; v = Verdict(verdict='pass', confidence=0.9, rationale='ok'); print(v.verdict, v.confidence); from voss.harness.auth import resolve; r1 = resolve(); r2 = resolve(role='judge'); assert r1.source == r2.source; print('OK')"
```

Result:

```text
pass 0.9
OK
```

```bash
pytest -q -m "not slow and not live" tests/eval/test_judge_verdict.py tests/eval/test_judge_skipped.py tests/harness/test_auth.py -k "judge or role"
```

Result: `5 passed`.

```bash
pytest -q tests/harness/test_auth.py -k role
```

Result: `2 passed`.

```bash
pytest -q -m "not slow and not live" tests/eval/
```

Result: `11 passed`.
