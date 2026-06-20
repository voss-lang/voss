# BOSR-06 Plan: End-to-End Validation and Cleanup

**Status:** Ready for execution
**Wave:** 5
**Type:** validation
**Requirements:** BOSR-01..06

## Objective

Prove the BOSR runtime substrate works end-to-end and close out stale planning
state so future work resumes from the consolidated phase.

## Scope

Implement or update:
- end-to-end BOSR fixture that projects events, appends ledger rows, writes a
  decision, writes an outcome, creates a shadow recommendation, and renders the
  read model
- phase validation doc
- summaries for executed BOSR plans
- roadmap checkboxes
- stale-placeholder note for BOS10-BOS18 and BOSI2-BOSI6

Do not:
- delete historical BOS artifacts without explicit human approval
- create backend/web implementation
- introduce online learning

## Read First

- `.planning/phases/BOSR-behavioral-os-runtime-foundation/BOSR-CONTEXT.md`
- `.planning/phases/BOSR-behavioral-os-runtime-foundation/BOSR-RESEARCH.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`

## Acceptance Criteria

1. Focused BOSR test suite passes.
2. Existing projection, session-redaction, swarm-store, and outcome-schema tests
   still pass.
3. ROADMAP/REQUIREMENTS/STATE agree that BOSR is the active phase.
4. Old BOS/BOSI artifacts are preserved but no longer active execution rows.
5. Summary documents record deviations and follow-up boundaries.

## Verification

```bash
pytest tests/harness/test_bos_event_projection.py \
  tests/harness/test_bos_event_ledger.py \
  tests/harness/test_bos_decision_outcome_writers.py \
  tests/harness/test_bos_shadow_recommendations.py \
  tests/harness/test_bos_read_model.py \
  tests/harness/test_session_redaction.py \
  tests/harness/test_swarm_store.py \
  tests/planning/test_bos_outcome_schema.py -q
rg -n "BOSR|BOS0-BOS18|BOSI" .planning/PROJECT.md \
  .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/STATE.md
```
