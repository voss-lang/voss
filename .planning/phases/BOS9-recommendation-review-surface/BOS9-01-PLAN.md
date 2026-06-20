---
phase: BOS9-recommendation-review-surface
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - contracts/recommendation-view.schema.json
autonomous: true
requirements:
  - BOS-REC-03
  - BOS-REC-01
  - BOS-REC-02

must_haves:
  truths:
    - "A reader can see ONE generic recommendation-view envelope schema that carries a TYPED reference to any BOS4 decision_type payload (task_to_agent/review_depth/validation_depth/escalation) rather than redefining or copying those payloads (D-01/D-02)"
    - "A reader can see the envelope adds only presentation-layer fields (display rationale, qualitative confidence band, policy version, autonomy band, available actions) on top of the typed payload ref (D-01/D-05)"
    - "A reader can see the confidence field is a QUALITATIVE enum (low/med/high + abstain) with NO numeric score field anywhere in the schema (D-05)"
    - "A reader can see the available-actions field enumerates exactly the four verdicts approve/override/dismiss/do-nothing and that acting writes a BOS4 human_verdict (referenced, not redefined) (D-03/D-04)"
    - "A reader can see the schema mirrors the contracts/events.schema.json discriminated-union style and is shaped to join the existing V13.1 contracts/openapi.json drift gate (BOS4 D-02 / BOS2 D-06)"
  artifacts:
    - path: "contracts/recommendation-view.schema.json"
      provides: "The BOS9 recommendation-view envelope JSON Schema (D-02): one shape, typed BOS4-payload ref, presentation-only fields, qualitative confidence, four-verdict action set — covers BOS-REC-03 contract substrate"
      contains: "decision_type"
  key_links:
    - from: "contracts/recommendation-view.schema.json envelope"
      to: "the four BOS4 decision_type payloads (task_to_agent/review_depth/validation_depth/escalation)"
      via: "a typed payload-ref discriminated on decision_type, not a copy of the payloads"
      pattern: "task_to_agent.*review_depth.*validation_depth.*escalation|decision_type"
    - from: "contracts/recommendation-view.schema.json confidence field"
      to: "the qualitative-only confidence rule (D-05)"
      via: "an enum of qualitative bands with no numeric score property"
      pattern: "low.*med.*high|abstain"
    - from: "contracts/recommendation-view.schema.json available_actions"
      to: "the four verdicts that write a BOS4 human_verdict (D-03/D-04)"
      via: "an enum approve/override/dismiss/do-nothing"
      pattern: "approve.*override.*dismiss.*do.?nothing|do_nothing"
---

<objective>
Produce the BOS9 recommendation-view envelope as a sibling JSON Schema under `contracts/`. This is the load-bearing D-01/D-02 contract substrate: ONE generic view envelope that wraps a typed reference to any of BOS4's four `decision_type` payloads (`task_to_agent` = delegation, `review_depth`, `validation_depth`, `escalation`) and adds ONLY presentation-layer fields — never redefining or copying the BOS4 payloads. Covers the contract spine of BOS-REC-03 and the schema-level shape of BOS-REC-01 (four-verdict action set) and BOS-REC-02 (rationale / qualitative confidence / policy version).

Purpose: The markdown spec (Plan 02) references this schema as the authoritative view contract. Producing the schema first gives the prose a real artifact to point at and matches the BOS-track "contract-before-prose" convention (cf. BOS4 ledger schema, BOS2 D-06 drift-gated contracts). It mirrors the `contracts/events.schema.json` discriminated-union style and is shaped to join the V13.1 `contracts/openapi.json` drift gate.

Output: `contracts/recommendation-view.schema.json` — the recommendation-view envelope JSON Schema. NO markdown spec here (that is Plan 02). NO code, NO UI, NO edits to BOS4's ledger schema, events.schema.json, or any voss/ or apps/ source.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/BOS9-recommendation-review-surface/BOS9-CONTEXT.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@contracts/events.schema.json
</context>

<notes>
- The eight LOCKED decisions D-01..D-08 in BOS9-CONTEXT.md are authoritative. This plan encodes the SCHEMA-expressible ones (D-01/D-02 envelope + typed ref; D-03/D-04 four-verdict action set + write-to-BOS4-verdict reference; D-05 qualitative confidence, no numeric score; D-06 no new telemetry field). The narrative/matrix/states (D-07/D-08) live in Plan 02's prose.
- VIEW-OVER-BOS4 is the load-bearing boundary: the envelope REFERENCES BOS4's `decision_type` payloads via a typed ref; it does NOT copy or redefine them. Do not duplicate any BOS4 payload field set into this schema. If the executor cannot locate a physical BOS4 ledger schema file under `contracts/`, treat BOS4's payloads as an upstream contract referenced by name (`decision_type` ∈ {task_to_agent, review_depth, validation_depth, escalation}) per BOS4-CONTEXT.md D-02 — reference the type, do not invent payload internals.
- NO numeric confidence anywhere (D-05): the schema must NOT contain a numeric confidence/score property. Confidence is a qualitative enum only.
- NO new telemetry/interaction-log object (D-06): the schema describes the view + its action set; it does NOT define a BOS9-owned interaction/telemetry record. Acting triggers a BOS4 `human_verdict` write (referenced).
- Mirror `contracts/events.schema.json` discriminated-union style (read it first) so the envelope is codegen/drift-gate friendly and joins `contracts/openapi.json` (V13.1).
- HARD INVARIANT (assert in every task acceptance): no edits to voss/, apps/, contracts/events.schema.json, contracts/openapi.json, or any BOS4 ledger schema. This plan ADDS one new file only.
- No fenced code blocks in `<action>` prose; the JSON Schema content itself is the deliverable file (written via the Write tool), which is correct.
</notes>

<tasks>

<task type="auto">
  <name>Task 1: Author the recommendation-view envelope JSON Schema (envelope + typed BOS4 payload ref + presentation fields)</name>
  <files>contracts/recommendation-view.schema.json</files>
  <read_first>
    - .planning/phases/BOS9-recommendation-review-surface/BOS9-CONTEXT.md (D-01 view-over-BOS4 + display-only fields; D-02 one generic envelope wrapping a typed payload ref; D-05 qualitative confidence)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md (D-02 the four decision_type payloads BOS9 references; D-05 recommended_action/human_verdict/actual_action field set)
    - contracts/events.schema.json (the discriminated-union JSON Schema style D-02 mirrors — match its $schema draft, $id convention, and discriminator/oneOf pattern)
  </read_first>
  <action>
    Create `contracts/recommendation-view.schema.json` as a JSON Schema (same draft/`$schema` and `$id` convention used by `contracts/events.schema.json`). Define ONE top-level object: the recommendation-view envelope (suggested title `RecommendationView`). It must contain:

    1. A `decision_type` discriminator string with the EXACT enum `["task_to_agent", "review_depth", "validation_depth", "escalation"]` (the four BOS4 payloads BOS9 views — delegation = `task_to_agent`). Do NOT include BOS4's `autonomy_band` or `no_action` as decision_types of the VIEW envelope (those are BOS4 ledger types; the view surfaces the four recommendation kinds named in BOS-REC-03).

    2. A typed REFERENCE to the underlying BOS4 decision payload — a single `payload_ref` property carrying the identifiers needed to resolve the BOS4 decision row (at minimum `decision_id`, plus an `as-of`/snapshot pointer reference per BOS4 D-03 if naming it as a ref). This is a REFERENCE into the BOS4 ledger, NOT a copy of the payload internals. Add a JSON Schema `description` on `payload_ref` stating it references the BOS4 `decision_type` payload and does not redefine it (D-01).

    3. Presentation-only fields layered on top (D-01/D-05): `rationale` (human-readable string, sourced from BOS4 — note in description), `policy_version` (string), `autonomy_band` (enum `["suggest_only", "approve_required", "auto_with_post_review", "full_auto"]`, the four BOS6 bands), and `confidence` as a QUALITATIVE enum `["low", "medium", "high", "abstain"]`. There MUST be NO numeric confidence/score property anywhere in the schema (D-05 anti-false-precision). Add a `description` on `confidence` stating it is qualitative-by-design, no numeric score.

    Use `oneOf` + the `decision_type` discriminator to mirror `events.schema.json` if that file uses that pattern; otherwise match whatever discriminated-union idiom that file uses. The ONE envelope shape must render all four recommendation types (D-02). Mark the structurally-required fields with a top-level `required` array.

    Ensure valid JSON (parseable). Do NOT edit any other file.
  </action>
  <verify>
    <automated>test -f contracts/recommendation-view.schema.json && node -e "JSON.parse(require('fs').readFileSync('contracts/recommendation-view.schema.json','utf8'))" && echo "valid JSON"</automated>
    <automated>S=contracts/recommendation-view.schema.json; for t in task_to_agent review_depth validation_depth escalation; do grep -q "$t" "$S" || { echo "MISSING decision_type: $t"; exit 1; }; done</automated>
    <automated>S=contracts/recommendation-view.schema.json; grep -q "decision_type" "$S" && grep -qi "payload_ref" "$S" && grep -qi "confidence" "$S" && grep -qi "policy_version" "$S" && grep -qi "autonomy_band" "$S"</automated>
    <automated>S=contracts/recommendation-view.schema.json; for b in suggest_only approve_required auto_with_post_review full_auto; do grep -q "$b" "$S" || { echo "MISSING band: $b"; exit 1; }; done</automated>
    <automated>S=contracts/recommendation-view.schema.json; grep -q '"low"' "$S" && grep -q '"high"' "$S" && grep -q '"abstain"' "$S"</automated>
    <automated>git diff --quiet voss/ apps/ contracts/events.schema.json contracts/openapi.json && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - `contracts/recommendation-view.schema.json` exists and is valid, parseable JSON.
    - Exactly one generic envelope is defined; `decision_type` enum is exactly the four BOS4 recommendation payloads task_to_agent / review_depth / validation_depth / escalation (D-02). BOS4 ledger-only types (autonomy_band, no_action) are NOT view decision_types.
    - The underlying BOS4 payload is carried by a typed `payload_ref` (reference into the BOS4 ledger via decision_id / as-of pointer), with a description stating it references-not-redefines the BOS4 payload (D-01) — no BOS4 payload internals are copied into this schema.
    - Presentation-only fields present: rationale, policy_version, autonomy_band (four BOS6 bands), confidence (qualitative enum low/medium/high/abstain). No numeric confidence/score property exists anywhere (D-05).
    - The schema uses the same discriminated-union idiom / `$schema` / `$id` convention as contracts/events.schema.json (D-02, codegen/drift-gate friendly).
    - `git diff --quiet voss/ apps/ contracts/events.schema.json contracts/openapi.json` (no edits to protected paths; only the new file added).
  </acceptance_criteria>
  <done>The recommendation-view envelope schema exists as valid JSON with one generic shape, the four-type discriminator, a typed BOS4 payload ref (not a copy), and presentation-only fields including qualitative-only confidence — encoding D-01/D-02/D-05.</done>
</task>

<task type="auto">
  <name>Task 2: Add the four-verdict action set + write-to-BOS4-verdict reference to the schema</name>
  <files>contracts/recommendation-view.schema.json</files>
  <read_first>
    - contracts/recommendation-view.schema.json (the envelope from Task 1 — extend it; do not rewrite the Task 1 fields)
    - .planning/phases/BOS9-recommendation-review-surface/BOS9-CONTEXT.md (D-03 each action writes a BOS4 human_verdict; D-04 four distinct verdict semantics accept/counter/decline/no-op; D-06 training signal owned by BOS4)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md (D-05 human_verdict ∈ {approve,override,dismiss,do-nothing} with actor+timestamp+actual_action; D-06 override-as-signal)
  </read_first>
  <action>
    Extend `contracts/recommendation-view.schema.json` (do not remove Task 1 fields). Add an `available_actions` property to the envelope: an array whose item values come from the EXACT four-verdict enum `["approve", "override", "dismiss", "do_nothing"]` (D-03/D-04). Add a `description` on `available_actions` stating that the set is constrained at render time by the autonomy band + kill-switch (the band→action matrix is specified in the BOS9 spec, Plan 02) and that selecting any action WRITES a BOS4 `human_verdict` record (actor id + timestamp + `actual_action`) — this is the training signal, owned by BOS4 (D-03/D-06). The schema must NOT define its own verdict/telemetry storage object (D-06): reference BOS4's `human_verdict`, do not redefine it.

    Encode the four distinct semantics (D-04) in per-value descriptions or an adjacent `$comment`/`description` block: `approve` = accept as-is (actual_action = recommended_action); `override` = counter / take a DIFFERENT action (actual_action ≠ recommended_action — the high-value learning signal); `dismiss` = decline/clear the recommendation without acting; `do_nothing` = affirmatively take no action. Make clear all four resolve to a BOS4 `actual_action`.

    Add a top-level `$comment` (or schema `description`) on the envelope stating: this is a VIEW over BOS4 (BOS-REC-03); it references BOS4 `decision_type` payloads and the BOS4 `human_verdict` record; it defines no parallel action store and no BOS9-owned telemetry/interaction log (D-01/D-03/D-06). Add a short reference to the requirement IDs covered (BOS-REC-01/02/03).

    Keep the file valid JSON. Do NOT edit any other file.
  </action>
  <verify>
    <automated>node -e "JSON.parse(require('fs').readFileSync('contracts/recommendation-view.schema.json','utf8'))" && echo "valid JSON"</automated>
    <automated>S=contracts/recommendation-view.schema.json; grep -qi "available_actions" "$S"; for v in approve override dismiss do_nothing; do grep -q "$v" "$S" || { echo "MISSING verdict: $v"; exit 1; }; done</automated>
    <automated>S=contracts/recommendation-view.schema.json; grep -qi "human_verdict" "$S" && grep -qi "actual_action" "$S"</automated>
    <automated>S=contracts/recommendation-view.schema.json; grep -Eqi "BOS4|decision ledger" "$S" && grep -Eqi "no.*(telemetry|interaction|parallel).*log|no.*(parallel|separate).*store|owned by BOS4" "$S"</automated>
    <automated>S=contracts/recommendation-view.schema.json; for r in BOS-REC-01 BOS-REC-02 BOS-REC-03; do grep -q "$r" "$S" || { echo "MISSING req: $r"; exit 1; }; done</automated>
    <automated>git diff --quiet voss/ apps/ contracts/events.schema.json contracts/openapi.json && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - `available_actions` exists with the exact four-verdict enum approve / override / dismiss / do_nothing (D-04).
    - A description ties action selection to writing a BOS4 `human_verdict` (actor+timestamp+actual_action) and states the action set is band/kill-switch constrained at render (D-03/D-07 boundary), referencing the Plan-02 matrix.
    - The four distinct semantics are documented (approve=accept-as-is / override=counter-different-action-the-signal / dismiss=decline-without-acting / do_nothing=affirmative-no-action), all resolving to a BOS4 actual_action (D-04/D-06).
    - The schema references BOS4 `human_verdict` and defines NO BOS9-owned parallel action store or telemetry/interaction log (D-03/D-06); a top-level comment states the view-over-BOS4 boundary.
    - The covered requirement IDs BOS-REC-01, BOS-REC-02, BOS-REC-03 appear in the schema.
    - File remains valid JSON; `git diff --quiet voss/ apps/ contracts/events.schema.json contracts/openapi.json` passes.
  </acceptance_criteria>
  <done>The schema carries the four-verdict action set referencing BOS4's human_verdict write-path with distinct accept/counter/decline/no-op semantics and no parallel store/telemetry — encoding D-03/D-04/D-06 and naming BOS-REC-01/02/03.</done>
</task>

</tasks>

<verification>
Phase-level checks (run after both tasks):
- `test -f contracts/recommendation-view.schema.json` and it parses as JSON.
- Four decision_types present: `task_to_agent`, `review_depth`, `validation_depth`, `escalation`.
- Four verdicts present: `approve`, `override`, `dismiss`, `do_nothing`.
- Four bands present: `suggest_only`, `approve_required`, `auto_with_post_review`, `full_auto`.
- Qualitative confidence enum present (`low`/`medium`/`high`/`abstain`); NO numeric confidence/score property.
- BOS4 references present (`human_verdict`, `actual_action`, decision ledger); no parallel store / no telemetry log.
- Requirement IDs BOS-REC-01/02/03 present.
- Protected paths untouched: `git diff --quiet voss/ apps/ contracts/events.schema.json contracts/openapi.json`.
</verification>

<success_criteria>
- `contracts/recommendation-view.schema.json` exists as the single new deliverable — one generic view envelope (D-02) referencing the four BOS4 decision_type payloads via a typed ref (D-01), never copying them.
- Presentation-only fields (rationale, policy_version, autonomy_band, qualitative confidence) and the four-verdict action set are present; no numeric confidence (D-05), no parallel action store / no telemetry log (D-03/D-06).
- The schema mirrors the events.schema.json discriminated-union style and is shaped to join the V13.1 drift gate.
- No edits to voss/, apps/, events.schema.json, openapi.json, or any BOS4 ledger schema.
</success_criteria>

<output>
Create `.planning/phases/BOS9-recommendation-review-surface/BOS9-01-SUMMARY.md` when done.
</output>
