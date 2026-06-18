# Phase BOS2: Monorepo and Stack Architecture - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS2 produces ONE docs-first artifact: the **architecture decision doc** for the v0.2 Behavioral OS foundation (covers BOS-ARCH-01..04). It specifies the target stack, package/workspace layout, service boundaries, the pnpm→Turborepo evolution trigger, and data-store options + migration boundaries.

It decides the SHAPE the codebase grows into as web + backend land. It does **not** design the actual event schema (BOS3), decision ledger (BOS4), outcome/reward spec (BOS5), governance (BOS6), or the web-vs-desktop responsibility detail (BOS7 / BOS-PROD-04). No code, no migrations, no scaffolding — decisions and rationale only.
</domain>

<decisions>
## Implementation Decisions

### Repo Topology & Service Boundaries (BOS-ARCH-01)
- **D-01:** **Single polyglot monorepo.** Future web app lands at `apps/web` (TypeScript); backend/event-ledger service(s) land under `services/*`, alongside the existing `crates/voss-*` (Rust), `sdk/{go,typescript}`, `apps/voss-app` (Tauri desktop), and the Python harness/runtime. This preserves the existing shape per PROJECT.md's "preserve the monorepo before introducing web/backend/RL services" constraint, and keeps shared contracts in-repo (no cross-repo codegen duplication).
- **D-02:** **Service-vs-library boundary = deployability.** A directory under `services/*` (and `apps/*`) is a deployable unit with its own entrypoint/runtime; everything else (`crates/*`, `sdk/*`, shared contract packages, Python libs) is a consumed library. The cloud-vs-local distinction is a **deploy/security concern, not a repo split** — local-first desktop/harness and the future cloud web/backend coexist in one tree.
- Rejected: split cloud repo (cleaner deploy/security boundary but duplicates contract + codegen tooling across repos; contradicts "preserve shape first").

### JS Toolchain & Build Orchestration (BOS-ARCH-03)
- **D-03:** **Consolidate on pnpm now; defer Turborepo behind a documented trigger.** Remove the stray `package-lock.json` so `pnpm-workspace.yaml` + `pnpm-lock.yaml` is the single JS source of truth (the repo currently carries BOTH lockfiles — a latent npm/pnpm split to resolve). The doc must record the **Turborepo adoption trigger** explicitly (e.g. web app present AND multiple interdependent JS packages causing CI/build-time pain) rather than leaving it to a future guess.
- Rejected: adopt Turborepo now (premature task-graph/caching orchestration before there is enough JS to orchestrate).

### Data Stores & Migration Boundary (BOS-ARCH-04)
- **D-04:** **Per-layer store choice:** local-first event log = **SQLite** (embeddable, point-in-time-correct, offline-capable); team-shared data = **Postgres** (the web control plane's store); analytics / offline-eval = **DuckDB over Parquet exports**.
- **D-05:** **Local→shared boundary = explicit export/sync** from local SQLite into shared Postgres at a defined sync point. Desktop must stay fully usable offline; shared state is a downstream projection, never a hard runtime dependency of the local ADE. (Concrete schema/columns are BOS3-5's job — BOS2 only fixes the engine choice + boundary rule.)
- Rejected: single Postgres everywhere (simpler but breaks local-first / offline operation, which the trust + product model require).

### Shared Contract Source of Truth (BOS-ARCH-01 shared contracts)
- **D-06:** **Extend the existing V13.1 contract artifact** — the already-committed `openapi.json` + event-union snapshot stay the single source of truth; TS/Go/Rust/Python types are codegen'd from it; the existing CI drift gate is preserved. Build on shipped infrastructure rather than re-tooling working codegen.
- Rejected: new broader contracts IDL (protobuf/TypeSpec) superseding V13.1 (more power, but re-tools a working, drift-gated artifact for no proven need yet).

### Language Ownership (carried forward — locked, NOT re-discussed)
- Per **BOS-ARCH-02** + PROJECT.md: TypeScript owns web + shared contracts; Python owns learning/eval + the existing harness/server local runtime; Rust/Tauri owns the desktop shell; Go/Rust own SDKs where already established. This phase's doc restates the map; it does not re-decide it.

### Web/Desktop Split (carried forward — locked, NOT re-discussed)
- Per PROJECT.md Key Decisions: web = shared team control plane / dataset-review surface; desktop = local execution + ADE node. The architecture doc's deployment boundary (D-02) must respect this. Detail belongs to BOS7 / BOS-PROD-04.

### Claude's Discretion
- Architecture-doc structure/format (no template preference given).
- Exact wording of the Turborepo trigger condition (within the D-03 "documented, not guessed" constraint).
- How the doc visualizes the target tree / layer map (table, tree, diagram-in-prose).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product & stack constraints
- `.planning/PROJECT.md` — Constraints §"Stack" (preserve monorepo before new services; justify new stack in BOS arch docs), §"Desktop/Web split", and Key Decisions (web=control-plane / desktop=local-ADE).
- `.planning/REQUIREMENTS.md` — the four target requirements: **BOS-ARCH-01** (monorepo shape inventory), **BOS-ARCH-02** (language ownership per layer), **BOS-ARCH-03** (pnpm/Turborepo workspace evolution), **BOS-ARCH-04** (data-store options + migration boundaries).
- `.planning/ROADMAP.md` §"BOS-prefixed phases" — BOS2 row + milestone build-order stance.

### Existing contract / codegen substrate (the D-06 source of truth)
- `contracts/` — current shared-contract directory.
- V13.1 contract artifact — the committed `openapi.json` + event-union snapshot + CI drift gate (see ROADMAP.md V13.1 entry). D-06 extends this; the planner/researcher must locate the exact committed paths before specifying codegen.

### Existing workspace manifests (current shape to inventory for BOS-ARCH-01)
- `pnpm-workspace.yaml`, `pnpm-lock.yaml`, and the stray `package-lock.json` (D-03 resolves the duplication).
- `Cargo.toml` (Rust workspace over `crates/voss-*`).
- `pyproject.toml` + `uv.lock` (Python harness/runtime).
- `apps/voss-app` (Tauri desktop), `sdk/go`, `sdk/typescript`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **V13.1 contract artifact** (`openapi.json` + event-union snapshot + drift gate): D-06 makes this the org-wide schema source — no new contract mechanism needed.
- **Existing pnpm + Cargo + uv workspaces**: the monorepo already houses three toolchains; D-01 extends the same tree rather than introducing a new layout.

### Established Patterns
- **Docs-first BOS track**: every BOS phase ships a contract/spec before code. BOS2's architecture doc is the shape all later BOS implementation phases inherit.
- **Polyglot single-tree monorepo**: Rust crates + TS SDK + Python runtime + Tauri app already coexist; the new web/backend slot into the same convention.

### Integration Points
- None executed in this phase (docs-only). The doc frames WHERE future `apps/web` + `services/*` attach and HOW they consume the shared contract; actual scaffolding is a later implementation phase.
</code_context>

<specifics>
## Specific Ideas

- The architecture doc must explicitly state the **Turborepo trigger** (D-03) so future adoption is a condition-met decision, not an ad-hoc one.
- The doc must call out the **dual-lockfile cleanup** (`package-lock.json` removal) as a concrete consequence of D-03.
- The local→shared **store boundary** (D-05) must be stated as a one-directional projection (SQLite → Postgres), with offline-first desktop as the invariant.
</specifics>

<deferred>
## Deferred Ideas

- Concrete event-store schema / table design — BOS3 (event schema), BOS4 (decision ledger), BOS5 (outcome labels).
- Backend service deploy/runtime target (container, host, serverless) — out of this milestone's scope per PROJECT.md (no cloud/accounts/multi-tenant in v0.2); revisit when web/backend implementation phases land.
- Contract versioning / breaking-change policy beyond the existing drift gate — fold into the contract-owning implementation phase, not BOS2.
- Web-vs-desktop responsibility map — BOS-PROD-04 / BOS7.
- CI build-graph topology specifics — follow the Turborepo trigger (D-03); not a BOS2 deliverable.

### Reviewed Todos (not folded)
None — no phase-matched todos surfaced for BOS2.
</deferred>

---

*Phase: BOS2-monorepo-and-stack-architecture*
*Context gathered: 2026-06-18*
