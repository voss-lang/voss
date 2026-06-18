# Phase BOS4: Decision Ledger Schema - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS4 produces ONE docs-first artifact: the **decision ledger contract** (covers BOS-DATA-02). It defines the record shape for recommendation/action decisions — task→agent, autonomy band, review depth, validation depth, escalation, and no-action — plus how each record doubles as a point-in-time-correct training signal.

It defines the SHAPE of decision records and their relationship to the engineering event stream. It does **not** define the event schema itself (BOS3), outcome labels / rewards (BOS5), the heuristic delegation policy that produces recommendations (BOS13), or any code/store implementation. No code, no migrations — contract + rationale only.

**Note on order:** BOS3 (Engineering Event Schema) was not locked before this discussion (user chose to discuss BOS4 directly). All references to event entities and the point-in-time "as-of" pointer are recorded below as **upstream assumptions BOS3 must satisfy** — see `<deferred>` and the `## Upstream Dependencies` decisions. BOS3 must reconcile against them.
</domain>

<decisions>
## Implementation Decisions

### Decision Record ↔ Event Stream (BOS-DATA-02)
- **D-01:** **Separate append-only ledger, not a BOS3 event.** Decisions live in their own append-only decision ledger, distinct from the BOS3 engineering-event log. A decision = a recommendation + a human verdict, which is semantically distinct from an immutable observed fact; conflating them would mix mutable verdict state into the event log. Each decision record carries a **point-in-time reference** (an "as-of" event sequence / snapshot id) into the BOS3 event stream identifying the state the recommendation was made against.

### Decision-Type Taxonomy (BOS-DATA-02)
- **D-02:** **Unified record + `decision_type` discriminator, all 6 payloads specified now.** One ledger record schema with a `decision_type` discriminator and a typed payload per kind. The decision set is closed and known, so all six payloads are specified in this phase: `task_to_agent`, `autonomy_band`, `review_depth`, `validation_depth`, `escalation`, `no_action`. (Mirrors the existing discriminated-union pattern in `contracts/events.schema.json`.)

### Training-Signal Capture / Point-in-Time Correctness (BOS-DATA-02)
- **D-03:** **As-of pointer + frozen feature snapshot (belt-and-suspenders).** Each record stores BOTH (a) the immutable as-of event-state pointer (D-01) AND (b) a frozen copy of the exact feature vector used to make the recommendation. This makes every record a self-contained, reproducible training row.
- **D-04:** **Outcome labels are joined later, never inline at decision time.** The outcome label (defined in BOS5) is associated to a decision **after the fact** by `decision_id` join — it is NEVER written into the decision record at decision time. This is the hard no-leakage guard from PROJECT.md (outcomes must not leak into the state used to make the original recommendation).

### Human Verdict & Autonomy Lifecycle (BOS-DATA-02 + governance)
- **D-05:** **Three explicit action fields.** The record separates `recommended_action` (what the system proposed), `human_verdict` (one of approve / override / dismiss / do-nothing, with actor id + timestamp), and `actual_action` (what was actually taken). Maximally auditable; honors the non-negotiable human-override governance constraint.
- **D-06:** **`autonomy_band` field** on the record; an **override is itself a captured training signal** (the divergence between recommended_action and actual_action under a human verdict is a labeled signal, surfaced for later learning).

### Upstream Dependencies (assumptions BOS3 must satisfy)
- **D-07:** BOS3 must expose a **stable, immutable "as-of" pointer** (event sequence number or snapshot id) that the ledger can reference (D-01, D-03). If BOS3 lands a different correctness mechanism, BOS4's reference field must be reconciled then.
- **D-08:** BOS3 must define **stable entity IDs** for the entities a decision targets (task, session, agent, swarm assignment) so the ledger can reference them. Cross-source identity resolution is deferred to BOS12 (BOS-INT-03) — BOS4 only locks the local entity-ref field shape.

### Carried Forward (locked elsewhere — NOT re-discussed)
- Store = SQLite local-first, point-in-time-correct, offline (BOS2 D-04).
- Contract mechanism = sibling JSON Schema under `contracts/` feeding the existing CI drift gate, extending the V13.1 artifact (BOS2 D-06).
- Language = TypeScript owns shared contracts (BOS-ARCH-02).
- Governance = team-level, explainable, human override, no individual ranking (PROJECT.md Constraints).

### Claude's Discretion
- Decision-ledger doc structure/format.
- Exact field names within each of the 6 typed payloads (within D-02's closed type set).
- How the doc represents the schema (JSON Schema excerpt, table, prose) — but the deliverable is the contract, and per BOS2 D-06 the authoritative form is a JSON Schema in `contracts/`.
- The rationale/explainability field shape on the record (a recommendation must be explainable per governance) — recommended to include a `rationale` field; exact shape is discretionary.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & product/governance constraints
- `.planning/REQUIREMENTS.md` — **BOS-DATA-02** (line ~26, the target requirement); BOS-DATA-01 (BOS3, the event schema this references); BOS-DATA-03..04 (BOS5, outcome labels/rewards joined later).
- `.planning/PROJECT.md` — Constraints §Data (point-in-time correctness, no outcome leakage), §Trust (human override, no individual ranking, explainable recommendations), §Safety.
- `.planning/ROADMAP.md` — BOS4 row + BOS3-BOS6 "data and trust substrate" build-order note (line ~121, ~139-140).

### Architecture (carried-forward locks)
- `.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md` — D-04 (SQLite local store), D-06 (sibling JSON Schema in contracts/ + drift gate, extend V13.1).

### Existing contract substrate (the form the ledger schema takes)
- `contracts/events.schema.json` — existing discriminated-union JSON Schema (the `decision_type` discriminator pattern D-02 mirrors); BOS3's engineering-event schema + this ledger schema are siblings here.
- `contracts/openapi.json` — the committed V13.1 contract artifact; the drift gate the ledger schema joins.

### Upstream (not yet locked — BOS3)
- BOS3 Engineering Event Schema (Pending, no dir yet) — must satisfy D-07 (as-of pointer) and D-08 (stable entity IDs). BOS4's event-ref fields are assumptions until BOS3 lands.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`contracts/events.schema.json` discriminated-union pattern**: D-02's unified record + `decision_type` discriminator follows the same pydantic-`Field(discriminator=...)` → JSON Schema → codegen pattern already used for the runtime event union.
- **V13.1 contract artifact + CI drift gate** (BOS2 D-06): the ledger schema joins this rather than introducing new contract tooling.

### Established Patterns
- **Docs-first BOS track**: contract before code. BOS4's ledger contract is inherited by the policy phases (BOS13/14) that emit recommendations and the eval phase (BOS15) that consumes decision rows.
- **Append-only + point-in-time correctness**: aligns with BOS2 D-04/D-05 (SQLite local-first, one-directional projection to shared Postgres).

### Integration Points
- None executed (docs-only). The contract frames how a future recommendation engine writes decision rows referencing BOS3 event state, and how BOS5 outcome labels join by `decision_id`.
</code_context>

<specifics>
## Specific Ideas

- A decision record must be a **self-contained reproducible training row** (D-03): as-of pointer + frozen feature snapshot, with the outcome label joined strictly after the fact (D-04).
- The **override-as-signal** idea (D-06): the gap between `recommended_action` and `actual_action` under a human verdict is one of the most valuable learning signals — the contract must make it explicit, not derived.
- Mirror the existing `contracts/events.schema.json` discriminated-union style so the ledger schema is consistent with the runtime/event schemas and codegen-friendly.
</specifics>

<deferred>
## Deferred Ideas

- **BOS3 event schema itself** — entity model, event taxonomy, the concrete as-of/point-in-time mechanism. BOS4 assumes D-07/D-08; BOS3 must reconcile. (Out-of-order discussion noted in `<domain>`.)
- **Outcome labels, rewards, guardrail metrics** — BOS5 (BOS-DATA-03..04). Joined to decisions by `decision_id` after the fact.
- **The heuristic delegation/review/validation policies** that actually produce recommendations — BOS13 (delegation), BOS14 (review/validation).
- **Cross-source identity resolution** (agent/human identity across Git/PM/CI) — BOS12 (BOS-INT-03). BOS4 locks only the local entity-ref field shape.
- **Ledger correction/amendment policy** beyond append-only (e.g. how a mistaken verdict is corrected) — raised as a possible further area; not decided this phase. Flag for the planner or a follow-up.
- **Offline-eval consumption** of decision rows — BOS15.

### Reviewed Todos (not folded)
None — no phase-matched todos surfaced for BOS4.
</deferred>

---

*Phase: BOS4-decision-ledger-schema*
*Context gathered: 2026-06-18*
