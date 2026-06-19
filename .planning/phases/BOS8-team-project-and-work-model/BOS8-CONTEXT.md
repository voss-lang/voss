# Phase BOS8: Team, Project, and Work Model - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS8 produces the **work model spec** (BOS-WORK-01..03): a docs-first specification
of the Behavioral OS engineering entities (team, project, task, PR, service, incident,
agent-run, engineer), the work intake + lifecycle states for engineering tasks, and how
work items connect to sessions, swarm tasks, files, reviews, validations, and outcomes.

This phase defines the **logical work/entity model + lifecycle contract only** — no
runtime, no store engine, no UI. It explicitly does NOT: build a PM suite (the standing
guardrail — define the model, don't rebuild Jira/Linear); re-define the event schema
(BOS3 owns events); define the decision ledger (BOS4) or outcome labels/reward (BOS5);
set governance/privacy policy (BOS6 — BOS8 must stay compatible with it); design the
recommendation surface (BOS9); or specify external Git/PM/CI ingestion + cross-source
identity resolution (BOS12 — BOS8 reserves the slot only).
</domain>

<decisions>
## Implementation Decisions

### Entity ↔ Event Relationship
- **D-01:** **Work model = projection over BOS3's append-only event log.** Work entities
  are a reduced/derived VIEW (read model) over BOS3 events; lifecycle transitions are
  driven by events, not by mutating an entity record. There is **no separate mutable
  authoritative entity store**. This keeps BOS3's D-02 point-in-time correctness +
  no-outcome-leakage guarantee structurally intact (state is reconstructable as-of any
  time). Rejected: authoritative mutable entity store (reintroduces mutation + leakage
  risk BOS3 designed away); hybrid store.
- **D-02:** **Reference entities enter via registration/upsert events.** Entities with no
  natural observed activity (team, project, engineer, service) are introduced through a
  registration/upsert event type (e.g. `project.registered`, `engineer.identified`) that
  flows through the **same append-only log** — one substrate, projection-consistent. No
  side config/reference tables. Rejected: plain config/seed tables (two substrates to
  reconcile); defer all identity population to BOS12 (BOS8 still defines the shape, but
  population uses registration events now).

### Lifecycle & Entity Coverage
- **D-03:** **One canonical task lifecycle state machine** (lean, the "no Jira" guardrail).
  A single small state machine governs the central work item — e.g.
  `intake → triaged → assigned → in_progress → in_review → validated → done`, plus
  off-path states (`blocked`, `abandoned`). Other entities reference it rather than each
  carrying its own full lifecycle. Rich enough to drive later review-depth /
  validation-depth recommendations; not a per-status PM workflow engine. Rejected:
  per-entity state machines (heavier, edges toward a PM suite); minimal open/active/closed
  enum (too thin for downstream recommendations).
- **D-04:** **Tiered entity coverage — work / actor / reference.**
  - **WORK items** (task, PR, incident, agent-run) carry the canonical lifecycle (D-03).
  - **ACTORS** (engineer; agent-run in its actor capacity) are identity references — they
    act on work, they do not have a work lifecycle.
  - **REFERENCE entities** (team, project, service) are lightweight reference objects with
    NO lifecycle (just identity + attributes).
  - All 8 entities are specified (satisfies BOS-WORK-01), but only work items get state
    machines — this is the anti-overbuild line. Rejected: all-8-full-lifecycle (Jira-shaped,
    against guardrail); task-only-now-rest-stubs (under-specifies BOS-WORK-01).
  - **NOTE (must reconcile in spec): `agent-run` is dual** — it is a WORK item (has a
    lifecycle: a run starts, executes, completes/fails) AND an ACTOR (it performs work on
    other items, must map to BOS4 `actor` and respect BOS6 anti-surveillance / no
    individual ranking). The spec must define both facets and how they relate without
    double-counting.

### Work Intake (BOS-WORK-02)
- **D-05:** **Auto-from-harness + manual creation; external ingestion deferred to BOS12.**
  Work items come into existence two ways in v0.2: (a) **auto-derived** from the harness
  sessions / swarm tasks Voss emits today (observed events project into work items), and
  (b) **explicit manual creation** — which, under D-01, is itself a creation event (e.g.
  `task.created`) so it stays projection-consistent, not a mutation. **External** Git/PM
  intake is a **reserved BOS12 source** (slot only, not built here). Rejected:
  auto-from-harness-only (can't represent work not yet routed through Voss);
  manual-first/tracker-shaped (PM-suite-shaped, against guardrail).

### Linking Model (BOS-WORK-03)
- **D-06:** **Reuse BOS3 correlation/causation + BOS5 outcome joins — no new link primitive.**
  Work items connect to sessions, swarm tasks, files, reviews, and validations via BOS3's
  existing **root correlation/trace id + parent/causation refs** (BOS3 D-04); outcomes
  connect via **BOS5's entity-anchored outcome joins** (BOS5 D-03). BOS8 names the link
  *semantics* over what BOS3/BOS5 already provide rather than inventing association tables.
  Rejected: new explicit work↔artifact link tables (duplicates BOS3 lineage, drift risk);
  hybrid with extra typed edges (revisit only if a genuine many-to-many, e.g. work↔service,
  proves BOS3 lineage insufficient — flagged for the spec to check, not pre-built).

### Claude's Discretion
- **Schema representation format** — recommend prose spec + tables PLUS a machine-readable
  schema (JSON Schema / Pydantic), mirroring the BOS3/BOS4 docs-first pattern. Final format
  + file location is planner/researcher discretion.
- **Exact state names, transition guards, and off-path states** of the canonical lifecycle
  (D-03) beyond the indicative set above.
- **Registration event field sets** (D-02) and exact entity attribute lists per tier (D-04).
- **Schema versioning notation** — mirror PROTOCOL.md / BOS3 `v` + migration-note convention.
- Whether the work↔service many-to-many warrants a typed edge (D-06 open check).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & requirements
- `.planning/ROADMAP.md` BOS phase table (~line 23: BOS8 = "Team, Project, and Work Model",
  deliverable "Work model spec") + "BOS-prefixed phases" rollup (~line 121, 151) + coverage
  row (~line 2698: BOS-WORK-01..03 = 3 reqs). Build order: BOS8 sits in BOS7-12 (surfaces/integrations).
- `.planning/REQUIREMENTS.md` lines 40–42 (BOS-WORK-01 entities; BOS-WORK-02 intake + lifecycle
  without a full PM suite; BOS-WORK-03 connections to sessions/swarm/files/reviews/validations/outcomes)
  + line 249 (coverage row).
- `.planning/PROJECT.md` — milestone goal ("can later expand into an engineering-team PM suite"),
  Out-of-Scope ("Replacing Jira/Linear in v0.2 — define the path, do not build a full PM suite"),
  Context §"Swarm impact" (observe/label existing events, don't create new infra).

### Locked upstream context (carry-forward — DO read, do not contradict)
- `.planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md` — **load-bearing.** D-02
  (append-only, bitemporal, as-of, outcomes-as-later-events), D-04 (stable entity IDs + root
  correlation/trace id + causation refs). BOS8's projection (D-01), registration events (D-02),
  and linking (D-06) all sit directly on this. BOS3 already names task/session/swarm/file/
  review/CI/validation/deploy/incident as event categories — BOS8 must not re-define them.
- `.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md` — `actor` model; BOS8's
  agent-run/engineer actors (D-04) must align with BOS4's actor concept.
- `.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md` — D-03 (outcomes anchor
  to the entity, join to decisions), D-05 (multi-label, append-only over entity lifecycle). BOS8's
  outcome linking (D-06) reuses these joins; the canonical lifecycle (D-03) is the spine outcomes accumulate over.
- `.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md` — anti-surveillance
  / no individual ranking, tenant=team, `actor` reconciliation. BOS8's engineer actor + agent-run
  dual role (D-04) must stay compatible (no per-engineer leaderboard surface).
- `.planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md` — D-01 (backend owns projection),
  D-02 (structured-signal-only crosses desktop→server). BOS8's projection model is the kind of
  derived state BOS7 places in backend services.
- `.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-CONTEXT.md` — wedge = delegation
  (task→agent); the work model's central object is the delegatable task.

### Existing substrate (the observed sources work items project FROM — D-05)
- `voss/harness/swarm/events.py` + `voss/harness/swarm_store.py` — swarm task ownership/assignment/
  completion; first auto-intake source for work items.
- `voss/harness/server/sessions.py` + `voss/harness/server/events.py` — session model + SSE emission.
- `voss/harness/audit/model.py` — audit event model.
- `.planning/PROTOCOL.md` — wire contract + `v` versioning convention to mirror (referenced, not modified).

### Forward dependencies BOS8 constrains (reserve, don't design)
- BOS9 recommendation surface — renders over work items.
- BOS12 external integration ingestion + identity resolution — the reserved external intake source (D-05).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- BOS3 event schema contract — the substrate BOS8 projects over; reuse its IDs + correlation model
  rather than inventing new ones (D-01, D-06).
- `voss/harness/swarm/*` + `server/sessions.py` — concrete event sources for auto-intake (D-05);
  researcher should map which produce work-item creation/transition signals.
- BOS5 outcome-join model — reused for work↔outcome linking (D-06).

### Established Patterns
- Docs-first BOS track: contract before code. BOS8 artifact = work model spec (entity defs +
  canonical lifecycle + projection/intake/linking semantics, prose + machine-readable schema).
- Projection / read-model over an append-only log (BOS3 D-02) — BOS8 codifies the work entities as
  exactly such projections.
- "Observe, don't re-emit" — work model derives from existing events; no new coordination substrate.

### Integration Points
- BOS8 work items are the objects BOS9 (recommendation surface) acts on, BOS4 decisions reference,
  and BOS5 outcomes anchor to. Its lifecycle (D-03) + actor model (D-04) must be sufficient for those.
- Projection placement is backend services per BOS7 D-01.
</code_context>

<specifics>
## Specific Ideas

- The work model is a **read model**, not a system of record — state of any work item is reconstructable
  as-of any time from BOS3 events (D-01). State this as an invariant, not a default.
- The canonical lifecycle (D-03) is the spine that BOS5 outcomes accumulate over and that future
  review-depth / validation-depth recommendations key off — keep it small but real (a state machine,
  not a status flag).
- `agent-run` dual role (work item + actor) is the trickiest modeling point — call it out explicitly
  in the spec and resolve both facets against BOS4 `actor` + BOS6 anti-surveillance.
- "Manual creation = a creation event" (D-05) preserves projection-consistency — manual intake must
  NOT be modeled as a mutable insert.
</specifics>

<deferred>
## Deferred Ideas

- External Git/PM/CI work intake + cross-source identity resolution — BOS12 (D-05 reserves the slot).
- Recommendation/approve/override UI over work items — BOS9.
- Governance/privacy who-sees-what rules over the work model — BOS6 (BOS8 stays compatible, doesn't set policy).
- Decision ledger entry types referencing work items — BOS4 (already specified there).
- Outcome label taxonomy + reward metrics — BOS5 (BOS8 only reuses the join).
- Physical store engine / DuckDB-vs-Postgres projection materialization — BOS2/runtime (BOS8 stays logical-contract-only).
- A typed work↔service many-to-many edge — only if D-06's correlation-id linkage proves insufficient (spec to check, not pre-build).
- Full PM-suite workflow features (sprints, boards-as-product, estimation, etc.) — out of milestone scope; the expansion path is BOS18.

### Reviewed Todos (not folded)
None — no todo cross-reference matches surfaced for this phase.

</deferred>

---

*Phase: BOS8-team-project-and-work-model*
*Context gathered: 2026-06-18*
