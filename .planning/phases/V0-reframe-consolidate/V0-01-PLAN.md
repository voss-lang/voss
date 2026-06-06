---
phase: V0-reframe-consolidate
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/docs/ORCHESTRATION_LAYERS.md
autonomous: true
requirements: [VRFM-01, VRFM-03, VRFM-04, VRFM-05]
must_haves:
  truths:
    - "A reader of the canonical PRD sees it explicitly declare itself the canonical PRD + architecture doc."
    - "A reader can name all six primitives with a meaning and an implementation surface from one table."
    - "A reader can map every roadmap track prefix (M, T, A, O, F, V) to at least one primitive."
    - "A reader can look up the 11 org-layer terms in one glossary."
    - "A reader sees the 'not a rigid pipeline' framing in the thesis."
  artifacts:
    - path: ".planning/docs/ORCHESTRATION_LAYERS.md"
      provides: "Canonical-PRD status line, normalized six-primitive table, phase→primitive map, glossary"
      contains: "canonical PRD"
  key_links:
    - from: ".planning/docs/ORCHESTRATION_LAYERS.md §4.3 phase→primitive map"
      to: "§4.1 six primitives"
      via: "each map row references ≥1 of the six primitive names"
      pattern: "Capabilities|Principles|Orchestration|Roles|Memory|Verification"
---

<objective>
Promote `.planning/docs/ORCHESTRATION_LAYERS.md` to the canonical PRD + architecture doc and complete its org-layer content: add a canonical-PRD status declaration, normalize the existing six-primitive table, add a net-new phase→primitive map covering all six track prefixes, and add a net-new terminology glossary covering the 11 required terms. Confirm the existing "not a rigid pipeline" thesis reads clearly.

Purpose: One source of truth for Voss's identity — a contributor can trace identity → six primitives → roadmap tracks → vocabulary from this single doc.
Output: Edits in place to `.planning/docs/ORCHESTRATION_LAYERS.md` only. No other file touched. No code/CLI/grammar change.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V0-reframe-consolidate/V0-SPEC.md
@.planning/phases/V0-reframe-consolidate/V0-CONTEXT.md

<critical_path_note>
The canonical doc lives at `.planning/docs/ORCHESTRATION_LAYERS.md` — NOT `docs/ORCHESTRATION_LAYERS.md`. The SPEC writes the wrong `docs/...` path repeatedly; ignore it and use the real `.planning/docs/...` path. The doc is ~834 lines; read the regions you edit before editing. Verified current-state anchors (2026-06-06):
- Line 1: title `# Voss PRD: Agent Engineering Organization Layer` (already correct — do not retitle).
- Line 3: existing `> **Roadmap status (2026-06-05):** ...` banner block (already states V↔O supersession + M13→V8 absorption — reuse this mapping, do not re-derive it).
- Line 5: `## 1. Product Thesis`; line 7 already contains "not a rigid automation pipeline".
- Line 89: `### 4.1 Six Product Primitives`; lines 91-98 = the existing 3-column table (Primitive | Product Meaning | Implementation Surface) with all six rows present.
- Line 100: `### 4.2 Recursive Architecture` (L0–L4 table, lines 104-110).
- Line 112: `## 5. Required User Experience` — the §4.3 phase→primitive map goes BETWEEN line 110 and line 112 (end of §4, inside Core Product Model).
- Line 158: `## 6. Phased Roadmap` — the glossary goes near the end of the doc, before any roadmap appendix; a top-level `## Glossary` at end-of-file is acceptable.
</critical_path_note>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Canonical-PRD status line + thesis confirm + six-primitive normalize</name>
  <files>.planning/docs/ORCHESTRATION_LAYERS.md</files>
  <read_first>
    - .planning/docs/ORCHESTRATION_LAYERS.md (lines 1-110: title, roadmap-status banner, §1 thesis, §4.1 primitives table, §4.2 recursion)
    - .planning/phases/V0-reframe-consolidate/V0-SPEC.md (REQ 1, REQ 3, "not a rigid pipeline" acceptance)
    - .planning/phases/V0-reframe-consolidate/V0-CONTEXT.md (REQ 1, REQ 3 decisions; canonical-path correction)
  </read_first>
  <action>
    In `.planning/docs/ORCHESTRATION_LAYERS.md`:
    (a) REQ 1 (VRFM-01): Add ONE status-declaration line near the top stating this doc is the canonical PRD + architecture doc for Voss. Place it immediately under the line-1 title or directly beside the existing line-3 roadmap-status banner. The line MUST contain the literal phrase "canonical PRD" and assert architecture-doc status. Do not restructure the doc, do not retitle line 1, do not delete the existing roadmap-status banner.
    (b) "Not a rigid pipeline" framing: confirm the §1 thesis (around line 7) reads clearly that Voss models an engineering organization and is NOT a rigid automation pipeline. Strengthen with at most a one-line edit only if it does not already read clearly; otherwise leave unchanged. No new section.
    (c) REQ 3 (VRFM-03): Normalize the §4.1 "Six Product Primitives" table in place so each of exactly these six rows — Capabilities, Principles, Orchestration, Roles, Memory, Verification — has a non-empty one-line Product Meaning cell AND a non-empty Implementation Surface cell. The table already has all three columns and all six rows; verify each cell is populated and meaningful, tighten wording if any cell is thin, and confirm there are exactly six rows (no more, no fewer). Edit in place — do NOT duplicate the table anywhere else in the repo.
    Do not touch any file other than `.planning/docs/ORCHESTRATION_LAYERS.md`. Do not edit §4.3/glossary here (Task 2 owns those).
  </action>
  <acceptance_criteria>
    - `grep -i "canonical PRD" .planning/docs/ORCHESTRATION_LAYERS.md` returns at least one line within the first 40 lines of the file.
    - `grep -i "architecture doc" .planning/docs/ORCHESTRATION_LAYERS.md` returns at least one line (canonical-PRD + architecture-doc status asserted).
    - `grep -i "not a rigid" .planning/docs/ORCHESTRATION_LAYERS.md` still returns the thesis line (framing preserved).
    - The §4.1 table contains exactly six primitive rows. Verify each of the six names appears as a row: `for p in Capabilities Principles Orchestration Roles Memory Verification; do grep -q "| *$p" .planning/docs/ORCHESTRATION_LAYERS.md || echo "MISSING $p"; done` prints nothing.
    - Line 1 still reads `# Voss PRD: Agent Engineering Organization Layer` (title unchanged).
    - `git diff --name-only` shows ONLY `.planning/docs/ORCHESTRATION_LAYERS.md` changed by this task.
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -iq "canonical PRD" .planning/docs/ORCHESTRATION_LAYERS.md && grep -iq "architecture doc" .planning/docs/ORCHESTRATION_LAYERS.md && grep -iq "not a rigid" .planning/docs/ORCHESTRATION_LAYERS.md && for p in Capabilities Principles Orchestration Roles Memory Verification; do grep -q "| *$p" .planning/docs/ORCHESTRATION_LAYERS.md || { echo "MISSING $p"; exit 1; }; done && echo OK</automated>
  </verify>
  <done>Canonical-PRD + architecture-doc status line present in the first screen; §1 thesis preserves the "not a rigid pipeline" framing; §4.1 has exactly six fully-populated primitive rows; title and roadmap-status banner intact.</done>
</task>

<task type="auto">
  <name>Task 2: Phase→primitive map (§4.3) + terminology glossary</name>
  <files>.planning/docs/ORCHESTRATION_LAYERS.md</files>
  <read_first>
    - .planning/docs/ORCHESTRATION_LAYERS.md (lines 89-112 for §4 placement; line 3 roadmap-status banner for the V↔O supersession mapping; near end-of-file for glossary placement)
    - .planning/ROADMAP.md (the "Phase Order" table + the "V-prefixed phases" section — authoritative source for the M/T/A/O/F/V track prefixes and what each track does; O-track rows marked ⊘ SUPERSEDED by V)
    - .planning/phases/V0-reframe-consolidate/V0-SPEC.md (REQ 4, REQ 5 acceptance)
    - .planning/phases/V0-reframe-consolidate/V0-CONTEXT.md (REQ 4, REQ 5 decisions: track-prefix granularity, O folds into V, 11 required terms)
  </read_first>
  <action>
    In `.planning/docs/ORCHESTRATION_LAYERS.md`, add two net-new sections (these do not exist yet):
    (a) REQ 4 (VRFM-04) — Phase→primitive map: Add a new subsection (suggested `### 4.3 Phase to Primitive Map`) placed at the end of §4 (after the §4.2 L0–L4 table, before `## 5. Required User Experience`). It is a table with one row per ROADMAP track prefix. Cover ALL SIX prefixes: M, T, A, O, F, V. Each row maps that prefix to ≥1 of the six primitive names spelled exactly as in §4.1 (Capabilities, Principles, Orchestration, Roles, Memory, Verification). Source the track meanings from `.planning/ROADMAP.md` (M = harness milestones, T = gap-closure, A = voss-app ADE, O = superseded orchestration, F = substrate features, V = agent-org layer). The O-track row MUST note it is folded into / superseded by the V-track — reuse the supersession mapping already in the line-3 roadmap-status banner; do not re-derive it. Map at track-prefix granularity only (one row per prefix) — no per-phase rows.
    (b) REQ 5 (VRFM-05) — Glossary: Add a top-level `## Glossary` section near the end of the doc (before any roadmap appendix; end-of-file is acceptable). Define AT LEAST these 11 terms, one concise definition each, consistent with how the PRD already uses them: capability, role, agent, subagent, EM, card, board, gate, verifier, reviewer, audit. Additional terms are allowed but not required. Keep definitions one line where possible.
    Single source of truth: the map and glossary live ONLY in this doc — do not duplicate them into PROJECT.md, PRD.md, or ROADMAP.md. Touch no file other than `.planning/docs/ORCHESTRATION_LAYERS.md`.
  </action>
  <acceptance_criteria>
    - A phase→primitive map section exists: `grep -niE "phase.*primitive|primitive.*map" .planning/docs/ORCHESTRATION_LAYERS.md` returns a heading line.
    - The map covers all six track prefixes. After locating the map section, each of M, T, A, O, F, V appears as a row label — verifiable that the six single-letter prefixes are each present as table-row leads in the new section.
    - Every map row references ≥1 of the six primitive names (the six names from §4.1 appear within the map section).
    - The O-track map row contains "supersed" or "fold" (case-insensitive) noting the V-fold: `grep -niE "O .*(supersed|fold)" .planning/docs/ORCHESTRATION_LAYERS.md` returns a line.
    - A glossary exists: `grep -niE "^## *Glossary" .planning/docs/ORCHESTRATION_LAYERS.md` returns exactly one line.
    - All 11 glossary terms are defined: `for t in capability role agent subagent EM card board gate verifier reviewer audit; do grep -iqw "$t" .planning/docs/ORCHESTRATION_LAYERS.md || echo "MISSING $t"; done` prints nothing (note: each of these terms appears in the glossary; subagent and EM are the tightest — confirm both are present).
    - `git diff --name-only` shows ONLY `.planning/docs/ORCHESTRATION_LAYERS.md` changed.
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -niE "^## *Glossary" .planning/docs/ORCHESTRATION_LAYERS.md && grep -niE "phase.*primitive|primitive.*map" .planning/docs/ORCHESTRATION_LAYERS.md && for t in capability role agent subagent EM card board gate verifier reviewer audit; do grep -iqw "$t" .planning/docs/ORCHESTRATION_LAYERS.md || { echo "MISSING TERM $t"; exit 1; }; done && echo OK</automated>
  </verify>
  <done>§4.3 phase→primitive map present covering all six prefixes M/T/A/O/F/V (each → ≥1 primitive, O noted as folded into V); a `## Glossary` section defines all 11 required terms; both sections exist only in this doc.</done>
</task>

</tasks>

<verification>
- `.planning/docs/ORCHESTRATION_LAYERS.md` is the only file changed by this plan: `git diff --name-only` lists exactly that path.
- Canonical-PRD + architecture-doc status declared in first screen.
- §4.1 has exactly six populated primitive rows; §4.3 map covers M/T/A/O/F/V; `## Glossary` defines the 11 terms.
- No source/CLI/grammar file appears in the diff (docs-only constraint).
</verification>

<success_criteria>
- VRFM-01 (canonical-PRD promotion, doc side), VRFM-03 (six primitives normalized), VRFM-04 (phase→primitive map), VRFM-05 (glossary) all satisfied in `.planning/docs/ORCHESTRATION_LAYERS.md`.
- "Not a rigid pipeline" thesis framing confirmed present.
- Zero non-documentation files in the diff.
</success_criteria>

<output>
Create `.planning/phases/V0-reframe-consolidate/V0-01-SUMMARY.md` when done.
</output>
