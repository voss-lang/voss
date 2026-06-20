# BOSR-04 Plan: Shadow Recommendation Baseline

**Status:** Ready for execution
**Wave:** 3
**Type:** code
**Requirements:** BOSR-05

## Objective

Generate shadow-mode recommendations from local BOS events and decisions
without increasing autonomy or changing runtime behavior.

## Scope

Implement:
- heuristic recommendation builder for delegation, review depth, validation
  depth, and escalation
- `policy_version` and rationale fields
- recommendation records that reference BOS decisions but do not duplicate
  decision payloads
- approve, override, dismiss, and do-nothing verdict capture
- tests proving shadow-mode recommendations do not execute actions

Do not implement:
- contextual bandits
- RL
- autonomy-band increases
- web UI

## Read First

- `.planning/phases/BOS9-recommendation-review-surface/BOS9-CONTEXT.md`
- `.planning/phases/BOS9-recommendation-review-surface/BOS9-01-PLAN.md`
- `contracts/decision-ledger.schema.json`
- `voss/harness/bos_events.py`

## Acceptance Criteria

1. Recommendations are derived from point-in-time event/decision data.
2. Each recommendation carries rationale and policy version.
3. Human verdicts write decision-ledger-compatible training signals.
4. Shadow mode means recommendations do not alter task assignment, review
   depth, validation depth, or escalation behavior by themselves.
5. Tests cover approve, override, dismiss, and do-nothing.

## Verification

```bash
pytest tests/harness/test_bos_shadow_recommendations.py \
  tests/harness/test_bos_decision_outcome_writers.py -q
python3 -m py_compile voss/harness/bos_recommendations.py
```
