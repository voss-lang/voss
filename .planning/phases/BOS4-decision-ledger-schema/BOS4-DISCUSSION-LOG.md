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
