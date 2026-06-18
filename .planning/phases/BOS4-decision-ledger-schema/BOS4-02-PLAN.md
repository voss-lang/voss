---
phase: BOS4-decision-ledger-schema
plan: 02
type: execute
wave: 2
depends_on:
  - BOS4-01
files_modified:
  - .planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md
autonomous: true
requirements:
  - BOS-DATA-02
must_haves:
  truths:
    - "A prose decision doc records the ledger model, rationale, and rejected alternatives"
    - "The doc explicitly flags BOS3 event-ref + entity-ref fields as upstream assumptions, not invented BOS3 schema"
    - "The doc documents the no-leakage guard (outcome joined later by decision_id) as a hard rule"
    - "The doc documents the override-as-signal training capture explicitly"
    - "The doc surfaces the undecided ledger correction/amendment policy as an open question, not a decided policy"
  artifacts:
    - path: ".planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md"
      provides: "Prose rationale + rejected-alternatives + upstream-assumptions doc for the decision ledger contract"
      contains: "## Upstream Assumptions (BOS3)"
  key_links:
    - from: ".planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md"
      to: "contracts/decision-ledger.schema.json"
      via: "doc references the authoritative schema as the contract form"
      pattern: "decision-ledger.schema.json"
---

<objective>
Produce the prose decision doc `BOS4-DECISION-LEDGER.md` that records the rationale behind the decision ledger contract authored in BOS4-01: the model (separate append-only ledger vs. BOS3 event), the six-type discriminated-union design, the dual as-of/frozen-snapshot training-signal capture, the no-leakage guard, the three action fields + override-as-signal, the autonomy_band, the rejected alternatives, the upstream BOS3 assumptions, and the ONE explicitly undecided item (ledger correction/amendment policy) surfaced as an open question.

Purpose: The schema is the machine-readable contract; this doc is the human-readable record of WHY — rationale, rejected alternatives, and the upstream dependencies BOS3 must reconcile against. Downstream phases (BOS3 reconcile, BOS5 join, BOS13/14 producers, BOS15 consumers) read it to understand the contract's intent and constraints.

Output: `.planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md
@contracts/decision-ledger.schema.json
@contracts/events.schema.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the decision ledger rationale doc</name>
  <files>.planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md</files>
  <read_first>
    - .planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md (locked decisions D-01..D-08, the deferred items, and the explicitly-undecided amendment policy — authoritative input)
    - contracts/decision-ledger.schema.json (the schema authored in BOS4-01 — the doc must describe and reference THIS as the authoritative contract form; do not contradict it)
    - .planning/PROJECT.md (Constraints §Data no-outcome-leakage; §Trust human-override / no individual ranking / explainable; §Safety)
    - contracts/events.schema.json (the sibling discriminated-union pattern the ledger mirrors — reference for the "consistent with the runtime/event schemas" rationale)
  </read_first>
  <action>
    Write `.planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md` as a prose decision doc with at minimum these sections (exact wording/structure is your discretion, but every named heading below MUST appear verbatim where called out):

    - An intro stating the authoritative contract form is `contracts/decision-ledger.schema.json` (per BOS2 D-06), and this doc is the rationale record. Name the requirement covered: BOS-DATA-02.
    - **The Model** — the ledger is a SEPARATE append-only ledger entry, NOT a BOS3 event (D-01); a decision = recommendation + human verdict (mutable verdict state) which is semantically distinct from an immutable observed fact, so conflating them would mix verdict state into the event log. Each record carries a point-in-time as-of reference into the BOS3 event stream.
    - **Decision Types** — the unified record + `decision_type` discriminator over the six closed, fully-specified kinds: `task_to_agent`, `autonomy_band`, `review_depth`, `validation_depth`, `escalation`, `no_action` (D-02). Note it mirrors the events.schema.json discriminated-union style for codegen consistency.
    - **Training-Signal Capture** — the belt-and-suspenders dual capture (D-03): the immutable as-of event-state pointer AND a frozen copy of the exact feature vector used at decision time, making each record a self-contained reproducible training row.
    - A section documenting the no-leakage guard (D-04): the outcome label (BOS5) is joined LATER by `decision_id` and is NEVER a field on the decision record at decision time. State this is the hard PROJECT.md §Data no-leakage rule and that the schema enforces it by ABSENCE of any outcome/label/reward field plus `additionalProperties: false` at the record envelope.
    - **Action Fields** — the three explicit fields recommended_action / human_verdict (enum approve / override / dismiss / do_nothing, with actor id + timestamp) / actual_action (D-05), honoring the non-negotiable human-override governance constraint. Document the override-as-signal explicitly (D-06): the divergence between recommended_action and actual_action under a human verdict is an explicit captured training signal — observable from the three fields, documented not derived. Note the `autonomy_band` field and that concrete band values are governed by BOS6.
    - **## Upstream Assumptions (BOS3)** — this heading MUST appear verbatim. Document D-07 (BOS3 must expose a stable immutable as-of pointer — event sequence or snapshot id — that the ledger's `as_of` field references; if BOS3 lands a different correctness mechanism, BOS4's reference field is reconciled then) and D-08 (BOS3 must define stable entity ids for task/session/agent/swarm assignment that the ledger's `entity_ref` references; cross-source identity resolution is deferred to BOS12 / BOS-INT-03 — BOS4 locks only the local entity-ref field shape). Frame these clearly as upstream dependencies BOS3 must satisfy, NOT as an invented BOS3 schema.
    - **## Rejected Alternatives** — this heading MUST appear verbatim. Record the rejected designs implied by the CONTEXT decisions, including at minimum: (a) making the decision a BOS3 event rather than a separate ledger (rejected per D-01 — would mix mutable verdict state into the immutable event log); (b) writing the outcome label inline on the record at decision time (rejected per D-04 — leakage); (c) a per-type record schema instead of a unified discriminated record (rejected per D-02 — the type set is closed/known so one record + discriminator is cleaner and codegen-consistent with events.schema.json).
    - **## Open Questions** — this heading MUST appear verbatim. Surface the ONE explicitly undecided item from CONTEXT: the ledger correction/amendment policy beyond append-only (e.g. how a mistaken verdict is corrected). State it is NOT decided this phase and flag it for a follow-up — do NOT invent or recommend a specific amendment mechanism.

    Respect CONTEXT deferred items: do NOT design the BOS3 event schema, outcome labels/rewards (BOS5), the recommendation-producing policies (BOS13/14), cross-source identity resolution (BOS12), or offline-eval consumption (BOS15). Where relevant, name them as out-of-scope / downstream.

    The doc must not contradict `contracts/decision-ledger.schema.json`; describe the field names as they exist in that file.
  </action>
  <verify>
    <automated>test -f .planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md && grep -q '^## Upstream Assumptions (BOS3)' .planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md && grep -q '^## Rejected Alternatives' .planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md && grep -q '^## Open Questions' .planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md && echo SECTIONS_OK