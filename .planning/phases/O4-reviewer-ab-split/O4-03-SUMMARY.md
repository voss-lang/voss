---
phase: O4-reviewer-ab-split
plan: 03
status: complete
completed_at: 2026-05-20
commits:
  - ed4ce72 — feat(O4-03): ReviewerA — verification-authoring reviewer via run_turn + judge_run
depends_on: [O4-01]
requirements: [ORVW-01, ORVW-02, ORVW-03, ORVW-08, ORVW-09]
---

# O4-03 Summary — ReviewerA (verification-authoring reviewer)

## Objective

Implement Reviewer-A: the cage's bar-author. A derives what "done" means from the original human idea (not EM AC/DoD), authors deterministic verification (tests for code cards, rubric for AI cards), and translates results to ReviewerVerdict.

## Files changed

- `voss/harness/board/reviewer_a.py` — **new** (218 lines): `ReviewerA` class, `REVIEWER_A_ROLE_PROMPT`, `_reviewer_a_task`, `_verdict_from_test_exit`, `_verdict_from_judge`, `_extract_exit_code`.
- `tests/harness/board/test_reviewer_a.py` — **rewritten**: 5 xfail scaffolds replaced with 6 GREEN tests (5 original + 1 added).

## Unchanged

- `voss/harness/board/verdict.py` — zero diff (O3 frozen contract).

## Key decisions

| Decision | Rationale |
|----------|-----------|
| `run_turn_fn` + `judge_run_fn` dependency injection | Tests mock run_turn and judge_run as callables rather than scripting full provider interactions. Tests verify the ReviewerA contract, not run_turn internals. |
| `EpisodicMemory(capacity=20)` inside `review()`, not `__init__` | ORVW-08: fresh memory per card. Prevents cross-card bleed. |
| Fresh `uuid.uuid4()` session_id per `review()` call | No shared session state between reviews. |
| `gate_for_role(spec, base_gate)` validated at construction | Fails fast if SubagentSpec is incompatible with the O2 gate system. Stored as `self._gate` for reuse. |
| `SubagentSpec(tools=frozenset({"fs", "shell"}))` | A needs `fs_write` for test authoring + `shell_run` for execution. |
| Sync `review()` bridging async via thread-pool | Same pattern as ReviewerB: detect running loop, use ThreadPoolExecutor. |
| Duck-typed `card: object` with `getattr` access | Matches Gate 3 finding: Card lacks O4-required fields. |

## Dual-path verdict production

**Code cards** (`domain == "code"`): A runs via `run_turn` with tools, parses `[exit N]` suffix from shell_run output using `_EXIT_CODE_RE`. Exit 0 = pass (conf=1.0), non-zero = fail (conf=0.0). `_verdict_from_test_exit` produces the ReviewerVerdict.

**AI cards** (`domain == "ai"`): A runs via `run_turn` to author a rubric (returned as `result.final`). Rubric is passed to `judge_run` which scores it. `_verdict_from_judge` translates `Verdict(confidence, verdict, rationale)` to `ReviewerVerdict(conf, source="A", tier="strong")`.

## Test summary

| Test | ORVW | Assertion |
|------|------|-----------|
| `test_a_uses_original_idea` | 01 | Task prompt contains "Build a REST API"; excludes "em_plan", "engineering manager", "DoD" |
| `test_a_authors_test_file_pass` | 02 | Exit 0 produces `verdict="pass"`, `conf=1.0`, `source="A"` |
| `test_a_authors_test_file_fail` | 02 | Exit 1 produces `verdict="fail"`, `conf=0.0`, `source="A"` |
| `test_a_ai_card_eval` | 03 | judge_run Verdict(confidence=0.85) translates to ReviewerVerdict(conf=0.85, tier="strong") |
| `test_a_memory_fresh_per_card` | 08 | Two sequential reviews get different EpisodicMemory instances; both start with 0 turns |
| `test_a_implements_protocol` | 09 | `isinstance(a, Reviewer)` passes (runtime_checkable Protocol) |

## Deviations from plan

- **6 tests instead of 5.** `test_a_authors_test_file` was split into `test_a_authors_test_file_pass` and `test_a_authors_test_file_fail` to separately cover the exit 0 (pass) and exit 1 (fail) paths. Both exercise ORVW-02.
- **Exception handling.** `_review_async` catches all exceptions from `run_turn` and returns a fail verdict (`notes="run_turn failed: {exc}"`). Plan specified BudgetExceededError only; implementation generalizes to any exception for robustness.

## Verification

```
pytest tests/harness/board/test_reviewer_a.py -q  # 6 passed
```

## Next

O4-04 (integration) wires A as the verification author called outside the Board, B as the gate reviewer.
