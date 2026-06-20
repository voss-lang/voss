---
phase: BOS3-engineering-event-schema
plan: 01
subsystem: data
tags: [event-schema, bitemporal, json-schema, draft-2020-12, append-only, as-of, point-in-time, contracts, docs-first]

# Dependency graph
requires: []
provides:
  - "bos-events.schema.json — normative JSON Schema (Draft 2020-12): 12-field bitemporal envelope + 4 live category payloads + 5 reserved external stubs"
  - "BOS-EVENT-SCHEMA.md — normative prose+tables spec: envelope, PIT invariants + glossary, 9-category taxonomy, field schemas, D-03 mapping table, D-04 correlation model, versioning"
  - "Point-in-time-correct event contract BOS4 (decision ledger), BOS5 (outcomes), BOS12 (external ingestion) build on"
affects: [BOS4, BOS5, BOS12, BOS15]

# Tech tracking
tech-stack:
  added: []
  patterns: ["bitemporal event envelope (event_time + ingest_time) with append-only immutable log + as-of reconstruction", "discriminated union on category (9-value locked taxonomy: 4 live + 5 reserved)", "projection-derived fields (ingest_time/trace_id/caused_by) not source-carried — D-03 no-source-modification", "JSON Schema Draft 2020-12 as language-agnostic normative contract mirroring PROTOCOL.md v-versioning"]

key-files:
  created:
    - .planning/schemas/bos-events.schema.json
    - .planning/BOS-EVENT-SCHEMA.md
  modified: []

key-decisions:
  - "D-01: 9-value category enum locked (session/swarm/task/file LIVE + review/ci/validation/deploy/incident RESERVED as envelope-only stubs deferred to BOS12)."
  - "D-02: Bitemporal model — event_time (valid/actual, from source) + ingest_time (transaction/record, projection-assigned); append-only immutable; outcomes as separate later events; as-of reconstruction = filter event_time<=T AND ingest_time<=T_decision (no-leakage guarantee)."
  - "D-03: BOS schema is NEW derived analytics event schema; existing harness surfaces (swarm_log/session/audit/sse/watch) are SOURCES that project into BOS events via documented mapping table; PROTOCOL.md and voss/harness/** unchanged."
  - "D-04: Stable entity IDs + root trace_id (seeding rule: originating user-task/root-session id; swarm inherits; standalone uses session id) + parent_event_id/caused_by causation; external_identity_ref reserved for BOS12 cross-integration identity."
  - "Pitfall 1 disambiguation: Voss-internal ReviewerAssessment maps to session/task DECISION event, NOT the reserved external review slot."

patterns-established:
  - "JSON Schema Draft 2020-12 as the normative multi-language contract artifact (TS/Go/Rust/Python codegen downstream)."
  - "Projection-derived fields: ingest_time/trace_id/caused_by defined ONLY in BOS schema, never added to sources (D-03 no-source-modification invariant)."
  - "Versioning mirrors PROTOCOL.md: schema_version=1; breaking bumps + migration note; additive (new optional field / new event_type / filling reserved payload) does NOT bump."

requirements-completed: [BOS-DATA-01]

# Metrics
duration: 1 min
completed: 2026-06-19
---

# Phase BOS3 Plan 01: Engineering Event Schema Summary

**BOS3 event schema contract: 150-line JSON Schema (Draft 2020-12) + 239-line prose spec encoding a 12-field bitemporal envelope, 4 live category payloads (session/swarm/task/file), 5 reserved external stubs, D-03 source→BOS mapping table, D-04 correlation model with trace_id seeding rule, and as-of no-leakage invariants — PROTOCOL.md and voss/harness/** byte-unchanged.**

## Performance

- **Duration:** ~1 min (docs-only; single subagent handled both tasks sequentially)
- **Started:** 2026-06-19
- **Completed:** 2026-06-19
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments
- `bos-events.schema.json` (150 lines): JSON Schema Draft 2020-12, lints clean against the meta-schema. 12-field bitemporal envelope, 4 live category payloads with real source fields (session/swarm/task/file), 5 reserved external stubs (review/ci/validation/deploy/incident) with `$comment` deferring to BOS12, discriminated union on category, PROTOCOL.md-style versioning via `$comment`.
- `BOS-EVENT-SCHEMA.md` (239 lines): normative prose+tables spec mirroring the JSON Schema. 7 sections: common bitemporal envelope table, PIT/bitemporal invariants + glossary (Fowler/SQL:2011/XTDB mapping), 9-category taxonomy, field-level schemas for 4 live categories, D-03 source→BOS mapping table (with Pitfall-1 internal-reviewer disambiguation), D-04 correlation/identity model (trace_id seeding rule), versioning & migration notes.
- Security: spec explicitly forbids secrets/credentials/PII in event payloads; payload fields enumerated; inherits existing session-redaction invariant.
- PROTOCOL.md and voss/harness/** byte-unchanged (verified: `git diff --quiet` exits 0 for both).

## Task Commits

No commits made yet — per project Git Safety rules, git write actions require Ben's explicit confirmation. The artifacts are written to disk and verified; commit is staged pending approval.

## Files Created/Modified
- `.planning/schemas/bos-events.schema.json` — normative JSON Schema (Draft 2020-12): 12-field bitemporal envelope + 4 live payloads + 5 reserved stubs + discriminated union.
- `.planning/BOS-EVENT-SCHEMA.md` — normative prose+tables spec: envelope, invariants + glossary, taxonomy, field schemas, D-03 mapping, D-04 correlation, versioning.

## Decisions Made
None — followed plan exactly. All decisions were pre-locked in BOS3-CONTEXT.md (D-01..D-04); the artifacts encode them. Research file (BOS3-RESEARCH.md) provided authoritative source field mappings — no source re-derivation needed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required (docs-only phase).

## Next Phase Readiness
- BOS3-01 deliverable (event schema contract) complete and verified against every acceptance criterion.
- Next per ROADMAP build order: BOS4 (Decision Ledger Schema) — depends on BOS3 entity IDs + correlation model + bitemporal model.
- BOS-DATA-01 is now satisfied. Marking complete in REQUIREMENTS.md.

## Self-Check: PASSED

Automated verification (ran in main context):
- Task 1: `jsonschema.Draft202012Validator.check_schema` → `schema valid + Draft2020-12 + taxonomy present` (9-value category enum present).
- Task 2: spec content checks → `spec content checks pass` (event_time/ingest_time present, bos-events.schema.json referenced, all 9 categories, mapping sources swarm_log/session/watch present, schema_version + external_identity_ref present).
- `git diff --quiet .planning/PROTOCOL.md` → `PROTOCOL unchanged` (exit 0).
- `git diff --quiet voss/` → `voss unchanged` (exit 0).
- Line counts: schema 150 (≥120 min), spec 239 (≥150 min).

---
*Phase: BOS3-engineering-event-schema*
*Completed: 2026-06-19*