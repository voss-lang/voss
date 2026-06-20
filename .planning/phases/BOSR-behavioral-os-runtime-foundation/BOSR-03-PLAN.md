# BOSR-03 Plan: Decision and Outcome Capture

**Status:** Ready for execution
**Wave:** 2
**Type:** code
**Requirements:** BOSR-03, BOSR-04

## Objective

Add runtime writers for BOS decision and outcome records while keeping decisions
and outcomes structurally separate.

## Scope

Implement:
- local decision writer under `.voss/bos/decisions.jsonl`
- local outcome writer under `.voss/bos/outcomes.jsonl`
- schema-validation tests against `contracts/decision-ledger.schema.json`
- schema-validation tests against `contracts/outcomes.schema.json`
- no-leakage tests: decision records cannot contain outcome/reward fields

Do not implement:
- policy recommendation generation
- UI review queue
- external Git/PM/CI ingestion

## Read First

- `contracts/decision-ledger.schema.json`
- `contracts/outcomes.schema.json`
- `tests/planning/test_bos_outcome_schema.py`
- `.planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md`
- `.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-RESEARCH.md`

## Acceptance Criteria

1. Decision records validate against the decision ledger schema.
2. Outcome records validate against the outcome schema.
3. Outcomes append as separate later records, never as decision mutations.
4. No decision record contains `outcome`, `label`, `reward`, or
   `recommended_outcome` fields.
5. Tests cover approve, override, dismiss, no-action, clean merge, rework, and
   failed validation examples.

## Verification

```bash
pytest tests/harness/test_bos_decision_outcome_writers.py \
  tests/planning/test_bos_outcome_schema.py -q
python3 -m py_compile voss/harness/bos_decisions.py
```
