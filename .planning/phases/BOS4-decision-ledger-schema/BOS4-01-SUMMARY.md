---
phase: BOS4-decision-ledger-schema
plan: 01
status: done
artifact: contracts/decision-ledger.schema.json
requirements: [BOS-DATA-02]
---

# BOS4-01 Summary

## What shipped

`contracts/decision-ledger.schema.json` — authoritative JSON Schema for a single append-only decision ledger record, sibling to `contracts/events.schema.json`.

## How it satisfies the plan

Mirrors the existing `events.schema.json` discriminated-union pattern: a top-level object with a `$defs` block of six named payload sub-schemas, a `discriminator` on `decision_type` with a `mapping`, and a `oneOf` over the six typed payload `$ref`s.

Common envelope (independent of `decision_type`), each required:
- `decision_id` — join key for BOS5 outcome labels (D-04).
- `decision_type` — discriminator enum, exactly six values: `task_to_agent`, `autonomy_band`, `review_depth`, `validation_depth`, `escalation`, `no_action` (D-02).
- `created_at` — record write timestamp.
- `as_of` — immutable point-in-time event-state pointer into the BOS3 event stream (D-01, D-03). Documented as upstream assumption D-07; shape reconciled when BOS3 lands.
- `feature_snapshot` — frozen copy of the exact feature vector at decision time (D-03); open object (`additionalProperties: true`).
- `entity_ref` — task/session/agent/swarm ids (D-08); documented as upstream assumption D-07, cross-source identity deferred to BOS12.
- `autonomy_band` — autonomy band in effect (D-06); concrete values governed by BOS6.
- `recommended_action` — what the system proposed (D-05); open object.
- `human_verdict` — `{verdict, actor_id, verdict_at}` with `verdict` enum exactly `approve`/`override`/`dismiss`/`do_nothing` (D-05); `additionalProperties: false`.
- `actual_action` — what was actually taken (D-05); open object.
- `rationale` — explainability string (PROJECT.md §Trust).
- `payload` — typed payload via the discriminated union.

Six typed payloads in `$defs`:
- `TaskToAgentPayload` — candidate/chosen agent + task id.
- `AutonomyBandPayload` — proposed band, current band, reason.
- `ReviewDepthPayload` — proposed depth, target ref, reason.
- `ValidationDepthPayload` — proposed depth, target ref, reason.
- `EscalationPayload` — escalation target, reason, source ref.
- `NoActionPayload` — near-empty, just reason.

## No-leakage guard (D-04)

The envelope object sets `additionalProperties: false`, structurally preventing any `outcome`/`label`/`reward` property key at the record level. No such key exists in the schema. The outcome label is joined LATER by `decision_id` (BOS5) and is NEVER written into the record at decision time.

## Override-as-signal (D-06)

Not modeled as a derived field. Documented in the `human_verdict` and `actual_action` descriptions: the divergence between `recommended_action` and `actual_action` under a verdict is an explicit captured training signal, observable from the three action fields.

## Upstream assumptions framed, not invented

`as_of` and `entity_ref` descriptions state plainly that BOS3 must expose a stable immutable as-of pointer and stable entity IDs (D-07), and that cross-source identity resolution is deferred to BOS12. BOS3 event schema, BOS5 outcome labels, BOS13/14 policies, and BOS12 identity are NOT designed here.

## Verification (all green)

- `jq .` exits 0 (valid JSON).
- Six and only six `decision_type` values enumerated (mapping keys and enum match).
- `discriminator.propertyName == "decision_type"`.
- `oneOf` length == 6.
- `recommended_action`, `human_verdict`, `actual_action` all present.
- `human_verdict.verdict.enum` == exactly approve/override/dismiss/do_nothing.
- `as_of` + `feature_snapshot` present (dual training-signal capture).
- `autonomy_band` present.
- No `outcome`/`label`/`reward` property key at record level (no-leakage guard).
- Envelope `additionalProperties: false`.

## Downstream impact

- BOS13/BOS14 recommendation engine writes these rows.
- BOS5 outcome labels join by `decision_id`.
- BOS15 offline-eval consumes decision rows as self-contained reproducible training rows.
- BOS3 must reconcile `as_of` pointer shape and stable entity IDs (D-07/D-08).
- BOS6 governs concrete `autonomy_band` values.
- BOS12 handles cross-source identity resolution.