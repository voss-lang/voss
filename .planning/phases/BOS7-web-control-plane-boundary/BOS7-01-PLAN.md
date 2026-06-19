---
phase: BOS7-web-control-plane-boundary
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md
autonomous: true
requirements:
  - BOS-PROD-04

must_haves:
  truths:
    - "A reader can look up any named capability and unambiguously see which of the 4 surfaces OWNS it (and which READS it) from a single capability x surface matrix"
    - "A reader can see all four surfaces partitioned: local harness runtime, desktop ADE, backend services, web control plane (D-01)"
    - "A reader can see the data flow source(harness) -> backend(projection/store) -> web(team surface), with desktop reading its own slice locally (D-01)"
    - "A reader can read the privacy invariant stated as an INVARIANT not a default: raw code/prompts/file content never leaves the desktop; only structured metadata/decisions/outcome labels cross the desktop->server boundary (D-02)"
    - "A reader can read that review lives on BOTH desktop (own runs) and web (team queue) rendered from a SINGLE BOS9 output contract, no logic duplication (D-03)"
    - "A reader can read that desktop runs fully standalone/offline and web+backend are additive; and that the local loopback ephemeral token is preserved while shared accounts/identity are out-of-scope with only the seam reserved (D-04)"
    - "A reader can see which downstream phases this contract constrains (BOS6, BOS9, BOS10, BOS12, future apps/web)"
  artifacts:
    - path: ".planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md"
      provides: "The BOS7 web-vs-desktop responsibility map (capability x surface matrix + flow + invariants + downstream-constrains) covering BOS-PROD-04"
      min_lines: 90
      contains: "| Capability |"
  key_links:
    - from: "BOS7-RESPONSIBILITY-MAP.md capability matrix"
      to: "the four surfaces named in BOS-PROD-04"
      via: "four matrix columns (local harness, desktop ADE, backend services, web control plane)"
      pattern: "local harness.*desktop ADE.*backend services.*web control plane"
    - from: "BOS7-RESPONSIBILITY-MAP.md privacy section"
      to: "the BOS6 governance phase (D-02 boundary feeds it)"
      via: "stated content-stays-local invariant + BOS6 reference"
      pattern: "never leave|never leaves"
    - from: "BOS7-RESPONSIBILITY-MAP.md flow section"
      to: "the source->backend->web direction (D-01)"
      via: "explicit one-directional flow narrative"
      pattern: "harness.*->.*backend.*->.*web|source.*backend.*web"
---

<objective>
Produce the BOS7 web-vs-desktop responsibility map — a single docs-first contract that fixes WHERE each capability lives across the four Voss surfaces (local harness runtime, desktop ADE, backend services, web control plane). The deliverable is a capability x surface matrix + a flow narrative + the privacy/offline invariants + a downstream-constrains map. Covers BOS-PROD-04.

Purpose: This doc is a placement contract every later surface/integration phase inherits. It tells BOS6 (privacy rules), BOS9 (review UI), BOS10 (worker node), BOS12 (ingestion), and a future apps/web build exactly where each responsibility sits — so they design within the boundary instead of re-litigating it. Decisions and placement only — NO code, NO web app build, NO edits to voss/, apps/, or PROTOCOL.md.

Output: `.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md`
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md
@.planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md
@.planning/PROTOCOL.md
</context>

<notes>
- The four LOCKED decisions D-01..D-04 in BOS7-CONTEXT.md are the spine of this deliverable. EXPRESS them; do not re-decide them.
- Established BOS docs-first convention: the deliverable artifact lives inside the phase directory (cf. BOS2-ARCHITECTURE.md, BOS3-RESEARCH.md). Use `BOS7-RESPONSIBILITY-MAP.md` in this phase dir.
- PROTOCOL.md is REFERENCE ONLY (its ephemeral loopback bearer token is the identity seam D-04 reserves). Do NOT modify it.
- BOS2-ARCHITECTURE.md may not exist (BOS2 may be planned-not-executed). Treat the SQLite->Postgres one-directional sync + DuckDB as an upstream ASSUMPTION cited from BOS2-CONTEXT.md/BOS7-CONTEXT.md carry-forward, not a hard dependency.
- HARD INVARIANT (assert in every task acceptance): no edits to voss/, apps/, or .planning/PROTOCOL.md.
</notes>

<tasks>

<task type="auto">
  <name>Task 1: Write the capability x surface matrix + scaffold the doc</name>
  <files>.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</files>
  <read_first>
    - .planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md (D-01 partition + the capability hints in <specifics> and <deliverable_shape>; the four surfaces)
    - .planning/PROJECT.md (lines 68, 78 — Desktop/Web split constraint + "Web is the shared control plane" Key Decision)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md (D-01/D-03 — projection placement; BOS3 events project in backend services)
  </read_first>
  <action>
    Create `.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md`. Begin with a title (`# BOS7: Web-vs-Desktop Responsibility Map`), a one-line statement that this is the BOS-PROD-04 placement contract, and a short "How to read this" note (each capability has exactly one OWNER surface; READS denotes a surface that consumes but does not own; this map places capabilities, it does not design any surface).

    Then write the core `## Capability x Surface Matrix` as a markdown table. The FOUR columns (in this order) are EXACTLY: `local harness` | `desktop ADE` | `backend services` | `web control plane`. The first column is `Capability`. Each cell value is one of: `owns`, `reads`, or `none`.

    Rows = the concrete capabilities from BOS7-CONTEXT.md <deliverable_shape> (at minimum, one row each, phrased as concrete capabilities): execute agent run; emit raw events; serve local clients (loopback); project/ingest events; store event ledger (Postgres); store decision ledger (BOS4); serve policy (BOS13+); inspect/review own runs; review team queue; manage team/work model; sync data up (metadata/decisions); hold identity/token. You MAY add finer rows at your discretion, but every capability named in BOS7-CONTEXT.md must have a row.

    Fill the cells to encode D-01 exactly: local harness OWNS execute + emit + serve-loopback; desktop ADE OWNS local-first own-run inspect/review and acts as worker node (reads shared slice); backend services OWN projection/ingestion + event ledger + decision-ledger store + policy serving; web control plane OWNS the shared team read/manage surface (reads backend, no business logic of its own). Identity/token: local harness OWNS the ephemeral loopback token today; web/backend identity is RESERVED (mark per D-04 — see Task 2, but the matrix cell for shared identity must NOT claim an owner this milestone; use `none` + a footnote that the seam is reserved).

    Add a short `### Matrix rationale` prose paragraph directly under the table restating the D-01 partition and naming the two rejected alternatives (fat-desktop; fat-web/terminal-only-desktop) so the placement is traceable to D-01.
  </action>
  <verify>
    <automated>test -f .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md && grep -q "Capability x Surface Matrix\|Capability . Surface Matrix" .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</automated>
    <automated>grep -Eq "local harness.*desktop ADE.*backend services.*web control plane" .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</automated>
    <automated>for cap in "execute" "emit" "project" "event ledger" "decision ledger" "policy" "own run" "team queue" "manage" "sync" "identity"; do grep -qi "$cap" .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md || { echo "MISSING capability row: $cap"; exit 1; }; done