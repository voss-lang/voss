# Phase BOS4: Decision Ledger Schema - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS4-decision-ledger-schema
**Areas discussed:** Decision record vs events, Decision-type taxonomy, Training-signal capture, Human verdict & autonomy lifecycle

> Note: invoked as `BO4` (typo) → resolved to BOS4. User declined to discuss BOS3 first; chose to discuss BOS4 directly with BOS3 event refs recorded as upstream assumptions (D-07/D-08).

---

## Decision Record ↔ Event Stream

| Option | Description | Selected |
|--------|-------------|----------|
| Separate ledger + event-snapshot ref | Own append-only ledger; each record carries an as-of pointer into the BOS3 stream; recommendation+verdict is distinct from observed fact | ✓ |
| Decision is a BOS3 event | Model decisions as a decision-type event in the unified event log; one store but conflates facts with mutable verdict | |
| You decide | — | |

**User's choice:** Separate ledger + event-snapshot ref (recommended)
**Notes:** Upstream assumption — BOS3 must expose a stable as-of pointer (D-07).

---

## Decision-Type Taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| Unified envelope + discriminator, all 6 payloads now | One schema, decision_type discriminator, typed payload per kind; closed set specified now | ✓ |
| Envelope + type list now, payloads deferred | Lock envelope + enumerate 6 types; defer payload fields to BOS13/14 | |
| You decide | — | |

**User's choice:** Unified envelope + discriminator, all 6 payloads now (recommended)
**Notes:** 6 kinds — task_to_agent, autonomy_band, review_depth, validation_depth, escalation, no_action. Mirrors existing events.schema.json discriminated union.

---

## Training-Signal Capture

| Option | Description | Selected |
|--------|-------------|----------|
| As-of pointer + frozen feature snapshot | Store both immutable as-of pointer AND frozen feature vector; outcome joined later by decision_id, never inline | ✓ |
| As-of pointer only (recompute features) | Store only pointer; recompute features deterministically; lighter but needs version-pinned feature code | |
| You decide | — | |

**User's choice:** As-of pointer + frozen feature snapshot (recommended)
**Notes:** Hard no-leakage guard — outcome label (BOS5) joined strictly after the fact (D-04).

---

## Human Verdict & Autonomy Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Three explicit fields + verdict actor/time | recommended_action, human_verdict (approve/override/dismiss/do-nothing w/ actor+ts), actual_action; autonomy_band; override = training signal | ✓ |
| Recommendation + verdict only (actual derived) | Store recommendation + verdict; actual inferred; fewer fields | |
| You decide | — | |

**User's choice:** Three explicit fields + verdict actor/time (recommended)
**Notes:** Honors non-negotiable human-override governance; override divergence is an explicit captured signal (D-06).

---

## Claude's Discretion

- Decision-ledger doc structure/format.
- Exact field names within the 6 typed payloads.
- Schema representation (JSON Schema authoritative per BOS2 D-06).
- Rationale/explainability field shape (recommended to include).

## Deferred Ideas

- BOS3 event schema + as-of mechanism + entity IDs (upstream; D-07/D-08).
- Outcome labels/rewards → BOS5 (joined by decision_id).
- Recommendation-producing policies → BOS13/14.
- Cross-source identity resolution → BOS12.
- Ledger correction/amendment policy beyond append-only → flagged, undecided.
- Offline-eval consumption of decision rows → BOS15.

---
---

# Phase BOS4: Decision Ledger RUNTIME - Discussion Log (reframe)

**Date:** 2026-06-20
**Phase:** BOS4-decision-ledger-schema (scope: Decision Ledger Runtime)
**Areas discussed:** Capture architecture, Decision-type coverage, Recommendation framing, PermissionGate verdict mapping, as_of pointer, feature_snapshot contents, Storage/module shape

> Context: BOS4 schema (contract + rationale doc) shipped 2026-06-18. ROADMAP
> 2026-06-20 reframed BOS4 to the runtime that WRITES decision records. This
> section gathers runtime context; the schema-era CONTEXT.md above is superseded
> by the runtime CONTEXT.md.

---

## Capture architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Inline emission at gates | Call ledger at decision time; only way to freeze as_of + feature_snapshot (D-03). Diverges from BOS3 pure-projection. | ✓ |
| Hybrid | Inline hooks + projection backfill. Best of both, more surface. | |
| Pure projection | Reconstruct from existing logs; keeps BOS3 purity but as_of/snapshot approximate. | |

**User's choice:** Inline emission at gates.
**Notes:** Deliberate, called-out divergence from BOS3 projection.

---

## Decision-type coverage (this phase)

| Option | Description | Selected |
|--------|-------------|----------|
| Only real sources now | Wire task_to_agent (swarm.assign) + permission verdicts; other 4 types schema-only until BOS9+. | ✓ |
| All 6 with stubs | Scaffold all six, stubbing the four with no producer. | |

**User's choice:** Only real sources now.
**Notes:** no_action on explicit operator dismiss/do-nothing.

---

## Recommendation framing (pre-BOS9)

| Option | Description | Selected |
|--------|-------------|----------|
| Operator-only, recommended_action null | Record actual choices now; BOS9 fills recommended_action later → override-as-signal. | ✓ |
| Defer ledger writes until BOS9 | Writer + scaffolding only, no live emission. | |

**User's choice:** Operator-only, recommended_action null.

---

## PermissionGate verdict mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Only human-prompted verdicts | Record only when a human answers a prompt; auto-allows stay BOS3 events only. | ✓ |
| All permission checks | Every check writes a record; muddies the signal. | |

**User's choice:** Only human-prompted verdicts.
**Notes:** allow→approve, deny→dismiss; override reserved for BOS9; do_nothing→no_action.

---

## feature_snapshot contents

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal-real gate context | Capture what the gate has; additionalProperties:true for BOS9 growth. | ✓ |
| Empty {} until BOS9 | Simpler but non-reproducible rows (weakens D-03). | |

**User's choice:** Minimal-real gate context.

---

## as_of pointer + Storage/module (confirm locks)

| Option | Description | Selected |
|--------|-------------|----------|
| Accept both as proposed | as_of = tail BOS event_id + session trace_id (null if empty); storage = .voss/bos/decisions.jsonl + voss/harness/bos_decisions.py, BOS3 pattern, dedup by decision_id. | ✓ |
| Accept storage, rethink as_of | Leave as_of to researcher/planner. | |
| Accept as_of, rethink storage | Reconsider storage (generalize BosEventLedger). | |

**User's choice:** Accept both as proposed.

---

## Claude's Discretion (runtime)

- Builder signatures / naming in `bos_decisions.py`.
- Reuse vs duplicate BOS3's `BosEventLedger` lock primitive.
- Exact `entity_ref` population from swarm/session context.
- Test layout (mirror `test_bos_event_ledger.py`).

## Deferred Ideas (runtime)

- Four no-producer decision types → BOS9/13/14.
- `recommended_action` + true override-as-signal → BOS9.
- Outcome label join by `decision_id` → BOS5.
- Ledger amendment policy beyond append-only → open question.
- Cross-source identity for `entity_ref` → BOS12.
