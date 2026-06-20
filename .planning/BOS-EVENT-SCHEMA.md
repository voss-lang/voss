# BOS Engineering Event Schema — v1

**Created:** 2026-06-19
**Status:** Contract (docs-first). Breaking changes require a `schema_version` bump + a migration note in §7. Additive changes do NOT bump.
**Machine source of truth:** [`.planning/schemas/bos-events.schema.json`](schemas/bos-events.schema.json) (JSON Schema Draft 2020-12). This document is the normative human spec; where the two disagree, the JSON Schema is authoritative.
**Driving decisions:** D-01 (taxonomy), D-02 (point-in-time correctness), D-03 (derived schema + mapping table), D-04 (correlation/identity) — see `BOS3-CONTEXT.md`.
**Scope:** within-Voss correlation only. Cross-integration identity resolution is BOS12. No runtime emitters, no ingestion pipeline, no storage engine — those are later phases. BOS3 references but does **NOT** modify `PROTOCOL.md` or any `voss/harness/**` file.

---

## 1. Common bitemporal envelope (D-01, D-02, D-03, D-04)

Every event of every category carries the **12 common fields** below. The envelope is defined in `$defs.envelope` of `bos-events.schema.json` and required on every event via `allOf`.

| # | Field | Type | Purpose | Source-derivable today? |
|---|-------|------|---------|--------------------------|
| 1 | `schema_version` | int (const 1) | Drift detection; mirrors PROTOCOL.md `v` | n/a (constant) |
| 2 | `event_id` | str | Stable unique id (from source id) | ✅ swarm `id`, run `id`, node `id` |
| 3 | `event_type` | str (namespaced, e.g. `task.completed`) | Discriminator; namespaced by category so external categories add values without colliding | ✅ derivable |
| 4 | `category` | enum (9 values — see §3) | Taxonomy discriminator | ✅/reserved |
| 5 | `event_time` | ISO-8601 date-time | Actual/valid time — when it occurred in the world. **FROM SOURCE** timestamp | ✅ from source's timestamp |
| 6 | `ingest_time` | ISO-8601 date-time | Transaction/record time — when BOS recorded it. **PROJECTION-DERIVED** (D-03); never source-carried. Invariant `ingest_time ≥ event_time`; for retroactive outcomes `ingest_time > event_time` | ⚠️ NEW — projector-assigned |
| 7 | `trace_id` | str | Root correlation threading the full lineage (D-04). **PROJECTION-DERIVED** | ⚠️ NEW — derived (join of swarm_id / root_id / session id) |
| 8 | `parent_event_id` | str, nullable | Lineage parent; null at a root event | ✅ partial (`parent_id`, `parent_run_id`, `lineage_parent_id`) |
| 9 | `caused_by` | str, nullable | Explicit causation pointer (D-04). **PROJECTION-DERIVED**; null when no explicit cause | ⚠️ NEW — derived |
| 10 | `actor` | str, nullable | Who/what produced it (`operator` / `coordinator` / `builder` / `system`) | ✅ swarm `actor`; ⚠️ missing on watch / some SSE |
| 11 | `source_ref` | object `{source, ref}` | Provenance back-pointer proving D-03 derivation. `source ∈ {swarm_log, session, audit, sse, watch}`; `ref` = source-local id/path | ✅ constructible |
| 12 | `external_identity_ref` | object, nullable | **RESERVED hook for BOS12** cross-integration identity (D-04 scope note). Present-but-null for all live (v1) events | reserved |
| 13 | `payload` | object | Category/type-specific fields (see §4 / §5) | per-category |

**Projection-derived fields (D-03 — never source-carried, never written back to sources):** `ingest_time`, `trace_id`, `caused_by`. These are populated **at projection time** when the projector reads a source record into the BOS log. Adding them to `PROTOCOL.md` or the harness would violate D-03 / PROJECT.md "BOS observes… rather than create new coordination infrastructure."

**Reserved hook (D-04):** `external_identity_ref` is present-but-null in v1 so BOS12 cross-integration identity resolution has a structural hook with zero schema change.

**Security:** payloads MUST NOT carry secrets, credentials, or PII. Payload fields are **enumerated**, not free-form dumps (see §4/§5). The schema inherits Voss's existing session-redaction invariant (`tests/harness/test_session_redaction.py` strips API keys/tokens from `SessionRecord`/`RunRecord`); the BOS projection MUST NOT reintroduce them. File-category payloads carry paths only — never file contents.

---

## 2. Point-in-time / bitemporal invariants + glossary (D-02)

The event log is **append-only and immutable**. No in-place mutation of past events. Outcomes arrive as **separate later events**, never by mutating the originating event/state. This is the structural guarantee that outcomes cannot leak into the state used to make the original recommendation.

### 2.1 Glossary

| D-02 term (Voss) | Fowler | Snodgrass / SQL:2011 | XTDB | Meaning |
|------------------|--------|----------------------|------|---------|
| `event_time` | actual time | valid time | valid-time | when it occurred in the world |
| `ingest_time` | record time | transaction time | transaction-time | when BOS learned/recorded it |
| outcomes as later events | append-only record history | append to transaction-time | retroactive `put` | corrections/results never mutate the original |
| as-of reconstruction | query at a record date | `AS OF SYSTEM TIME` | `as-of` (ts + tx-ts) | state knowable at a chosen point on both axes |

### 2.2 Standard invariants (D-02)

1. **`ingest_time` is append-only and monotonic.** The past is immutable; you only ever append later knowledge. This is the structural no-leakage guarantee.
2. **`event_time` may be written into the past.** A late-arriving outcome event carries an `event_time` earlier than its `ingest_time`. This is exactly "outcomes arrive as separate later events" (D-02). Enforced structurally: `ingest_time ≥ event_time`, and for retroactive outcomes `ingest_time > event_time`.
3. **As-of feature reconstruction = filter on both axes.** To reconstruct the state used for a decision made at time `T`, select events with `event_time ≤ T` AND `ingest_time ≤ T_decision`. Events whose `ingest_time` is *after* the decision are invisible to it → **outcomes provably cannot leak**. This is the literal mechanism PROJECT.md (Constraints §Data, line 66) demands: *"Features must be point-in-time correct; outcomes cannot leak into the state used to make the original recommendation."* The bitemporal structure *is* the guarantee — not a validation rule bolted on later.
4. **Projection mode = `as-at`.** BOS3 feature reconstruction is the **as-at** flavor on the decision's knowledge horizon (state at a date, *current knowledge* — i.e. bounded by both `event_time ≤ T` and `ingest_time ≤ T_decision`). Named explicitly to avoid ambiguity with `as-of` (includes later retroactive events) and `as-of-until` in BOS4/BOS5/BOS15.

**Non-binding implementation note (out of BOS3 scope):** temporal queries should be served by purpose-built projections, not raw replay per query — but storage/index/snapshot design belongs to BOS2/later, not this contract.

---

## 3. The 9-category taxonomy (D-01)

The `category` enum is **locked now** (9 values). External categories already have their slot; BOS12 only fills `payload` + adds `event_type` values under that category — no version bump.

| Category | Status | Field detail |
|----------|--------|--------------|
| `session` | **LIVE** | field-detailed (see §4) |
| `swarm` | **LIVE** | field-detailed (see §4) |
| `task` | **LIVE** | field-detailed (see §4) |
| `file` | **LIVE** | field-detailed (see §4) |
| `review` | **RESERVED** | envelope-only stub — **field detail deferred to BOS12** |
| `ci` | **RESERVED** | envelope-only stub — **field detail deferred to BOS12** |
| `validation` | **RESERVED** | envelope-only stub — **field detail deferred to BOS12** |
| `deploy` | **RESERVED** | envelope-only stub — **field detail deferred to BOS12** |
| `incident` | **RESERVED** | envelope-only stub — **field detail deferred to BOS12** |

Reserved categories ship in the JSON Schema as `$defs.payload.reserved` (`payload: {}` permitted, `additionalProperties: true`, `$comment` "field detail deferred to BOS12") so an external event validates against the envelope today with zero version bump.

---

## 4. Field-level schemas for the 4 live categories (session / swarm / task / file)

Each payload is a `$defs.payload.<category>` object in `bos-events.schema.json`. Payloads are closed (`unevaluatedProperties: false` on the envelope) but **additive-tolerant**: consumers MUST ignore unknown payload keys (mirrors the codebase's `extra="ignore"` discipline) → new optional fields are additive, no version bump.

### 4.1 `session` payload

Sources: `SessionRecord` (`session.py`) + SSE `final` / `status` / `stream.finalize` + `RunRecord`.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `session_id` | str | `SessionRecord.id` | required |
| `parent_session_id` | str, nullable | `SessionRecord.parent_id` | fork lineage |
| `started_at` | date-time | `SessionRecord.started_at` | required |
| `ended_at` | date-time, nullable | `SessionRecord.updated_at` / run end | |
| `model` | str, nullable | `SessionRecord.model` | |
| `total_cost_usd` | number ≥ 0 | `SessionRecord.total_cost_usd` | |
| `turn_count` | int ≥ 0 | `len(SessionRecord.turns)` | |
| `tokens` | object (ints ≥ 0), optional | SSE `status.tokens` | input/output/cache |
| `confidence` | number [0,1], nullable | SSE `final.confidence` / `stream.finalize.confidence` | |
| `ctx_pct` | number [0,100], nullable | SSE `status.ctx_pct` | |

### 4.2 `swarm` payload

Sources: swarm log `swarm.create` / `swarm.assign` (`swarm_store.py`) + SSE `swarm.gate` / `swarm.needs_operator` / `swarm.complete`.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `swarm_id` | str | swarm envelope `swarm_id` | required |
| `task_id` | str, nullable | `swarm.task` / `swarm.assign` payload | |
| `session_id` | str, nullable | `swarm.assign` / SSE `swarm.*` | |
| `goal` | str, nullable | `swarm.create.goal` | |
| `cwd` | str, nullable | `swarm.create.cwd` | |
| `roster` | array<str> | `swarm.create.roster` | |
| `owned_files` | array<str> | SSE `swarm.assign.owned_files` | |
| `role` | str, nullable | SSE `swarm.assign.role` | |
| `gate_type` | enum `{ownership_denied, reviewer_reject}`, nullable | SSE `swarm.gate.gate_type` | decision/outcome |
| `gate_detail` | str, nullable | SSE `swarm.gate.detail` | |
| `tool_name` | str, nullable | SSE `swarm.needs_operator.tool_name` | |
| `tool_path` | str, nullable | SSE `swarm.needs_operator.path` | |
| `task_count` | int ≥ 0, nullable | SSE `swarm.complete.task_count` | |
| `summary` | str, nullable | `swarm.create` / `swarm.complete` summary | |

### 4.3 `task` payload

Sources: swarm `swarm.task` / `swarm.worker_done` + `RunRecord` (goal, `exit_reason` ∈ EXIT_REASONS, `changed[]`) + SSE `plan`.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `task_id` | str | `swarm.task.task_id` | required |
| `session_id` | str, nullable | `swarm.assign.session_id` / `RunRecord` | |
| `swarm_id` | str, nullable | swarm envelope `swarm_id` | |
| `run_id` | str, nullable | `RunRecord.id` | when the task is an agent run |
| `goal` | str | `swarm.task.goal` / `RunRecord.goal` | required |
| `owned_files` | array<str> | `swarm.task.owned_files` | |
| `depends_on` | array<str> | `swarm.task.depends_on` | |
| `exit_reason` | enum `{done, timeout, interrupt, budget, error}`, nullable | `RunRecord.exit_reason` (EXIT_REASONS) | task-outcome enum |
| `changed` | array<str> | `RunRecord.changed[]` | paths |
| `summary` | str, nullable | `swarm.worker_done.summary` | |
| `cost_usd` | number ≥ 0, nullable | `RunRecord.cost_usd` / SSE `final.cost_usd` | |
| `confidence` | number [0,1], nullable | SSE `plan.confidence` / `final.confidence` | |
| `plan_steps` | array<object>, optional | SSE `plan.steps[]` | additive shape |

### 4.4 `file` payload

**PRIMARY** source: `RunRecord.changed` / `inspected` / `avoided` (correlated, run-scoped). **SECONDARY** source: `watch/backend.py` log (`ts_ms` epoch ms, **NO** correlation — best-effort, requires cwd + time-window enrichment). SSE `tool` (`fs_*`).

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `path` | str | `RunRecord.changed[]` / watch `path` / SSE `tool.args` | required |
| `operation` | enum `{created, modified, deleted, moved, inspected, avoided}` | watch `event_type` / `RunRecord` inspected/avoided | required |
| `src_path` | str, nullable | watch `src_path` (moved) | |
| `task_id` | str, nullable | `RunRecord` correlation | null for uncorrelated watch events (best-effort) |
| `session_id` | str, nullable | `RunRecord` / enriched watch | |
| `run_id` | str, nullable | `RunRecord.id` | |
| `swarm_id` | str, nullable | swarm context | |
| `ts_ms` | int ≥ 0, nullable | watch `ts_ms` | raw epoch-ms; normalized to `event_time` by the projection (Pitfall 5) |
| `diff_summary` | str, nullable | `RunRecord.diff_summary` | |
| `tool_name` | str, nullable | SSE `tool.name` (`fs_write`/`fs_edit`/`fs_edit_many`) | |

**File events are never orphaned:** `trace_id` + `parent_event_id` always thread back to the owning task. Watch-sourced events with no correlation are best-effort and must be enriched (cwd + time-window join) before promotion to a correlated file event.

---

## 5. D-03 source → BOS mapping table (MANDATORY)

One row per live category naming the concrete source(s) and which source fields feed which BOS fields. Reserved categories are marked external — BOS12.

| BOS category | Concrete source(s) | Source fields → BOS fields | Projection-derived (NEW, D-03) |
|--------------|---------------------|----------------------------|--------------------------------|
| **session** | `session` (`SessionRecord`), `sse` (`final`/`status`/`stream.finalize`), `session` (`RunRecord`) | `SessionRecord.id`→`event_id`,`session_id`; `started_at`→`event_time`,`started_at`; `parent_id`→`parent_session_id`,`parent_event_id`(partial); `model`→`model`; `total_cost_usd`→`total_cost_usd`; SSE `final.confidence`→`confidence`; SSE `status.tokens`/`ctx_pct`→`tokens`/`ctx_pct`; `RunRecord`→`task` events | `ingest_time` (projector-assigned); `trace_id` (seed = root-session id); `caused_by` (from parent session/run) |
| **swarm** | `swarm_log` (`swarm.create`/`swarm.assign`), `sse` (`swarm.gate`/`swarm.needs_operator`/`swarm.complete`) | swarm envelope `id`→`event_id`; `swarm_id`→`swarm_id`,`trace_id`(seed for swarm root); `ts`→`event_time`; `actor`→`actor`; `swarm.create.{goal,cwd,roster}`→payload; SSE `swarm.assign.{owned_files,role}`→payload; SSE `swarm.gate.{gate_type,detail}`→payload; SSE `swarm.complete.{task_count,summary}`→payload | `ingest_time`; `trace_id` (swarm runs inherit originating user-task trace); `caused_by` (swarm.create ← user task; swarm.assign ← swarm.create) |
| **task** | `swarm_log` (`swarm.task`/`swarm.worker_done`), `session` (`RunRecord`), `sse` (`plan`) | `swarm.task.task_id`→`event_id`(per-task) or `RunRecord.id`→`event_id`; `RunRecord.started_at`→`event_time`; `swarm.task.{goal,owned_files,depends_on}`→payload; `RunRecord.{goal,changed,exit_reason,cost_usd,diff_summary}`→payload; SSE `plan.{confidence,steps}`→payload | `ingest_time`; `trace_id` (inherit swarm/user-task); `caused_by` (task ← swarm.assign; worker_done ← task) |
| **file** | `session` (`RunRecord.changed`/`inspected`/`avoided`) — PRIMARY; `watch` (`backend.py` log) — SECONDARY; `sse` (`tool` fs_*) | `RunRecord.changed[]`→`path`,`operation=modified`; `inspected[]`→`operation=inspected`; `avoided[]`→`operation=avoided`; `RunRecord.id`→`run_id`,`parent_event_id`; watch `path`→`path`; watch `event_type`→`operation`; watch `ts_ms`→`ts_ms` (normalized to `event_time`); watch `src_path`→`src_path`; SSE `tool.{name,args}`→`tool_name`,`path` | `ingest_time`; `trace_id` (inherit owning task/session; watch requires cwd+time-window enrichment); `caused_by` (file ← task/run); `actor` (missing on watch — enriched or null) |
| **review** | external — BOS12 | (reserved) | `external_identity_ref` populated by BOS12 |
| **ci** | external — BOS12 | (reserved) | external identity BOS12 |
| **validation** | external — BOS12 (NB: `RunRecord.validation[]` is an *internal* validation precedent only, not this slot) | (reserved) | external identity BOS12 |
| **deploy** | external — BOS12 | (reserved) | external identity BOS12 |
| **incident** | external — BOS12 | (reserved) | external identity BOS12 |

### 5.1 Pitfall-1 disambiguation: Voss-internal ReviewerAssessment

`voss/harness/audit/model.py:ReviewerAssessment` (`conf, source, tier, verdict ∈ {pass, fail, block}, notes, evidence_refs[]`) is Voss's **internal** reviewer verdict on a run. It is **NOT** the reserved external `review` category (which D-01 reserves for external GitHub/GitLab PR review — BOS12). Mapping the internal reviewer into the `review` slot would wrongly fill a reserved slot and create churn when BOS12 arrives.

**Correct mapping:** `ReviewerAssessment` projects to a **`session` or `task` decision event** (an internal verdict happened on a Voss run) — e.g. `event_type = "task.reviewed"` or `session.reviewed`, category `task`/`session`, carrying `verdict`, `confidence` (from `conf`), `evidence_refs` in the payload. The reserved `review` category stays envelope-only until BOS12. Likewise `RoutingRationale` / `KillRecord` / `RescopeRecord` / `LivenessEvent` from `audit/model.py` project into `session`/`task`/`swarm` events (they have lineage via `root_id`/`parent_run_id`), never into reserved external slots.

---

## 6. D-04 correlation / identity model

**Stable entity IDs.** Each entity (task, session, swarm-assignment, file event, …) has a stable id carried as `event_id`. Sources already provide these: swarm `id` (`uuid4().hex[:8]`), `RunRecord.id`, `SessionRecord.id` (`uuid4().hex[:12]`), `AuditNode.id`.

**`trace_id` seeding rule (D-04):**
- **Originating user-task / root session** seeds `trace_id`. A user-initiated task or a root session (no `parent_id`) seeds a new trace.
- **Swarm runs inherit** the originating user-task's `trace_id` (threaded through `swarm.create` → `swarm.assign` → tasks → files).
- **Standalone runs** (a single agent run with no swarm, `swarm_id = None`) use their **session `id`** as `trace_id`.
- `trace_id` is **PROJECTION-DERIVED** (D-03) — never written back to sources. It is the LEM "document" boundary (every event in a lineage resolves to one trace id).

**Causation pointers:**
- `parent_event_id` — structural lineage parent (from `parent_id` / `parent_run_id` / `lineage_parent_id`). Null at a root event.
- `caused_by` — explicit causation pointer (D-04), **PROJECTION-DERIVED**. Distinct from `parent_event_id` when causation is not the immediate structural parent (e.g. a `task.reviewed` event caused_by the run that produced the artifact). Null when no explicit cause.

**External identity (D-04 scope note):** `external_identity_ref` is **reserved for BOS12** cross-integration identity resolution (e.g. same human across Git/PM/CI accounts). Present-but-null for all live (v1) events. Within-Voss correlation only in BOS3.

**No FK-joins-only, no implicit time+session** (D-04 rejected alternatives): multi-hop lineage (task → session → swarm-assign → files → review → CI → deploy → incident) requires explicit `trace_id` + `caused_by`, not lossy time+session inference.

---

## 7. Versioning & migration notes (mirror PROTOCOL.md)

Mirrors `PROTOCOL.md` §1: *"Every JSON body carries `v: 1`. A breaking change increments `v` and ships a migration note here."* The BOS schema uses `schema_version` (int) on the envelope in the same role.

**Current:** `schema_version = 1`.

**Breaking changes** (require `schema_version` bump + a migration note appended below):
- Removing or renaming a required envelope field.
- Narrowing the `category` enum (removing a value) or changing a field's type incompatibly.
- Changing a closed payload's required set in a way that invalidates previously-valid events.

**Additive changes** (do NOT bump `schema_version`):
- Adding an optional field to an envelope or payload (consumers ignore unknown keys — `extra="ignore"` discipline).
- Adding a new `event_type` value under an **existing** category (namespaced, no collision).
- **Filling a reserved payload** (`review`/`ci`/`validation`/`deploy`/`incident`) — BOS12 populates `$defs.payload.reserved` → a concrete `$defs.payload.review` etc. without a version bump, because the category slot already exists and `payload` was always open.

### Migration notes
*(none yet — v1)*

---

## Security

- Payloads MUST NOT carry secrets, credentials, or PII. Payload fields are **enumerated** (§4/§5), not free-form dumps.
- The schema inherits Voss's existing session-redaction invariant (`tests/harness/test_session_redaction.py` strips API keys/tokens from `SessionRecord`/`RunRecord`). The projection MUST NOT reintroduce them.
- File-category payloads carry **paths only** — never file contents.
- Events are append-only + immutable (D-02) — no in-place edit, mitigating tampering/injection (source JSONL already uses `json.dumps` only, no string formatting).

---

*Implements BOS-DATA-01. Bound by D-01..D-04 (BOS3-CONTEXT.md) and PROJECT.md Constraints §Data. Does not modify PROTOCOL.md or any `voss/harness/**` file.*