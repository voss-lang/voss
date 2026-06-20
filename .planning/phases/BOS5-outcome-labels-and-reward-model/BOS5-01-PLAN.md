---
phase: BOS5
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - contracts/outcomes.schema.json
  - docs/BOS5-OUTCOME-REWARD-SPEC.md
autonomous: true
requirements: [BOS-DATA-03, BOS-DATA-04]

must_haves:
  truths:
    - "A reader can determine the exact shape of all 7 categorical outcome labels and the cycle_time measure from the contract"
    - "A reader can determine, for any outcome label, that it carries no decision_id/recommended_action (no-leakage guard) and both event_time + ingest_time (bitemporal)"
    - "A reader can determine the reward model shape (objective vector + named versioned scalarization + horizon) and reproduce any reward from (objective_vector + weight_set_version)"
    - "Every named reward objective in the contract has >=1 named counter-metric guardrail (tension-pair coverage), each tagged hard_gate or dashboard"
    - "A reader can map every BOS3 source event to its outcome label via a deterministic derivation-rule table, and find default observation windows + reward horizons in the rationale doc"
  artifacts:
    - path: "contracts/outcomes.schema.json"
      provides: "Normative JSON Schema (Draft 2020-12): categorical label union (7 variants), outcome_measure union (cycle_time), RewardRecord, WeightSetRecord, GuardrailMetricSpec"
      contains: "https://json-schema.org/draft/2020-12/schema"
      min_lines: 180
    - path: "docs/BOS5-OUTCOME-REWARD-SPEC.md"
      provides: "Rationale prose: derivation-rules table, observation-window table, reward-objective table, scalarization, tension-pair table, migration notes"
      contains: "tension"
      min_lines: 150
  key_links:
    - from: "docs/BOS5-OUTCOME-REWARD-SPEC.md"
      to: "contracts/outcomes.schema.json"
      via: "prose spec documents the same field set + enums the JSON Schema enforces"
      pattern: "outcomes.schema.json"
    - from: "contracts/outcomes.schema.json GuardrailMetricSpec.linked_reward_objective"
      to: "WeightSetRecord.objectives keys"
      via: "every reward objective is the linked_reward_objective of >=1 guardrail"
      pattern: "linked_reward_objective"
---

<objective>
Author the two NORMATIVE contract artifacts for the BOS5 outcome/reward model: a
machine-readable JSON Schema (`contracts/outcomes.schema.json`, sibling to the
existing `events.schema.json`) and a human-readable rationale spec
(`docs/BOS5-OUTCOME-REWARD-SPEC.md`). Together they define the append-only,
bitemporal, no-leakage outcome label + continuous measure families, the
multi-objective reward record, the versioned team-level weight set, and the
anti-Goodhart tension-pair guardrail contract.

Purpose: BOS-DATA-03 (the 7 categorical labels + cycle_time measure) and
BOS-DATA-04 (reward + guardrail metrics with bad-proxy detection), defined BEFORE
any learning system. DOCS-FIRST phase: a contract, not runtime emitters, derivation
engines, or storage. No code, no migrations.

Output:
- `contracts/outcomes.schema.json` (source-of-truth machine contract)
- `docs/BOS5-OUTCOME-REWARD-SPEC.md` (normative human spec mirroring the schema)
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md
@.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-RESEARCH.md
@.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-VALIDATION.md

<interfaces>
<!-- Authoritative inputs from BOS5-RESEARCH.md + CONTEXT.md. Use these directly;
     do NOT re-derive label semantics by reading the harness. The analog pattern to
     MIRROR is contracts/events.schema.json (discriminated union on a `type`-style
     field with a `const` per variant + `v: 1` on every variant). The new schema is
     a sibling file under contracts/. Field names below are RECOMMENDED (CONTEXT.md
     Claude's Discretion); the structure + enum membership are NORMATIVE. -->

Mirror pattern (from contracts/events.schema.json, e.g. SwarmAssign):
  each variant is a $def object; discriminator field carries {"const": "<value>"};
  every variant carries {"v": {"const": 1}}; required[] lists all required fields;
  optional fields (severity, supersedes_outcome_id) are NOT in required.

Shared outcome-event envelope (EVERY categorical label + measure record):
  v (int const 1) | outcome_id (str) | entity_id (str, BOS3 stable id) |
  entity_type (enum: task|pr|session|external_reserved) | trace_id (str) |
  event_time (date-time, valid time) | ingest_time (date-time, transaction time, >= event_time) |
  obs_window_id (str, references named window in the rationale doc) |
  source_rule (str, the D-01 derivation rule id) |
  supersedes_outcome_id (str, OPTIONAL — D-02/D-05 supersession pointer)
  NO decision_id / recommended_action on label or measure records (no-leakage, D-04 carried).

CATEGORICAL label family — discriminated on `label_type` (closed enum, 7 variants, D-04):
  clean_merge | rework | revert | failed_validation | escaped_defect | incident | human_override
  severity (OPTIONAL enum low|medium|high) ONLY on: rework, escaped_defect, incident (D-06).
  Others (clean_merge, revert, failed_validation, human_override) carry no severity.

CONTINUOUS measure family — discriminated on `measure_type` (D-04, room for more):
  cycle_time — required: value (number, seconds, float), unit (const "seconds"),
  measure_definition_id (str, pins the definition: task.created_at -> pr.merged_at, RESEARCH Pitfall 1).

RewardRecord (computed/derived, append-only — NOT an outcome event; MAY carry decision_id):
  required: v (const 1) | reward_id (str) | decision_id (str) | objective_vector (object: objective-name -> number) |
  weight_set_version (str) | horizon (enum: short|long, open to more) | computed_at (date-time) | ingest_time (date-time)
  scalarized_reward (number, OPTIONAL).
  Append-only recompute: later horizon = NEW RewardRecord, same decision_id, higher ingest_time; never mutates the original.

WeightSetRecord (versioned team-level config shape, per decision_type — D-08):
  required: weight_set_id (str) | weight_set_version (str) | decision_type (str) |
  objectives (object: objective-name -> number weight) | scalarization (enum string) | effective_from (date-time)
  scalarization enum MUST include "linear_weighted" (present); reserve "chebyshev","epsilon_constrained" as valid future values (migration note).
  Recommended objective set (D-07 discretion): throughput | quality | rework_cost | flow.

GuardrailMetricSpec (config/spec record, NOT a runtime event — D-10/D-11):
  required: guardrail_id (str) | counter_metric_formula (str) | linked_reward_objective (str) |
  role (enum EXACTLY hard_gate|dashboard) | threshold_shape (object: {type, window_days, max_value-nullable})
  COVERAGE RULE (normative, D-10): every key in WeightSetRecord.objectives MUST appear as
  linked_reward_objective on >=1 GuardrailMetricSpec. This is ACC-05.

Versioning (mirror PROTOCOL.md `v` + migration-note, as BOS3/BOS4 did):
  schema_version 1; additive changes (new label_type filling a reserved slot, new objective via new
  weight-set version, new horizon name) do NOT bump; breaking changes bump + migration note in the doc.

Recommended default observation windows (RESEARCH; tunable team config, named not hard-coded):
  clean_merge 30d | rework 14d | revert 0d | failed_validation 0d | escaped_defect 90d | incident 90d | human_override 0d.
Recommended reward horizons (RESEARCH; D-09): short=7d, long=90d.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author contracts/outcomes.schema.json (normative JSON Schema, Draft 2020-12)</name>
  <files>contracts/outcomes.schema.json</files>
  <read_first>
    - contracts/events.schema.json (the EXACT discriminated-union pattern to mirror: per-variant $def, `const` discriminator, `v` on every variant, `required[]` arrays, top-level oneOf + discriminator.mapping)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-RESEARCH.md (§Architecture Patterns 1-3 for schema skeleton; §Outcome Label Definitions for the 7 labels + severity-bearing set; §Multi-Objective Reward Design for RewardRecord/WeightSetRecord; §Goodhart and Guardrail Patterns for GuardrailMetricSpec; §Common Pitfalls 1-7 for the no-leakage/supersession/window/reward-record traps)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md (D-01..D-12 verbatim — cite the driving D-ID per construct)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-VALIDATION.md (ACC-01..ACC-07 + the 13-check suite this schema must satisfy)
  </read_first>
  <action>
    Create `contracts/outcomes.schema.json` as a JSON Schema Draft 2020-12 document
    (`"$schema": "https://json-schema.org/draft/2020-12/schema"`, versioned `"$id"` e.g.
    `https://voss.dev/contracts/outcomes.schema.json`, a `description` noting `v: 1`). Build,
    per the <interfaces> block and the driving decisions:

    (a) A shared `$defs.OutcomeEnvelope` object requiring v, outcome_id, entity_id, entity_type,
        trace_id, event_time, ingest_time, obs_window_id, source_rule. `entity_type` is an enum
        of task|pr|session|external_reserved. event_time/ingest_time use `format: date-time`.
        `supersedes_outcome_id` is an OPTIONAL string (NOT in required) — the D-02/D-05 supersession
        pointer. The envelope MUST NOT define decision_id or recommended_action (no-leakage, D-04 carried;
        Pitfall 6). Set additionalProperties handling so a stray decision_id is detectable by the suite
        (do NOT allow a decision_id key on label/measure records).
    (b) The 7 categorical label `$defs` (CleanMergeLabel, ReworkLabel, RevertLabel, FailedValidationLabel,
        EscapedDefectLabel, IncidentLabel, HumanOverrideLabel), each composing the envelope and adding
        `label_type` as a `const` (clean_merge|rework|revert|failed_validation|escaped_defect|incident|
        human_override) plus `v` const 1. Add an OPTIONAL `severity` enum (low|medium|high) ONLY to
        ReworkLabel, EscapedDefectLabel, IncidentLabel (D-06); the other 4 carry no severity field.
    (c) The continuous measure `$def` CycleTimeMeasure composing the envelope, with `measure_type` const
        "cycle_time", required value (number), unit const "seconds", and `measure_definition_id` (string,
        pins the task.created_at -> pr.merged_at definition per Pitfall 1). Leave the measure family open
        to additional measure_type variants (additive, no version bump).
    (d) `$defs.RewardRecord` (separate top-level family — NOT an outcome event, Pitfall 3): required v(const 1),
        reward_id, decision_id, objective_vector (object, additionalProperties number), weight_set_version,
        horizon (enum short|long), computed_at (date-time), ingest_time (date-time); OPTIONAL scalarized_reward
        (number). RewardRecord MAY carry decision_id (reward is computed FOR a decision); label/measure records may not.
    (e) `$defs.WeightSetRecord` (D-08): required weight_set_id, weight_set_version, decision_type,
        objectives (object: objective-name -> number weight), scalarization (string enum that MUST include
        "linear_weighted" and SHOULD list chebyshev, epsilon_constrained as reserved future values),
        effective_from (date-time). Use throughput|quality|rework_cost|flow as the documented objective keys
        in the schema's example/description (D-07 recommended set). Do NOT bake weight VALUES into the schema —
        only the shape (deferred per CONTEXT scope fence).
    (f) `$defs.GuardrailMetricSpec` (D-10/D-11): required guardrail_id, counter_metric_formula,
        linked_reward_objective (string), role (enum EXACTLY ["hard_gate","dashboard"] — no other values,
        ACC-?? / test_guardrail_role_enum), threshold_shape (object with type, window_days, max_value where
        max_value may be null = team-configured). Do NOT embed observation-window day-counts as schema constants
        (Pitfall 4) — windows are referenced by obs_window_id and documented in the rationale doc.
    (g) Two top-level outcome-event unions: a `oneOf` over the 7 categorical labels with a
        `discriminator` mapping on `label_type`, and a `oneOf` over the measure variants with a
        `discriminator` mapping on `measure_type` (mirror events.schema.json's discriminator.mapping form).
        RewardRecord, WeightSetRecord, GuardrailMetricSpec are referenced $defs (config/derived records),
        not part of the outcome-event oneOf.
    (h) A `$comment` migration note (mirror PROTOCOL.md `v`): "schema_version=1; additive changes (new
        label_type, new measure_type, new objective via new weight-set version, new horizon) do NOT bump;
        breaking changes increment + add a migration note in docs/BOS5-OUTCOME-REWARD-SPEC.md."

    Do NOT author runtime code, emitters, derivation engines, or migrations. Do NOT modify
    contracts/events.schema.json, contracts/openapi.json, PROTOCOL.md, or any voss/harness/** source.
    NO git add/commit/push — the operator commits manually.
  </action>
  <verify>
    <automated>.venv/bin/python -c "import json,jsonschema; s=json.load(open('contracts/outcomes.schema.json')); jsonschema.Draft202012Validator.check_schema(s); blob=json.dumps(s); labels={'clean_merge','rework','revert','failed_validation','escaped_defect','incident','human_override'}; assert all(('\"const\": \"%s\"'%l) in blob or l in blob for l in labels), 'all 7 label_type consts present'; assert 'cycle_time' in blob, 'cycle_time measure present'; assert 'RewardRecord' in s.get('\$defs',{}), 'RewardRecord def'; assert 'WeightSetRecord' in s.get('\$defs',{}), 'WeightSetRecord def'; assert 'GuardrailMetricSpec' in s.get('\$defs',{}), 'GuardrailMetricSpec def'; assert 'linear_weighted' in blob, 'named scalarization'; assert 'hard_gate' in blob and 'dashboard' in blob, 'guardrail roles'; assert 'decision_id' not in json.dumps(s['\$defs'].get('OutcomeEnvelope',{})), 'no decision_id on envelope'; print('outcomes.schema.json valid Draft2020-12 + coverage + no-leakage envelope')"</automated>
  </verify>
  <acceptance_criteria>
    - (ACC-01) `contracts/outcomes.schema.json` parses as JSON and passes `jsonschema.Draft202012Validator.check_schema` (lints clean against the Draft 2020-12 meta-schema).
    - (ACC-02) All 7 categorical `label_type` consts (clean_merge, rework, revert, failed_validation, escaped_defect, incident, human_override) are present as discriminated variants, and a `cycle_time` `measure_type` variant exists in the measure family.
    - (ACC-03) Every categorical label and measure variant composes an envelope requiring entity_id, event_time, ingest_time, obs_window_id, source_rule; optional severity appears ONLY on rework/escaped_defect/incident; optional supersedes_outcome_id is available on every label.
    - The `OutcomeEnvelope` (and thus every label/measure record) defines NO decision_id and NO recommended_action field (no-leakage guard, D-04); `RewardRecord` DOES require decision_id.
    - `RewardRecord`, `WeightSetRecord`, `GuardrailMetricSpec` `$defs` exist; WeightSetRecord.scalarization enum includes `linear_weighted`; GuardrailMetricSpec.role enum is EXACTLY {hard_gate, dashboard}; GuardrailMetricSpec requires `linked_reward_objective`.
    - `git diff --quiet contracts/events.schema.json contracts/openapi.json` exits 0 and `git diff --quiet voss/` exits 0 (no existing contract or harness source touched).
  </acceptance_criteria>
  <done>The outcomes JSON Schema exists, lints clean against Draft 2020-12, encodes the no-leakage bitemporal envelope, all 7 categorical labels (severity on the 3 magnitude labels), the cycle_time measure, and the RewardRecord / WeightSetRecord (named versioned scalarization) / GuardrailMetricSpec (hard_gate|dashboard) families, with a PROTOCOL.md-style migration note; no existing source files modified.</done>
</task>

<task type="auto">
  <name>Task 2: Author docs/BOS5-OUTCOME-REWARD-SPEC.md (rationale prose + tables)</name>
  <files>docs/BOS5-OUTCOME-REWARD-SPEC.md</files>
  <read_first>
    - contracts/outcomes.schema.json (the artifact authored in Task 1 — the spec MUST mirror its field set, enums, and the objective/guardrail names)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-RESEARCH.md (§Outcome Label Definitions table; §Observation Window Guidance table; §Derivation Rules Pattern rule table; §Multi-Objective Reward Design objective table + scalarization; §Goodhart and Guardrail Patterns tension-pair table; §State of the Art deprecated approaches)
    - .planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md (D-01..D-12 verbatim, to cite by ID in each section)
    - .planning/PROJECT.md (Constraints §Data no-leakage / §Trust team-level, no individual ranking / §Safety — the governance framing for the tension-pair section)
  </read_first>
  <action>
    Create `docs/BOS5-OUTCOME-REWARD-SPEC.md` as the normative human spec, referencing
    `contracts/outcomes.schema.json` as the machine source of truth. Sections (each citing the
    driving D-ID; mirror the schema exactly):

    1. Outcome label catalog (D-04/D-06) — a table of the 7 categorical labels (label_type value,
       meaning, primary BOS3 source event, whether severity applies) + the cycle_time measure row
       (definition pinned to task.created_at -> pr.merged_at, unit seconds, measure_definition_id).
    2. Derivation-rules table (D-01) — one row per rule: rule id (the source_rule value), trigger
       BOS3 event(s), conditions, output label_type, entity anchor. Note which rules activate now
       (internal: human_override, swarm task failure) vs activate when BOS12 fills reserved external
       slots (pr.merged, ci.failed, incident.opened). Use the word "derivation".
    3. Observation-window table (D-02) — named window ids + default day-counts (clean_merge 30d,
       rework 14d, revert 0d, failed_validation 0d, escaped_defect 90d, incident 90d, human_override 0d),
       stated as tunable team config referenced by obs_window_id (NOT schema constants). Use the phrase
       "observation window". Document the supersession model (clean_merge -> escaped_defect via
       supersedes_outcome_id) and the as-of no-leakage join (labels visible only where ingest_time <= T_decision).
    4. Reward model (D-07/D-08/D-09) — the named objective table (throughput|quality|rework_cost|flow:
       what each aggregates, direction), the named scalarization (linear_weighted as initial; chebyshev /
       epsilon_constrained reserved), the WeightSetRecord shape (versioned, team-level, per decision_type),
       reproducibility rule (objective_vector + weight_set_version => scalar), and the short/long horizons
       with append-only recomputation semantics. Use the word "objective".
    5. Tension-pair / bad-proxy table (D-10/D-11) — REQUIRED. One row per (reward objective ->
       counter-metric -> gaming pattern detected -> role hard_gate|dashboard -> threshold shape). MUST
       cover every objective named in §4 (each objective appears as the optimized axis with >=1 counter-metric).
       Note thresholds are tunable team config (shape fixed by contract, values set in BOS15). Use the word "tension".
    6. Scope + downstream consumers (D-12) — state BOS5 owns reward/outcome guardrails ONLY; fairness/
       autonomy-creep/fatigue are BOS6 (BOS-GOV-04) / BOS17 (BOS-BEH-02); enforcement gates + horizon
       selection are BOS15; reward weight VALUES + tuning are BOS13/14/15. List as references, not built here.
    7. Versioning & migration notes — schema_version=1; additive vs breaking rules (mirror PROTOCOL.md);
       deprecated approaches to avoid (individual-ranking reward; time-discounted reward — RESEARCH §State of the Art).
       Use the word "migration".

    Do NOT author runtime code. Do NOT modify contracts/*, PROTOCOL.md, or any voss/harness/** source.
    NO git add/commit/push — the operator commits manually.
  </action>
  <verify>
    <automated>.venv/bin/python -c "t=open('docs/BOS5-OUTCOME-REWARD-SPEC.md').read(); body='\n'.join(l for l in t.splitlines() if not l.strip().startswith('#')); assert 'outcomes.schema.json' in t, 'links machine schema'; assert all(l in t for l in ['clean_merge','rework','revert','failed_validation','escaped_defect','incident','human_override','cycle_time']), 'all labels+measure'; assert all(s in body.lower() for s in ['derivation','observation window','objective','tension','migration']), 'required section keywords'; assert 'linear_weighted' in t, 'named scalarization'; assert 'hard_gate' in t and 'dashboard' in t, 'guardrail roles'; assert 'supersedes_outcome_id' in t, 'supersession model'; print('rationale spec content checks pass')"</automated>
  </verify>
  <acceptance_criteria>
    - (ACC-07) `docs/BOS5-OUTCOME-REWARD-SPEC.md` exists and references `contracts/outcomes.schema.json` as the machine source of truth.
    - The doc contains, as distinct tables: a derivation-rules table, an observation-window table, a reward-objective table, and a tension-pair table; plus a migration-notes section (the 5 keywords derivation / observation window / objective / tension / migration all present in body prose).
    - All 7 categorical label_type values + `cycle_time` appear; the cycle_time definition is pinned (task.created_at -> pr.merged_at) per Pitfall 1; severity is documented as optional on rework/escaped_defect/incident only.
    - The tension-pair table covers every reward objective named in the reward section with >=1 counter-metric, each tagged hard_gate or dashboard; `linear_weighted` named as the initial scalarization; the supersession + as-of no-leakage join is documented.
    - The scope section names BOS6/BOS17/BOS15/BOS13-14 as downstream consumers (D-12) without building them; deprecated individual-ranking + time-discounted reward are called out.
    - `git diff --quiet contracts/ PROTOCOL.md` exits 0 and `git diff --quiet voss/` exits 0 (Task 2 authors only the doc; it does not alter the schema).
  </acceptance_criteria>
  <done>The rationale spec exists, mirrors the schema's field set + enums, and contains the derivation-rules / observation-window / reward-objective / tension-pair tables, the scalarization + horizon + reproducibility rules, the D-12 scope fence with downstream consumer references, and PROTOCOL.md-style versioning/migration notes; no existing source files modified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (no runtime boundary in this phase) | Docs-only contract phase: no code executes, no inputs are processed at runtime. Threats are data-governance correctness, not classic appsec. |
| future label-writer -> outcome log (BOS11/12 era) | The schema IS the validation contract for that future boundary; BOS5 only authors the contract. The no-leakage + append-only structure is the guarantee. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-BOS5-01 | Information disclosure | outcome label record fields (leakage of outcomes into decision-time features) | mitigate | PRIMARY modeled threat. Structural mitigation: the OutcomeEnvelope defines NO decision_id / recommended_action; the join runs decision -> outcome (entity + as-of, ingest_time <= T_decision), never the reverse. RewardRecord may carry decision_id (computed after the fact). Verified by Task 1 acceptance + BOS5-02 test_no_decision_leakage_in_label. |
| T-BOS5-02 | Tampering / Repudiation | reward objectives without counter-metrics (reward hacking / Goodhart) | mitigate | D-10 tension-pair coverage: every reward objective has >=1 named GuardrailMetricSpec.linked_reward_objective, each tagged hard_gate|dashboard. Coverage is machine-checkable (ACC-05 / BOS5-02 test_tension_pair_coverage). |
| T-BOS5-03 | Information disclosure | PII / individual-ranking fields in outcome or reward records | mitigate | Records anchor to BOS3 opaque entity_id (task/pr/session), NOT engineer name/email; reward is team-level. Schema introduces no engineer_id field; rationale doc forbids individual-ranking + time-discounted reward (§State of the Art deprecated). |
| T-BOS5-04 | Tampering | existing contract / harness source (events.schema.json, openapi.json, PROTOCOL.md, voss/**) | mitigate | Acceptance criteria assert `git diff --quiet` for those paths; BOS5 authors only the NEW sibling schema + doc. No emitters, migrations, or runtime code. |
| T-BOS5-SC | Tampering | package installs | accept | No package-manager installs in this plan; `jsonschema` 4.26.0 already present in `.venv`. No legitimacy gate needed. Note: no runtime code in this phase; threats are data-governance, mitigated by contract structure. |
</threat_model>

<verification>
Run the per-task automated checks. After both tasks:
- `.venv/bin/python -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('contracts/outcomes.schema.json')))"` — schema lints clean (ACC-01).
- Both artifacts exist; the doc references the schema; all 7 labels + cycle_time present in both (ACC-02/ACC-07).
- `git diff --quiet contracts/events.schema.json contracts/openapi.json PROTOCOL.md && git diff --quiet voss/` — no existing source modified.
</verification>

<success_criteria>
- `contracts/outcomes.schema.json` authored, lints clean (Draft 2020-12), encodes the no-leakage bitemporal envelope, 7 categorical labels (severity on the 3 magnitude labels), cycle_time measure, RewardRecord, versioned WeightSetRecord (named scalarization incl. linear_weighted), GuardrailMetricSpec (hard_gate|dashboard) with tension-pair coverage hooks.
- `docs/BOS5-OUTCOME-REWARD-SPEC.md` authored, mirrors the schema, contains derivation-rules / observation-window / reward-objective / tension-pair tables + migration notes + D-12 scope fence.
- BOS-DATA-03 and BOS-DATA-04 contract artifacts exist and are internally consistent (ACC-01, ACC-02, ACC-03, ACC-05, ACC-07 checkable on these artifacts).
- contracts/events.schema.json, openapi.json, PROTOCOL.md, and voss/harness/** unchanged.
</success_criteria>

<output>
Create `.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-01-SUMMARY.md` when done.
</output>
</content>
</invoke>
