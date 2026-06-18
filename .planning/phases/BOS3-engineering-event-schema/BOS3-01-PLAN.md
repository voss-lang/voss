---
phase: BOS3-engineering-event-schema
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/schemas/bos-events.schema.json
  - .planning/BOS-EVENT-SCHEMA.md
autonomous: true
requirements: [BOS-DATA-01]

must_haves:
  truths:
    - "A reader can determine the exact shape of any session/swarm/task/file BOS event from the contract"
    - "A reader can see which existing harness source every BOS category projects from (D-03 mapping)"
    - "A reader can determine, for any decision event, how to reconstruct as-of state without outcome leakage (D-02)"
    - "External categories (review/ci/validation/deploy/incident) have reserved taxonomy slots usable with no schema-version bump (D-01)"
    - "PROTOCOL.md and all voss/harness/** source files are byte-for-byte unchanged"
  artifacts:
    - path: ".planning/schemas/bos-events.schema.json"
      provides: "Normative JSON Schema (Draft 2020-12): bitemporal envelope + 4 live category payloads + reserved-stub for 5 external categories"
      contains: "https://json-schema.org/draft/2020-12/schema"
      min_lines: 120
    - path: ".planning/BOS-EVENT-SCHEMA.md"
      provides: "Normative prose+tables contract: envelope, PIT/bitemporal invariants, glossary, 9-category taxonomy, field schemas, D-03 mapping table, D-04 correlation model, versioning"
      contains: "ingest_time"
      min_lines: 150
  key_links:
    - from: ".planning/BOS-EVENT-SCHEMA.md"
      to: ".planning/schemas/bos-events.schema.json"
      via: "prose spec documents the same field set the JSON Schema enforces"
      pattern: "bos-events.schema.json"
    - from: ".planning/BOS-EVENT-SCHEMA.md mapping table"
      to: "voss/harness source events"
      via: "D-03 source->BOS projection rows"
      pattern: "swarm_log|session|audit|sse|watch"
---

<objective>
Author the two NORMATIVE contract artifacts for the canonical engineering event
schema: a machine-readable JSON Schema (Draft 2020-12) and the human-readable
prose+tables spec. Together they define the bitemporal, append-only,
as-of-reconstructable BOS event model derived from Voss's existing harness/swarm/
audit/session/watch event substrate.

Purpose: BOS-DATA-01 — establish the point-in-time-correct event contract that
BOS4 (decision ledger), BOS5 (outcomes/reward) and BOS12 (external ingestion)
build on. This is a DOCS-FIRST phase: a contract, not runtime emitters or storage.

Output:
- `.planning/schemas/bos-events.schema.json` (source-of-truth machine contract)
- `.planning/BOS-EVENT-SCHEMA.md` (normative human spec mirroring the schema)
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md
@.planning/phases/BOS3-engineering-event-schema/BOS3-RESEARCH.md
@.planning/phases/BOS3-engineering-event-schema/BOS3-VALIDATION.md

<interfaces>
<!-- Authoritative inputs from BOS3-RESEARCH.md. Use these directly; do NOT
     re-derive source fields by reading the harness — research already enumerated
     them from source on 2026-06-18. Read PROTOCOL.md REFERENCE-ONLY for the
     `v`+migration-note versioning convention to mirror. -->

9-VALUE category enum (LOCKED taxonomy, D-01 — 4 live + 5 reserved):
  session | swarm | task | file | review | ci | validation | deploy | incident

Common envelope fields (RESEARCH §Forward-Compatible Envelope — EVERY event, all categories):
  schema_version (int)            -- drift detection, mirrors PROTOCOL.md `v`
  event_id (str)                  -- stable unique id (from source id)
  event_type (str enum)           -- namespaced discriminator e.g. "task.completed"
  category (enum, the 9 above)
  event_time (ISO-8601)           -- valid/actual time, FROM SOURCE timestamp
  ingest_time (ISO-8601)          -- transaction/record time, PROJECTION-ASSIGNED (NEW, never source-derived)
  trace_id (str)                  -- root correlation, PROJECTION-DERIVED (NEW)
  parent_event_id (str, nullable) -- lineage parent
  caused_by (str, nullable)       -- explicit causation pointer, PROJECTION-DERIVED (NEW)
  actor (str, nullable)
  source_ref (object)             -- {source: swarm_log|session|audit|sse|watch, ref: <id/path>} proves D-03 derivation
  external_identity_ref (object, nullable) -- RESERVED hook for BOS12, present-but-null in v1
  payload (object)                -- category/type-specific

Live-category payload sources (RESEARCH §Existing Event Substrate + DRAFT mapping):
  session: SessionRecord (id, parent_id, started_at, model, cost) + SSE final/status/stream.finalize + RunRecord
  task:    swarm.task/swarm.worker_done (task_id, goal, owned_files, depends_on, summary) + RunRecord (goal, exit_reason in EXIT_REASONS, changed[]) + SSE plan
  swarm:   swarm.create/swarm.assign (swarm_id, task_id, session_id, roster, owned_files, role) + SSE swarm.gate/needs_operator/complete
  file:    RunRecord.changed/inspected/avoided (correlated, PRIMARY) + watch backend.py (ts_ms epoch, NO correlation, best-effort SECONDARY) + SSE tool(fs_*)

Bitemporal glossary mapping (RESEARCH §Bitemporal Pattern — include in spec):
  event_time  = Fowler "actual time"  = SQL:2011 valid time      = XTDB valid-time
  ingest_time = Fowler "record time"  = SQL:2011 transaction time = XTDB transaction-time

Disambiguation (RESEARCH Pitfall 1 + A5): Voss-internal ReviewerAssessment
(audit/model.py pass/fail/block) maps to a SESSION/TASK decision event, NOT the
reserved external `review` slot. Document this in the mapping table.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author bos-events.schema.json (normative JSON Schema, Draft 2020-12)</name>
  <files>.planning/schemas/bos-events.schema.json</files>
  <read_first>
    - .planning/phases/BOS3-engineering-event-schema/BOS3-RESEARCH.md (§Forward-Compatible Envelope for the 12 envelope fields + 9-value category enum; §Existing Event Substrate for live-category payload fields; §Schema Representation for Draft 2020-12 + versioning)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md (D-01 reserved slots; D-02 bitemporal; D-04 correlation/external_identity_ref)
    - .planning/PROTOCOL.md (REFERENCE ONLY — `v` + additive-only divergence convention to mirror; do NOT modify)
  </read_first>
  <action>
    Create `.planning/schemas/bos-events.schema.json` as a JSON Schema Draft 2020-12 document
    (`"$schema": "https://json-schema.org/draft/2020-12/schema"`, versioned `"$id"` e.g.
    `.../bos-events/v1`). Define, per D-01/D-02/D-04 and the RESEARCH envelope:
    (a) a `$defs.envelope` object requiring the 12 common fields listed in <interfaces>
        (schema_version, event_id, event_type, category, event_time, ingest_time, trace_id,
        parent_event_id, caused_by, actor, source_ref, external_identity_ref, payload).
        `category` is an enum of EXACTLY the 9 values (session, swarm, task, file, review, ci,
        validation, deploy, incident). `event_time`/`ingest_time` use `format: date-time`.
        `external_identity_ref` is nullable, present in v1 as the reserved BOS12 hook (D-04).
        `source_ref` requires `{source: enum[swarm_log,session,audit,sse,watch], ref}`.
    (b) `$defs` payload schemas for the 4 LIVE categories (session, swarm, task, file) using the
        real source fields from <interfaces>. Mark `task.exit_reason` against the EXIT_REASONS-style
        enum (done/timeout/interrupt/budget/error). Set `unevaluatedProperties: false` on closed
        payloads but document that payloads are otherwise additive-tolerant (RESEARCH extra=ignore).
    (c) `$defs` for the 5 RESERVED external categories (review, ci, validation, deploy, incident) as
        envelope-only STUBS: `payload: {}` permitted, with a `$comment` "field detail deferred to BOS12"
        on each — so an external event validates against the envelope today with zero version bump (D-01).
    (d) The top-level schema is a `oneOf`/discriminated union on `category` (or `event_type`) binding
        each category to its envelope+payload composition.
    (e) Use `$comment` for the migration note (mirror PROTOCOL.md `v`): "schema_version=1; breaking
        changes increment + add migration note in BOS-EVENT-SCHEMA.md; additive changes do not bump."
    Do NOT modify PROTOCOL.md or any voss/harness/** file. ingest_time/trace_id/caused_by MUST be
    documented (via `$comment` or description) as PROJECTION-DERIVED, not source-carried (D-03).
  </action>
  <verify>
    <automated>.venv/bin/python -c "import json,jsonschema; s=json.load(open('.planning/schemas/bos-events.schema.json')); jsonschema.Draft202012Validator.check_schema(s); cats=set(); [cats.update(d.get('properties',{}).get('category',{}).get('enum',[])) for d in s.get('$defs',{}).values()]; assert {'session','swarm','task','file','review','ci','validation','deploy','incident'}.issubset(cats) or 'session' in json.dumps(s), 'taxonomy check'; print('schema valid + Draft2020-12 + taxonomy present')"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/schemas/bos-events.schema.json` parses as JSON and passes `jsonschema.Draft202012Validator.check_schema` (lints clean against the Draft 2020-12 meta-schema).
    - The `category` enum contains EXACTLY the 9 values (4 live + 5 reserved); none missing, none extra.
    - The envelope `$def` requires all 12 common fields including `event_time` AND `ingest_time` (both `format: date-time`) and the nullable `external_identity_ref` reserved hook.
    - The 4 live categories (session/swarm/task/file) have field-level payload schemas; the 5 external categories are envelope-only stubs with a `$comment` deferring field detail to BOS12.
    - `git diff --quiet .planning/PROTOCOL.md` exits 0 (PROTOCOL.md unchanged) and `git diff --quiet voss/` exits 0 (no harness source touched).
  </acceptance_criteria>
  <done>JSON Schema exists, lints clean against Draft 2020-12, encodes the 12-field bitemporal envelope, 4 live payloads, 5 reserved stubs, and the locked 9-value taxonomy; no source files modified.</done>
</task>

<task type="auto">
  <name>Task 2: Author BOS-EVENT-SCHEMA.md (normative prose+tables spec) with D-03 mapping + D-02 invariants</name>
  <files>.planning/BOS-EVENT-SCHEMA.md</files>
  <read_first>
    - .planning/schemas/bos-events.schema.json (the artifact authored in Task 1 — the spec MUST mirror its field set)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-RESEARCH.md (§Bitemporal Pattern for the glossary + 4 invariants; DRAFT mapping table; Pitfall 1 internal-reviewer disambiguation; §Schema Representation for versioning)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md (D-01..D-04 verbatim, to cite by ID in each section)
    - .planning/PROJECT.md (Constraints §Data line 66 — point-in-time correct, no outcome leakage)
  </read_first>
  <action>
    Create `.planning/BOS-EVENT-SCHEMA.md` as the normative human spec, referencing
    `bos-events.schema.json` as the machine source of truth. Sections (each citing the driving D-ID):
    1. Common bitemporal envelope — a table of the 12 fields (type, purpose, source-derivable today?),
       matching the JSON Schema exactly. Flag `ingest_time`, `trace_id`, `caused_by` as PROJECTION-DERIVED
       and `external_identity_ref` as the RESERVED BOS12 hook (D-02/D-04/D-03).
    2. PIT / bitemporal invariants + glossary (D-02) — state the 4 standard invariants from RESEARCH
       (ingest_time append-only/monotonic; event_time may be written into the past for retroactive outcomes;
       as-of reconstruction = filter event_time<=T AND ingest_time<=T_decision so outcomes provably cannot leak;
       name the as-at projection mode). Include the glossary table mapping event_time/ingest_time to
       Fowler actual/record + SQL:2011 valid/transaction + XTDB. Explicitly tie to PROJECT.md line-66 constraint.
    3. The 9-category taxonomy (D-01) — list all 9; mark session/swarm/task/file LIVE (field-detailed),
       review/ci/validation/deploy/incident RESERVED (envelope-only, "field detail deferred to BOS12").
    4. Field-level schemas for the 4 live categories (session/swarm/task/file) — per-category payload tables
       using the real source fields (mirror the JSON Schema $defs).
    5. D-03 source->BOS mapping table (MANDATORY) — one row per live category naming the concrete source(s)
       (swarm_log, session/RunRecord, sse, watch, audit) and which source fields feed which BOS fields; reserved
       categories marked "external — BOS12". Include the Pitfall-1 note: internal ReviewerAssessment maps to a
       session/task DECISION event, not the reserved `review` slot.
    6. D-04 correlation/identity model — stable entity IDs; trace_id seeding rule (originating user-task/root-session
       id; swarm runs inherit; standalone runs use session id); parent_event_id/caused_by causation; external_identity_ref
       reserved for BOS12. Within-Voss only.
    7. Versioning & migration notes (mirror PROTOCOL.md) — schema_version=1; breaking bumps + migration note here;
       additive (new optional field / new event_type under an existing category / filling a reserved payload) does NOT bump.
    Do NOT modify PROTOCOL.md or any voss/harness/** file.
  </action>
  <verify>
    <automated>.venv/bin/python -c "t=open('.planning/BOS-EVENT-SCHEMA.md').read(); import re; body='\n'.join(l for l in t.splitlines() if not l.strip().startswith('#')); assert 'event_time' in t and 'ingest_time' in t, 'bitemporal fields'; assert 'bos-events.schema.json' in t, 'links machine schema'; assert all(c in t for c in ['session','swarm','task','file','review','ci','validation','deploy','incident']), 'all 9 categories'; assert all(s in body for s in ['swarm_log','session','watch']), 'mapping sources'; assert 'schema_version' in t, 'versioning'; assert 'external_identity_ref' in t, 'reserved hook'; print('spec content checks pass')"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/BOS-EVENT-SCHEMA.md` exists and references `bos-events.schema.json` as the machine source of truth.
    - All 9 category names appear; the 4 live are marked field-detailed, the 5 external are marked reserved/deferred-to-BOS12.
    - The envelope field table documents both `event_time` and `ingest_time`, with `ingest_time`/`trace_id`/`caused_by` labeled projection-derived and `external_identity_ref` labeled reserved.
    - A D-03 mapping table is present with a row per live category naming concrete sources (at minimum swarm_log, session, watch appear in table body) and reserved categories marked external/BOS12; the internal-reviewer disambiguation note is present.
    - The bitemporal invariants section states the as-of no-leakage filter and ties to PROJECT.md's point-in-time constraint; a `schema_version` versioning/migration section is present.
    - `git diff --quiet .planning/PROTOCOL.md` exits 0 and `git diff --quiet voss/` exits 0.
  </acceptance_criteria>
  <done>The prose spec exists, mirrors the JSON Schema field set, documents the bitemporal/PIT invariants + glossary, the full 9-category taxonomy with live/reserved split, the mandatory D-03 mapping table, the D-04 correlation model, and PROTOCOL.md-style versioning; no source files modified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| future projector -> BOS event log | Untrusted/raw harness source records cross into the BOS log; the schema IS the validation contract for that future boundary (BOS12). No runtime crosses it in BOS3. |
| spec author -> repo source files | The plan must NOT cross into PROTOCOL.md or voss/harness/** (D-03 read-only constraint). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-BOS3-01 | Information disclosure | event `payload` field set | mitigate | Spec explicitly forbids secrets/credentials/PII in payloads; payload fields enumerated, not free-form dumps; inherit existing session-redaction invariant (RESEARCH §Security). Documented in BOS-EVENT-SCHEMA.md. |
| T-BOS3-02 | Tampering | normative source artifacts (PROTOCOL.md / voss harness) | mitigate | Acceptance criteria assert `git diff --quiet` for PROTOCOL.md and voss/; all NEW fields are projection-derived, defined only in the BOS schema (D-03). |
| T-BOS3-03 | Tampering | append-only event log semantics | accept/mitigate | Contract states events are append-only + immutable (no in-place edit); outcomes arrive as separate later events. Structural, not runtime-enforced in BOS3 (logical-only). |
| T-BOS3-SC | Tampering | package installs | accept | No package-manager installs in this plan; `jsonschema` 4.26.0 already present in `.venv`. No legitimacy gate needed. |
</threat_model>

<verification>
Run the per-task automated checks. After both tasks:
- `.venv/bin/python -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('.planning/schemas/bos-events.schema.json')))"` — schema lints clean.
- Both artifacts exist; spec references the schema; 9-category taxonomy present in both.
- `git diff --quiet .planning/PROTOCOL.md && git diff --quiet voss/` — no source modified.
</verification>

<success_criteria>
- JSON Schema (Draft 2020-12) authored, lints clean, encodes 12-field bitemporal envelope + 4 live payloads + 5 reserved stubs + locked 9-value taxonomy.
- Prose spec authored, mirrors the schema, documents PIT/bitemporal invariants + glossary, taxonomy, mandatory D-03 mapping table, D-04 correlation model, versioning.
- BOS-DATA-01 contract artifacts exist and are internally consistent.
- PROTOCOL.md and voss/harness/** unchanged.
</success_criteria>

<output>
Create `.planning/phases/BOS3-engineering-event-schema/BOS3-01-SUMMARY.md` when done.
</output>
