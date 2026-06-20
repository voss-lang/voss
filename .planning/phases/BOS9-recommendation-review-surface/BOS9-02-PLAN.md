---
phase: BOS9-recommendation-review-surface
plan: 02
type: execute
wave: 2
depends_on:
  - BOS9-01
files_modified:
  - .planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md
autonomous: true
requirements:
  - BOS-REC-01
  - BOS-REC-02
  - BOS-REC-03

must_haves:
  truths:
    - "A reader can see the spec states the REC-03 output contract is a VIEW over BOS4 — it references the contracts/recommendation-view.schema.json envelope and BOS4's four decision_type payloads and adds display-only fields, redefining nothing (D-01/D-02)"
    - "A reader can see the four verdicts approve/override/dismiss/do-nothing enumerated with DISTINCT accept / counter / decline / no-op semantics, each writing a BOS4 human_verdict (actor+timestamp+actual_action), with override-as-signal called out (D-03/D-04)"
    - "A reader can see each recommendation MUST display rationale + policy version + autonomy band + a QUALITATIVE confidence band, and an explicit statement that confidence is qualitative not numeric (no score) (D-05)"
    - "A reader can see the spec states training-signal logging is owned by BOS4 (the verdict record IS the signal) and that BOS9 defines NO new telemetry/interaction log (D-06)"
    - "A reader can see a band -> action-availability matrix covering all four bands (suggest_only/approve_required/auto_with_post_review/full_auto) PLUS the kill-switch safe-state row, and a statement that human override is reversible even in full_auto (D-07/D-08)"
    - "A reader can see the named interaction states (review queue, empty, loading, stale/invalidated recommendation, post-kill-switch) and that the SINGLE contract renders to BOTH targets desktop=my-scope and web=team-scope (D-08, BOS7 D-03)"
    - "A reader can map BOS-REC-01 (four actions), BOS-REC-02 (rationale/confidence/policy-version/training-signal), and BOS-REC-03 (the four output contracts) to spec sections via a requirement-coverage section"
  artifacts:
    - path: ".planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md"
      provides: "The BOS9 recommendation review surface spec: view-over-BOS4 output contract, four-verdict action semantics, mandatory display + qualitative confidence, band->action matrix + kill-switch + reversibility, interaction states, dual-target rendering — covers BOS-REC-01/02/03"
      min_lines: 110
      contains: "Band"
  key_links:
    - from: "BOS9-REVIEW-SURFACE-SPEC.md output-contract section"
      to: "contracts/recommendation-view.schema.json + the four BOS4 decision_type payloads"
      via: "explicit reference to the envelope schema and BOS4 payloads, stating display-only-fields-no-duplication"
      pattern: "recommendation-view.schema.json|view envelope"
    - from: "BOS9-REVIEW-SURFACE-SPEC.md verdict section"
      to: "the BOS4 human_verdict write-path (D-03)"
      via: "each of the four verdicts persisting a BOS4 verdict record"
      pattern: "human_verdict|actual_action"
    - from: "BOS9-REVIEW-SURFACE-SPEC.md band->action matrix"
      to: "the four BOS6 autonomy bands + kill-switch (D-07)"
      via: "a matrix row per band plus a kill-switch safe-state row"
      pattern: "suggest_only.*approve_required.*auto_with_post_review.*full_auto|kill.?switch"
    - from: "BOS9-REVIEW-SURFACE-SPEC.md placement section"
      to: "the single-contract dual-target rule (BOS7 D-03 / D-08)"
      via: "desktop my-scope + web team-scope rendered from one contract"
      pattern: "my.?scope.*team.?scope|desktop.*web"
---

<objective>
Produce the BOS9 recommendation review surface spec — a single docs-first UI/contract specification that fully specifies how recommendations are reviewed and acted on, as a presentation + view-contract layer OVER BOS4 and honoring BOS6 governance + BOS7 dual-target placement. It references the Plan-01 view envelope schema and encodes: (a) the REC-03 view-over-BOS4 output contract for delegation / review-depth / validation-depth / escalation, (b) the four-verdict action model (approve/override/dismiss/do-nothing) and its write-back into the BOS4 ledger, (c) mandatory display fields + qualitative-only confidence + the training-signal-owned-by-BOS4 boundary, and (d) the band -> action-availability matrix + kill-switch + always-reversible override + interaction states + single-contract dual-target rendering. Covers BOS-REC-01, BOS-REC-02, BOS-REC-03.

Purpose: This spec is the contract+UX inherited by the future desktop Review tab (my-scope) and web team queue (team-scope), which both render the SINGLE contract per BOS7 D-03. It fixes the surface fully before any implementation so the build phase has no contract to re-litigate, and it states the anti-nudge / view-over-BOS4 guardrails as constraints. Decisions + spec only — NO code, NO UI build, NO edits to voss/, apps/, the BOS4 ledger schema, or PROTOCOL.md.

Output: `.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md`
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
@.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md
@.planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md
@contracts/recommendation-view.schema.json
</context>

<notes>
- The eight LOCKED decisions D-01..D-08 in BOS9-CONTEXT.md are the spine. EXPRESS them; do not re-decide. Requirement mapping (from CONTEXT): BOS-REC-01 ← D-03/D-04/D-07; BOS-REC-02 ← D-05/D-06; BOS-REC-03 ← D-01/D-02.
- VIEW-OVER-BOS4 is load-bearing: the spec REFERENCES the Plan-01 envelope schema + BOS4 payloads + BOS4 human_verdict; it does NOT redefine the ledger, the payloads, or the verdict record. State this boundary explicitly (D-01/D-03/D-06).
- ANTI-NUDGE / ANTI-FALSE-PRECISION are CONSTRAINTS not defaults: confidence is qualitative, no numeric score (D-05); no BOS9 telemetry/interaction log (D-06, BOS6 no-nudge ban). Frame them as constraints traceable to BOS6.
- Reversibility reconciliation (D-08): "human override always-reversible even in full_auto" is the explicit reconciliation of BOS6 override-always with auto bands — full_auto must NOT read as irreversible.
- Dual-target (BOS7 D-03 / D-08): ONE contract renders to desktop=my-scope (own recommendations) and web=team-scope (team queue), no logic duplication. BOS9 specs the contract both render; it does not build either app.
- BOS5 outcome labels are joined by decision_id AFTER the fact and are NOT a pre-action signal on this surface (no-leakage) — keep them out of the displayed pre-action fields.
- Bulk/batch team-queue verdicts: lean default single-item; note as a candidate, do NOT pre-design (CONTEXT discretion).
- The actual desktop Review tab / web team queue builds are DEFERRED to a future implementation phase — do not specify implementation, only the contract + UX.
- HARD INVARIANT (assert in every task acceptance): no edits to voss/, apps/, contracts/ schemas, or PROTOCOL.md. This plan writes ONE markdown file in the phase dir.
- No fenced code blocks in `<action>` prose. A JSON-Schema excerpt INSIDE the deliverable markdown is acceptable if the executor wants to illustrate the referenced envelope, but the authoritative schema is the Plan-01 file — reference it, do not re-author it.
</notes>

<tasks>

<task type="auto">
  <name>Task 1: Write the output-contract (view-over-BOS4) + verdict-action-semantics + display/confidence sections</name>
  <files>.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md</files>
  <read_first>
    - .planning/phases/BOS9-recommendation-review-surface/BOS9-CONTEXT.md (D-01/D-02 view-over-BOS4 envelope; D-03/D-04 four-verdict write-back + distinct semantics; D-05 mandatory display + qualitative confidence; D-06 training signal owned by BOS4)
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md (D-02 four decision_type payloads; D-05 recommended_action/human_verdict/actual_action; D-06 override-as-signal)
    - contracts/recommendation-view.schema.json (the Plan-01 envelope this spec references as the authoritative output contract)
    - .planning/REQUIREMENTS.md (lines 43-45 — BOS-REC-01/02/03 wording)
  </read_first>
  <action>
    Create `.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md`. Start with a title (`# BOS9: Recommendation Review Surface Spec`), a one-line statement that this is the BOS-REC-01..03 UI/contract spec and is a VIEW over BOS4 (system of record stays BOS4), and a short "How to read this" note (this PLACES the surface contract + UX; it does not build the desktop/web apps, which are deferred).

    Then write these three sections:

    1. `## Output Contract (View over BOS4)` — encode D-01/D-02. State that the output contract is the single generic recommendation-view envelope defined in `contracts/recommendation-view.schema.json` (reference the file by name), which carries a TYPED reference to one of BOS4's four `decision_type` payloads — `task_to_agent` (delegation), `review_depth`, `validation_depth`, `escalation` — and adds ONLY presentation-layer fields. State explicitly: no payload duplication, no ledger redefinition; one envelope shape renders all four recommendation types (mirrors BOS4's discriminated union). Name the rejected alternatives from D-01/D-02 (new standalone contract = drift risk; per-type view contracts = 4 shapes to maintain).

    2. `## Verdict Action Semantics` — encode D-03/D-04. State that the surface offers four verdicts and each one WRITES a BOS4 `human_verdict` record (actor id + timestamp + `actual_action`) — the surface is a write-path INTO the BOS4 ledger, not a parallel store. Then enumerate the four with DISTINCT semantics: `approve` = accept as-is (actual_action = recommended_action); `override` = counter / take a DIFFERENT action (actual_action ≠ recommended_action — call out that this divergence is the high-value learning signal, BOS4 D-06 override-as-signal); `dismiss` = decline/clear the recommendation without acting now; `do-nothing` = affirmatively choose no action (esp. for no_action recommendations). State all four set actual_action and that dismiss vs do-nothing are kept distinct on purpose to preserve signal.

    3. `## Display & Confidence` — encode D-05/D-06. State each recommendation MUST display: rationale (from BOS4), policy version, current autonomy band, and a QUALITATIVE confidence band (low / medium / high, with optional abstain). State as a CONSTRAINT (traceable to BOS6): confidence is qualitative — there is NO numeric confidence score (anti-false-precision, anti-nudge). Then state the training-signal boundary: the training signal IS the BOS4 verdict record (frozen feature snapshot + override-as-signal, BOS4 D-03/D-06); BOS9 only TRIGGERS that write and defines NO new telemetry/interaction log (BOS6 no-nudge ban). Note that BOS5 outcome labels join by decision_id after the fact and are NOT shown as a pre-action signal (no-leakage).

    Do NOT touch voss/, apps/, contracts/ schemas, or PROTOCOL.md.
  </action>
  <verify>
    <automated>test -f .planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -q "## Output Contract" "$SP" && grep -q "## Verdict Action Semantics" "$SP" && grep -q "## Display" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -q "recommendation-view.schema.json" "$SP"; for t in task_to_agent review_depth validation_depth escalation; do grep -q "$t" "$SP" || { echo "MISSING payload: $t"; exit 1; }; done</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; for v in approve override dismiss; do grep -qi "$v" "$SP" || { echo "MISSING verdict: $v"; exit 1; }; done; grep -Eqi "do.?nothing" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -qi "human_verdict" "$SP" && grep -qi "actual_action" "$SP" && grep -Eqi "override.?as.?signal|learning signal|high.value" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -Eqi "qualitative" "$SP" && grep -Eqi "no numeric|not numeric|no.*score" "$SP" && grep -qi "rationale" "$SP" && grep -qi "policy version" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -Eqi "no.*(new|bos9).*(telemetry|interaction).*log|owned by BOS4|signal IS the BOS4" "$SP"</automated>
    <automated>git diff --quiet voss/ apps/ contracts/ .planning/PROTOCOL.md && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - The spec file exists with `## Output Contract (View over BOS4)`, `## Verdict Action Semantics`, and `## Display & Confidence` sections.
    - Output Contract references `contracts/recommendation-view.schema.json` and the four BOS4 payloads (task_to_agent/review_depth/validation_depth/escalation), states display-only-fields / no-duplication / one-envelope-renders-all-four, and names the rejected alternatives (D-01/D-02).
    - Verdict section enumerates approve/override/dismiss/do-nothing with the four DISTINCT semantics, states each writes a BOS4 human_verdict (actor+timestamp+actual_action), and calls out override-as-signal (D-03/D-04).
    - Display section lists mandatory rationale + policy version + autonomy band + qualitative confidence, states confidence is qualitative-with-NO-numeric-score as a constraint, and states training-signal is owned by BOS4 with NO new BOS9 telemetry/interaction log (D-05/D-06).
    - `git diff --quiet voss/ apps/ contracts/ .planning/PROTOCOL.md` passes (no edits to protected paths).
  </acceptance_criteria>
  <done>The output-contract (view-over-BOS4), verdict-action-semantics, and display/confidence sections exist in the spec encoding D-01..D-06 with the view-over-BOS4 boundary and anti-nudge constraints stated, and pass all grep checks.</done>
</task>

<task type="auto">
  <name>Task 2: Write the band->action matrix + kill-switch + reversibility + interaction states + dual-target placement + requirement coverage</name>
  <files>.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md</files>
  <read_first>
    - .planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md (the sections from Task 1 — append below; do not rewrite them)
    - .planning/phases/BOS9-recommendation-review-surface/BOS9-CONTEXT.md (D-07 band drives action set + kill-switch safe-state; D-08 always-reversible override + interaction states + dual-target)
    - .planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md (D-01 four bands; D-02 global + per-surface kill-switch; D-03 override always)
    - .planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md (D-03 single output contract renders desktop my-scope + web team-scope, no logic duplication)
    - .planning/REQUIREMENTS.md (lines 43-45 — BOS-REC-01/02/03 wording for the coverage section)
  </read_first>
  <action>
    Append these sections to BOS9-REVIEW-SURFACE-SPEC.md (below Task 1; do not edit Task 1 sections):

    1. `## Autonomy Band -> Action Availability` — a markdown matrix mapping each of the four BOS6 bands to the available action set, encoding D-07 exactly: `suggest_only` = view-only (no write action); `approve_required` = approve / override / dismiss / do-nothing all active; `auto_with_post_review` = already-applied + an override/undo window; `full_auto` = log-only / audit view. Add a kill-switch row: the global + per-surface kill-switch (BOS6 D-02) forces ALL affected recommendations to a safe state (suggest_only / off). Name the rejected alternative (show-band-but-all-actions-always-enabled).

    2. `## Override Is Always Reversible` — encode D-08's reconciliation: even an auto-applied recommendation (auto_with_post_review or full_auto) keeps a post-hoc override/flag path, and that post-hoc override writes an override verdict = signal (BOS4 D-06). State explicitly that full_auto does NOT mean irreversible — this satisfies BOS6 "human override always" (BOS6 D-03).

    3. `## Interaction States` — enumerate the named states from D-08: review queue, empty, loading, stale/invalidated recommendation, and post-kill-switch. For each, give a one-line description of what the surface shows. State that stale-invalidation deeper mechanics are deferred to implementation (named here as a state only). You MAY add further states at discretion (within D-08).

    4. `## Surface Placement (Dual-Target)` — encode D-08 + BOS7 D-03: the SAME single output contract renders to BOTH targets — desktop = my-scope (the user's OWN recommendations / V24 Review tab) and web = team-scope (the team recommendation queue) — with NO logic duplication. State BOS9 specs the contract both targets render; building the apps is deferred. Note bulk/batch team-queue verdicts as a single-item-default candidate, not pre-designed (CONTEXT discretion).

    5. `## Requirement Coverage` — a short mapping: BOS-REC-01 (four actions) -> Verdict Action Semantics + band->action matrix (D-03/D-04/D-07); BOS-REC-02 (rationale/confidence/policy-version/training-signal logging) -> Display & Confidence (D-05/D-06); BOS-REC-03 (output contracts for delegation/review-depth/validation-depth/escalation) -> Output Contract + the Plan-01 envelope schema (D-01/D-02). The three IDs BOS-REC-01/02/03 must appear literally.

    Then confirm the completed doc passes the structural checks below (all sections present, >=110 non-blank lines, all eight decisions traceable, protected paths untouched).

    Do NOT touch voss/, apps/, contracts/ schemas, or PROTOCOL.md.
  </action>
  <verify>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -q "## Autonomy Band" "$SP" && grep -Eqi "## Override Is Always Reversible|## Override.*Reversible" "$SP" && grep -q "## Interaction States" "$SP" && grep -Eqi "## Surface Placement" "$SP" && grep -q "## Requirement Coverage" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; for b in suggest_only approve_required auto_with_post_review full_auto; do grep -q "$b" "$SP" || { echo "MISSING band: $b"; exit 1; }; done; grep -Eqi "kill.?switch" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -Eqi "reversible" "$SP" && grep -Eqi "full_auto" "$SP" && grep -Eqi "post.?hoc|undo|override window" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; for s in queue empty loading stale "kill"; do grep -qi "$s" "$SP" || { echo "MISSING state: $s"; exit 1; }; done</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; grep -Eqi "my.?scope" "$SP" && grep -Eqi "team.?scope|team queue" "$SP" && grep -Eqi "single.*contract|same.*contract|one.*contract" "$SP" && grep -Eqi "no.*(logic )?duplicat" "$SP"</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; for r in BOS-REC-01 BOS-REC-02 BOS-REC-03; do grep -q "$r" "$SP" || { echo "MISSING req: $r"; exit 1; }; done</automated>
    <automated>SP=.planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md; lines=$(grep -vc '^[[:space:]]*$' "$SP"); [ "$lines" -ge 110 ] || { echo "doc too short: $lines non-blank lines (<110)"; exit 1; }</automated>
    <automated>git diff --quiet voss/ apps/ contracts/ .planning/PROTOCOL.md && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - Doc contains `## Autonomy Band -> Action Availability`, `## Override Is Always Reversible`, `## Interaction States`, `## Surface Placement (Dual-Target)`, and `## Requirement Coverage` sections.
    - The band->action matrix covers all four bands with the exact D-07 action sets (suggest_only=view-only / approve_required=all-four / auto_with_post_review=applied+override-window / full_auto=log-only) PLUS a kill-switch safe-state row (BOS6 D-02), and names the rejected alternative.
    - Reversibility section states full_auto is NOT irreversible — post-hoc override path writes an override verdict = signal, satisfying BOS6 override-always (D-08/BOS6 D-03).
    - Interaction States enumerates review queue / empty / loading / stale-invalidated / post-kill-switch (D-08), with stale-mechanics deferred to implementation.
    - Placement section states the SINGLE contract renders to desktop my-scope + web team-scope with no logic duplication (D-08/BOS7 D-03), apps deferred, bulk/batch noted as single-item-default candidate.
    - Requirement Coverage maps BOS-REC-01/02/03 to sections; all three IDs appear literally; doc is >=110 non-blank lines.
    - `git diff --quiet voss/ apps/ contracts/ .planning/PROTOCOL.md` passes.
  </acceptance_criteria>
  <done>The band->action matrix, reversibility, interaction-states, dual-target placement, and requirement-coverage sections are appended encoding D-07/D-08 (+ BOS6/BOS7 ties); the completed spec passes structural verification (all sections, >=110 non-blank lines, BOS-REC-01/02/03 present, protected paths untouched).</done>
</task>

</tasks>

<verification>
Phase-level checks (run after both tasks):
- `test -f .planning/phases/BOS9-recommendation-review-surface/BOS9-REVIEW-SURFACE-SPEC.md`.
- Output contract references the Plan-01 envelope schema + the four BOS4 payloads, states view-over-BOS4 / no duplication.
- Four verdicts present with distinct semantics + BOS4 human_verdict write-back + override-as-signal.
- Qualitative confidence + explicit no-numeric-score; training signal owned by BOS4, no new telemetry log.
- Band->action matrix covers all four bands + kill-switch safe-state row; override reversible in full_auto.
- Interaction states (queue/empty/loading/stale/post-kill-switch) present; dual-target my-scope + team-scope single contract, no duplication.
- BOS-REC-01/02/03 present; doc >=110 non-blank lines.
- Protected paths untouched: `git diff --quiet voss/ apps/ contracts/ .planning/PROTOCOL.md`.
</verification>

<success_criteria>
- BOS9-REVIEW-SURFACE-SPEC.md exists in the phase directory as the single prose deliverable for BOS-REC-01/02/03.
- The spec is a VIEW over BOS4: references the Plan-01 envelope + BOS4 payloads + BOS4 human_verdict; redefines no ledger, payload, or verdict record (D-01/D-03/D-06).
- All eight locked decisions are traceable: D-01/D-02 (output contract), D-03/D-04 (verdict semantics), D-05 (display + qualitative confidence), D-06 (training-signal-owned-by-BOS4), D-07 (band->action matrix + kill-switch), D-08 (reversibility + interaction states + dual-target).
- Anti-nudge / anti-false-precision constraints (no numeric confidence, no BOS9 telemetry log) are stated as constraints traceable to BOS6.
- No edits to voss/, apps/, contracts/ schemas, or PROTOCOL.md.
</success_criteria>

<output>
Create `.planning/phases/BOS9-recommendation-review-surface/BOS9-02-SUMMARY.md` when done.
</output>
