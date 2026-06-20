# Phase BOS3: Engineering Event Schema - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS3-engineering-event-schema
**Areas discussed:** Schema scope/taxonomy, Point-in-time correctness, Relation to harness events, Correlation/identity model

---

## Schema Scope / Taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| Voss-emitted full + external placeholders | Field-level for session/swarm/task/file; reserve slots + envelope for external, defer detail to BOS12 | ✓ |
| All 9 fully specced now | Complete field-level for all categories immediately | |
| Voss-emitted only, external deferred | Spec only today's events; external out of scope | |

**User's choice:** Voss-emitted full + external placeholders (Recommended).
**Notes:** Avoid over-committing to BOS12 integration shapes; keep taxonomy stable to prevent churn.

---

## Point-in-Time Correctness

| Option | Description | Selected |
|--------|-------------|----------|
| Append-only + bitemporal + as-of | Immutable log, event_time+ingest_time, outcomes as separate later events, as-of reconstruction | ✓ |
| Mutable + version history | In-place updates with valid-time | |
| Periodic snapshot feature store | Interval snapshots | |

**User's choice:** Append-only + bitemporal + as-of (Recommended).
**Notes:** Structural no-leakage guarantee matching PROJECT.md data constraint.

---

## Relation to Existing Harness Events

| Option | Description | Selected |
|--------|-------------|----------|
| New derived schema, harness = source | Project PROTOCOL/audit/swarm events into BOS events via mapping; don't modify PROTOCOL.md | ✓ |
| Extend PROTOCOL.md wire contract | Add BOS fields to live wire protocol | |
| Dual-write from harness | Harness emits both wire + BOS events | |

**User's choice:** New derived schema, harness = source (Recommended).
**Notes:** Mapping table (BOS event ← source) mandatory. Matches PROJECT.md "observe, don't re-emit."

---

## Correlation / Identity Model

| Option | Description | Selected |
|--------|-------------|----------|
| Entity IDs + root trace id + causation refs | Stable IDs, root correlation id threading lineage, explicit parent/causation pointers | ✓ |
| Foreign-key joins only | ID refs, reconstruct via joins, no trace id | |
| Implicit time + session correlation | Session id + timestamp proximity | |

**User's choice:** Entity IDs + root trace/correlation id + causation refs (Recommended).
**Notes:** Within-Voss correlation only; cross-integration identity = BOS12. Reserve external-identity ref field.

---

## Claude's Discretion

- Schema representation format (default: prose + tables + machine-readable JSON Schema/Pydantic).
- Field names, enum value sets, envelope field ordering.
- Versioning notation (mirror PROTOCOL.md `v` + migration note).

## Deferred Ideas

- External-source field-level schemas → BOS12.
- Cross-integration identity resolution → BOS12.
- Decision ledger event types → BOS4.
- Outcome labels + reward/guardrails → BOS5.
- Physical storage backend → BOS2/later (BOS2 skipped).
- Offline-eval over schema → BOS15.
