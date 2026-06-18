# Phase BOS2: Monorepo and Stack Architecture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS2-monorepo-and-stack-architecture
**Areas discussed:** Repo topology & service boundaries, JS toolchain + Turborepo evolution, Data-store choices + migration boundary, Shared-contract source of truth

---

## Repo Topology & Service Boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| Single polyglot monorepo | Add apps/web (TS) + services/* (backend/event) into this repo alongside crates/*, sdk/*, Python; deployable dirs = services, rest = libraries; cloud/local is a deploy concern | ✓ |
| Split cloud repo | Local-first here; web + backend in a separate cloud repo; cleaner deploy/security boundary but duplicates contract + codegen tooling | |
| You decide | Infer topology from constraints | |

**User's choice:** Single polyglot monorepo (recommended)
**Notes:** Aligns with PROJECT.md "preserve the monorepo before introducing new services." Service-vs-library boundary keyed on deployability (D-02).

---

## JS Toolchain + Turborepo Evolution

| Option | Description | Selected |
|--------|-------------|----------|
| Consolidate pnpm now, defer Turbo | Remove package-lock.json; single pnpm-workspace; adopt Turborepo only when a documented trigger hits | ✓ |
| Adopt Turborepo now | Add turbo.json + task graph/caching immediately | |
| You decide | Pick trajectory + document trigger | |

**User's choice:** Consolidate on pnpm now, defer Turborepo (recommended)
**Notes:** Repo currently carries BOTH pnpm-lock.yaml and package-lock.json — D-03 resolves the duplication and requires the doc to name the Turborepo trigger explicitly.

---

## Data-Store Choices + Migration Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite local / Postgres shared / DuckDB+Parquet eval | Local-first event log = SQLite; team-shared = Postgres; analytics/offline-eval = DuckDB over Parquet; boundary = export/sync SQLite→Postgres at a defined sync point | ✓ |
| Document options only, defer engine pick to BOS3-5 | Name layers + boundary rule, leave engines to data-schema phases | |
| You decide | Choose engines + boundary | |

**User's choice:** SQLite local / Postgres shared / DuckDB+Parquet eval (recommended)
**Notes:** Offline-first desktop is the invariant; shared state is a one-directional projection (D-05). Concrete schema deferred to BOS3-5.

---

## Shared-Contract Source of Truth

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing V13.1 contract artifact | openapi.json + event-union snapshot stay the single source; codegen TS/Go/Rust/Python; keep CI drift gate | ✓ |
| New broader contracts package | Fresh IDL (protobuf/TypeSpec) in contracts/ superseding V13.1 | |
| You decide | Pick mechanism + document migration | |

**User's choice:** Extend existing V13.1 contract artifact (recommended)
**Notes:** Builds on shipped, drift-gated infrastructure rather than re-tooling working codegen.

---

## Claude's Discretion

- Architecture-doc structure/format.
- Exact wording of the Turborepo trigger condition (within the "documented, not guessed" constraint).
- How the doc visualizes the target tree / layer map.

## Deferred Ideas

- Concrete event-store schema / table design → BOS3-5.
- Backend service deploy/runtime target → out of v0.2 scope per PROJECT.md.
- Contract versioning / breaking-change policy beyond the drift gate → contract-owning implementation phase.
- Web-vs-desktop responsibility map → BOS-PROD-04 / BOS7.
- CI build-graph topology specifics → follows the Turborepo trigger.
