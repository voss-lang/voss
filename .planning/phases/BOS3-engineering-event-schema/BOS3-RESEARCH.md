# Phase BOS3: Engineering Event Schema - Research

**Researched:** 2026-06-18
**Domain:** Point-in-time-correct (bitemporal) engineering event schema — a docs-first logical contract derived from Voss's existing harness/swarm/audit event substrate.
**Confidence:** HIGH (internal substrate enumerated from source; bitemporal pattern confirmed against canonical references)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (Scope/Taxonomy):** Fully spec the events Voss emits TODAY — `session`, `swarm`, `task`, `file` categories get **field-level schemas**. For external/not-yet-integrated categories (`review`, `CI`, `validation`, `deploy`, `incident`) **reserve taxonomy slots + a forward-compatible common envelope shape**, but defer field-level detail to BOS12 ingestion. Rejected: all-9-fully-now (premature); Voss-only-external-dropped (causes churn).
- **D-02 (Point-in-Time Correctness):** Append-only immutable event log + bitemporal + as-of reconstruction.
  - Events are immutable, append-only. No in-place mutation of past events.
  - Every event carries two timestamps: `event_time` (when it occurred in the world) and `ingest_time` (when BOS recorded it).
  - Outcomes arrive as SEPARATE later events, never by mutating the originating event/state.
  - Features for any decision are reconstructed **as-of** that decision's `event_time`.
  - Satisfies PROJECT.md "point-in-time correct; outcomes cannot leak into the state used to make the original recommendation."
  - Rejected: mutable-with-version-history (weak leakage guarantee); periodic snapshots (too coarse).
- **D-03 (Relation to Existing Events):** BOS3 is a NEW derived analytics/decision event schema. Existing harness surfaces (`PROTOCOL.md` SSE `_EventEnvelope`, `audit/model.py`, `swarm/events.py`, `server/events.py`) are SOURCES that project into BOS events via a documented **mapping table** (mandatory deliverable). BOS3 references but does NOT modify `PROTOCOL.md`. Rejected: extending PROTOCOL.md directly; dual-write from harness at emission.
- **D-04 (Correlation/Identity):** Stable entity IDs + a root correlation/trace id + explicit causation refs.
  - Each entity (task, session, swarm-assignment, file, review, …) has a stable ID.
  - A root correlation/trace id threads the full lineage: task → session → swarm-assign → files → review → CI → deploy → incident.
  - Each event carries explicit parent / causation pointers.
  - Within-Voss correlation only. Cross-integration identity resolution is BOS12 — but reserve an external-identity reference field.
  - Rejected: FK-joins-only; implicit time+session.

### Claude's Discretion
- **Schema representation format.** Default: prose spec + tables PLUS a concrete machine-readable schema (JSON Schema or Pydantic). Final format + file location is planner/researcher discretion, consistent with the docs-first BOS pattern. **→ Researcher recommendation below: JSON Schema (Draft 2020-12) as the normative artifact + prose/tables as the human spec. See §Schema Representation.**
- Exact field names, enum value sets per event category, and envelope field ordering.
- Schema versioning/evolution notation (mirror PROTOCOL.md's `v` + migration-note pattern).

### Deferred Ideas (OUT OF SCOPE)
- Field-level schemas for external sources (review/CI/validation/deploy/incident) — BOS12.
- Cross-integration identity resolution (same human across Git/PM/CI accounts) — BOS12.
- Decision ledger event types (task-to-agent, autonomy band, review/validation depth, escalation, no-action) — BOS4 (BOS-DATA-02).
- Outcome labels + reward/guardrail metrics — BOS5 (BOS-DATA-03..04).
- Physical storage backend / store engine choice — depends on BOS2 (skipped); BOS3 stays logical-contract-only.
- Offline-eval requirements over this schema — BOS15 (BOS-DATA-05).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BOS-DATA-01 | Voss specifies a point-in-time-correct engineering event schema covering tasks, sessions, swarm events, files, reviews, CI, validation, deploys, and incidents. | §Existing Event Substrate (concrete source fields for task/session/swarm/file), §Bitemporal Pattern (event_time/ingest_time + as-of, satisfying PIT correctness), §D-03 Mapping Table (source→BOS projection), §Forward-Compat Envelope (reserved slots for review/CI/validation/deploy/incident), §Schema Representation (JSON Schema + prose deliverable), §Validation Architecture (how the contract is validated). |
</phase_requirements>

## Summary

BOS3 is a **docs-first logical contract**, not runtime code. The deliverable is a canonical engineering-event schema: a human-readable spec (prose + tables) plus a machine-readable schema, expressing a **bitemporal, append-only, as-of-reconstructable** event model derived from event surfaces Voss already emits. No emitters, ingestion pipeline, or storage engine — those belong to later/parallel phases.

The good news from the codebase audit: Voss's existing substrate is already very close to what D-02/D-04 need. The swarm event log (`swarm/events.py` + `swarm_store.py`) is **already append-only JSONL, already carries a stable `id` per event, a `type` tag, a `swarm_id` correlation key, an `actor`, an ISO-8601 `ts`, a `v:1` version, and a `payload`** — i.e. it is functionally a single-timestamp event-sourcing log with replay. The session/run records (`session.py`) carry rich per-run provenance (goal, inspected, changed, decisions, cost, tokens, exit_reason, started/ended_at). The SSE protocol (`PROTOCOL.md` §6, `server/events.py`) is the live wire taxonomy. The audit layer (`audit/model.py`) already normalizes routing/kill/rescope/reviewer-verdict/liveness records with `root_id` + `parent_run_id` lineage. **What is consistently MISSING across all sources is the second time axis (`ingest_time` — sources have only one timestamp), an explicit causation pointer (parent lineage exists structurally but not as a per-event `caused_by` ref), and a uniform cross-source correlation/trace id** (swarm has `swarm_id`, audit has `root_id`, sessions have `id`+`parent_id` — none is unified). BOS3's contract must *define* these as derived fields the projection populates, NOT add them to the sources (D-03: don't modify PROTOCOL.md or the harness).

The canonical bitemporal pattern (Martin Fowler's actual-time/record-time; Snodgrass/SQL:2011 valid-time/transaction-time; XTDB/event-sourcing "as-of") maps **exactly** onto D-02: `event_time` = valid/actual time, `ingest_time` = transaction/record time, outcomes-as-later-events = append-only retroactive facts, as-of reconstruction = "what was knowable at decision time." This is a well-established model; the research confirms D-02 is the textbook-correct choice and the contract should adopt the standard vocabulary (with a glossary mapping Voss terms to the canonical ones).

**Primary recommendation:** Write the contract as a markdown spec at `.planning/BOS-EVENT-SCHEMA.md` (mirroring where BOS1 put `AUDIT-INDEX.md` and PROTOCOL.md lives) **plus** a normative **JSON Schema (Draft 2020-12)** artifact at `.planning/schemas/bos-events.schema.json`. Structure it as: (1) a common bitemporal envelope, (2) field-level schemas for the 4 live categories, (3) reserved-slot stubs for the 5 external categories sharing the envelope, (4) the mandatory D-03 source→BOS mapping table, (5) a correlation/lineage model, (6) versioning via `schema_version` + inline migration notes mirroring PROTOCOL.md's `v` convention. Validate with example-event round-trip + mapping-completeness + schema-lint checks (see §Validation Architecture).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Define event taxonomy + field schemas | Shared contract (docs) | — | BOS3 is a contract artifact; no runtime tier owns it yet. PROTOCOL.md is the analogue precedent. |
| Source events (live) | Local harness runtime (Python) | Desktop ADE (consumes SSE) | Swarm/audit/session/SSE all originate in `voss/harness/*`; BOS3 only references them. |
| Projection source→BOS event | Backend/event service (future, not BOS3) | — | The mapping table is *specified* now; the projector is built later (BOS11/BOS12 era). BOS3 stays logical. |
| Bitemporal storage / as-of query engine | Backend/event store (future, BOS2/later) | — | Explicitly out of scope (D-02 logical-only; BOS2 skipped). |
| Outcome events (later append) | Backend/event service (future) | — | Outcomes are BOS5 content; BOS3 only reserves the structural "later append-only event" shape. |

## Existing Event Substrate (SOURCES to project from — feeds D-03 mapping)

> This section is the empirical core of the phase. Every field below was read from source on 2026-06-18 so the planner builds the D-03 mapping table from REAL fields, not guesses. `[VERIFIED: codebase]`.

### A. Swarm event log — `voss/harness/swarm/events.py` + `voss/harness/swarm_store.py`
The closest existing analogue to a BOS event log. **Already append-only JSONL, already has a uniform envelope, already replayable.**

**Envelope** (`SwarmStore._event`, swarm_store.py:219-229):
| Field | Type | Notes |
|-------|------|-------|
| `v` | int | =1. Matches PROTOCOL.md `v` convention. |
| `id` | str | `uuid4().hex[:8]` — stable per-event id. |
| `type` | str | event tag (below). |
| `swarm_id` | str | **correlation key** scoping all events of one swarm. |
| `ts` | str | ISO-8601 UTC, `timespec="seconds"`. **Single timestamp** — equivalent to `event_time` only; no `ingest_time`. |
| `actor` | str | `"operator"` / `"coordinator"` / `"builder"`. |
| `payload` | dict | type-specific (below). |

**Event types + payloads** (emitted in swarm_store.py):
| `type` | payload fields | BOS category |
|--------|---------------|--------------|
| `swarm.create` | `goal, cwd, roster[]` | swarm |
| `swarm.task` | `task_id, goal, owned_files[], depends_on[]` | task |
| `swarm.assign` | `task_id, session_id` | swarm (delegation — the wedge event) |
| `swarm.worker_done` | `task_id, summary` | task (outcome-ish) |

Lifecycle states: `OPEN → ASSIGNED → DONE` (swarm_store.py:32-35). `replay()` rebuilds full state from the log; `replay_timeline()` gives per-task ordered transitions — **a working as-of-by-replay precedent**. `extra="ignore"` on models = forward-compatible to new payload keys (Pitfall-relevant: BOS schema should adopt the same tolerance).

**Decision audit sidecar** (`record_gate_decision`, swarm_store.py:343): writes `.voss/decisions/<date>-<slug>.md` with frontmatter `id, status, related_session, confidence, created_at, swarm_id, task_id, gate_type`. This is a **gate/decision outcome** source — relevant to BOS4 lineage but the *shape* (confidence + gate_type + lineage refs) is a BOS3 correlation precedent.

### B. SSE wire taxonomy — `PROTOCOL.md` §6 + `voss/harness/server/events.py`
The live event union. BOS3 **references, does not modify** (D-03). Pydantic v2 discriminated union on `type`; shared `_Base` envelope is just `{v:int}` + `type` literal (no timestamp on the wire — these are streamed, not stored).

Live swarm SSE events (richer than the JSONL log — these carry `owned_files`, `role`, `gate_type`, `tool_name`, `path`):
| SSE `type` | key fields | BOS category |
|-----------|-----------|--------------|
| `swarm.assign` | `swarm_id, task_id, session_id, owned_files[], role` | swarm |
| `swarm.worker_done` | `swarm_id, task_id, session_id, summary` | task |
| `swarm.gate` | `swarm_id, task_id, gate_type("ownership_denied"\|"reviewer_reject"), detail` | swarm (decision/outcome) |
| `swarm.needs_operator` | `swarm_id, task_id, session_id, tool_name, path` | swarm |
| `swarm.complete` | `swarm_id, task_count, summary` | swarm |
| `tool` | `name, args, summary, state(ok\|error\|pending)` | file (when name ∈ fs_write/fs_edit/fs_edit_many) / task |
| `final` | `text, confidence, cost_usd` | session/task (turn outcome) |
| `stream.finalize` | `role, confidence, cost_usd, timestamp` | session |
| `status` | `model, tokens, cost_usd, ctx_pct` | session |
| `plan` | `confidence, steps[], cost_usd` | task (decision) |
| `gate.updated` | `session_id, gate, decision` | session (decision) |
| `permission.updated` | `id, tool_name, args, dimension(tool\|confidence\|budget)` | session (gate) |

**Versioning precedent to mirror (D-04 / discretion):** PROTOCOL.md §1 — "Every JSON body and every SSE `data` payload carries `v:1`. A breaking change increments `v` and ships a migration note here." Additive-only divergence rule (§12) = the model for BOS schema evolution.

### C. Session / run provenance — `voss/harness/server/sessions.py` + `voss/harness/session.py`
**`SessionRecord`** (session.py:159): `id (uuid4().hex[:12]), name, cwd, model, started_at, updated_at, total_cost_usd, turns[], runs[], parent_id, parent_turn_index`. **`parent_id`/`parent_turn_index` = existing fork lineage** (a causation precedent for D-04).

**`RunRecord`** (session.py:118) — the richest provenance source, one per agent run (= COG-08 audit row):
`id, started_at, ended_at, goal, plan, inspected[], changed[], avoided[], assumptions[], decisions[], risks[], validation[], failures[], diff_summary, follow_ups[], cost_usd, iterations[], iteration_count, exit_reason, iteration_total_prompt/completion_tokens, skill_events[], scope_denials[], capability_invocations[], factory_fallbacks[]`.
- `exit_reason` is validated against an `EXIT_REASONS` set (`done`/`timeout`/`interrupt`/`budget`/etc.) — a ready-made **task-outcome enum source**.
- `changed[]` / `inspected[]` / `avoided[]` → **file-category events**.
- `decisions[]` / `validation[]` / `failures[]` → decision/outcome sources (BOS4/BOS5 territory; BOS3 reserves the lineage hook).
- `started_at`/`ended_at` = single time axis → `event_time` source; **no `ingest_time`**.

**`ServerSession`** (sessions.py:27) carries live swarm linkage: `swarm_id, swarm_task_id, swarm_owned_files[], swarm_role` — the in-memory bridge that ties a session to a swarm task (correlation precedent).

### D. Audit normalization — `voss/harness/audit/model.py` + `audit/load.py`
O6/V9 frozen audit snapshot. Already a **derived/normalized projection layer** — the closest structural precedent to what BOS3 is.
- `AuditNode`: `id, root_id, parent_run_id, envelope, terminal_state, created_at, ended_at, transitions[], cards[], liveness_events[]`. **`root_id` = a real correlation-root precedent; `parent_run_id` = a real causation precedent** (D-04). `created_at`/`ended_at` = single time axis.
- `RoutingRationale`: `id, card_id, chosen_role, candidates_considered[], rationale_text, ts, confidence_hint` — a delegation-decision record (BOS4 source; lineage shape relevant now).
- `KillRecord`: `killed_node_id, rationale_text, evidence_refs[], killed_at, lineage_parent_id, successor_card_id` — explicit lineage + successor pointers.
- `RescopeRecord`: `predecessor_card_id, successor_card_id, diff_summary, …` — predecessor/successor lineage.
- `ReviewerAssessment`: `conf, source, tier, verdict(pass\|fail\|block), notes, evidence_refs[]` — an **internal review/verdict** event (note: this is Voss's *internal* reviewer, distinct from the external `review` category reserved for BOS12 — the planner must disambiguate these in the taxonomy).
- `LivenessEvent`: `node_id, event_type(timeout\|reserve_exhausted\|open_node\|terminal), severity(ok\|warning\|blocked\|accepted_gap), detail`.
- `load.py` reads node JSON deterministically (sorted by id), normalizes missing payloads to empty tuples, **never writes** — an as-of-style read-only reconstruction precedent. Transitions carry `kind` tags (`board.transition`, `em.routing`, `em.kill`, `em.rescope`, `em.run_final`, `em.ticket`, `audit.leak6`) — a parallel event-kind taxonomy worth cross-referencing.

### E. File-change watch — `voss/harness/watch/backend.py`
Append-only JSONL file-event log (`.voss-cache/watch/<handle>.log`). Record shape (`_on_debounced_event`, backend.py:79):
`{ts_ms (int epoch ms), event_type (created/modified/deleted/moved), path, src_path}`. Debounced. **Note:** `ts_ms` is millisecond-epoch, NOT ISO-8601 — a normalization wrinkle for the projection. This is the most direct **file-category** source, but it is raw filesystem events (no correlation id, no actor, no session linkage) — the projection must *enrich* it (join on cwd + time window) to attach correlation. Flag: lowest-fidelity source; may be a "best-effort" file source vs. the higher-fidelity `RunRecord.changed[]`.

### Candidate source → BOS category mapping (DRAFT for the planner to formalize as the D-03 table)

| BOS category | Primary source(s) | Key correlation field available | Missing for D-02/D-04 |
|--------------|-------------------|--------------------------------|-----------------------|
| **session** | `SessionRecord` + SSE `final`/`status`/`stream.finalize` + `RunRecord` | `id`, `parent_id` | `ingest_time`; unified trace id |
| **task** | swarm `swarm.task`/`swarm.worker_done`; `RunRecord` (goal/exit_reason/changed); SSE `plan` | `task_id`, `swarm_id`, run `id` | `ingest_time`; explicit `caused_by`; cross-source trace id |
| **swarm** | swarm log (`swarm.create/assign`) + SSE `swarm.*` | `swarm_id`, `task_id`, `session_id` | `ingest_time`; trace id binding swarm→session→run |
| **file** | `RunRecord.changed/inspected/avoided`; watch `backend.py` log; SSE `tool`(fs_*) | path; (watch: none) | correlation id on watch events; `event_time` vs `ingest_time` split; actor |
| **review** *(reserved)* | external — BOS12 (NB: Voss-internal `ReviewerAssessment` exists but is a distinct internal-verdict source, not the external `review` slot) | — | full field detail deferred |
| **CI / validation / deploy / incident** *(reserved)* | external — BOS12 (`RunRecord.validation[]` is an internal validation precedent only) | — | full field detail deferred |

**Universal gap (applies to every live source):** none carries a second timestamp. Sources record *one* time (when it happened / `ts` / `started_at` / `ts_ms`). The BOS contract must define `ingest_time` as a **projection-assigned** field (stamped when the projector reads the source into the BOS log), and define `event_time` as derived from the source's existing timestamp. This is the single most important schema invariant to call out: **`event_time` comes from the source; `ingest_time` is assigned at projection; they are never equal by construction unless projection is synchronous.**

## Bitemporal / Event-Sourcing Pattern (informs the contract's field set + invariants)

Confirmed against canonical references — D-02 is the textbook-correct model. Vocabulary mapping (include as a glossary in the spec so reviewers can cross-check against standard literature):

| D-02 term (Voss) | Fowler | Snodgrass / SQL:2011 | XTDB | Meaning |
|------------------|--------|----------------------|------|---------|
| `event_time` | actual time | valid time | valid-time | when it occurred in the world |
| `ingest_time` | record time | transaction time | transaction-time | when BOS learned/recorded it |
| outcomes as later events | append-only record history | append to transaction-time | retroactive `put` | corrections/results never mutate the original |
| as-of reconstruction | query at a record date | `AS OF SYSTEM TIME` | `as-of` (ts + tx-ts) | state knowable at a chosen point on both axes |

**Standard invariants the contract should state explicitly** `[CITED: martinfowler.com/articles/bitemporal-history.html, juxt.pro/blog/value-of-bitemporality, infoq.com/news/2018/02/retroactive-future-event-sourced]`:
1. **Record/transaction time (`ingest_time`) is append-only and monotonic** — the past is immutable; you only ever append later knowledge. This is the structural no-leakage guarantee.
2. **Actual/valid time (`event_time`) can be written into the past** — a late-arriving outcome event carries an `event_time` earlier than its `ingest_time`. This is *exactly* "outcomes arrive as separate later events" (D-02).
3. **As-of feature reconstruction = filter on both axes:** to reconstruct the state used for a decision made at time T, select events with `event_time ≤ T` AND `ingest_time ≤ T_decision`. Events whose `ingest_time` is *after* the decision are invisible to it → outcomes provably cannot leak (this is the literal mechanism the contract must specify; InfoQ's "as of" / "viewpoint date vs projection date" is the same idea).
4. **Three projection modes exist** (InfoQ): `as-at` (state at a date, current knowledge), `as-of` (state at a date incl. later retroactive events), `as-of-until` (bounded). BOS3 feature reconstruction is the **as-at** flavor on the decision's knowledge horizon — name the mode explicitly to avoid ambiguity in BOS4/BOS5/BOS15.
5. **Temporal queries should be served by purpose-built projections, not raw replay per query** (NILUS) — but since BOS3 is logical-only and BOS2 (storage) is skipped, the contract states this as a *non-binding implementation note* for the future store, not a BOS3 requirement.

**What to keep OUT** (scope discipline): no storage engine, no index design, no replay-performance/snapshotting decisions (those are BOS2/later — NILUS's snapshot/materialized-view advice is implementation, not contract). BOS3 specifies *fields + invariants + query semantics*, full stop.

## Schema Representation (Claude's Discretion — RECOMMENDATION)

**Recommend: dual artifact.**
1. **Normative human spec** — markdown at `.planning/BOS-EVENT-SCHEMA.md` (sibling to PROTOCOL.md / BOS1's AUDIT-INDEX.md). Prose + tables: envelope, per-category field tables, mapping table, correlation model, invariants, glossary, versioning notes.
2. **Normative machine schema** — **JSON Schema Draft 2020-12** at `.planning/schemas/bos-events.schema.json`.

**Why JSON Schema over Pydantic for the BOS3 deliverable** `[ASSUMED]` (reasoning, not tool-verified):
| Criterion | JSON Schema (Draft 2020-12) | Pydantic v2 models |
|-----------|----------------------------|--------------------|
| Language-agnostic | ✅ Web (TS), Python lab, Rust/Go SDKs all consume it (BOS-ARCH-02 spans TS+Python+Rust/Go) | ❌ Python-only; other tiers must mirror |
| Docs-first fit | ✅ Pure data artifact, no runtime import | ⚠️ Code — implies a runtime home BOS3 doesn't have |
| Discriminated union | ✅ `oneOf` + `discriminator`/const on `type` | ✅ (already used in `server/events.py`) |
| Versioning + migration notes | ✅ `$id` with version, `$comment` migration notes | ⚠️ docstrings, less portable |
| Codegen downstream (BOS4/5/12) | ✅ json-schema-to-{ts,pydantic,rust} all exist | one-directional |
| Matches existing precedent | PROTOCOL.md already exposes the wire union **as JSON Schema** via OpenAPI components (`_EventEnvelope`) | the *source* uses Pydantic, but emits JSON Schema for the contract |

**Decisive point:** PROTOCOL.md's own pattern is "Pydantic in the code, **JSON Schema as the published contract**" (`EventEnvelope` → OpenAPI component → codegen'd Rust enum). BOS3 should publish the *contract* in the same portable form. Pydantic models, if any, are a downstream BOS4-era convenience, not the BOS3 artifact. The planner MAY additionally ship a Pydantic reference module if it wants the validation-test harness in Python — but the JSON Schema is the source of truth.

**Versioning notation (mirror PROTOCOL.md):** top-level `schema_version: 1` (analogue of `v`), breaking changes increment it + add an inline migration note in the markdown spec; additive-only changes (new optional fields, new reserved category) do **not** bump it (the `extra="ignore"` / additive-only divergence rule the codebase already follows). Per-event envelope carries `schema_version` so a consumer can detect drift — exactly as every PROTOCOL.md payload carries `v`.

## Forward-Compatible Envelope (D-01 reserved external categories)

The minimal common envelope must let BOS12 slot in `review`/`CI`/`validation`/`deploy`/`incident` **without a schema-version bump**. Required common fields (every event, all categories — live and reserved):

| Field | Type | Purpose | Source-derivable today? |
|-------|------|---------|-------------------------|
| `schema_version` | int | drift detection (mirrors `v`) | n/a (constant) |
| `event_id` | str | stable unique id | ✅ swarm `id`, run `id`, node `id` |
| `event_type` | str (enum, namespaced e.g. `task.completed`) | discriminator; **namespaced by category** so external categories add values without colliding | ✅ derivable |
| `category` | enum: `session\|swarm\|task\|file\|review\|ci\|validation\|deploy\|incident` | the 4 live + 5 reserved slots — **the taxonomy is fixed now; field detail is not** | ✅/reserved |
| `event_time` | ISO-8601 | valid/actual time (from source) | ✅ from source's timestamp |
| `ingest_time` | ISO-8601 | transaction/record time (assigned at projection) | ⚠️ NEW — projector-assigned |
| `trace_id` | str | root correlation threading the full lineage (D-04) | ⚠️ NEW — derived (join swarm_id/root_id/session id) |
| `parent_event_id` | str? | lineage parent | ✅ partial (`parent_id`, `parent_run_id`, `lineage_parent_id`) |
| `caused_by` | str? | explicit causation pointer (D-04) | ⚠️ NEW — derived |
| `actor` | str? | who/what produced it | ✅ swarm `actor`; ⚠️ missing on watch/some SSE |
| `source_ref` | object | provenance back-pointer to the originating harness record (`{source: "swarm_log\|session\|audit\|sse\|watch", ref: <id/path>}`) — proves D-03 derivation | ✅ constructible |
| `external_identity_ref` | object? | **reserved hook for BOS12** cross-integration identity (D-04 scope note) — present-but-null for all live events | reserved |
| `payload` | object | category/type-specific fields | per-category |

**Forward-compat mechanism (state explicitly in the contract):**
- The **9-value `category` enum is locked now** (the taxonomy stability D-01 demands). External categories already have their enum slot; BOS12 only fills `payload` + adds `event_type` values under that category.
- `payload` is an open object; consumers MUST ignore unknown payload keys (the `extra="ignore"` discipline already in the codebase) → new external fields are additive, no version bump.
- `external_identity_ref` exists from v1 (nullable) so BOS12 identity resolution has a hook with zero schema change.
- Reserved categories ship as **envelope-only stubs** in the JSON Schema (`payload: {}` permitted, documented as "field detail TBD — BOS12") so an external event validates against the envelope today.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event versioning convention | A new bespoke version scheme | Mirror PROTOCOL.md's `v` + inline migration-note rule | Consistency across Voss contracts; reviewers already know it |
| Bitemporal vocabulary | Invent Voss-only time terms | Adopt actual/record ≈ valid/transaction with a glossary | Cross-checkable against SQL:2011 / Fowler / XTDB; avoids reviewer confusion |
| Correlation primitives | A from-scratch ID model | Build on existing `swarm_id` / `root_id` / `parent_run_id` / `parent_id` precedents | The substrate already has lineage; BOS3 unifies, doesn't reinvent |
| Schema serialization format | Custom DSL | JSON Schema Draft 2020-12 | Tooling (validators, codegen) exists; PROTOCOL.md precedent |
| Outcome-leakage prevention | A validation rule bolted on later | Structural: outcomes-as-later-append-only-events + as-of filter on both axes (D-02) | The bitemporal structure *is* the guarantee; a post-hoc rule is weaker |

**Key insight:** BOS3 is almost entirely *naming and unifying things the codebase already does* (append-only logs, replay, lineage, versioned envelopes) plus *adding two derived fields* (`ingest_time`, `trace_id`) and *one reserved hook* (`external_identity_ref`). The risk is over-engineering a storage/replay design that belongs to BOS2/later. Stay at the contract layer.

## Common Pitfalls

### Pitfall 1: Conflating Voss's internal reviewer with the reserved external `review` category
**What goes wrong:** `audit/model.py:ReviewerAssessment` (Voss's own pass/fail/block reviewer) looks like the `review` category, but D-01 reserves `review` for **external** code review (GitHub/GitLab PR review — BOS12). Mapping the internal reviewer into the `review` slot would wrongly fill a reserved slot and create churn when BOS12 arrives.
**How to avoid:** Map the internal reviewer to a **session/task decision** event (it's an internal verdict on a Voss run), and keep `review` envelope-only/reserved. Document the distinction in the mapping table.

### Pitfall 2: Treating `ingest_time` as derivable from sources
**What goes wrong:** Every source has exactly one timestamp; a planner may map `ingest_time` to the source's `ts`/`started_at`, collapsing the two axes and destroying the no-leakage guarantee.
**How to avoid:** Spec `event_time` = source timestamp, `ingest_time` = **assigned by the projector at read time** (explicitly NEW, not source-derived). State the invariant: `ingest_time ≥ event_time`, and for retroactive outcomes `ingest_time > event_time`.

### Pitfall 3: Modifying PROTOCOL.md or the harness
**What goes wrong:** Adding `trace_id`/`ingest_time` to the SSE union or swarm log "to make projection easy" violates D-03 (contract stays decoupled; PROJECT.md bars new coordination infra).
**How to avoid:** All NEW fields are **derived at projection**, defined only in the BOS schema. The mapping table documents *how* each is computed from existing source fields. Zero source edits.

### Pitfall 4: Over-specifying the storage/replay engine
**What goes wrong:** BOS2 is skipped, so a planner might fill the gap with index/snapshot/store decisions, bloating BOS3 and front-running BOS2.
**How to avoid:** Keep storage/replay strictly as non-binding "implementation notes." The contract specifies fields, invariants, and query *semantics* (as-of), not a store.

### Pitfall 5: `watch/backend.py` timestamp + correlation mismatch
**What goes wrong:** Watch events use `ts_ms` (epoch ms) and carry **no** correlation/actor/session — naively mapping them yields uncorrelated, wrong-typed file events.
**How to avoid:** Prefer `RunRecord.changed[]` (correlated, run-scoped) as the primary file source; treat `watch` as best-effort/secondary requiring enrichment (cwd + time-window join). Normalize `ts_ms` → ISO-8601 in the projection. Document both.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-timestamp event logs (Voss swarm log, session records) | Bitemporal (event_time + ingest_time) | BOS3 contract | Enables provable no-leakage as-of reconstruction |
| Mutable state + version history (rejected D-02 alt) | Append-only + outcomes-as-later-events | BOS3 | Stronger leakage guarantee; matches event-sourcing canon |
| Per-subsystem correlation (`swarm_id`, `root_id`, `parent_id`) | Unified `trace_id` + `caused_by` across all categories | BOS3 | Multi-hop lineage task→…→incident becomes traceable |

**Deprecated/outdated:** Snodgrass valid/transaction-time terminology is still standard (SQL:2011) but Fowler now prefers "actual/record" for clarity — the contract should present both and pick one consistently (recommend `event_time`/`ingest_time` as the Voss surface names, glossed to both).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | JSON Schema (Draft 2020-12) is the better normative artifact than Pydantic for this docs-first, multi-language contract | Schema Representation | Low — if the planner prefers Pydantic, both express the same model; JSON Schema can be generated from Pydantic. Either satisfies the deliverable. |
| A2 | Deliverable file location `.planning/BOS-EVENT-SCHEMA.md` + `.planning/schemas/bos-events.schema.json` | Summary / Schema Representation | Low — pattern-matched to PROTOCOL.md + BOS1's `.planning/`-root convention; planner may relocate. |
| A3 | The 9-value `category` enum (4 live + 5 reserved) is the right fixed taxonomy granularity | Forward-Compat Envelope | Medium — if BOS12 needs a category not in the 5 (e.g. "observability" distinct from "incident"), a version bump results. Mitigate: allow a documented reserved `category` extension note. |
| A4 | `watch/backend.py` is lower-fidelity than `RunRecord.changed[]` for file events | Existing Substrate E / Pitfall 5 | Low — both are real sources; relative priority is a planner call, both should be in the mapping. |
| A5 | Internal `ReviewerAssessment` maps to session/task decision, NOT the reserved `review` slot | Pitfall 1 | Medium — if the project later decides internal reviews ARE the `review` category, the mapping shifts. Flag for discuss-phase confirmation. |

## Open Questions

1. **Should the internal Voss reviewer (`ReviewerAssessment`) and gate decisions be in BOS3 at all, or are they BOS4 decision-ledger content?**
   - What we know: they're decision/verdict records with lineage; BOS4 owns the decision ledger (BOS-DATA-02).
   - What's unclear: whether BOS3's `session`/`task` categories include decision-flavored events or only "what happened" events.
   - Recommendation: BOS3 includes them as **events** (a verdict happened) but does NOT model them as *decisions-to-be-scored* (that framing is BOS4). Keep the lineage hook; defer decision semantics. Confirm in planning.

2. **Granularity of `trace_id`: one per top-level user task, or one per swarm?**
   - What we know: D-04 wants a root id threading task→session→swarm-assign→…→incident.
   - What's unclear: a single agent run with no swarm has `swarm_id=None` — what seeds its `trace_id`?
   - Recommendation: `trace_id` = the originating user-task/root-session id; swarm runs inherit it; standalone runs use their session `id`. State the seeding rule explicitly in the correlation model.

3. **Does "file" warrant a first-class category, or is it always a sub-event of task/session?**
   - What we know: D-01 lists `file` as a live field-level category; sources are `RunRecord.changed[]` + watch.
   - Recommendation: keep `file` first-class (D-01 says so) but always carry `parent_event_id`/`trace_id` back to the owning task — a file event is never orphaned.

## Environment Availability

> Docs-first phase. The "dependencies" are doc-generation/validation tooling, not runtime services.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 + venv | Running schema-validation tests | ✓ (project `.venv`) | per project (use `.venv/bin/python`) | — |
| `jsonschema` (PyPI) | Example-event round-trip validation against the JSON Schema | ✗ (not yet installed) | — | Pydantic round-trip if Pydantic chosen; or skip-with-note |

**Missing dependencies with no fallback:** none (this is a docs deliverable; validation tooling is the only need and has a fallback).
**Missing dependencies with fallback:** `jsonschema` — if the planner chooses JSON Schema as normative, a Wave-0 task should `pip install jsonschema` (verify on PyPI first — see Package Legitimacy below) into `.venv` so example-event validation runs; otherwise validation can ride a Pydantic reference module.

## Package Legitimacy Audit

> Only ONE candidate external package, and only if the planner wants automated JSON-Schema validation in tests. The deliverable itself (markdown + .json) needs no packages.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `jsonschema` | PyPI | ~10 yrs (well-established) | very high (top-tier) | github.com/python-jsonschema/jsonschema | not run (offline; ASSUMED) | Approved-pending-verify |

slopcheck was not run in this research session. Per protocol, `jsonschema` is tagged `[ASSUMED]`; the planner should gate its install behind a `checkpoint:human-verify` or run `pip index versions jsonschema` before install. It is a famous, low-risk package (Draft 2020-12 reference validator) — flagged only for procedural correctness, not genuine suspicion.

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Validation Architecture

> nyquist_validation = true in config → this section is REQUIRED.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | project root (existing `tests/` tree) |
| Quick run command | `.venv/bin/python -m pytest tests/planning/test_bos_event_schema.py -x` (file is Wave-0) |
| Full suite command | `.venv/bin/python -m pytest tests/planning/ -x` (or the contract subset) |

Note: this is a **docs/contract** phase, so "tests" validate the *artifact* (schema + spec consistency), not runtime behavior. Validation is lightweight, deterministic, and fast.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BOS-DATA-01 | The JSON Schema is itself valid (lints clean against Draft 2020-12 meta-schema) | unit | `pytest tests/planning/test_bos_event_schema.py::test_schema_is_valid -x` | ❌ Wave 0 |
| BOS-DATA-01 | Every committed example event round-trips: validates against the envelope + its category schema | unit | `pytest tests/planning/test_bos_event_schema.py::test_examples_validate -x` | ❌ Wave 0 |
| BOS-DATA-01 | Bitemporal invariant: every example has both `event_time` and `ingest_time`, and `ingest_time ≥ event_time` | unit | `pytest tests/planning/test_bos_event_schema.py::test_bitemporal_invariant -x` | ❌ Wave 0 |
| BOS-DATA-01 | All 9 categories present in the `category` enum (4 live field-detailed + 5 reserved stubs) | unit | `pytest tests/planning/test_bos_event_schema.py::test_taxonomy_complete -x` | ❌ Wave 0 |
| BOS-DATA-01 | D-03 mapping completeness: every live category (session/swarm/task/file) has ≥1 named source row; every reserved category is marked external/BOS12 | unit (parse the markdown table) | `pytest tests/planning/test_bos_event_schema.py::test_mapping_table_complete -x` | ❌ Wave 0 |
| BOS-DATA-01 | Correlation invariant: every non-root example carries `trace_id`; file events carry `parent_event_id` | unit | `pytest tests/planning/test_bos_event_schema.py::test_correlation_invariant -x` | ❌ Wave 0 |
| BOS-DATA-01 | Reserved hook present: `external_identity_ref` exists (nullable) in the envelope schema | unit | `pytest tests/planning/test_bos_event_schema.py::test_external_identity_hook -x` | ❌ Wave 0 |
| BOS-DATA-01 | Versioning: `schema_version` present on envelope; spec contains a migration-notes section (mirrors PROTOCOL.md) | unit | `pytest tests/planning/test_bos_event_schema.py::test_versioning_present -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/planning/test_bos_event_schema.py -x`
- **Per wave merge:** `.venv/bin/python -m pytest tests/planning/ -x`
- **Phase gate:** all contract tests green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/planning/test_bos_event_schema.py` — the contract-validation tests above (covers BOS-DATA-01)
- [ ] `.planning/schemas/bos-events.schema.json` — the normative JSON Schema (the artifact under test)
- [ ] Example events fixture (e.g. `.planning/schemas/examples/*.json` — at least one per live category + one reserved-stub) — feeds round-trip tests
- [ ] Framework install (only if JSON Schema path chosen): `.venv/bin/pip install jsonschema` (verify on PyPI first)

*If the planner chooses a Pydantic reference module instead of JSON Schema, the same tests run via `model_validate` round-trips and no `jsonschema` install is needed.*

## Security Domain

> `security_enforcement` absent from config = enabled. This is a docs-only schema contract with no runtime, auth, or data handling — security surface is minimal. ASVS categories assessed for completeness.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | no auth in a schema doc |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes (indirectly) | The schema **is** the input-validation contract for downstream ingestion (BOS12). Spec should note: no secrets/PII/credentials in event payloads (PROJECT.md + global CLAUDE.md sensitive-data rule); session redaction precedent exists (`tests/harness/test_session_redaction.py` strips API keys/tokens from SessionRecord/RunRecord — the BOS schema must NOT reintroduce them). |
| V6 Cryptography | no | n/a |

### Known Threat Patterns for a derived event schema
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PII/secret leakage into event payloads | Information disclosure | Schema explicitly forbids secret/credential/PII fields; inherit the existing session-redaction invariant; payload fields enumerated, not free-form dumps. |
| Forged/injected log lines (relevant to the JSONL sources) | Tampering | Already mitigated in source (`swarm/events.py` uses `json.dumps` only, no string formatting — T-V25-01-02); the BOS schema notes events are append-only + immutable (no in-place edit). |

## Sources

### Primary (HIGH confidence)
- Codebase (read 2026-06-18): `voss/harness/swarm/events.py`, `swarm_store.py`, `server/events.py`, `server/sessions.py`, `session.py`, `audit/model.py`, `audit/load.py`, `watch/backend.py` — concrete event field enumeration.
- `.planning/PROTOCOL.md` §1, §6, §12 — versioning + `_EventEnvelope` discriminated-union + additive-only precedent.
- `.planning/PROJECT.md` Constraints §Data + Context §Swarm impact; `.planning/REQUIREMENTS.md` BOS-DATA-01; `.planning/phases/BOS3-.../BOS3-CONTEXT.md` D-01..D-04.

### Secondary (MEDIUM confidence)
- martinfowler.com/articles/bitemporal-history.html — actual/record time, append-only record history, events must be bitemporal.
- juxt.pro/blog/value-of-bitemporality — valid vs transaction time, as-of queries, upstream-fed valid time.
- infoq.com/news/2018/02/retroactive-future-event-sourced — as-at / as-of / as-of-until projection modes; viewpoint vs projection date.
- v1-docs.xtdb.com/concepts/bitemporality — as-of with (valid-time, transaction-time) pair; immutability of transaction time.

### Tertiary (LOW confidence)
- nilus.be/blog/temporal_queries_in_event_stores_in_event_sourcing — purpose-built projections vs raw replay (implementation guidance, out of BOS3 scope; cited for completeness).

## Metadata

**Confidence breakdown:**
- Existing substrate enumeration: HIGH — read directly from source.
- Bitemporal pattern + invariants: HIGH — D-02 confirmed against 4 canonical references.
- Schema representation recommendation (JSON Schema): MEDIUM — sound reasoning + PROTOCOL.md precedent, but a discretionary call (A1).
- Mapping table draft: HIGH for live categories, by-design-reserved for external.
- Validation architecture: HIGH — standard pytest + schema-validation pattern.

**Research date:** 2026-06-18
**Valid until:** ~2026-12-18 (internal substrate is stable; bitemporal patterns are decades-stable; only the codebase enumeration could drift if the harness event shapes change).
