# Phase BOS3: Engineering Event Schema - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS3 produces the **canonical engineering event schema contract** — a docs-first
specification of the point-in-time-correct event model that the Behavioral OS
consumes as its data substrate. Covers BOS-DATA-01.

Entity categories in scope: tasks, sessions, swarm events, files, reviews, CI,
validation, deploys, incidents.

This phase defines the **schema/contract only** (no runtime emitters, no ingestion
pipeline, no storage engine). It does NOT define: the decision ledger (BOS4),
outcome labels/reward (BOS5), governance (BOS6), or external-integration ingestion
mechanics + cross-integration identity resolution (BOS12). Build context: BOS2
(monorepo/stack) was skipped for now — BOS3 must not assume a specific storage
backend; it specifies the logical event contract, leaving physical store to BOS2/later.
</domain>

<decisions>
## Implementation Decisions

### Schema Scope / Taxonomy
- **D-01:** **Fully spec the events Voss emits TODAY** — `session`, `swarm`, `task`,
  `file` categories get field-level schemas. For the external/not-yet-integrated
  categories (`review`, `CI`, `validation`, `deploy`, `incident`) **reserve taxonomy
  slots + a forward-compatible common envelope shape**, but defer field-level detail
  to BOS12 ingestion. Rationale: avoid over-committing to integration shapes BOS12
  hasn't decided, while keeping the taxonomy stable so external events slot in without
  schema churn. Rejected: all-9-fully-now (premature); Voss-only-external-dropped (causes churn).

### Point-in-Time Correctness
- **D-02:** **Append-only immutable event log + bitemporal + as-of reconstruction.**
  - Events are immutable, append-only. No in-place mutation of past events.
  - Every event carries **two timestamps**: `event_time` (when it occurred in the world)
    and `ingest_time` (when BOS recorded it).
  - **Outcomes arrive as SEPARATE later events**, never by mutating the originating
    event/state. This is the structural guarantee that outcomes cannot leak into the
    state used to make the original recommendation.
  - Features for any decision are reconstructed **as-of** that decision's `event_time`.
  - This directly satisfies PROJECT.md's "point-in-time correct; outcomes cannot leak
    into the state used to make the original recommendation" constraint.
  - Rejected: mutable-with-version-history (weak leakage guarantee), periodic snapshots (too coarse).

### Relation to Existing Harness Events
- **D-03:** BOS3 is a **NEW derived analytics/decision event schema**. Existing harness
  event surfaces — `PROTOCOL.md` SSE `_EventEnvelope` union, `voss/harness/audit/model.py`,
  `voss/harness/swarm/events.py`, `voss/harness/server/events.py` — are **SOURCES** that
  **project into** BOS events via a documented mapping (source event → BOS event).
  BOS3 **references but does NOT modify** `PROTOCOL.md` (the wire contract stays
  decoupled from analytics). Matches PROJECT.md "BOS observes/labels existing events
  rather than create new coordination infrastructure."
  - The contract must include a **mapping table**: for each BOS event category, which
    existing harness/swarm/audit source(s) it derives from (or "external — BOS12").
  - Rejected: extending PROTOCOL.md directly (couples analytics to transport, PROJECT bars it);
    dual-write from harness at emission (runtime work, not docs-first).

### Correlation / Identity Model
- **D-04:** **Stable entity IDs + a root correlation/trace id + explicit causation refs.**
  - Each entity (task, session, swarm-assignment, file, review, …) has a stable ID.
  - A **root correlation/trace id** threads the full lineage:
    task → session → swarm-assign → files → review → CI → deploy → incident.
  - Each event carries explicit **parent / causation pointers** (what caused this event).
  - Enables full decision-context reconstruction needed for as-of PIT features (D-02).
  - Scope note: this is **within-Voss** correlation. **Cross-integration identity
    resolution** (e.g. same human across Git/PM/CI accounts) is BOS12, not BOS3 — but
    BOS3's ID model should leave room for an external-identity reference field.
  - Rejected: FK-joins-only (hard multi-hop lineage), implicit time+session (lossy across hops).

### Claude's Discretion
- **Schema representation format.** Default recommendation: express the contract as a
  prose spec + tables PLUS a concrete machine-readable schema (JSON Schema or Pydantic
  models) so downstream codegen/validation is possible. Final format choice + file
  location is planner/researcher discretion, consistent with the docs-first BOS pattern.
- Exact field names, enum value sets per event category, and envelope field ordering.
- Schema versioning/evolution notation (should mirror PROTOCOL.md's `v` + migration-note pattern).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & requirements
- `.planning/ROADMAP.md` BOS phase table (~line 18) + "BOS-prefixed phases" section (~line 113-140) — BOS3 goal, deliverable ("Event schema contract"), build order (BOS3-6 = data/trust substrate).
- `.planning/REQUIREMENTS.md` line 25 (BOS-DATA-01) + line 244 (coverage row). Related downstream: BOS-DATA-02 (BOS4 decision ledger), BOS-DATA-03..04 (BOS5 outcomes/reward) — BOS3 must not bleed into these.
- `.planning/PROJECT.md` — Constraints §"Data" (point-in-time correctness, no outcome leakage); Context §"Swarm impact" (observe/label existing events, don't create new infra).

### Existing event substrate (SOURCES to project from — D-03 mapping)
- `.planning/PROTOCOL.md` — harness wire contract; SSE `_EventEnvelope` union (§6), event/part/gate types. BOS3 references, does NOT modify. Versioning pattern (`v` + migration note) to mirror.
- `voss/harness/audit/model.py` + `voss/harness/audit/load.py` — audit event model (a primary projection source).
- `voss/harness/swarm/events.py` + `voss/harness/swarm_store.py` — swarm event shapes (`swarm.assign`, task ownership, gates, completion).
- `voss/harness/server/events.py` + `voss/harness/server/sessions.py` — server-side SSE event emission + session model.
- `voss/harness/watch/backend.py` — long-running/watch events (potential source).

### Prior BOS context
- `.planning/phases/BOS1-planning-audit-and-archive-map/BOS1-PRODUCT-CONTEXT.md` — wedge = delegation (task→agent); the event schema must capture delegation decisions + their observable signals (D-02 swarm.assign is the first event source).
- `.planning/phases/BOS1-planning-audit-and-archive-map/BOS1-CONTEXT.md` — sibling docs-first BOS phase (pattern reference).
- `.planning/docs/ORCHESTRATION_LAYERS.md` — V-track agent-org design; V25 server-native swarm is the first ADE event source feeding BOS.
- `.planning/seeds/SEED-001-coordination-bus.md` — planted context; external-agent events arrive as CLI verbs over the existing server plane (relevant to external-event placeholders, D-01).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PROTOCOL.md` `_EventEnvelope` union — the existing tagged-event pattern + `v`-versioning convention BOS3's envelope + versioning should mirror.
- `voss/harness/audit/model.py`, `swarm/events.py`, `server/events.py` — concrete existing event shapes the BOS schema projects FROM. Researcher should enumerate these to build the D-03 mapping table.

### Established Patterns
- Docs-first BOS track: contract before code. BOS3 artifact = event schema contract (prose + machine-readable schema per D-01/discretion).
- Versioning via a `v` field + inline migration note (PROTOCOL.md convention) — adopt for the BOS schema.
- BOS "observe, don't re-emit": BOS schema is downstream/derived, harness wire stays authoritative for transport.

### Integration Points
- BOS3 schema is the substrate that BOS4 (decision ledger) and BOS5 (outcomes/reward) build on — its entity IDs + correlation model (D-04) and bitemporal model (D-02) must be sufficient for those phases. BOS12 ingestion fills the external-event placeholders (D-01).
</code_context>

<specifics>
## Specific Ideas

- "No outcome leakage" is enforced structurally: outcomes = separate later append-only events + as-of feature reconstruction (D-02), not a validation rule bolted on later.
- The D-03 mapping table (BOS event ← harness source) is a mandatory part of the deliverable, not optional commentary — it proves BOS reuses existing events.
- Reserve an external-identity reference field in the ID model (D-04) so BOS12 cross-integration identity resolution has a hook without a BOS3 schema change.
</specifics>

<deferred>
## Deferred Ideas

- Field-level schemas for external sources (review/CI/validation/deploy/incident) — BOS12 ingestion (D-01 reserves the slots only).
- Cross-integration identity resolution (same human across Git/PM/CI accounts) — BOS12.
- Decision ledger event types (task-to-agent, autonomy band, review/validation depth, escalation, no-action) — BOS4 (BOS-DATA-02).
- Outcome labels + reward/guardrail metrics — BOS5 (BOS-DATA-03..04).
- Physical storage backend / store engine choice — depends on BOS2 (skipped for now); BOS3 stays logical-contract-only.
- Offline-eval requirements over this schema — BOS15 (BOS-DATA-05).

### LEM-readiness (north-star, non-blocking — see `.planning/LEM-VISION.md`)
The event schema is the future Large Event Model training corpus. Keep it **tokenizable**,
but do NOT pull model work into BOS3:
- **Trace/correlation id (D-04) must be a clean, complete sequence key** — every event in a
  lineage resolves to one trace id; this is the LEM "document" boundary. Already intended by D-04;
  just don't let it become optional/partial.
- **Every continuous field needs a quantization story** (latency, durations, counts, diff sizes) —
  not necessarily binned in BOS3, but the field must be representable as discretizable for the LEM
  vocabulary (reuse BOS5's bin choices when they land, rather than inventing a second scheme).
- **Bitemporal as-of (D-02) is the no-leakage guard for training**, not only for live features —
  a sequence prefix predicting an outcome must contain only `event_time ≤ decision_time`.
This is a forward-compatibility note only. No BOS3 deliverable changes; flag for the planner as context.

### Reviewed Todos (not folded)
None — no todo cross-reference matches surfaced for this phase.

</deferred>

---

*Phase: BOS3-engineering-event-schema*
*Context gathered: 2026-06-18*
