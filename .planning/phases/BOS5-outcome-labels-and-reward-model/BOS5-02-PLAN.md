---
phase: BOS5
plan: 02
type: execute
wave: 2
depends_on: ["BOS5-01"]
files_modified:
  - .planning/schemas/examples/
  - tests/planning/__init__.py
  - tests/planning/test_bos_outcome_schema.py
autonomous: true
requirements: [BOS-DATA-03, BOS-DATA-04]

must_haves:
  truths:
    - "The outcomes JSON Schema is proven valid against the Draft 2020-12 meta-schema by an automated test"
    - "At least one example record per categorical label + the cycle_time measure + a RewardRecord + a supersede scenario (clean_merge -> escaped_defect) round-trips against the schema"
    - "The bitemporal invariant (event_time + ingest_time present, ingest_time >= event_time) and the no-leakage guard (no decision_id on label records) are enforced by tests over the schema + examples"
    - "Tension-pair coverage is proven: every named reward objective has >=1 GuardrailMetricSpec linking to it; guardrail role enum is exactly {hard_gate, dashboard}; scalarization names linear_weighted"
    - "contracts/outcomes.schema.json is added to the CI drift/contract gate so it cannot silently change unnoticed"
  artifacts:
    - path: "tests/planning/test_bos_outcome_schema.py"
      provides: "13-check contract suite (ACC-01..ACC-07): schema-valid, label+measure coverage, example round-trip, bitemporal, no-leakage, reward-record shape, decision-no-outcome (conditional), tension-pair coverage, role enum, named scalarization, round-trip scenario, versioning, drift guard"
      contains: "Draft202012Validator"
      min_lines: 110
    - path: ".planning/schemas/examples"
      provides: "Bundled example outcome records: >=1 per categorical label + cycle_time measure + RewardRecord + a clean_merge->escaped_defect supersede pair"
      min_lines: 0
  key_links:
    - from: "tests/planning/test_bos_outcome_schema.py"
      to: "contracts/outcomes.schema.json"
      via: "loads + validates the schema and example records against it"
      pattern: "outcomes.schema.json"
    - from: "tests/planning/test_bos_outcome_schema.py"
      to: ".planning/schemas/examples/outcome*.json"
      via: "globs + round-trips every example outcome record"
      pattern: "outcome.*\\.json"
---

<objective>
Build the contract-validation harness for the BOS5 outcome/reward schema: bundled
example records (>=1 per categorical label + the cycle_time measure + a RewardRecord
+ a clean_merge -> escaped_defect supersede scenario) and the 13-check pytest suite
that proves the schema is valid, the examples round-trip, the bitemporal + no-leakage
invariants hold, tension-pair coverage is complete, the guardrail role enum + named
scalarization are correct, and versioning is documented. Add `contracts/outcomes.schema.json`
to the contract/drift gate (ACC-06).

Purpose: BOS-DATA-03 / BOS-DATA-04 — make the BOS5-01 contract machine-verifiable so
downstream phases (BOS13/14 policies, BOS15 eval, BOS6 dashboards) inherit a proven,
regression-guarded outcome/reward substrate. This is the Wave-0 validation listed in
BOS5-VALIDATION.md, run against the REAL artifacts authored in Wave 1 — no xfail/skip
scaffolding, no fictional API. On a green suite this plan flips `nyquist_compliant: true`
in BOS5-VALIDATION.md frontmatter.

Output:
- `.planning/schemas/examples/outcome*.json` (example outcome/measure/reward records)
- `tests/planning/test_bos_outcome_schema.py` + `tests/planning/__init__.py`
- `contracts/outcomes.schema.json` joined to the contract gate (ACC-06)
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-VALIDATION.md
@.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-RESEARCH.md
@.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md

<interfaces>
<!-- The artifacts under test were authored in BOS5-01. Load contracts/outcomes.schema.json
     directly for the exact field names + enums; do NOT re-derive them. The 13 test names below
     are NORMATIVE (from BOS5-VALIDATION.md); the example records validate against the REAL schema. -->

Schema under test: contracts/outcomes.schema.json (Draft 2020-12; authored BOS5-01).
Round-trip scenario (RESEARCH §Code Examples Example 2), authored as example records:
  T=3d  swarm.worker_done (a BOS3 event — descriptive only, not validated by this schema)
  T=4d  CycleTimeMeasure for the entity (event_time=T3, ingest_time=T4, value=3*86400, unit seconds)
  T=4d  CleanMergeLabel  (event_time=T3, ingest_time=T4, obs_window_id="clean-merge-30d")
  T=4d  short-horizon RewardRecord (decision_id, objective_vector, weight_set_version, horizon="short", computed_at)
  T=25d EscapedDefectLabel supersedes the clean_merge (supersedes_outcome_id=<clean_merge outcome_id>,
        severity="medium", ingest_time=T25 > event_time)
  -> the supersede pair proves D-02/D-05; ingest_time>event_time on the late label proves bitemporal/no-leakage.

13 contract checks (BOS5-VALIDATION.md — function names are NORMATIVE):
  test_schema_is_valid, test_categorical_label_coverage, test_measure_coverage,
  test_label_examples_validate, test_bitemporal_invariant, test_no_decision_leakage_in_label,
  test_reward_record_shape, test_decision_schema_no_outcome_field, test_tension_pair_coverage,
  test_guardrail_role_enum, test_scalarization_named, test_round_trip_scenario, test_versioning_present.

CONDITIONAL: contracts/decisions.schema.json (BOS4) does NOT exist yet (BOS4 planned, not executed
as of 2026-06-18). test_decision_schema_no_outcome_field MUST skip (pytest.skip) when that file is
absent so it is never a false-red; when present it asserts no reward/outcome field on the decision record.

Contract gate (ACC-06): the existing drift gate is tests/harness/server/test_contract_drift.py, which
REGENERATES events.schema.json/openapi.json from pydantic models. outcomes.schema.json is hand-authored
(no pydantic source — docs-first, no runtime code), so it canNOT join that regeneration gate. Instead the
"gate" for outcomes.schema.json is a stability/lint check in THIS suite (test_schema_is_valid loads + lints
it on every run; add a test_outcome_schema_in_gate that asserts the file is tracked + lints). Do NOT add a
pydantic model or wire outcomes.schema.json into export_contract.py (that would require runtime code, out of scope).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bundle example outcome records (.planning/schemas/examples/outcome*.json)</name>
  <files>.planning/schemas/examples/outcome-clean-merge.json, .planning/schemas/examples/outcome-rework.json, .planning/schemas/examples/outcome-revert.json, .planning/schemas/examples/outcome-failed-validation.json, .planning/schemas/examples/outcome-escaped-defect.json, .planning/schemas/examples/outcome-incident.json, .planning/schemas/examples/outcome-human-override.json, .planning/schemas/examples/outcome-cycle-time.json, .planning/schemas/examples/outcome-reward.json</files>
  <read_first>
    - contracts/outcomes.schema.json (authored in BOS5-01 — examples MUST validate against it; copy the exact required field names + enum values)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-RESEARCH.md (§Code Examples Example 2 for the round-trip + supersede scenario values; §Outcome Label Definitions for realistic per-label field values; §Multi-Objective Reward Design for a realistic objective_vector)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-VALIDATION.md (ACC-04 — the supersede scenario the round-trip test exercises)
  </read_first>
  <action>
    Create `.planning/schemas/examples/` with one valid example record per categorical label
    (clean_merge, rework, revert, failed_validation, escaped_defect, incident, human_override),
    one cycle_time measure, and one RewardRecord — each validating against `contracts/outcomes.schema.json`.
    Use realistic, internally consistent values:
    - All label/measure records carry v=1, outcome_id, entity_id (e.g. "task-abc123"), entity_type,
      trace_id, event_time, ingest_time (ingest_time >= event_time), obs_window_id (matching a named
      window from the rationale doc, e.g. "clean-merge-30d"), source_rule (the derivation rule id).
    - The escaped_defect example is the SUPERSEDE record: it carries severity="medium" and
      supersedes_outcome_id set to the clean_merge example's outcome_id, with ingest_time strictly
      LATER than the clean_merge example's ingest_time (proves D-02/D-05 + late-arriving / no-leakage). 
    - The rework + incident examples carry severity (low/medium/high); revert / failed_validation /
      human_override / clean_merge carry NO severity field.
    - The cycle_time example: measure_type="cycle_time", value=259200 (3 days in seconds), unit="seconds",
      measure_definition_id pinning task.created_at -> pr.merged_at.
    - The reward example (outcome-reward.json): RewardRecord with v=1, reward_id, decision_id,
      objective_vector (throughput/quality/rework_cost/flow numbers), weight_set_version, horizon="short",
      computed_at, ingest_time, scalarized_reward. (RewardRecord legitimately carries decision_id.)
    Label/measure example records MUST NOT contain a decision_id or recommended_action key (no-leakage).
    Do NOT modify the schema or the rationale doc — these examples are CONSUMERS of the contract.
    NO git add/commit/push — the operator commits manually.
  </action>
  <verify>
    <automated>.venv/bin/python -c "import json,glob,jsonschema; s=json.load(open('contracts/outcomes.schema.json')); v=jsonschema.Draft202012Validator(s); fs=sorted(glob.glob('.planning/schemas/examples/outcome*.json')); assert len(fs)>=9, f'need >=9 examples got {len(fs)}'; recs={f:json.load(open(f)) for f in fs}; [j for f,j in recs.items() if 'reward' not in f and ('decision_id' in j or 'recommended_action' in j) and (_ for _ in ()).throw(AssertionError('label/measure example '+f+' leaks decision ref'))]; cm=json.load(open('.planning/schemas/examples/outcome-clean-merge.json')); ed=json.load(open('.planning/schemas/examples/outcome-escaped-defect.json')); assert ed.get('supersedes_outcome_id')==cm['outcome_id'], 'escaped_defect supersedes clean_merge'; assert ed['ingest_time']>cm['ingest_time'], 'supersede label arrives later'; print(f'{len(fs)} example records present; supersede chain + no-leakage ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/schemas/examples/` contains >=9 `outcome*.json` records: one per categorical label (7), one cycle_time measure, one RewardRecord.
    - (ACC-04) The escaped_defect example carries `supersedes_outcome_id` equal to the clean_merge example's `outcome_id` and an `ingest_time` strictly later than the clean_merge example's ingest_time (the supersede + late-arrival scenario).
    - Every label/measure example record contains NO `decision_id` and NO `recommended_action` key (no-leakage); the reward example DOES carry `decision_id`.
    - severity appears only on the rework/escaped_defect/incident examples; cycle_time carries value/unit/measure_definition_id.
    - `git diff --quiet contracts/ docs/BOS5-OUTCOME-REWARD-SPEC.md` exits 0 (Task 1 adds only example files; schema + doc unchanged) and `git diff --quiet voss/` exits 0.
  </acceptance_criteria>
  <done>>=9 example outcome records exist, each validating against the BOS5-01 schema; the clean_merge -> escaped_defect supersede chain is present with a later ingest_time; label/measure records carry no decision reference; the reward record does; schema + doc untouched.</done>
</task>

<task type="auto">
  <name>Task 2: Author the 13-check contract suite + join outcomes.schema.json to the gate</name>
  <files>tests/planning/__init__.py, tests/planning/test_bos_outcome_schema.py</files>
  <read_first>
    - contracts/outcomes.schema.json + .planning/schemas/examples/outcome*.json (the artifacts under test, from BOS5-01 + Task 1)
    - docs/BOS5-OUTCOME-REWARD-SPEC.md (test_versioning_present + tension-pair coverage cross-checks the doc tables)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-VALIDATION.md (the 13 NORMATIVE test names + ACC-01..ACC-07 + the per-task verification map)
    - tests/harness/server/test_contract_drift.py (REFERENCE ONLY — the existing pydantic-regeneration gate; understand why outcomes.schema.json canNOT join it and instead gets a load+lint stability check in this suite)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-02-PLAN.md (REFERENCE — the sibling contract-suite shape to match: load schema, parametrize examples, assert taxonomy/bitemporal/versioning)
  </read_first>
  <action>
    Create `tests/planning/__init__.py` (empty package marker) and
    `tests/planning/test_bos_outcome_schema.py` implementing EXACTLY these 13 test functions
    (names are normative), loading `contracts/outcomes.schema.json` and the
    `.planning/schemas/examples/outcome*.json` records via pathlib + json + jsonschema:
    - test_schema_is_valid: jsonschema.Draft202012Validator.check_schema on the schema (ACC-01); doubles as
      the stability/lint gate for outcomes.schema.json (ACC-06 — it canNOT join the pydantic regeneration gate).
    - test_categorical_label_coverage: all 7 label_type consts present in the schema (ACC-02).
    - test_measure_coverage: cycle_time measure_type present (ACC-02).
    - test_label_examples_validate: parametrize over every outcome*.json; each validates against the schema (ACC-04).
    - test_bitemporal_invariant: every label/measure example carries event_time + ingest_time with ingest_time >= event_time.
    - test_no_decision_leakage_in_label: the OutcomeEnvelope (and label/measure example records) define/contain
      NO decision_id and NO recommended_action; assert against both schema $defs and the example records (D-04).
    - test_reward_record_shape: RewardRecord $def requires decision_id, objective_vector, weight_set_version,
      horizon, computed_at (BOS-DATA-04).
    - test_decision_schema_no_outcome_field: CONDITIONAL — if contracts/decisions.schema.json exists, assert it has
      no reward/outcome field; else pytest.skip("BOS4 decisions.schema.json not yet authored"). Never a false-red.
    - test_tension_pair_coverage: collect the objective keys from WeightSetRecord.objectives (or the documented
      objective set) and assert each appears as a GuardrailMetricSpec.linked_reward_objective somewhere in the
      schema/doc (ACC-05). Filter comment lines if parsing the doc.
    - test_guardrail_role_enum: GuardrailMetricSpec.role enum is EXACTLY {hard_gate, dashboard}.
    - test_scalarization_named: WeightSetRecord.scalarization enum includes "linear_weighted".
    - test_round_trip_scenario: load the cycle_time + clean_merge + escaped_defect(supersede) + reward examples;
      assert all validate, the supersede pointer links clean_merge->escaped_defect, and the late label's
      ingest_time > the decision-time (ACC-04 round-trip; mirrors RESEARCH Example 2).
    - test_versioning_present: schema variants carry v (const 1); docs/BOS5-OUTCOME-REWARD-SPEC.md contains a
      migration-notes section (grep the doc body, comment-filtered).
    Use `.venv/bin/python -m pytest`. Do NOT add a pydantic model, do NOT modify export_contract.py or
    contracts/events.schema.json/openapi.json (that would require runtime code, out of scope). Do NOT modify
    the schema, the doc, or the examples — this suite only READS them. NO git add/commit/push.
    After the suite is green, flip `nyquist_compliant: false -> true` in BOS5-VALIDATION.md frontmatter.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/planning/test_bos_outcome_schema.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `tests/planning/__init__.py` and `tests/planning/test_bos_outcome_schema.py` exist; the suite defines all 13 normative test functions named in BOS5-VALIDATION.md.
    - `.venv/bin/python -m pytest tests/planning/test_bos_outcome_schema.py -q` passes with 0 failures/errors (test_decision_schema_no_outcome_field may report skipped while BOS4's decisions.schema.json is absent — that is expected, not a failure).
    - test_schema_is_valid lints contracts/outcomes.schema.json against Draft 2020-12 (the ACC-06 stability gate for the hand-authored sibling schema); test_tension_pair_coverage proves every reward objective has >=1 linked guardrail (ACC-05); test_guardrail_role_enum proves role is exactly {hard_gate, dashboard}; test_scalarization_named proves linear_weighted present.
    - test_round_trip_scenario proves the cycle_time + clean_merge + escaped_defect(supersede) + reward chain validates and the supersede pointer + late ingest_time hold (ACC-04).
    - `nyquist_compliant: true` is set in BOS5-VALIDATION.md frontmatter after the green run.
    - `git diff --quiet contracts/ docs/ .planning/schemas/examples/` exits 0 (the suite authored in this task reads, does not modify, those artifacts) and `git diff --quiet voss/` exits 0.
  </acceptance_criteria>
  <done>The 13-check contract suite exists and passes against the real BOS5-01 schema + BOS5-02 examples; outcomes.schema.json is lint-gated on every run (ACC-06); tension-pair coverage, role enum, named scalarization, no-leakage, bitemporal, and the supersede round-trip are all proven; the BOS4 decision-no-outcome check skips cleanly while BOS4 is unbuilt; nyquist_compliant flipped true.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (no runtime boundary in this phase) | Docs-only contract validation. The suite reads JSON Schema + example records and asserts structural properties; no service, network, or untrusted input at runtime. Threats are data-governance correctness. |
| example/test author -> existing source artifacts | The plan must NOT cross into contracts/events.schema.json, openapi.json, export_contract.py, PROTOCOL.md, or voss/** — examples + tests are new consumers only. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-BOS5-02-01 | Information disclosure | no-leakage guard regression | mitigate | test_no_decision_leakage_in_label asserts (over schema $defs AND example records) that label/measure records carry no decision_id/recommended_action; makes the D-04 structural guard machine-checked and regression-proof. |
| T-BOS5-02-02 | Tampering | reward hacking / Goodhart coverage regression | mitigate | test_tension_pair_coverage (ACC-05) fails if any reward objective loses its counter-metric; test_guardrail_role_enum pins role to {hard_gate, dashboard}. Coverage cannot silently erode. |
| T-BOS5-02-03 | Tampering | silent drift of the hand-authored outcomes.schema.json | mitigate | test_schema_is_valid loads + Draft-2020-12-lints the schema on every run (ACC-06 gate for a schema with no pydantic source); a malformed edit fails CI. |
| T-BOS5-02-04 | Tampering | false-green from a missing upstream artifact (BOS4 decisions.schema.json) | mitigate | test_decision_schema_no_outcome_field is CONDITIONAL (pytest.skip when absent) — it can neither false-red on BOS4 being unbuilt nor false-green by silently passing; it activates only when the file exists. Guards the [[gsd-scaffold-fictional-api]] trap. |
| T-BOS5-02-SC | Tampering | package installs | accept | No package-manager installs; `jsonschema` 4.26.0 + pytest already in `.venv`. No legitimacy gate needed. No runtime code in this phase; threats are data-governance, mitigated by contract structure + tests. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/planning/test_bos_outcome_schema.py -x -q` — full 13-check suite green (one skip allowed for the conditional BOS4 check).
- `.venv/bin/python -c "import json,glob,jsonschema; s=json.load(open('contracts/outcomes.schema.json')); v=jsonschema.Draft202012Validator(s); [v.validate(json.load(open(f))) for f in glob.glob('.planning/schemas/examples/outcome*.json')]"` — every example round-trips.
- `nyquist_compliant: true` present in BOS5-VALIDATION.md.
- `git diff --quiet contracts/ docs/ && git diff --quiet voss/` — no existing source or BOS5-01 artifact modified by this plan.
</verification>

<success_criteria>
- >=9 example outcome records authored (7 labels + cycle_time + RewardRecord), each round-tripping against the schema; supersede scenario present (ACC-04).
- 13-check pytest suite authored under tests/planning/ and passing (ACC-01..ACC-07), with the BOS4 decision check skipping cleanly while BOS4 is unbuilt.
- contracts/outcomes.schema.json lint-gated on every run (ACC-06).
- nyquist_compliant flipped true in BOS5-VALIDATION.md.
- contracts/events.schema.json, openapi.json, export_contract.py, PROTOCOL.md, voss/harness/**, and the BOS5-01 artifacts unchanged.
</success_criteria>

<output>
Create `.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-02-SUMMARY.md` when done.
</output>
</content>
