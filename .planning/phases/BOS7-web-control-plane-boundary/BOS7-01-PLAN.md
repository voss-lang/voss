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
      contains: "Capability x Surface Matrix"
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
      pattern: "harness.*backend.*web|source.*backend.*web"
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
- BOS2-ARCHITECTURE.md may not exist (BOS2 may be planned-not-executed). Treat the SQLite->Postgres one-directional sync + DuckDB as an upstream ASSUMPTION cited from BOS2-CONTEXT.md / BOS7-CONTEXT.md carry-forward, not a hard dependency.
- HARD INVARIANT (assert in every task acceptance): no edits to voss/, apps/, or .planning/PROTOCOL.md.
</notes>

<tasks>

<task type="auto">
  <name>Task 1: Write the capability x surface matrix + scaffold the doc</name>
  <files>.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</files>
  <read_first>
    - .planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md (D-01 partition + capability hints in <specifics> and <deliverable_shape>; the four surfaces)
    - .planning/PROJECT.md (lines 68, 78 — Desktop/Web split constraint + "Web is the shared control plane" Key Decision)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md (D-01/D-03 — projection placement; BOS3 events project in backend services)
  </read_first>
  <action>
    Create `.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md`. Begin with a title (`# BOS7: Web-vs-Desktop Responsibility Map`), a one-line statement that this is the BOS-PROD-04 placement contract, and a short "How to read this" note (each capability has exactly one OWNER surface; READS denotes a surface that consumes but does not own; this map PLACES capabilities, it does not design any surface).

    Then write the core `## Capability x Surface Matrix` as a markdown table. The FOUR columns (in this order) are EXACTLY: `local harness` | `desktop ADE` | `backend services` | `web control plane`. The first column header is `Capability`. Each cell value is one of: `owns`, `reads`, or `none`.

    Rows = the concrete capabilities from BOS7-CONTEXT.md <deliverable_shape>, at minimum one row each phrased as a concrete capability: execute agent run; emit raw events; serve local clients (loopback); project/ingest events; store event ledger (Postgres); store decision ledger (BOS4); serve policy (BOS13+); inspect/review own runs; review team queue; manage team/work model; sync data up (metadata/decisions); hold identity/token. You MAY add finer rows at your discretion, but every capability named in BOS7-CONTEXT.md must have a row.

    Fill cells to encode D-01 exactly: local harness OWNS execute + emit + serve-loopback; desktop ADE OWNS local-first own-run inspect/review and acts as worker node (reads shared slice); backend services OWN projection/ingestion + event ledger + decision-ledger store + policy serving; web control plane OWNS the shared team read/manage surface (reads backend, no business logic of its own). For the identity/token row: local harness OWNS the ephemeral loopback token TODAY; the shared web/backend identity cell must NOT claim an owner this milestone — use `none` with a footnote that the seam is reserved (detail comes in Task 2).

    Add a short `### Matrix rationale` paragraph directly under the table restating the D-01 partition and naming the two rejected alternatives (fat-desktop; fat-web / terminal-only-desktop) so the placement is traceable to D-01.

    Do NOT touch voss/, apps/, or PROTOCOL.md.
  </action>
  <verify>
    <automated>test -f .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md && grep -q "Capability x Surface Matrix" .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</automated>
    <automated>grep -Eq "local harness.*desktop ADE.*backend services.*web control plane" .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</automated>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; for cap in "execute" "emit" "project" "event ledger" "decision ledger" "policy" "own run" "team queue" "manage" "sync" "identity"; do grep -qi "$cap" "$MAP" || { echo "MISSING capability row: $cap"; exit 1; }; done</automated>
  </verify>
  <acceptance_criteria>
    - BOS7-RESPONSIBILITY-MAP.md exists and contains a `## Capability x Surface Matrix` heading.
    - The matrix has all four surface columns named exactly: local harness, desktop ADE, backend services, web control plane.
    - Every capability listed in BOS7-CONTEXT.md <deliverable_shape> has a row (execute, emit, project/ingest, event ledger, decision ledger, policy, review own runs, team queue, manage, sync, identity/token).
    - Each filled cell is one of owns / reads / none.
    - A `### Matrix rationale` paragraph names the two rejected alternatives (fat-desktop, fat-web/terminal-only-desktop), tracing to D-01.
    - `git diff --quiet voss/ apps/ .planning/PROTOCOL.md` (no edits outside the deliverable).
  </acceptance_criteria>
  <done>The capability x surface matrix encoding D-01 exists in BOS7-RESPONSIBILITY-MAP.md with all 4 columns, all required rows, owns/reads/none cells, and a rationale tracing to D-01.</done>
</task>

<task type="auto">
  <name>Task 2: Write the flow narrative + privacy invariant + offline/identity-seam sections</name>
  <files>.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</files>
  <read_first>
    - .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md (the matrix written in Task 1 — append below it, do not rewrite)
    - .planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md (D-02 privacy boundary; D-03 review placement; D-04 offline/identity)
    - .planning/PROTOCOL.md (REFERENCE ONLY — the ephemeral loopback bearer token, lines ~24-28, that D-04 reserves as the identity seam; cite it, do not modify it)
  </read_first>
  <action>
    Append four sections to BOS7-RESPONSIBILITY-MAP.md (below the Task 1 matrix; do not edit the matrix):

    1. `## Data Flow` — a flow narrative encoding D-01's direction: source (local harness emits raw events) -> backend services (projection/ingestion + ledgers) -> web control plane (shared team surface); desktop ADE reads its OWN slice locally and acts as a worker node over shared state. Render it as an ASCII/text arrow diagram AND a short prose paragraph. The arrow line must literally show harness -> backend -> web.

    2. `## Privacy Boundary (Invariant)` — state D-02 as an INVARIANT, not a default. Required: the load-bearing claim that raw code, prompts, and file content NEVER leave the desktop; ONLY structured event metadata + decision records + outcome labels cross the desktop->server boundary; this crossing IS the privacy boundary and feeds BOS6 governance (BOS7 places the boundary, BOS6 sets the policy). Use the word "invariant" and an explicit "never leave the desktop" statement. Name the two rejected alternatives (full-sync-filter-at-web; manual-export-only).

    3. `## Review Placement` — encode D-03: review lives on BOTH desktop (the user's OWN runs / V24 Review tab, my-scope) and web (TEAM-level recommendation queue, team-scope), both rendered from a SINGLE BOS9 output contract to two targets, with NO logic duplication. State that BOS7 only PLACES review; BOS9 designs the UI.

    4. `## Offline + Identity Seam` — encode D-04: desktop works fully standalone/offline; web + backend are ADDITIVE (absent => desktop still runs, only team sync is lost). The local harness keeps its ephemeral loopback bearer token (cite PROTOCOL.md as the seam). Shared web identity / accounts / multi-tenancy are OUT-OF-SCOPE this milestone — BOS7 only RESERVES the boundary seam where a future web-auth layer attaches. Include an explicit out-of-scope-accounts line.

    Do NOT touch voss/, apps/, or PROTOCOL.md.
  </action>
  <verify>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; grep -q "## Data Flow" "$MAP" && grep -q "## Privacy Boundary" "$MAP" && grep -q "## Review Placement" "$MAP" && grep -q "## Offline + Identity Seam" "$MAP"</automated>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; grep -Eqi "never leave[s]? the desktop" "$MAP" && grep -qi "invariant" "$MAP"</automated>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; grep -Eqi "harness.*->.*backend.*->.*web|source.*->.*backend.*->.*web" "$MAP"</automated>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; grep -qi "both" "$MAP" && grep -Eqi "single.*(bos9|output).*contract|single.*contract" "$MAP" && grep -Eqi "no.*duplicat" "$MAP"</automated>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; grep -Eqi "out.of.scope|out of scope" "$MAP" && grep -qi "account" "$MAP"</automated>
  </verify>
  <acceptance_criteria>
    - Doc contains `## Data Flow`, `## Privacy Boundary (Invariant)`, `## Review Placement`, and `## Offline + Identity Seam` sections.
    - Data Flow shows an explicit harness -> backend -> web arrow line plus prose; desktop's local own-slice read is stated (D-01).
    - Privacy section uses the word "invariant" and the literal "never leave(s) the desktop" claim; lists only metadata/decisions/outcome-labels as crossing; references BOS6 (D-02).
    - Review section places review on BOTH desktop (own runs) and web (team queue) via a SINGLE BOS9 contract, no logic duplication (D-03).
    - Offline section states desktop standalone/offline + web/backend additive, preserves the loopback token (cites PROTOCOL.md), and has an explicit out-of-scope accounts/identity line with the seam reserved (D-04).
    - `git diff --quiet voss/ apps/ .planning/PROTOCOL.md` (no edits outside the deliverable).
  </acceptance_criteria>
  <done>The flow, privacy-invariant, review-placement, and offline/identity-seam sections encoding D-01..D-04 are appended to BOS7-RESPONSIBILITY-MAP.md and pass all grep checks.</done>
</task>

<task type="auto">
  <name>Task 3: Write the downstream-constrains map + final structural verification</name>
  <files>.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md</files>
  <read_first>
    - .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md (the matrix + sections from Tasks 1-2 — append below; do not rewrite)
    - .planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md (<canonical_refs> "Forward dependencies BOS7 constrains" — BOS6, BOS9, BOS10, BOS12, future apps/web)
    - .planning/REQUIREMENTS.md (line 14 — BOS-PROD-04, to cite in the doc's coverage line)
  </read_first>
  <action>
    Append a final `## This Constrains` section to BOS7-RESPONSIBILITY-MAP.md: a short table or list mapping each downstream consumer to WHAT BOS7 hands it. Required entries: BOS6 (privacy rules — consumes the D-02 boundary placement); BOS9 (recommendation review UI — consumes the D-03 single-contract / dual-target placement); BOS10 (desktop worker-node contract — consumes the D-01 "desktop as worker node" placement); BOS12 (external integration ingestion — consumes the D-01 "ingestion lives in backend services" placement); future apps/web build (consumes the whole web-control-plane column as its scope). State that BOS7 PLACES these; the named phases DESIGN them.

    Add a closing one-line `## Requirement Coverage` note citing that this document satisfies BOS-PROD-04 (defines what belongs in desktop ADE, web control plane, backend services, and local harness runtime).

    Then run the full structural verification (the automated checks below) over the completed doc to confirm all four decisions D-01..D-04 are traceable and no protected paths were touched.

    Do NOT touch voss/, apps/, or PROTOCOL.md.
  </action>
  <verify>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; grep -q "## This Constrains" "$MAP" && for ph in BOS6 BOS9 BOS10 BOS12 "apps/web"; do grep -qi "$ph" "$MAP" || { echo "MISSING downstream: $ph"; exit 1; }; done</automated>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; grep -q "BOS-PROD-04" "$MAP"</automated>
    <automated>MAP=.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md; lines=$(grep -vc '^[[:space:]]*$' "$MAP"); [ "$lines" -ge 90 ] || { echo "doc too short: $lines non-blank lines (<90)"; exit 1; }</automated>
    <automated>git diff --quiet voss/ apps/ .planning/PROTOCOL.md && echo "protected paths untouched"</automated>
  </verify>
  <acceptance_criteria>
    - Doc contains a `## This Constrains` section naming BOS6, BOS9, BOS10, BOS12, and the future apps/web build, each mapped to the specific placement it consumes.
    - Doc contains a `## Requirement Coverage` line citing BOS-PROD-04.
    - The completed doc is at least 90 non-blank lines.
    - All four locked decisions are traceable: D-01 (matrix + flow), D-02 (privacy invariant), D-03 (review placement), D-04 (offline/identity seam) — confirmed by the Task 1/2/3 grep checks all passing.
    - `git diff --quiet voss/ apps/ .planning/PROTOCOL.md` passes (no edits to protected paths).
  </acceptance_criteria>
  <done>The downstream-constrains map + requirement-coverage line are appended; the full doc passes structural verification (all sections present, >=90 non-blank lines, all 4 decisions traceable, protected paths untouched).</done>
</task>

</tasks>

<verification>
Phase-level checks (run after all tasks):
- `test -f .planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md`
- All four surface columns present: `grep -Eq "local harness.*desktop ADE.*backend services.*web control plane" <map>`
- Privacy invariant present: `grep -Eqi "never leave[s]? the desktop" <map>` and `grep -qi invariant <map>`
- Flow direction present: `grep -Eqi "harness.*->.*backend.*->.*web" <map>`
- Out-of-scope accounts/identity seam present: `grep -Eqi "out.of.scope" <map>` and `grep -qi account <map>`
- Downstream constrains present: BOS6, BOS9, BOS10, BOS12, apps/web all grep-hit
- Protected paths untouched: `git diff --quiet voss/ apps/ .planning/PROTOCOL.md`
</verification>

<success_criteria>
- BOS7-RESPONSIBILITY-MAP.md exists in the phase directory and is the single deliverable for BOS-PROD-04.
- The capability x surface matrix unambiguously partitions all named capabilities across the four surfaces (owns/reads/none) per D-01.
- The flow narrative, privacy invariant (D-02), review placement (D-03), and offline/identity-seam (D-04) sections are all present and traceable to their locked decisions.
- The downstream-constrains map names BOS6/BOS9/BOS10/BOS12/future apps/web with the specific placement each inherits.
- No edits to voss/, apps/, or PROTOCOL.md.
</success_criteria>

<output>
Create `.planning/phases/BOS7-web-control-plane-boundary/BOS7-01-SUMMARY.md` when done.
</output>
