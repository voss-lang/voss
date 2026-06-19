---
phase: BOS2-monorepo-and-stack-architecture
plan: 01
subsystem: architecture
tags: [monorepo, stack, pnpm, turborepo, sqlite, postgres, duckdb, contracts, architecture-decision, docs-first]

# Dependency graph
requires: []
provides:
  - "BOS2-ARCHITECTURE.md — architecture decision doc locking monorepo shape, service/library boundary, language map, pnpm/Turborepo trigger, data stores, migration boundary, shared contracts"
  - "Shape all later BOS implementation phases (BOS3-BOS17) inherit"
affects: [BOS3, BOS4, BOS5, BOS7, BOS11, BOS12]

# Tech tracking
tech-stack:
  added: []
  patterns: ["single polyglot monorepo (pnpm + Cargo + uv) extending to apps/web + services/*", "service-vs-library boundary = deployability", "one-directional SQLite → Postgres sync with offline-first invariant", "V13.1 contracts as drift-gated single source of truth"]

key-files:
  created:
    - .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md
  modified: []

key-decisions:
  - "D-01: Single polyglot monorepo — apps/web (TS) + services/* added to same tree; rejected split cloud repo."
  - "D-02: Service-vs-library boundary = deployability; cloud-vs-local is deploy/security, not a repo split."
  - "D-03: Consolidate on pnpm now (remove package-lock.json); defer Turborepo behind documented trigger (apps/web present AND multiple interdependent JS packages causing measurable CI/build-time pain)."
  - "D-04: SQLite (local-first event log) / Postgres (team-shared) / DuckDB over Parquet (analytics/offline-eval)."
  - "D-05: One-directional SQLite → Postgres sync; desktop stays fully usable offline; shared state is downstream projection."
  - "D-06: contracts/openapi.json + contracts/events.schema.json stay the single schema source of truth; CI drift gate preserved; rejected new IDL (protobuf/TypeSpec)."

patterns-established:
  - "Architecture decision doc as the shape contract later BOS phases inherit — decisions + rationale + rejected alternatives, no code."

requirements-completed: [BOS-ARCH-01, BOS-ARCH-02, BOS-ARCH-03, BOS-ARCH-04]

# Metrics
duration: 1 min
completed: 2026-06-19
---

# Phase BOS2 Plan 01: Monorepo and Stack Architecture Summary

**BOS2-ARCHITECTURE.md: 158-line architecture decision doc locking single-polyglot-monorepo shape (apps/web + services/* in same tree), deployability as service/library boundary, TS/Python/Rust-Tauri/Go language map, pnpm consolidation + named Turborepo trigger, SQLite/Postgres/DuckDB per-layer stores, one-directional SQLite→Postgres sync with offline-first invariant, and V13.1 contracts as drift-gated source of truth.**

## Performance

- **Duration:** ~1 min (docs-only; single subagent handled both tasks sequentially)
- **Started:** 2026-06-19
- **Completed:** 2026-06-19
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- BOS2-ARCHITECTURE.md written with all 11 required sections: Current Monorepo Shape, Target Monorepo Shape, Service vs Library Boundary, Language Ownership, JS Toolchain & Build Orchestration, Data Stores, Migration Boundary, Shared Contracts, Out of Scope, Target Tree, Decision Traceability.
- Every section grounded in locked CONTEXT.md decisions (D-01..D-06) with rationale and rejected alternatives recorded.
- Target Tree shows existing dirs (apps/voss-app, sdk/go, sdk/typescript, crates/voss-*, contracts/, Python harness) + target additions (apps/web, services/*) with deployable/library annotations per D-02.
- Decision Traceability table maps BOS-ARCH-01..04 → D-01..D-06 → doc sections.
- 158 lines (exceeds 80-line minimum); no code, no manifest edits, no migrations.

## Task Commits

No commits made yet — per project Git Safety rules, git write actions require Ben's explicit confirmation. The artifact is written to disk and verified; commit is staged pending approval.

## Files Created/Modified
- `.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md` — 11 sections covering BOS-ARCH-01..04, D-01..D-06, target tree, decision traceability.

## Decisions Made
None — followed plan exactly. All decisions were pre-locked in BOS2-CONTEXT.md (D-01..D-06); the doc records them with rationale.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required (docs-only phase).

## Next Phase Readiness
- BOS2-01 deliverable (architecture decision doc) complete and verified against every acceptance criterion.
- Phase BOS2 complete (1/1 plan). Next per ROADMAP build order: BOS3 (Engineering Event Schema).
- BOS-ARCH-01, BOS-ARCH-02, BOS-ARCH-03, BOS-ARCH-04 are now satisfied. Marking complete in REQUIREMENTS.md.

## Self-Check: PASSED

Automated verification (ran in main context):
- `test -f BOS2-ARCHITECTURE.md` → FILE_EXISTS_OK
- All 11 section headings present → ALL SECTIONS PRESENT
- All values present: apps/web, services/, SQLite, Postgres, DuckDB, contracts/openapi.json, package-lock.json → ALL VALUES PRESENT
- All IDs present: BOS-ARCH-01..04, D-01..D-06 → ALL IDS PRESENT
- Line count: 158 (exceeds 80-line minimum)
- No code/migrations/manifest edits produced.

---
*Phase: BOS2-monorepo-and-stack-architecture*
*Completed: 2026-06-19*