# Phase BOS8: Team, Project, and Work Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS8-team-project-and-work-model
**Areas discussed:** Entity↔event relation, Lifecycle + coverage, Work intake, Linking model

---

## Entity ↔ Event Relation

| Option | Description | Selected |
|--------|-------------|----------|
| Projection over events | Work entities = reduced view over BOS3 append-only events; lifecycle driven by events; no mutable store; keeps PIT + no-leakage | ✓ |
| Authoritative entity store | Separate mutable entity store of record; events just an audit trail | |
| Hybrid | Authoritative for reference data, projection for observed work | |

**User's choice:** Projection over events
**Notes:** Aligns with BOS3 D-02. Locked as D-01.

### Follow-up: reference entity entry

| Option | Description | Selected |
|--------|-------------|----------|
| Registration events | Registration/upsert event type through same append-only log; one substrate | ✓ |
| Config/reference tables | Reference entities in plain config/seed tables outside the log | |
| Defer identity to BOS12 | Spec shape now, defer population to BOS12 ingestion | |

**User's choice:** Registration events
**Notes:** One substrate, projection-consistent. Locked as D-02.

---

## Lifecycle + Coverage

| Option | Description | Selected |
|--------|-------------|----------|
| One canonical task lifecycle | Single small state machine for the central work item; others reference it | ✓ |
| Per-entity state machines | Distinct lifecycles per task/PR/incident/agent-run | |
| Minimal status enum | open/active/closed, no real state machine | |

**User's choice:** One canonical task lifecycle
**Notes:** The "no Jira" guardrail. Locked as D-03.

### Follow-up: entity coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Tiered: work / actor / ref | Work items get lifecycle; engineer/agent-run = actor refs; team/project/service = lightweight reference | ✓ |
| All 8 full lifecycle | Every entity gets states + transitions | |
| Task-only now, rest stubs | Only task fully specified, rest reserved stubs | |

**User's choice:** Tiered: work / actor / ref
**Notes:** Locked as D-04. Flagged agent-run as dual (work item + actor) for spec reconciliation.

---

## Work Intake

| Option | Description | Selected |
|--------|-------------|----------|
| Auto from harness + manual, ext deferred | Auto-derive from harness sessions/swarm + manual creation; external Git/PM → BOS12 | ✓ |
| Auto-from-harness only | Only observed harness/swarm events create work | |
| Manual-first | Primarily explicit creation; harness links to it | |

**User's choice:** Auto from harness + manual, external deferred
**Notes:** Manual creation modeled as a creation event (projection-consistent). Locked as D-05.

---

## Linking Model

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse BOS3 correlation/causation | Links ride BOS3 correlation/trace id + causation refs + BOS5 outcome joins; no new primitive | ✓ |
| New explicit link tables | BOS8 defines its own work↔artifact association records | |
| Hybrid | Correlation id for lineage + explicit typed edges where insufficient | |

**User's choice:** Reuse BOS3 correlation/causation
**Notes:** Locked as D-06. Work↔service many-to-many flagged as an open check, not pre-built.

---

## Claude's Discretion

- Schema representation format (recommend prose + machine-readable schema, mirroring BOS3/BOS4).
- Exact state names, transition guards, off-path states of the canonical lifecycle.
- Registration event field sets and per-tier entity attribute lists.
- Schema versioning notation (mirror PROTOCOL.md/BOS3 `v` + migration note).
- Whether work↔service warrants a typed edge.

## Deferred Ideas

- External Git/PM/CI intake + cross-source identity resolution — BOS12.
- Recommendation/approve-override UI over work items — BOS9.
- Governance who-sees-what rules — BOS6.
- Decision ledger entry types — BOS4.
- Outcome label taxonomy + reward metrics — BOS5.
- Physical store engine / projection materialization — BOS2/runtime.
- Typed work↔service many-to-many edge — only if correlation-id linkage proves insufficient.
- Full PM-suite workflow features (sprints, boards-as-product, estimation) — BOS18 expansion path.
