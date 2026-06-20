---
phase: BOS4-decision-ledger-schema
plan: 02
status: done
artifact: .planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md
requirements: [BOS-DATA-02]
---

# BOS4-02 Summary

## What shipped

`BOS4-DECISION-LEDGER.md` — the human-readable rationale record for the decision ledger contract. The schema (`contracts/decision-ledger.schema.json`, BOS4-01) is the machine-readable contract; this doc is the WHY.

## Sections (all required headings present verbatim)

- **Intro** — names BOS-DATA-02 as the requirement covered; states `contracts/decision-ledger.schema.json` is the authoritative contract form per BOS2 D-06.
- **Model: Separate Append-Only Ledger (D-01)** — decision ≠ event; mutable verdict state must not enter the immutable event log; each record carries an as-of pointer into BOS3.
- **Decision Types: Unified Record + Discriminator (D-02)** — one record + `decision_type` discriminator over the six closed kinds; mirrors `events.schema.json` for codegen consistency.
- **Training-Signal Capture (D-03)** — belt-and-suspenders: `as_of` pointer + frozen `feature_snapshot`; every record is a self-contained reproducible training row.
- **No-Leakage Guard (D-04)** — outcome joined LATER by `decision_id`, NEVER written at decision time; enforced structurally by `additionalProperties: false` + absence of any outcome/label/reward key.
- **Action Fields and Override-as-Signal (D-05, D-06)** — three explicit fields; `human_verdict` enum approve/override/dismiss/do_nothing; divergence between recommended and actual is an explicit captured signal, observable not derived; `autonomy_band` field present, concrete values governed by BOS6.
- **`## Upstream Assumptions (BOS3)`** — D-07 (stable immutable as-of pointer) and D-08 (stable entity IDs) framed as dependencies BOS3 must satisfy, not an invented BOS3 schema; cross-source identity deferred to BOS12.
- **`## Rejected Alternatives`** — (a) decision-as-BOS3-event (rejected D-01), (b) inline outcome label (rejected D-04), (c) per-type schemas instead of unified discriminator (rejected D-02).
- **`## Open Questions`** — ledger correction/amendment policy beyond append-only surfaced as undecided; candidate mechanisms listed as examples for a future phase, NOT prescribed.
- **Out of Scope** — BOS3 event schema, BOS5 outcome labels/rewards, BOS13/14 policies, BOS12 identity, BOS15 offline-eval all named as deferred/downstream.

## Verification (all green)

- File exists.
- Verbatim headings present: `## Upstream Assumptions (BOS3)`, `## Rejected Alternatives`, `## Open Questions`.
- References `contracts/decision-ledger.schema.json` and `BOS-DATA-02`.
- `decision_id` present (no-leakage join stated).
- All six decision_type values appear.
- Three action fields appear (`recommended_action`, `human_verdict`, `actual_action`).
- Amendment policy flagged as open, not decided.

## Downstream impact

- BOS3 reconciles `as_of` (D-07) and stable entity IDs (D-08) against this doc.
- BOS5 joins outcome labels by `decision_id` per the no-leakage rule recorded here.
- BOS13/14 producers write rows conforming to the contract described here.
- BOS15 consumers read the training-signal capture model documented here.
- A future phase must decide the ledger correction/amendment policy flagged in Open Questions.