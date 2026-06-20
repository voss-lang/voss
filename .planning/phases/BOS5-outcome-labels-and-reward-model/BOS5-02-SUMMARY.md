---
phase: BOS5-outcome-labels-and-reward-model
plan: 02
status: done
artifacts:
  - .planning/schemas/examples/outcome*.json (9 records)
  - tests/planning/__init__.py
  - tests/planning/test_bos_outcome_schema.py
  - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-VALIDATION.md (frontmatter flip)
requirements: [BOS-DATA-03, BOS-DATA-04]
---

# BOS5-02 Summary

## What shipped

The Wave-2 contract-validation harness for the BOS5 outcome/reward schema, run against the REAL BOS5-01 artifacts (no xfail/skip scaffolding, no fictional API):

1. **`.planning/schemas/examples/outcome*.json`** — 9 example records, each validating against `contracts/outcomes.schema.json`.
2. **`tests/planning/__init__.py`** — empty package marker.
3. **`tests/planning/test_bos_outcome_schema.py`** — 13-check pytest suite (normative test names from BOS5-VALIDATION.md).
4. **`BOS5-VALIDATION.md`** — frontmatter flipped `nyquist_compliant: false -> true`, `wave_0_complete: false -> true`.

## Task 1 — bundled example records (ACC-04)

9 example records at `.planning/schemas/examples/`, all internally consistent and validating against the schema:

| File | record type | notable fields |
|---|---|---|
| `outcome-clean-merge.json` | `clean_merge` label | `obs_window_id="clean-merge-30d"`, `source_rule="rule:pr_merge_clean"`, no severity |
| `outcome-rework.json` | `rework` label | `severity="medium"`, `obs_window_id="rework-14d"` |
| `outcome-revert.json` | `revert` label | `obs_window_id="revert-0d"`, no severity |
| `outcome-failed-validation.json` | `failed_validation` label | `obs_window_id="failed-validation-0d"`, no severity |
| `outcome-escaped-defect.json` | `escaped_defect` label | `severity="medium"`, **`supersedes_outcome_id="outcome-cleanmerge-001"`** (the supersede scenario), `ingest_time` strictly later than clean_merge's |
| `outcome-incident.json` | `incident` label | `severity="high"`, `obs_window_id="incident-90d"` |
| `outcome-human-override.json` | `human_override` label | `obs_window_id="human-override-0d"`, no severity |
| `outcome-cycle-time.json` | `cycle_time` measure | `value=259200` (3 days in seconds), `unit="seconds"`, `measure_definition_id="cycle-time:task.created_at->pr.merged_at"` (Pitfall 1 pinned definition) |
| `outcome-reward.json` | `RewardRecord` | `decision_id` present (only record with it), `objective_vector={throughput:0.9, quality:1.0, rework_cost:0.0, flow:0.85}`, `weight_set_version="ws-v1-task-to-agent"`, `horizon="short"`, `scalarized_reward=0.91` |

Supersede scenario (ACC-04): `outcome-escaped-defect.json.supersedes_outcome_id` == `outcome-clean-merge.json.outcome_id` ("outcome-cleanmerge-001"); `ingest_time` 2026-07-15T00:10:00Z strictly > clean_merge's 2026-06-21T00:00:00Z — late-arriving / no-leakage proof.

No-leakage verified: every label/measure record carries NO `decision_id` and NO `recommended_action` key; only the reward example carries `decision_id`.

## Task 2 — 13-check contract suite

`tests/planning/test_bos_outcome_schema.py` implements the 13 NORMATIVE test functions named in BOS5-VALIDATION.md. Uses `jsonschema.Draft202012Validator` (4.26.0 in `.venv`), loads schema via `pathlib`, parametrizes over example records.

| Test | Checks | ACC |
|---|---|---|
| `test_schema_is_valid` | `Draft202012Validator.check_schema(schema)`; doubles as ACC-06 stability/lint gate for the hand-authored sibling schema (cannot join the pydantic regeneration gate in `tests/harness/server/test_contract_drift.py` because outcomes.schema.json has no pydantic source — docs-first, no runtime code) | ACC-01, ACC-06 |
| `test_categorical_label_coverage` | all 7 `label_type` consts present in `$defs` | ACC-02 |
| `test_measure_coverage` | `cycle_time` `measure_type` const present in `CycleTimeMeasure` | ACC-02 |
| `test_label_examples_validate` | every `outcome*.json` validates against the schema | ACC-04 |
| `test_bitemporal_invariant` | every label/measure carries `event_time` + `ingest_time` with `ingest_time >= event_time` | — |
| `test_no_decision_leakage_in_label` | `OutcomeEnvelope` defines NO `decision_id`/`recommended_action`; label/measure examples carry no `decision_id`/`recommended_action` (T-BOS5-02-01 / D-04) | — |
| `test_reward_record_shape` | `RewardRecord` requires `decision_id`, `objective_vector`, `weight_set_version`, `horizon`, `computed_at`; `additionalProperties: false` | BOS-DATA-04 |
| `test_decision_schema_no_outcome_field` | **CONDITIONAL** — checks `contracts/decisions.schema.json` OR `contracts/decision-ledger.schema.json` (BOS4's actual artifact name, which the plan assumed differently); when found, asserts no `outcome`/`label`/`reward` property key; else `pytest.skip`. **Currently runs against the real BOS4 artifact and passes** — verifies BOS4's no-leakage guard structurally. Never a false-red (T-BOS5-02-04 / gsd-scaffold-fictional-api guard). | — |
| `test_tension_pair_coverage` | `GuardrailMetricSpec` requires `linked_reward_objective`; every objective in the reward example's `objective_vector` appears in the rationale spec's tension-pair table | ACC-05 |
| `test_guardrail_role_enum` | `GuardrailMetricSpec.role` enum is exactly `{hard_gate, dashboard}` | — |
| `test_scalarization_named` | `WeightSetRecord.scalarization` enum includes `linear_weighted` | — |
| `test_round_trip_scenario` | cycle_time + clean_merge + escaped_defect(supersede) + reward all validate; supersede pointer links clean_merge -> escaped_defect; late label `ingest_time` > decision-time; reward carries `decision_id`; cycle_time pins `measure_definition_id` (RESEARCH Example 2) | ACC-04 |
| `test_versioning_present` | every Label/Measure `$def` carries `v: const 1`; every example record has `v: 1`; rationale doc contains a migration-notes section | — |

### Suite result

```
.venv/bin/python -m pytest tests/planning/test_bos_outcome_schema.py -v
============================= 13 passed in 0.12s =============================
```

13/13 pass, 0 failures, 0 skipped. The conditional BOS4 check ran (BOS4's `decision-ledger.schema.json` exists from BOS4-01) and verified the decision schema has no `outcome`/`label`/`reward` property key — the no-leakage guarantee is now machine-checked end-to-end (BOS4 -> BOS5).

### Plan deviation (noted, not a regression)

The plan's `<interfaces>` assumed the BOS4 artifact is named `contracts/decisions.schema.json`. BOS4 actually shipped `contracts/decision-ledger.schema.json` (see BOS4-01-SUMMARY.md). `test_decision_schema_no_outcome_field` checks for both names and runs against whichever exists — the conditional guard activates rather than skipping, which is stronger than the plan required. This matches the plan's intent (never a false-red, never a false-green; activates when the file exists) and is recorded here so a future reader knows why the test does not skip.

## Verification (all green)

- `.venv/bin/python -m pytest tests/planning/test_bos_outcome_schema.py -x -q` — 13 passed, 0 failures, 0 skipped.
- `.venv/bin/python -c "import json,glob,jsonschema; s=json.load(open('contracts/outcomes.schema.json')); v=jsonschema.Draft202012Validator(s); [v.validate(json.load(open(f))) for f in glob.glob('.planning/schemas/examples/outcome*.json')]"` — every example round-trips.
- `nyquist_compliant: true` present in `BOS5-VALIDATION.md` frontmatter.
- `git diff --quiet contracts/ docs/BOS5-OUTCOME-REWARD-SPEC.md` — clean (BOS5-01 artifacts untouched).
- `git diff --quiet voss/` — clean (no harness source touched).
- `git diff --quiet .planning/schemas/examples/` — clean (Task 2 reads, does not modify, the examples).
- `tests/harness/server/test_contract_drift.py`, `export_contract.py`, `contracts/events.schema.json`, `contracts/openapi.json`, `contracts/decision-ledger.schema.json` — all untouched.

## Threat model (per plan)

- **T-BOS5-02-01 (no-leakage regression):** mitigated by `test_no_decision_leakage_in_label` over both schema `$defs` and example records.
- **T-BOS5-02-02 (Goodhart coverage regression):** mitigated by `test_tension_pair_coverage` (ACC-05) + `test_guardrail_role_enum`.
- **T-BOS5-02-03 (silent drift of hand-authored schema):** mitigated by `test_schema_is_valid` linting the schema on every run (ACC-06).
- **T-BOS5-02-04 (false-green from missing upstream):** mitigated by the CONDITIONAL `test_decision_schema_no_outcome_field` — currently activates against the real BOS4 artifact (stronger than skip), would skip cleanly if BOS4 were absent.
- **T-BOS5-02-SC (package installs):** accept — no installs; `jsonschema` 4.26.0 + pytest 8.4.2 already in `.venv`.

## Downstream impact

- **BOS5 contract is now machine-verifiable** — downstream phases inherit a proven, regression-guarded outcome/reward substrate.
- **BOS6 (BOS-GOV-04)** can rely on the tension-pair coverage check as the dashboard source of truth.
- **BOS13/BOS14** policies produce decisions whose rewards validate against `RewardRecord`.
- **BOS15 (BOS-RL-02)** offline eval / promotion gates wire `hard_gate` guardrails against `GuardrailMetricSpec`; the round-trip scenario test is the canonical acceptance shape.
- **BOS11/12 era** label writers validate emitted records against this schema; the example records serve as fixtures.
- The conditional `test_decision_schema_no_outcome_field` will keep verifying BOS4's no-leakage guard on every run going forward — a structural cross-phase guarantee.