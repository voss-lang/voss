---
phase: BOS2-monorepo-and-stack-architecture
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md
autonomous: true
requirements:
  - BOS-ARCH-01
  - BOS-ARCH-02
  - BOS-ARCH-03
  - BOS-ARCH-04

must_haves:
  truths:
    - "A reader can see the CURRENT monorepo shape (pnpm + Cargo + uv workspaces, apps/voss-app, sdk/{go,typescript}, crates/voss-*, contracts/) inventoried in one place"
    - "A reader can see the TARGET shape: apps/web + services/* added to the SAME single monorepo, with the service-vs-library boundary defined as deployability"
    - "A reader can read the language-ownership map (TS / Python / Rust-Tauri / Go-Rust) restated per layer"
    - "A reader can read the pnpm consolidation decision (remove package-lock.json) and a named Turborepo adoption trigger"
    - "A reader can read the per-layer store choice (SQLite / Postgres / DuckDB-over-Parquet) and the one-directional SQLite -> Postgres sync boundary"
    - "A reader can read that the shared contract source of truth is the existing V13.1 openapi.json + events.schema.json with the CI drift gate preserved"
  artifacts:
    - path: ".planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md"
      provides: "The BOS2 architecture decision doc covering BOS-ARCH-01..04"
      min_lines: 80
      contains: "## Data Stores"
  key_links:
    - from: "BOS2-ARCHITECTURE.md ## Shared Contracts section"
      to: "contracts/openapi.json + contracts/events.schema.json"
      via: "named file paths cited as the single source of truth (D-06)"
      pattern: "contracts/openapi\\.json"
    - from: "BOS2-ARCHITECTURE.md ## Data Stores section"
      to: "the local->shared migration boundary"
      via: "one-directional SQLite -> Postgres statement (D-05)"
      pattern: "SQLite.*->.*Postgres|SQLite.*Postgres"
---

<objective>
Produce the BOS2 architecture decision doc — a single prose artifact recording the target stack, package/workspace layout, service boundaries, the pnpm/Turborepo evolution, and the per-layer data-store options + migration boundary for the v0.2 Behavioral OS foundation. Covers BOS-ARCH-01, BOS-ARCH-02, BOS-ARCH-03, BOS-ARCH-04.

Purpose: This doc fixes the SHAPE the codebase grows into as web + backend land. It is the architectural contract every later BOS implementation phase (BOS3-BOS17) inherits. Decisions and rationale only — NO code, NO scaffolding, NO migrations, NO turbo.json/package.json edits.

Output: `.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md`
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md
@.planning/REQUIREMENTS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Draft the BOS2 architecture decision doc (current + target shape, language map, toolchain, data stores, contracts)</name>
  <files>.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md</files>
  <read_first>
    - .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md — the authoritative locked decisions D-01..D-06; every section below must trace to one of these.
    - .planning/PROJECT.md — Constraints "Stack" (preserve the monorepo shape before introducing web/backend/RL services; new stack must be justified in BOS arch docs) and "Desktop/Web split" + Key Decisions (web = shared control plane, desktop = local ADE node).
    - .planning/REQUIREMENTS.md lines ~70-73 — the exact text of BOS-ARCH-01, BOS-ARCH-02, BOS-ARCH-03, BOS-ARCH-04.
    - The CURRENT workspace manifests to inventory: pnpm-workspace.yaml (currently globs only `apps/*`), pnpm-lock.yaml, the stray package-lock.json (the dual-lockfile to resolve), package.json (packageManager pnpm@10.0.0), Cargo.toml (Rust workspace over crates/voss-*), pyproject.toml + uv.lock (Python harness/runtime).
    - The CURRENT directory shape to inventory: apps/voss-app (Tauri desktop), sdk/go, sdk/typescript, crates/voss-* (voss-agent, voss-app-core, voss-auth, voss-bridge, voss-cli, voss-providers, voss-render, voss-sdk, voss-tools, voss-tui), contracts/.
    - contracts/ — confirm the committed source-of-truth files BEFORE writing the Shared Contracts section: contracts/openapi.json and contracts/events.schema.json (the event-union snapshot). Cite these exact paths; do not invent a path.
    - BOS2-ARCHITECTURE.md itself if it already exists (overwrite is fine; do not duplicate content).
  </read_first>
  <action>
    Write the doc as prose decisions + rationale. Required sections, each grounded in the named locked decision and concrete values:

    "## Current Monorepo Shape (BOS-ARCH-01)" — inventory the EXISTING tree: a single polyglot monorepo already housing pnpm (apps/*), Cargo (crates/voss-*), and uv (Python harness/runtime) workspaces, plus apps/voss-app (Tauri desktop), sdk/go, sdk/typescript, contracts/. Note the current pnpm-workspace.yaml globs only `apps/*`. Note the latent dual-lockfile state (both pnpm-lock.yaml and package-lock.json present at root).

    "## Target Monorepo Shape (BOS-ARCH-01, D-01)" — the future web app lands at `apps/web` (TypeScript) and backend/event-ledger service(s) land under `services/*`, added to the SAME single polyglot monorepo (not a new repo). State the rationale: preserves the PROJECT.md "preserve the monorepo before introducing web/backend/RL services" constraint and keeps shared contracts in-repo (no cross-repo codegen duplication). Record the rejected alternative (split cloud repo) and why (duplicates contract + codegen tooling).

    "## Service vs Library Boundary (BOS-ARCH-01, D-02)" — define the boundary as DEPLOYABILITY: a directory under `services/*` (and `apps/*`) is a deployable unit with its own entrypoint/runtime; everything else (crates/*, sdk/*, shared contract packages, Python libs) is a consumed library. State explicitly that cloud-vs-local is a deploy/security concern, NOT a repo split — local-first desktop/harness and the future cloud web/backend coexist in one tree.

    "## Language Ownership (BOS-ARCH-02)" — RESTATE (do not re-decide) the per-layer map: TypeScript owns web + shared contracts; Python owns learning/eval + the existing harness/server local runtime; Rust/Tauri owns the desktop shell (apps/voss-app); Go/Rust own the SDKs where already established (sdk/go, sdk/typescript, plus Rust SDK crate). Tie back to PROJECT.md.

    "## JS Toolchain & Build Orchestration (BOS-ARCH-03, D-03)" — consolidate on pnpm NOW: state that package-lock.json is to be removed so pnpm-workspace.yaml + pnpm-lock.yaml is the single JS source of truth (call out the dual-lockfile cleanup as a concrete consequence). Defer Turborepo behind an EXPLICITLY-NAMED trigger condition — state the trigger as a concrete condition (e.g. apps/web present AND multiple interdependent JS packages causing measurable CI/build-time pain), not "later" or a guess. Record the rejected alternative (adopt Turborepo now) and why (premature task-graph/caching before there is enough JS to orchestrate).

    "## Data Stores (BOS-ARCH-04, D-04)" — per-layer engine choice: SQLite = local-first event log (embeddable, point-in-time-correct, offline-capable); Postgres = team-shared data / web control plane store; DuckDB over Parquet exports = analytics / offline-eval. Name all three engines.

    "## Migration Boundary (BOS-ARCH-04, D-05)" — the local->shared boundary is an explicit ONE-DIRECTIONAL export/sync from local SQLite into shared Postgres at a defined sync point. State the invariant: desktop stays fully usable offline; shared state is a downstream projection, never a hard runtime dependency of the local ADE. Note that concrete schema/columns are deferred to BOS3-5 (BOS2 fixes engine choice + boundary rule only). Record the rejected alternative (single Postgres everywhere) and why (breaks local-first/offline).

    "## Shared Contracts (BOS-ARCH-01, D-06)" — the existing V13.1 contract artifact (the committed contracts/openapi.json + contracts/events.schema.json event-union snapshot) stays the single schema source of truth; TS/Go/Rust/Python types are codegen'd from it; the existing CI drift gate is preserved. Cite the exact contract file paths confirmed in <read_first>. Record the rejected alternative (new IDL such as protobuf/TypeSpec superseding V13.1) and why (re-tools a working drift-gated artifact for no proven need).

    "## Out of Scope (deferred)" — explicitly list what this doc does NOT decide, per CONTEXT.md deferred items: event-store schema/table design (BOS3-5), backend deploy/runtime target (out of v0.2 scope), contract versioning/breaking-change policy beyond the drift gate, the web-vs-desktop responsibility map (BOS-PROD-04 / BOS7), and CI build-graph topology specifics (follows the D-03 trigger).

    Do NOT design event-store schemas, backend deploy targets, contract versioning policy, the web/desktop responsibility map, or CI build-graph specifics. Do NOT emit any code, turbo.json, or manifest edits — this is a decision doc only.
  </action>
  <acceptance_criteria>
    - BOS2-ARCHITECTURE.md exists at .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md.
    - Doc contains a "## Current Monorepo Shape" section that names pnpm, Cargo, and uv workspaces AND names apps/voss-app, sdk/go, sdk/typescript, crates/voss-*, and contracts/.
    - Doc contains a "## Target Monorepo Shape" section that names the literal paths `apps/web` and `services/*` and states they are added to the SAME single monorepo (D-01).
    - Doc contains a "## Service vs Library Boundary" section stating the boundary is deployability and that cloud-vs-local is NOT a repo split (D-02).
    - Doc contains a "## Language Ownership" section naming TypeScript, Python, Rust/Tauri, and Go for their respective layers (BOS-ARCH-02).
    - Doc contains a "## JS Toolchain & Build Orchestration" section that states package-lock.json removal AND names a specific Turborepo adoption trigger condition (D-03).
    - Doc contains a "## Data Stores" section naming SQLite, Postgres, and DuckDB (D-04).
    - Doc contains a "## Migration Boundary" section stating the SQLite -> Postgres sync is one-directional and offline-first desktop is the invariant (D-05).
    - Doc contains a "## Shared Contracts" section citing contracts/openapi.json and contracts/events.schema.json as the source of truth with the CI drift gate preserved (D-06).
    - Doc contains a "## Out of Scope" (deferred) section listing the deferred items.
    - No fenced code blocks containing turbo.json, package.json, or migration code (decision doc only).
  </acceptance_criteria>
  <verify>
    <automated>test -f .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && for s in "## Current Monorepo Shape" "## Target Monorepo Shape" "## Service vs Library Boundary" "## Language Ownership" "## JS Toolchain" "## Data Stores" "## Migration Boundary" "## Shared Contracts" "## Out of Scope"; do grep -qF "$s" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md || { echo "MISSING SECTION: $s"; exit 1; }; done && grep -qF "apps/web" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && grep -qF "services/" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && grep -qiE "SQLite" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && grep -qiE "Postgres" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && grep -qiE "DuckDB" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && grep -qF "contracts/openapi.json" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && grep -qF "package-lock.json" .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && echo "ALL SECTIONS + VALUES PRESENT"</automated>
  </verify>
  <done>BOS2-ARCHITECTURE.md exists with all 10 required sections and all locked-decision values (apps/web, services/*, SQLite/Postgres/DuckDB, contracts/openapi.json, package-lock.json removal) present and grep-verified.</done>
</task>

<task type="auto">
  <name>Task 2: Add the target tree + layer-ownership diagram and a decision-traceability table</name>
  <files>.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md</files>
  <read_first>
    - .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md — the doc drafted in Task 1; append to it, do not rewrite existing sections.
    - .planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md — re-check D-01..D-06 IDs so the traceability table maps each requirement+decision to its doc section.
    - The current directory layout (apps/voss-app, sdk/go, sdk/typescript, crates/voss-*, contracts/) so the tree shows the existing dirs plus the target apps/web + services/* additions accurately.
  </read_first>
  <action>
    Append two reader aids to BOS2-ARCHITECTURE.md:

    "## Target Tree" — a prose/ASCII tree (the diagram format is Claude's discretion per D-discretion) of the single monorepo showing the EXISTING dirs (apps/voss-app, sdk/go, sdk/typescript, crates/voss-*, contracts/, the Python harness/runtime, root pnpm/Cargo/uv manifests) AND the TARGET additions clearly marked as new: `apps/web` (TS) and `services/*` (backend/event ledger). Annotate each top-level dir with its language owner and whether it is a deployable unit (apps/*, services/*) or a consumed library (crates/*, sdk/*, contracts/, Python libs), per D-02.

    "## Decision Traceability" — a markdown table mapping each requirement to its locked decision(s) and the doc section that records it: rows for BOS-ARCH-01 (D-01, D-02, D-06 -> Current/Target Shape, Service vs Library Boundary, Shared Contracts), BOS-ARCH-02 (-> Language Ownership), BOS-ARCH-03 (D-03 -> JS Toolchain & Build Orchestration), BOS-ARCH-04 (D-04, D-05 -> Data Stores, Migration Boundary).

    Do NOT alter any decision from Task 1; this task only adds the tree and the traceability table.
  </action>
  <acceptance_criteria>
    - Doc contains a "## Target Tree" section that names both `apps/web` and `services/` and marks them as target/new additions alongside the existing dirs (apps/voss-app, crates/, sdk/, contracts/).
    - The Target Tree annotates deployable units (apps/*, services/*) distinctly from libraries (crates/*, sdk/*) per D-02.
    - Doc contains a "## Decision Traceability" section with a table referencing all four requirement IDs (BOS-ARCH-01, BOS-ARCH-02, BOS-ARCH-03, BOS-ARCH-04) and decision IDs D-01 through D-06.
    - Task 1's ten sections remain intact (no section deleted or renamed).
  </acceptance_criteria>
  <verify>
    <automated>F=.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md && grep -qF "## Target Tree" "$F" && grep -qF "## Decision Traceability" "$F" && for id in BOS-ARCH-01 BOS-ARCH-02 BOS-ARCH-03 BOS-ARCH-04 D-01 D-02 D-03 D-04 D-05 D-06; do grep -qF "$id" "$F" || { echo "MISSING ID: $id"; exit 1; }; done && grep -qF "## Data Stores" "$F" && grep -qF "## Shared Contracts" "$F" && echo "TREE + TRACEABILITY + ALL IDS PRESENT, TASK 1 SECTIONS INTACT"</automated>
  </verify>
  <done>BOS2-ARCHITECTURE.md has a Target Tree showing existing + new (apps/web, services/*) dirs with deployable/library annotation, and a Decision Traceability table covering BOS-ARCH-01..04 and D-01..D-06; all Task 1 sections still present.</done>
</task>

</tasks>

<verification>
The doc is a decision artifact, not code. Automated checks confirm structural presence of every required section and locked-decision value (see each task's <verify>). FINAL acceptance is human review: the developer reads BOS2-ARCHITECTURE.md against the locked CONTEXT.md decisions D-01..D-06 and confirms each decision is recorded faithfully with rationale and rejected-alternative. No test command proves correctness of prose — only presence.
</verification>

<success_criteria>
- BOS2-ARCHITECTURE.md exists and passes both tasks' grep verifications.
- All four requirements (BOS-ARCH-01..04) and all six decisions (D-01..D-06) are recorded with rationale and (where the decision had one) the rejected alternative.
- The doc explicitly states: apps/web + services/* in the same monorepo; deployability as the service/library boundary; the TS/Python/Rust-Tauri/Go language map; package-lock.json removal + a named Turborepo trigger; SQLite/Postgres/DuckDB per layer; one-directional SQLite -> Postgres sync with offline-first invariant; contracts/openapi.json + contracts/events.schema.json as the drift-gated source of truth.
- The doc names its out-of-scope deferrals (event-store schema, backend deploy target, contract versioning policy, web/desktop responsibility map, CI build-graph specifics).
- No code, no manifest edits, no migrations produced.
</success_criteria>

<output>
Create `.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-01-SUMMARY.md` when done.
</output>
