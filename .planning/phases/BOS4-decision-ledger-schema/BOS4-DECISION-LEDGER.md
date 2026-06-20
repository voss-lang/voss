# BOS4: Decision Ledger — Rationale Record

**Phase:** BOS4-decision-ledger-schema
**Requirement covered:** BOS-DATA-02
**Authoritative contract:** `contracts/decision-ledger.schema.json` (per BOS2 D-06, sibling JSON Schema under `contracts/` feeding the existing CI drift gate, extending the V13.1 artifact).

This document is the human-readable record of **why** the decision ledger contract is shaped as it is. The schema is the machine-readable contract; this doc is the rationale, rejected alternatives, and upstream dependencies. Downstream phases — BOS3 reconcile, BOS5 outcome join, BOS13/14 recommendation producers, BOS15 offline-eval consumers — read it to understand the contract's intent and constraints.

It records the locked decisions D-01..D-08 from `BOS4-CONTEXT.md` and the one explicitly undecided item (ledger correction/amendment policy) surfaced as an open question.

## Model: Separate Append-Only Ledger (D-01)

The decision ledger is a **separate append-only ledger**, NOT a BOS3 event. A decision = a recommendation + a human verdict; the verdict is mutable state, which is semantically distinct from an immutable observed engineering fact. Conflating decisions with events would mix mutable verdict state into the BOS3 event log, violating the immutability invariant that gives the event stream its point-in-time-correctness guarantees.

Each decision record carries a **point-in-time as-of reference** (`as_of` field) into the BOS3 event stream identifying the event state the recommendation was made against. The record lives in its own store; the event log remains untouched.

## Decision Types: Unified Record + Discriminator (D-02)

One ledger record schema with a `decision_type` discriminator and a typed payload per kind. The decision set is closed and known, so all six payloads are specified now:

- `task_to_agent` — delegate a task to a chosen agent.
- `autonomy_band` — set/adjust the autonomy band for a decision target.
- `review_depth` — propose the review depth level.
- `validation_depth` — propose the validation depth level.
- `escalation` — escalate to a human target.
- `no_action` — explicit no-action record.

This mirrors the existing `contracts/events.schema.json` discriminated-union pattern: a `$defs` block of named sub-schemas, a `discriminator` with `propertyName` + `mapping`, and a `oneOf` over typed payload `$ref`s. The consistency is deliberate — codegen over the decision union and the event union produces the same shape of typed client code.

## Training-Signal Capture: As-Of Pointer + Frozen Feature Snapshot (D-03)

Each record stores BOTH:

1. The immutable **as-of event-state pointer** (`as_of`) — the point in the BOS3 event stream the recommendation was made against.
2. A **frozen copy of the exact feature vector** (`feature_snapshot`) used at decision time.

This is belt-and-suspenders: the as-of pointer lets a consumer replay the state; the frozen snapshot makes the record self-contained and reproducible without re-querying. Together they make every decision record a self-contained, reproducible training row.

## No-Leakage Guard (D-04)

The outcome label (defined in BOS5) is associated to a decision **after the fact** by `decision_id` join — it is NEVER written into the decision record at decision time. This is the hard PROJECT.md §Data no-outcome-leakage rule: features must be point-in-time correct; outcomes cannot leak into the state used to make the original recommendation.

The schema enforces this structurally:

- The record envelope sets `additionalProperties: false`.
- No `outcome`, `label`, `reward`, or `result-of-decision` property key exists anywhere in the schema.
- `feature_snapshot`, `recommended_action`, and `actual_action` are intentionally open objects (`additionalProperties: true`) because their inner shape varies — but the record envelope itself is closed, so an outcome field cannot be added at the record level.

BOS5 outcome labels attach by `decision_id`; the join happens later, offline, and never mutates the decision record.

## Action Fields and Override-as-Signal (D-05, D-06)

The record separates three explicit action fields:

- `recommended_action` — what the system proposed.
- `human_verdict` — `{ verdict, actor_id, verdict_at }` where `verdict` is exactly one of `approve`, `override`, `dismiss`, `do_nothing`.
- `actual_action` — what was actually taken after the verdict.

This honors the non-negotiable PROJECT.md §Trust human-override governance constraint and maximizes auditability: every recommendation, every human verdict, and every actual action is its own field with its own attribution.

**Override-as-signal (D-06):** the divergence between `recommended_action` and `actual_action` under a human verdict is one of the most valuable learning signals in the corpus. The contract captures it explicitly — it is observable from the three action fields and documented in their descriptions, NOT derived into a separate computed field. A downstream learner reads the three fields and computes the divergence; the contract does not pre-bake it.

`autonomy_band` is a field on the record (D-06), recording the band in effect for this decision. The concrete band values are governed by BOS6 governance — BOS4 locks the field, not the value set.

## Upstream Assumptions (BOS3)

BOS3 (Engineering Event Schema) was not locked before this phase. The ledger's event-ref and entity-ref fields are therefore framed as **upstream assumptions BOS3 must satisfy**, not as an invented BOS3 schema. BOS3 must reconcile against them when it lands.

- **D-07 — As-of pointer.** BOS3 must expose a stable, immutable "as-of" pointer (event sequence number or snapshot id) that the ledger's `as_of` field references. If BOS3 lands a different point-in-time-correctness mechanism, BOS4's `as_of` field shape is reconciled then. The placeholder shape in the schema (an object with `event_seq` and/or `snapshot_id`) is provisional.
- **D-08 — Stable entity IDs.** BOS3 must define stable entity IDs for the entities a decision targets (task, session, agent, swarm assignment) so the ledger's `entity_ref` field can reference them. Cross-source identity resolution (agent/human identity across Git/PM/CI) is deferred to BOS12 (BOS-INT-03). BOS4 locks only the local `entity_ref` field shape; it does not define how identities are resolved across sources.

These are dependencies, not designs. BOS4 does not specify the BOS3 event schema, its event taxonomy, or its entity model.

## Rejected Alternatives

- **Decision as a BOS3 event rather than a separate ledger.** Rejected per D-01. A decision carries mutable verdict state (the human verdict changes the record's meaning); a BOS3 event is an immutable observed fact. Conflating them would mix mutable verdict state into the immutable event log and break the event stream's point-in-time-correctness invariant. The ledger is separate; it references the event stream by as-of pointer.
- **Outcome label written inline on the record at decision time.** Rejected per D-04. Writing the outcome at decision time leaks the label into the state used to make the original recommendation — exactly the leakage PROJECT.md §Data forbids. The outcome is joined later by `decision_id`, strictly after the fact.
- **Per-type record schema instead of a unified discriminated record.** Rejected per D-02. The decision-type set is closed and known (six kinds, fully specified now), so one record + `decision_type` discriminator is cleaner than six separate top-level schemas. It is also codegen-consistent with `contracts/events.schema.json`, which uses the same discriminated-union pattern.

## Open Questions

- **Ledger correction/amendment policy beyond append-only.** How is a mistaken human verdict corrected after it has been appended? The ledger is append-only by design (D-01), but the CONTEXT discussion flagged that an amendment/correction policy may be needed (e.g. a correction record that supersedes an earlier verdict). This is **NOT decided this phase.** It is flagged here as an open question for a follow-up — BOS4 does not prescribe or recommend a specific correction mechanism. A future phase should decide whether correction is handled by a supersession record, a separate correction table, or disallowed entirely (with corrections expressed only in the outcome-label join).

## Out of Scope (deferred)

The following are explicitly out of scope for BOS4 and are not designed here:

- **BOS3 event schema** — entity model, event taxonomy, the concrete as-of/point-in-time mechanism. BOS4 assumes D-07/D-08; BOS3 reconciles.
- **Outcome labels, rewards, guardrail metrics** — BOS5 (BOS-DATA-03..04). Joined to decisions by `decision_id` after the fact.
- **Heuristic delegation/review/validation policies** that produce recommendations — BOS13 (delegation), BOS14 (review/validation).
- **Cross-source identity resolution** (agent/human identity across Git/PM/CI) — BOS12 (BOS-INT-03). BOS4 locks only the local `entity_ref` field shape.
- **Offline-eval consumption** of decision rows — BOS15.

---

*Phase: BOS4-decision-ledger-schema*
*Authoritative contract: `contracts/decision-ledger.schema.json`*
*Rationale record: this document.*