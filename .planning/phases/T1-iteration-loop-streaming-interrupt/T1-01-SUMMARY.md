---
phase: T1-iteration-loop-streaming-interrupt
plan: 01
status: complete
completed_at: 2026-05-15
commits:
  - 5b58fb8 — feat(session): enhance RunRecord with iteration tracking and exit reasons (Task 1)
  - 2fb4f40 — feat(T1-01): RunRecorder.begin_iteration/end_iteration + finalize wiring (Task 2)
---

# T1-01 Summary — Additive iteration-record schema substrate

## Files changed

- `voss/harness/session.py` — added `IterationRecord` dataclass, `EXIT_REASONS` frozenset, five additive `RunRecord` fields, `__post_init__` validation.
- `voss/harness/recorder.py` — added `_iterations` field, `begin_iteration()`, `end_iteration()`, extended `finalize(*, exit_reason=None)`.
- `tests/harness/test_session_iterations.py` — 9 tests covering construction defaults, asdict round-trip, all four exit reasons, invalid-reason rejection, pre-T1 fixture round-trip.
- `tests/harness/test_recorder_iterations.py` — 10 tests covering begin/end iteration + finalize forwarding + invalid exit_reason rejection at both layers.
- `tests/harness/test_session_redaction.py` — updated expected RunRecord key set (+5 keys) and field count (16 → 21).

## IterationRecord fields

```
IterationRecord(
    index: int,                       # required, 0-based
    plan: dict = {},
    tool_results: list[dict] = [],
    cost_usd: float = 0.0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    started_at: str = "",
    ended_at: str = "",
    exit_reason: Optional[str] = None,
)
```

## RunRecord new fields (all additive, all default-safe)

- `iterations: list[IterationRecord] = []`
- `iteration_count: int = 0`
- `exit_reason: Optional[str] = None`  (validated by `__post_init__`)
- `iteration_total_prompt_tokens: int = 0`
- `iteration_total_completion_tokens: int = 0`

## EXIT_REASONS frozenset

```python
EXIT_REASONS: frozenset[str] = frozenset({"done", "max-iter", "budget", "interrupt"})
```

Enforced at the `RunRecord.__post_init__` level (single source of truth);
`RunRecorder.end_iteration` and `RunRecorder.finalize` both raise `ValueError`
on out-of-vocabulary `exit_reason` before construction reaches `RunRecord`.

## Deviations from plan

- **Test redaction update was required, not optional.** Plan listed the redaction test under "regression assertion: existing test still passes" but the existing test asserted `len(dataclasses.fields(RunRecord)) == 16` and an exact 16-key set — adding 5 fields would have broken it. Updated the expected set (+5 additive keys) and field count (16 → 21). All new keys are inert (no credential shape).
- **Task 1 was auto-committed by a hook** between tool calls as commit `5b58fb8` before Task 2 finished; Task 2 was committed manually as `2fb4f40`. No content deviations vs. the plan.

## Verification

```
uv run pytest tests/harness/test_session_iterations.py \
              tests/harness/test_recorder_iterations.py \
              tests/harness/test_session_redaction.py \
              tests/harness/test_recorder.py \
              tests/harness/test_session.py -x -q
```

44 tests pass, 1 skipped (pre-existing wave-2 skip in `test_recorder.py`).

`grep -rn _substitute_placeholders voss/` count unchanged at 6 — T1-04 territory, not touched here.
