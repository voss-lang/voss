# BOS2 — Monorepo and Stack Architecture

**Phase:** BOS2-monorepo-and-stack-architecture
**Scope:** Architecture decision doc covering requirements BOS-ARCH-01..04.
**Status:** Decisions + rationale only. No code, no scaffolding, no migrations, no manifest edits.
**Locked decisions:** D-01..D-06 (see `BOS2-CONTEXT.md`). This doc records them; it does not re-decide them.

---

## Current Monorepo Shape (BOS-ARCH-01)

Voss is already a single polyglot monorepo housing three coexisting workspaces, each managed by its own toolchain:

- **pnpm workspace** — `pnpm-workspace.yaml` declares `packages: ["apps/*"]`. The glob covers only `apps/*` today; it does NOT yet include `services/*` or `sdk/*`. The JS dependency graph is rooted at `apps/voss-app` (the Tauri desktop shell's web side).
- **Cargo workspace** — `Cargo.toml` (resolver v2) members: `crates/voss-cli`, `crates/voss-agent`, `crates/voss-providers`, `crates/voss-auth`, `crates/voss-tools`, `crates/voss-render`, `crates/voss-bridge`, `crates/voss-app-core`, `crates/voss-tui`, `crates/voss-sdk`, and `apps/voss-app/src-tauri` (the Tauri Rust backend). Ten `crates/voss-*` libraries plus the desktop app's native slice share one workspace.
- **uv / Python workspace** — `pyproject.toml` (name=`voss`, version=`0.1.1`, requires-python>=3.11) with `uv.lock` owns the Python harness/runtime, learning/eval deps, and the optional FastAPI+SSE harness server.

Alongside the three workspaces the repo carries:

- `apps/voss-app` — the Tauri desktop ADE (deployable unit, Rust + TypeScript).
- `sdk/go` and `sdk/typescript` — established SDK trees in Go and TypeScript respectively.
- `contracts/` — the shared schema source of truth (see § Shared Contracts).
- `crates/voss-*` — the ten Rust libraries enumerated above.

**Latent dual-lockfile state:** BOTH `pnpm-lock.yaml` (95,536 bytes) and `package-lock.json` (28,888 bytes) are present at the repo root. This is the npm/pnpm split D-03 resolves. No `services/` directory exists yet. No `apps/web` exists yet.

## Target Monorepo Shape (BOS-ARCH-01, D-01)

Per D-01, the future web app and backend/event-ledger land INSIDE the same single polyglot monorepo — not in a split cloud repo:

- **Web app** → `apps/web` (TypeScript). Added as a new entry under the existing `apps/*` glob.
- **Backend / event-ledger service(s)** → `services/*`. New top-level directory introduced alongside `apps/`, `crates/`, `sdk/`, and `contracts/`.

Rationale (D-01): this preserves PROJECT.md's "Stack" constraint — *"preserve the existing monorepo shape and Voss runtime before introducing web/backend/RL services"* — and keeps the shared `contracts/` artifact in-repo so TS/Go/Rust/Python codegen runs from one source with one CI drift gate rather than being duplicated across repositories.

**Rejected alternative (D-01):** split the cloud services into a separate repository. Cleaner deploy/security boundary in theory, but it duplicates the contract artifact and codegen tooling across two repos, drifts faster, and contradicts the "preserve shape first" constraint. Cloud-vs-local is a deploy/security concern, not a repo-split concern (see next section).

## Service vs Library Boundary (BOS-ARCH-01, D-02)

The boundary between "service" and "library" is **deployability**, not language or cloud-vs-local:

- **Deployable units (own entrypoint/runtime):** `apps/*` (e.g. `apps/voss-app`, the future `apps/web`) and `services/*` (future backend/event-ledger). These get a process, container, or bundle runtime of their own.
- **Consumed libraries:** `crates/voss-*`, `sdk/go`, `sdk/typescript`, `contracts/`, and the Python harness/runtime libraries. They are linked/imported into a deployable unit; they do not run standalone.

**Cloud-vs-local is a deploy/security concern, NOT a repo split.** The local-first desktop/harness and the future cloud web/backend coexist in one tree. Whether a unit runs on a developer laptop or in a shared environment is a deployment attribute of that unit, not a reason to fork the repository.

## Language Ownership (BOS-ARCH-02)

Restated from PROJECT.md and BOS2-CONTEXT.md (not re-decided here):

- **TypeScript** owns the web app (`apps/web`) and the shared contracts layer (codegen consumers in `sdk/typescript`).
- **Python** owns learning/eval plus the existing harness/server local runtime (the `pyproject.toml` package and its optional FastAPI+SSE server extras).
- **Rust / Tauri** owns the desktop shell (`apps/voss-app`, `apps/voss-app/src-tauri`) and the `crates/voss-*` libraries.
- **Go** and **Rust** own SDKs where already established: `sdk/go` (Go) and `crates/voss-sdk` / `sdk/typescript` (Rust SDK crate plus TS SDK).

This maps back to PROJECT.md's Stack constraint and Key Decisions: the desktop ADE is Rust/Tauri; the harness/server local runtime is Python; web is TypeScript; SDKs follow the languages already established.

## JS Toolchain & Build Orchestration (BOS-ARCH-03, D-03)

D-03 consolidates on **pnpm now** and defers Turborepo behind an explicitly named trigger.

- **Consolidate on pnpm NOW.** The stray `package-lock.json` at repo root is to be removed so that `pnpm-workspace.yaml` + `pnpm-lock.yaml` is the single JS lockfile and source of truth. This resolves the latent npm/pnpm split visible in the current tree (both lockfiles present).
- **Defer Turborepo behind a documented trigger condition.** Turborepo is NOT adopted now. The trigger for revisiting adoption is explicit: *when `apps/web` is present AND multiple interdependent JS packages cause measurable CI/build-time pain.* Until that condition is met, the pnpm workspace alone is sufficient — there is not yet enough JS to justify a task-graph/caching orchestrator.

**Rejected alternative (D-03):** adopt Turborepo now. Premature — adds task-graph/caching orchestration overhead before the JS surface area is large enough to benefit. Recording the trigger ensures a future adoption decision is condition-met, not ad-hoc.

This doc does not modify `turbo.json` or `package.json`. Those are implementation-phase concerns, not architecture-decision concerns.

## Data Stores (BOS-ARCH-04, D-04)

Per-layer store engine choice (D-04):

- **SQLite** — local-first event log. Embeddable, point-in-time correct, offline-capable. Lives inside the desktop ADE / local runtime.
- **Postgres** — team-shared data and the web control plane's store. Holds the shared projection of state that multiple team members read/write through the web app.
- **DuckDB** — analytics and offline-eval. Runs over Parquet exports (i.e. over snapshots produced from the event log), not over the live store.

All three engines are named explicitly because each maps to a distinct workload: embeddable local log, shared online store, and analytical batch evaluation.

## Migration Boundary (BOS-ARCH-04, D-05)

The local→shared boundary is an **explicit, one-directional export/sync from local SQLite into shared Postgres** at a defined sync point:

- **One-directional:** SQLite is the source; Postgres receives a downstream projection. Postgres does not write back into the local store as a runtime dependency.
- **Invariant — offline-first desktop:** the desktop ADE must stay fully usable offline. Shared state is a downstream projection, never a hard runtime dependency. If the sync point is unavailable, local execution continues; sync resumes when connectivity returns.
- **Concrete schema/columns deferred** to BOS3-5 (event schema, decision ledger, outcome labels). BOS2 only fixes the engine choice (D-04) and the boundary rule (D-05).

**Rejected alternative (D-05):** a single Postgres store everywhere. Simpler in one dimension, but it breaks local-first / offline operation, which the trust model and PROJECT.md's Desktop/Web split require. Local-first execution cannot depend on a shared cloud store being reachable.

## Shared Contracts (BOS-ARCH-01, D-06)

D-06 extends the existing V13.1 contract artifact rather than introducing a new IDL:

- **Single source of truth:** `contracts/openapi.json` (56,657 bytes) and `contracts/events.schema.json` (25,160 bytes), both at the repo-root `contracts/` directory. These committed files are the org-wide schema source.
- **Codegen consumers:** TypeScript, Go, Rust, and Python types are generated from these two artifacts. No language maintains its own hand-rolled schema copy.
- **CI drift gate preserved:** the existing V13.1 drift-gate stays in place — generated types must not drift from the source artifact. This is the working, shipped mechanism; D-06 builds on it.

**Rejected alternative (D-06):** a new broader IDL (protobuf, TypeSpec) superseding V13.1. More expressive in theory, but it re-tools a working, drift-gated artifact for no proven need, and would force re-generating every consumer in four languages. The cost is not justified by any current requirement.

## Out of Scope (deferred)

Explicitly deferred from BOS2 (per BOS2-CONTEXT.md § Deferred Ideas):

- **Event-store schema / table design** — BOS3 (event schema), BOS4 (decision ledger), BOS5 (outcome labels). BOS2 fixes engines and the boundary rule only.
- **Backend deploy/runtime target** (container vs host vs serverless) — out of v0.2 scope per PROJECT.md ("Cloud sync, accounts, billing, multi-tenant SaaS, or enterprise admin in this milestone — design boundaries only"). Revisited when web/backend implementation phases land.
- **Contract versioning / breaking-change policy beyond the existing drift gate** — folds into the contract-owning implementation phase, not BOS2.
- **Web-vs-desktop responsibility map** — BOS-PROD-04 / BOS7. BOS2 only fixes the deployment boundary (D-02).
- **CI build-graph topology specifics** — follows the Turborepo trigger (D-03). Not a BOS2 deliverable.

---

## Target Tree

Single polyglot monorepo. Existing entries unchanged; NEW entries marked. Deployable units (apps/*, services/*) are annotated distinctly from consumed libraries (crates/*, sdk/*, contracts/, Python libs) per D-02.

    voss/                                     # repo root — single monorepo (D-01)
    ├─ apps/                                  # deployable app units (D-02)
    │  ├─ voss-app/                           # Rust/Tauri desktop ADE — EXISTING deployable
    │  │  └─ src-tauri/                       # Rust (Cargo workspace member)
    │  └─ web/                                # TypeScript web control plane — NEW (D-01), deployable
    ├─ services/                              # deployable backend units — NEW top-level dir (D-01, D-02)
    │  └─ (event-ledger / backend service(s)) # future deployable units, runtime TBD
    ├─ crates/                                # Rust libraries — consumed, NOT deployable (D-02)
    │  ├─ voss-agent/                         # Rust
    │  ├─ voss-app-core/                      # Rust
    │  ├─ voss-auth/                          # Rust
    │  ├─ voss-bridge/                        # Rust
    │  ├─ voss-cli/                           # Rust
    │  ├─ voss-providers/                     # Rust
    │  ├─ voss-render/                        # Rust
    │  ├─ voss-sdk/                           # Rust SDK crate
    │  ├─ voss-tools/                         # Rust
    │  └─ voss-tui/                           # Rust
    ├─ sdk/                                   # SDKs — consumed, NOT deployable (D-02)
    │  ├─ go/                                 # Go SDK — EXISTING
    │  └─ typescript/                         # TypeScript SDK — EXISTING
    ├─ contracts/                             # shared schema source of truth — consumed (D-06)
    │  ├─ openapi.json                        # EXISTING — single SSOT artifact
    │  └─ events.schema.json                 # EXISTING — single SSOT artifact
    ├─ pyproject.toml + uv.lock               # Python harness/runtime — consumed library (BOS-ARCH-02)
    ├─ pnpm-workspace.yaml                    # JS workspace — globs apps/* (to include apps/web)
    ├─ pnpm-lock.yaml                         # single JS lockfile after D-03 cleanup
    └─ Cargo.toml                             # Rust workspace root (10 crates + apps/voss-app/src-tauri)

Notes:
- `apps/voss-app` and the future `apps/web` and `services/*` are deployable units (own entrypoint/runtime).
- `crates/voss-*`, `sdk/go`, `sdk/typescript`, `contracts/`, and the Python harness/runtime are consumed libraries — linked/imported, not run standalone.
- `services/` does not exist today; it is introduced when the backend/event-ledger implementation phase lands.
- The stray `package-lock.json` (present today) is removed per D-03; it is intentionally not shown in the target tree.

## Decision Traceability

| Requirement | Locked decision(s) | Section recording it |
|-------------|--------------------|----------------------|
| BOS-ARCH-01 (target monorepo shape: desktop, web, backend, contracts, SDKs, RL/eval) | D-01, D-02, D-06 | Current Monorepo Shape; Target Monorepo Shape; Service vs Library Boundary; Shared Contracts |
| BOS-ARCH-02 (language ownership per layer: TS, Python, Rust/Tauri, Go/Rust SDKs) | (carried forward, locked) | Language Ownership |
| BOS-ARCH-03 (pnpm workspace + future Turborepo evolution) | D-03 | JS Toolchain & Build Orchestration |
| BOS-ARCH-04 (data-store options + migration boundaries: local-first, shared, analytics) | D-04, D-05 | Data Stores; Migration Boundary |

All decisions D-01 through D-06 trace to a section above; no decision is left unrecorded. Items deferred to later BOS phases are enumerated in § Out of Scope.