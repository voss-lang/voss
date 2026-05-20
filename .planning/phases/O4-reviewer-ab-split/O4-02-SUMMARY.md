---
phase: O4-reviewer-ab-split
plan: 02
status: complete
completed_at: 2026-05-20
commits:
  - 5efc5f9 — feat: implement command palette fuzzy matching and keyboard chord normalization utilities (includes ReviewerB + test_reviewer_b GREEN)
depends_on: [O4-01]
requirements: [ORVW-04, ORVW-05, ORVW-06, ORVW-07, ORVW-09]
---

# O4-02 Summary — ReviewerB (independent tiered judgment)

## Objective

Implement Reviewer-B: the cage's independent confidence source. B sees ONLY original idea, acceptance criteria, artifact, repo context, and A's verification summary. Produces ReviewerVerdict via a single `provider.complete()` call with strict message-list isolation.

## Files changed

- `voss/harness/board/reviewer_b.py` — **new** (175 lines): `ReviewerB` class, `_ReviewerBOutput` pydantic mirror, `REVIEWER_B_SYSTEM` prompt constant.
- `tests/harness/board/test_reviewer_b.py` — **rewritten**: 5 xfail scaffolds replaced with 5 GREEN tests.

## Unchanged

- `voss/harness/board/verdict.py` — zero diff (O3 frozen contract).

## Key decisions

| Decision | Rationale |
|----------|-----------|
| `_ReviewerBOutput(BaseModel)` pydantic mirror | ReviewerVerdict is a frozen dataclass; `provider.complete()` requires pydantic as `response_format`. Mirror fields: `conf`, `verdict`, `notes`, `evidence_refs`. |
| `source="B"` and `tier` hardcoded in `_to_verdict` | LLM output does not control these fields. Prevents spoofing (T-O4-04). |
| `ParseError` / `parsed is None` returns `verdict="block"` | Fail-safe: a parse failure at the gate is safer than a silent skip. Contrast with `judge.py` which returns `None`. |
| Sync `review()` bridging async via thread-pool | Reviewer Protocol is sync (Gate 2). `_call_provider_sync` detects running loop and uses `concurrent.futures.ThreadPoolExecutor` + `asyncio.run` in a worker thread. |
| Duck-typed `card: object` with `getattr` access | Card missing O4 fields (Gate 3). B reads `original_idea`, `acceptance_criteria`, `artifact_text`, `file_diff`, `a_verification_summary` via `getattr` with fallbacks. |

## Information isolation (ORVW-04)

Structural guarantee: `messages[]` contains exactly 2 entries (system + user). The user message is built from 5 card attributes only. No method on ReviewerB accepts EM context, history, or memory. B does not import from `voss.harness.agent`, `voss.harness.subagents`, or `voss_runtime.memory`.

## Test summary

| Test | ORVW | Assertion |
|------|------|-----------|
| `test_b_message_isolation` | 04 | messages list length == 2; system == REVIEWER_B_SYSTEM; user contains card data; no EM-narrative strings |
| `test_b_tier_selection` | 05 | `provider.calls[0]["model"] == "test-fast"` |
| `test_b_tier_strong` | 06 | `provider.calls[0]["model"] == "test-strong"` |
| `test_b_residual_2_block` | 07 | `verdict.verdict == "block"`, `verdict.source == "B"` |
| `test_b_implements_protocol` | 09 | `isinstance(b, Reviewer)` passes (runtime_checkable Protocol) |

## Deviations from plan

- **Commit message not O4-prefixed.** ReviewerB was committed alongside unrelated voss-app changes in `5efc5f9`. The implementation matches the plan fully.

## Verification

```
pytest tests/harness/board/test_reviewer_b.py -q  # 5 passed
```

## Next

O4-04 (integration) wires B into the Board as the gate reviewer.
