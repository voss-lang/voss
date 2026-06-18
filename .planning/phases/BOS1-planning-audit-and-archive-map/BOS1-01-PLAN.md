---
phase: BOS1-planning-audit-and-archive-map
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/AUDIT-INDEX.md
autonomous: true
requirements:
  - BOS-PLAN-01
  - BOS-PLAN-02
  - BOS-PLAN-03
  - BOS-PLAN-04
must_haves:
  truths:
    - "A single AUDIT-INDEX.md exists at .planning/ root"
    - "Every one of the 12 loose root .md plans has its own index row"
    - "Every file under .planning/seeds, .planning/notes, .planning/docs has its own index row"
    - "All 10 phase track prefixes (01-07, M, A, V, O, F, E, T, BOS, 999.x) each have exactly one rollup row"
    - "Every index row carries BOTH a status (axis 1) and a BOS-relationship (axis 2) value"
    - "Supersession pointers mirror STATE.md/ROADMAP.md markers (M13->V8, O6->V9, O1-O6->V-track, M5->E-track) rather than inventing new ones"
    - "BOS-PLAN-01 (BOS prefix present) and BOS-PLAN-03 (BOS0-18 split adequate) are verified and recorded, not re-done"
    - "Stray docs outside .planning/ appear only in an appendix, never as first-class rows"
    - "No file under .planning/ is moved or deleted by this plan"
  artifacts:
    - path: ".planning/AUDIT-INDEX.md"
      provides: "Two-axis classification index of the full .planning corpus + track rollup + external appendix"
      contains: "| doc / track | status |"
  key_links:
    - from: ".planning/AUDIT-INDEX.md"
      to: ".planning/STATE.md"
      via: "status + supersession cells sourced from STATE.md Phase Status table"
      pattern: "superseded|absorbed|active|historical|archive-candidate"
    - from: ".planning/AUDIT-INDEX.md"
      to: ".planning/ROADMAP.md"
      via: "track rollup status + BOS-relationship sourced from ROADMAP phase table"
      pattern: "substrate|dependency|historical-context|out-of-scope"
---

<objective>
Build `.planning/AUDIT-INDEX.md`: a single human-readable two-axis classification
of the entire `.planning/` planning corpus, so that no archive, supersession, or
deletion can happen "blind" (the index is the gate PROJECT.md requires).

Purpose: Close BOS-PLAN-02 (audit + index before any archive/delete) and
BOS-PLAN-04 (map existing Voss tracks into BOS), and place on the record the
already-true facts for BOS-PLAN-01 (BOS prefixes exist) and BOS-PLAN-03 (BOS0-18
split is adequate).

Output: `.planning/AUDIT-INDEX.md` — one markdown table for per-file loose docs,
one rollup table for the 10 phase tracks, an appendix for stray external docs,
and short verification notes for BOS-PLAN-01/03. Pure doc write, no file moves.
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
@.planning/phases/BOS1-planning-audit-and-archive-map/BOS1-CONTEXT.md

<taxonomy>
<!-- LOCKED enums from BOS1-CONTEXT.md D-02. Every row MUST use exactly these. -->
Axis 1 — Status (covers BOS-PLAN-02): active | historical | superseded | archive-candidate
Axis 2 — BOS-relationship (covers BOS-PLAN-04): substrate | dependency | historical-context | out-of-scope

Table column set (D-03), in this order:
| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |
</taxonomy>

<audit_subjects>
<!-- The exact net from D-01. These lists are authoritative — do not add system docs. -->

PER-FILE — 12 loose root .md plans (audit subjects):
  ADE-REDESIGN.md, CODEX-OAUTH-PLAN.md, Feature Plan.md, HARNESS-PLAN.md,
  HYBRID-REFACTOR-PLAN.md, MCP-PLAN.md, OPENCODE-TUI-ADAPTER-CONTRACT.md,
  ORCHESTRATION-PLAN.md, PROTOCOL.md, RUST-PORT-PLAN.md, TUI-FIXES-HANDOFF.md,
  VOSS-USERSPACE-OS-HANDOFF.md

PER-FILE — .planning/seeds/ (6 files):
  agent-capability-surface.md, managed-docs-generation.md, project-memory-voss-md.md,
  SEED-001-coordination-bus.md, SEED-002-codebase-rag-tiered-indexing.md, tui-shell-textual.md

PER-FILE — .planning/notes/ (5 files):
  daily-driver-punch-list.md, e-track-eval-decisions.md, plan-grid-drag-rearrange.md,
  seed-structured-pane-rendering.md, voss-agent-unfair-advantage.md

PER-FILE — .planning/docs/ (2 files):
  AST-JSON-CONTRACT.md, ORCHESTRATION_LAYERS.md

NOT audit subjects (system planning docs — exclude from rows): PROJECT.md, ROADMAP.md,
  REQUIREMENTS.md, STATE.md, MILESTONES.md, AUDIT-INDEX.md (the output itself).

TRACK ROLLUP — 10 prefix groups under .planning/phases/ (one row each, NOT per phase):
  01-07 (numbered language-compiler track, 7 dirs) · M (15) · A (12) · V (30) ·
  O (6) · F (5) · E (5) · T (8) · BOS (2) · 999.x (2)

APPENDIX (noted, NOT first-class rows): stray planning docs OUTSIDE .planning/, e.g.
  .vscode/voss_v_0_1_scope_lock.md and any repo-root design docs.
</audit_subjects>

<supersession_truth>
<!-- Mirror these existing markers from STATE.md / ROADMAP.md. Do not invent. -->
- M13 -> ABSORBED into V8
- O6 -> SUPERSEDED by V9 (O6 ready plans re-point to V9)
- O1-O6 (whole O-track) -> superseded by V-track (O1->V4, O2->V3, O3->V5, O4->V6, O5->V7, O6->V9)
- M5 (eval scope) -> SUPERSEDED by E-track (E1/E2); M5-06 packaging smoke stays shipped
- A13-02..06 transport -> SUPERSEDED by V25; A13-01 file schema retained as audit layer
- RUST-PORT-PLAN.md -> superseded by HYBRID-REFACTOR-PLAN.md (per ROADMAP "supersedes RUST-PORT-PLAN")
</supersession_truth>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build per-file audit table (loose root + seeds + notes + docs)</name>
  <files>.planning/AUDIT-INDEX.md</files>
  <read_first>
    - .planning/phases/BOS1-planning-audit-and-archive-map/BOS1-CONTEXT.md (D-01..D-05, the locked net + taxonomy)
    - .planning/PROJECT.md (Out-of-Scope deletion bar; carry-forward stance on historical V/M/A/F/E context)
    - .planning/ROADMAP.md "Granularity" line (~5) + change-log line 8 (which design docs back which tracks: ORCHESTRATION-PLAN->O, Feature Plan->F, ORCHESTRATION_LAYERS->V, HYBRID-REFACTOR->H/port, PROTOCOL->wire contract, e-track-eval-decisions->E, daily-driver-punch-list->T, SEED-001->BOS swarm, seed-structured-pane-rendering->V15)
    - The 25 audit-subject files themselves: open each loose root .md, each .planning/seeds/* , .planning/notes/* , .planning/docs/* to read enough (title + first ~30 lines) to assign status + relationship + reason. Use the <supersession_truth> block for pointers.
  </read_first>
  <action>
    Create .planning/AUDIT-INDEX.md. Add a title + one-line purpose + a "Taxonomy"
    legend block restating the two axes and their enums (verbatim from the
    <taxonomy> context block). Then write the first table, "## Per-file audit",
    with the locked column set: `| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |`.
    Emit exactly one row for each of the 25 audit-subject files listed in
    <audit_subjects> (12 loose root + 6 seeds + 5 notes + 2 docs). Group rows under
    sub-headings (### Loose root plans, ### seeds/, ### notes/, ### docs/) — grouping
    and reason wording are Claude's discretion (D-05). For each row pick exactly one
    Axis-1 enum and one Axis-2 enum from <taxonomy>; both cells MUST be non-empty.
    Fill the supersession cell from <supersession_truth> where applicable (e.g.
    RUST-PORT-PLAN.md -> "superseded-by HYBRID-REFACTOR-PLAN.md"), else "—".
    Anchoring guidance (assign from the file content + ROADMAP, not guesses):
    PROTOCOL.md and HYBRID-REFACTOR-PLAN.md are live wire/refactor contracts (active,
    substrate); ORCHESTRATION-PLAN.md and Feature Plan.md and ORCHESTRATION_LAYERS.md
    are design docs for superseded/absorbed-or-active tracks (status per their track's
    STATE row, relationship historical-context or dependency); SEED-001 is planted
    BOS context (historical/active, dependency per PROJECT carry-forward); RUST-PORT-PLAN.md
    is superseded. Do NOT add rows for PROJECT/ROADMAP/REQUIREMENTS/STATE/MILESTONES/AUDIT-INDEX.
    Do NOT move or delete any file — this task only writes AUDIT-INDEX.md.
  </action>
  <verify>
    <automated>test -f .planning/AUDIT-INDEX.md && grep -c '| ' .planning/AUDIT-INDEX.md && for f in ADE-REDESIGN CODEX-OAUTH-PLAN HARNESS-PLAN HYBRID-REFACTOR-PLAN MCP-PLAN OPENCODE-TUI-ADAPTER-CONTRACT ORCHESTRATION-PLAN PROTOCOL RUST-PORT-PLAN TUI-FIXES-HANDOFF VOSS-USERSPACE-OS-HANDOFF SEED-001-coordination-bus SEED-002-codebase-rag-tiered-indexing agent-capability-surface managed-docs-generation project-memory-voss-md tui-shell-textual daily-driver-punch-list e-track-eval-decisions plan-grid-drag-rearrange seed-structured-pane-rendering voss-agent-unfair-advantage AST-JSON-CONTRACT ORCHESTRATION_LAYERS; do grep -q "$f" .planning/AUDIT-INDEX.md || echo "MISSING ROW: $f"; done; grep -q 'Feature Plan' .planning/AUDIT-INDEX.md || echo "MISSING ROW: Feature Plan"</automated>
    <!-- Enum-membership gate: every data row's status cell (col 2) and BOS-relationship cell (col 3) MUST be one of the locked enums. Flags any axis cell outside the allowed sets. Excludes table header/separator rows. -->
    <automated>grep -E '^\| ' .planning/AUDIT-INDEX.md | grep -vE '^\| doc / track' | grep -vE '^\|[ -]*\|[ -]*\|' | grep -vE '\|[[:space:]]*(active|historical|superseded|archive-candidate)[[:space:]]*\|[[:space:]]*(substrate|dependency|historical-context|out-of-scope)[[:space:]]*\|' && echo "BAD AXIS CELL (status or BOS-relationship outside allowed enum)" || echo "axis enums OK"</automated>
    <!-- Excluded-doc gate: no system planning doc may appear as a first-class row. -->
    <automated>grep -E '^\| (PROJECT|ROADMAP|REQUIREMENTS|STATE|MILESTONES|AUDIT-INDEX)' .planning/AUDIT-INDEX.md && echo "EXCLUDED DOC LEAKED" || echo "no excluded docs as rows"</automated>
  </verify>
  <acceptance_criteria>
    - AUDIT-INDEX.md exists at .planning/ root.
    - The per-file table contains a row for every one of the 25 audit-subject files (verify commands print no "MISSING ROW" lines — including the "Feature Plan" space-named file, now machine-checked).
    - Every per-file data row's status cell is one of {active, historical, superseded, archive-candidate} and is non-empty (enum-membership grep prints "axis enums OK", never "BAD AXIS CELL").
    - Every per-file data row's BOS-relationship cell is one of {substrate, dependency, historical-context, out-of-scope} and is non-empty (same enum grep).
    - RUST-PORT-PLAN.md's supersedes/superseded-by cell points to HYBRID-REFACTOR-PLAN.md.
    - No row exists for PROJECT.md, ROADMAP.md, REQUIREMENTS.md, STATE.md, MILESTONES.md, or AUDIT-INDEX.md (excluded-doc grep prints "no excluded docs as rows", never "EXCLUDED DOC LEAKED").
    - No file under .planning/ was moved or deleted.
  </acceptance_criteria>
  <done>AUDIT-INDEX.md exists with a complete 25-row per-file table, both axes populated on every row from the locked enums, no excluded system docs as rows, supersession pointers mirrored from STATE/ROADMAP.</done>
</task>

<task type="auto">
  <name>Task 2: Build track rollup table, external appendix, and BOS-PLAN-01/03 verification notes</name>
  <files>.planning/AUDIT-INDEX.md</files>
  <read_first>
    - .planning/STATE.md "## Phase Status" table (lines ~35-73) — authoritative per-track status + the ⊘ SUPERSEDED/ABSORBED markers to mirror.
    - .planning/ROADMAP.md phase table (lines ~14-110) + "## BOS-prefixed phases" section (lines ~113-145) — track goals, BOS build order, and the BOS0 planned note (proves BOS prefix is live = BOS-PLAN-01) and the BOS0-18 listing (proves the split = BOS-PLAN-03).
    - .planning/REQUIREMENTS.md lines 18-21 — BOS-PLAN-01..04 wording.
    - The AUDIT-INDEX.md created in Task 1 (append to it; do not overwrite).
  </read_first>
  <action>
    Append to .planning/AUDIT-INDEX.md a second table "## Track rollup (.planning/phases/)"
    using the same locked column set, with exactly one row per phase track prefix —
    all 10: `01-07` (numbered compiler track), `M`, `A`, `V`, `O`, `F`, `E`, `T`,
    `BOS`, `999.x`. Source each track's Axis-1 status from its STATE.md rows (e.g.
    O-track = superseded; M13 absorbed but M-track overall mixed active/complete; BOS
    = active; V = active/substrate; numbered 01-07 = historical shipped language core).
    Source Axis-2 BOS-relationship from ROADMAP + PROJECT carry-forward (e.g. V/A =
    substrate or dependency for BOS; O = historical-context — superseded into V; numbered
    01-07 = historical-context; M = dependency/historical-context; BOS = substrate;
    999.x = out-of-scope or historical-context). Both cells non-empty per row, each
    drawn from the locked enums in <taxonomy>. In the supersession cell, mirror the
    O1-O6->V-track, M13->V8, M5->E-track, A13-02..06->V25 chains from
    <supersession_truth>; use "—" where none.
    Then add "## Appendix: stray planning docs outside .planning/" — a short bulleted
    or table list noting external strays (.vscode/voss_v_0_1_scope_lock.md and any
    repo-root design docs found), each annotated with status + relationship but
    explicitly marked NOT a first-class index row (appendix-only, per D-01). Run
    `ls .vscode/*.md` and a quick repo-root `*.md` scan to populate it.
    Finally add "## Requirement verification" with two short notes:
    (1) BOS-PLAN-01 — confirm BOS phase prefixes already exist in ROADMAP (cite the
    BOS0/BOS1 rows + "BOS-prefixed phases" section); record as VERIFIED, not re-done.
    (2) BOS-PLAN-03 — confirm the BOS0-BOS18 split is recorded and adequate (cite the
    18-row BOS table); record as VERIFIED-adequate, no re-split (per Deferred in CONTEXT).
    Do NOT move or delete any file.
  </action>
  <verify>
    <automated>for t in '01-07' '| M ' '| A ' '| V ' '| O ' '| F ' '| E ' '| T ' '| BOS ' '999.x'; do grep -q "$t" .planning/AUDIT-INDEX.md || echo "MISSING TRACK: $t"; done; grep -qi 'BOS-PLAN-01' .planning/AUDIT-INDEX.md && grep -qi 'BOS-PLAN-03' .planning/AUDIT-INDEX.md && grep -qi 'appendix' .planning/AUDIT-INDEX.md && echo "sections present"</automated>
    <!-- Enum-membership gate (re-run after appending the rollup table): every data row's status (col 2) + BOS-relationship (col 3) MUST be a locked enum. Header/separator rows excluded. Catches any bad axis cell introduced by the rollup or appendix tables. -->
    <automated>grep -E '^\| ' .planning/AUDIT-INDEX.md | grep -vE '^\| doc / track' | grep -vE '^\|[ -]*\|[ -]*\|' | grep -vE '\|[[:space:]]*(active|historical|superseded|archive-candidate)[[:space:]]*\|[[:space:]]*(substrate|dependency|historical-context|out-of-scope)[[:space:]]*\|' && echo "BAD AXIS CELL (status or BOS-relationship outside allowed enum)" || echo "axis enums OK"</automated>
    <!-- Excluded-doc gate (re-run): system planning docs must not appear as first-class rows in any table. -->
    <automated>grep -E '^\| (PROJECT|ROADMAP|REQUIREMENTS|STATE|MILESTONES|AUDIT-INDEX)' .planning/AUDIT-INDEX.md && echo "EXCLUDED DOC LEAKED" || echo "no excluded docs as rows"</automated>
  </verify>
  <acceptance_criteria>
    - The track rollup table contains exactly one row for each of the 10 track prefixes (verify command prints no "MISSING TRACK" lines).
    - Every track row has a non-empty status cell (axis 1 enum) AND a non-empty BOS-relationship cell (axis 2 enum) — enum-membership grep prints "axis enums OK", never "BAD AXIS CELL".
    - O-track row's supersession cell references the V-track (O1-O6 -> V); A13/M13/M5 chains mirrored where rolled up.
    - An "Appendix" section exists listing external strays (incl. .vscode/voss_v_0_1_scope_lock.md), marked as non-first-class (and not appearing as a `^|` table row — excluded-doc grep stays clean).
    - A "Requirement verification" section records BOS-PLAN-01 as VERIFIED (prefix exists) and BOS-PLAN-03 as VERIFIED-adequate (no re-split).
    - No system planning doc appears as a first-class row (excluded-doc grep prints "no excluded docs as rows").
    - No file under .planning/ was moved or deleted.
  </acceptance_criteria>
  <done>AUDIT-INDEX.md now has the 10-row track rollup, the external appendix, and BOS-PLAN-01/03 verification notes — both axes populated everywhere from the locked enums, no excluded docs as rows, no files touched.</done>
</task>

</tasks>

<verification>
- `test -f .planning/AUDIT-INDEX.md` passes.
- 25 per-file rows present (one per audit subject, including "Feature Plan.md" — machine-checked), 10 track-rollup rows present.
- Enum-membership grep prints "axis enums OK" — every data row's status AND BOS-relationship cell is drawn from the locked enums.
- Excluded-doc grep prints "no excluded docs as rows" — no system planning doc leaked in as a first-class row.
- Supersession pointers match STATE.md/ROADMAP.md (no invented chains).
- `git status --porcelain .planning/` shows ONLY AUDIT-INDEX.md added/modified — no moves, no deletes.
</verification>

<success_criteria>
A reviewer can open `.planning/AUDIT-INDEX.md` and see, for every loose planning
doc and every phase track, both its lifecycle status and its relationship to BOS,
with supersession traced to existing markers — the gate that makes any later
archive/delete "not blind". Both axes are machine-verified against the locked
enums, no system docs leak in as rows, and BOS-PLAN-01/03 are recorded as
verified. Zero files moved or deleted.
</success_criteria>

<output>
Create `.planning/phases/BOS1-planning-audit-and-archive-map/BOS1-01-SUMMARY.md` when done.
</output>
