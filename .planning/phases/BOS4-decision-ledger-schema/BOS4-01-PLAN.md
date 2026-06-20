---
phase: BOS4-decision-ledger-schema
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - contracts/decision-ledger.schema.json
autonomous: true
requirements:
  - BOS-DATA-02
must_haves:
  truths:
    - "The decision ledger record shape is captured as an authoritative JSON Schema sibling to contracts/events.schema.json"
    - "All six decision_type kinds are enumerated with a typed payload each, in a discriminated-union shape"
    - "Each record carries an immutable as-of event-state pointer AND a frozen feature-vector snapshot"
    - "Each record carries recommended_action, human_verdict (with actor + timestamp), and actual_action"
    - "The record has an autonomy_band field"
    - "The record has NO outcome / label field (no-leakage guard is enforced by absence)"
    - "Event-ref and entity-ref fields are present but documented as upstream BOS3 assumptions"
  artifacts:
    - path: "contracts/decision-ledger.schema.json"
      provides: "Authoritative JSON Schema for the decision ledger record (discriminated union over decision_type)"
      contains: "decision_type"
  key_links:
    - from: "contracts/decision-ledger.schema.json"
      to: "contracts/events.schema.json"
      via: "mirrors the discriminator + $defs + oneOf discriminated-union pattern"
      pattern: "discriminator"
    - from: "decision record"
      to: "BOS3 event stream"
      via: "as-of event-state pointer field (upstream assumption D-07)"
      pattern: "as_of"
---

<objective>
Produce the authoritative decision ledger contract as a JSON Schema at `contracts/decision-ledger.schema.json`, sibling to the existing `contracts/events.schema.json`. This is the deliverable form mandated by BOS2 D-06 (sibling JSON Schema under `contracts/` feeding the CI drift gate). It defines the shape of a single append-only decision ledger record (BOS-DATA-02): a unified record with a `decision_type` discriminator over six typed payloads, the dual as-of/frozen-snapshot training-signal capture, the three explicit action fields, the autonomy_band field, and an explicit no-outcome-field no-leakage guard.

Purpose: Lock the record shape downstream phases inherit — the recommendation engine (BOS13/14) writes these rows, BOS5 outcome labels join them by `decision_id`, BOS15 offline-eval consumes them. Getting the contract right now prevents schema churn across the data-and-trust substrate.

Output: `contracts/decision-ledger.schema.json` — a valid JSON Schema mirroring the discriminated-union style of events.schema.json.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@contracts/events.schema.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author the decision ledger JSON Schema</name>
  <files>contracts/decision-ledger.schema.json</files>
  <read_first>
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md (locked decisions D-01..D-08; this is the authoritative input)
    - contracts/events.schema.json (the existing discriminated-union pattern to mirror: top-level object with a `$defs` map of typed sub-records, a discriminator on `propertyName`, a `mapping`, and a `oneOf` list of `$ref`s)
    - .planning/PROJECT.md (Constraints §Data no-outcome-leakage; §Trust human-override / explainable; §Safety)
    - .planning/REQUIREMENTS.md (BOS-DATA-02, line ~26 — the target requirement)
  </read_first>
  <action>
    Create `contracts/decision-ledger.schema.json` as a JSON Schema describing ONE decision ledger record, mirroring the structure of `contracts/events.schema.json` (a top-level object with a `$defs` block of named sub-schemas, a `discriminator` with `propertyName` + `mapping`, and a `oneOf` over the six payload `$ref`s). Use `decision_type` as the discriminator property (per D-02).

    Define a common envelope carried by every record (independent of decision_type), with these required fields, each named explicitly:
    - `decision_id` — stable unique id for this record; the join key BOS5 outcome labels attach to later (D-04).
    - `decision_type` — the discriminator enum, with exactly these six values and NO others (per D-02): `task_to_agent`, `autonomy_band`, `review_depth`, `validation_depth`, `escalation`, `no_action`.
    - `created_at` — record write timestamp.
    - `as_of` — the immutable point-in-time event-state pointer into the BOS3 event stream (D-01, D-03; D-07 upstream assumption). Shape it as a small object holding an event sequence number and/or snapshot id; in its `description` state plainly that BOS3 must expose a stable immutable as-of pointer and that this field's exact shape is reconciled when BOS3 lands.
    - `feature_snapshot` — a frozen copy of the exact feature vector used at decision time (D-03). Model it as an open key→value object (use `additionalProperties: true`) so it is self-contained and reproducible; in its `description` state it is captured at decision time and is immutable.
    - `entity_ref` — stable references to the entities the decision targets: task / session / agent / swarm assignment ids (D-08; D-07 upstream assumption). In its `description` state these are local entity-ref fields BOS3 must supply stable ids for, and cross-source identity resolution is deferred to BOS12.
    - `autonomy_band` — the autonomy band in effect for this decision (D-06). Model as a string/enum field with a `description` noting the concrete band values are governed by BOS6 governance.
    - `recommended_action` — what the system proposed (D-05). Model as an open object (`additionalProperties: true`) since action shape varies by decision_type.
    - `human_verdict` — an object with `verdict` (enum: exactly `approve`, `override`, `dismiss`, `do_nothing` — per D-05), `actor_id` (string), and `verdict_at` (timestamp). Per D-05 maximal auditability + the non-negotiable human-override governance constraint.
    - `actual_action` — what was actually taken (D-05). Open object, same modeling as recommended_action.
    - `rationale` — explainability field (Claude's discretion per CONTEXT, recommended). Model as a string or small structured object capturing why the recommendation was made, satisfying PROJECT.md §Trust "explainable recommendations".

    Then define the six typed payloads in `$defs`, one per `decision_type` value, each a small object with fields specific to that kind (your discretion on exact inner field names within D-02's closed type set):
    - `TaskToAgentPayload` — references the candidate/chosen agent for the task.
    - `AutonomyBandPayload` — the proposed/selected autonomy band.
    - `ReviewDepthPayload` — the proposed review depth level.
    - `ValidationDepthPayload` — the proposed validation depth level.
    - `EscalationPayload` — the escalation target / reason.
    - `NoActionPayload` — the no-action record (may be near-empty beyond a reason).

    CRITICAL no-leakage guard (D-04): the schema MUST NOT contain any `outcome`, `label`, `reward`, or `result-of-decision` field anywhere. The outcome is joined LATER by `decision_id` and is NEVER written into the record at decision time. Set `additionalProperties: false` on the envelope object (NOT on `feature_snapshot`/`recommended_action`/`actual_action`, which are intentionally open) so the no-outcome constraint is structurally enforced at the record level.

    The override-as-signal idea (D-06): do NOT add a derived field; instead, in the `human_verdict` or `actual_action` `description`, state plainly that the divergence between `recommended_action` and `actual_action` under a verdict is an explicit captured training signal (it is observable from the three action fields, documented not derived).

    Do NOT design the BOS3 event schema, outcome labels (BOS5), recommendation policies (BOS13/14), or cross-source identity (BOS12). The `as_of` and `entity_ref` fields are framed AS upstream BOS3 assumptions in their descriptions, not invented BOS3 schema.

    Output valid JSON only (no comments, no trailing commas) so `jq` parses it.
  </action>
  <verify>
    <automated>jq . contracts/decision-ledger.schema.json > /dev/null && echo PARSE_OK</automated>
  </verify>
  <acceptance_criteria>
    - `jq . contracts/decision-ledger.schema.json` exits 0 (valid JSON).
    - `jq -e '.properties.decision_type.enum // (.. | objects | select(has("propertyName")) | .mapping | keys)' contracts/decision-ledger.schema.json` resolves the six discriminator values; manually confirm the set is exactly `task_to_agent`, `autonomy_band`, `review_depth`, `validation_depth`, `escalation`, `no_action` and nothing else.
    - The file contains a `discriminator` object with `propertyName` set to `decision_type` (mirrors events.schema.json): `jq -e '.. | objects | select(.propertyName? == "decision_type")' contracts/decision-ledger.schema.json` exits 0.
    - A `oneOf` list of six `$ref`s exists (one per payload): `jq -e '[.. | objects | select(has("oneOf")) | .oneOf | length] | any(. == 6)' contracts/decision-ledger.schema.json` exits 0.
    - Record carries all three action fields: `grep -q '"recommended_action"' contracts/decision-ledger.schema.json && grep -q '"human_verdict"' contracts/decision-ledger.schema.json && grep -q '"actual_action"' contracts/decision-ledger.schema.json`.
    - `human_verdict` enumerates exactly approve/override/dismiss/do_nothing: confirm the four values present and no fifth verdict value.
    - Dual training-signal capture present: `grep -q '"as_of"' contracts/decision-ledger.schema.json && grep -q '"feature_snapshot"' contracts/decision-ledger.schema.json`.
    - `autonomy_band` field present: `grep -q '"autonomy_band"' contracts/decision-ledger.schema.json`.
    - No-leakage guard: the record defines NO outcome field — `grep -Eiq '"(outcome|label|reward)"[[:space:]]*:' contracts/decision-ledger.schema.json` returns NON-zero (no match). (Mentions inside `description` strings are acceptable; a property KEY named outcome/label/reward is not.)
    - Envelope object sets `additionalProperties: false`: `grep -q '"additionalProperties": false' contracts/decision-ledger.schema.json`.
  </acceptance_criteria>
  <done>
    `contracts/decision-ledger.schema.json` exists, is valid JSON, mirrors the events.schema.json discriminated-union pattern with a `decision_type` discriminator over exactly the six payloads, carries the as_of + feature_snapshot pair, the three action fields, human_verdict with the four-value enum, autonomy_band, and no outcome/label/reward property at the record level.
  </done>
</task>

</tasks>

<verification>
- `jq . contracts/decision-ledger.schema.json` exits 0.
- Six and only six decision_type values enumerated.
- as_of + feature_snapshot + recommended_action + human_verdict + actual_action + autonomy_band all present.
- No outcome/label/reward property key at record level.
</verification>

<success_criteria>
The authoritative decision ledger contract exists as a valid JSON Schema sibling to events.schema.json, structurally enforcing the locked CONTEXT decisions (D-01..D-06) and framing BOS3 event/entity references as upstream assumptions (D-07/D-08).
</success_criteria>

<output>
Create `.planning/phases/BOS4-decision-ledger-schema/BOS4-01-SUMMARY.md` when done.
</output>
