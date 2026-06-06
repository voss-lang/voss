---
phase: V0-reframe-consolidate
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - PRD.md
  - .planning/PROJECT.md
autonomous: true
requirements: [VRFM-01, VRFM-02]
must_haves:
  truths:
    - "A reader landing on the old root PRD.md immediately sees it is SUPERSEDED and is pointed to the canonical PRD."
    - "A reader of PROJECT.md sees Voss framed first as an agent engineering organization layer, atop the named .voss + harness substrate."
    - "README.md and npm package copy are byte-unchanged (scope guard)."
    - "No non-documentation files appear in the phase diff (scope guard)."
  artifacts:
    - path: "PRD.md"
      provides: "Top-of-doc ⊘ SUPERSEDED banner linking to the canonical PRD"
      contains: "SUPERSEDED"
    - path: ".planning/PROJECT.md"
      provides: "Org-layer-atop-substrate lead paragraph"
      contains: "agent engineering organization"
  key_links:
    - from: "PRD.md SUPERSEDED banner"
      to: ".planning/docs/ORCHESTRATION_LAYERS.md"
      via: "relative markdown link"
      pattern: "ORCHESTRATION_LAYERS\\.md"
---

<objective>
Reframe the two satellite identity docs so they point at the canonical PRD and lead with the org-layer identity: prepend a `⊘ SUPERSEDED` banner to root `PRD.md` linking to the canonical PRD, and rewrite the lead paragraph of `.planning/PROJECT.md` to name "agent engineering organization layer" atop the named `.voss` language + harness substrate. Enforce the docs-only / README-unchanged scope guard.

Purpose: Anyone arriving via the old PRD or the planning entry doc is routed to (and framed by) the canonical org-layer identity, without erasing the shipped language+harness brand.
Output: Banner-only edit to `PRD.md`; lead-paragraph-only edit to `.planning/PROJECT.md`. No other files touched. No code/CLI/grammar change. `README.md` byte-unchanged.
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
The canonical PRD lives at `.planning/docs/ORCHESTRATION_LAYERS.md` — NOT `docs/ORCHESTRATION_LAYERS.md`. The SPEC writes the wrong path; use the real one.
- `PRD.md` is at repo ROOT. The relative link from `PRD.md` (root) to the canonical doc is `.planning/docs/ORCHESTRATION_LAYERS.md`.
- `.planning/PROJECT.md`: the lead is the `## What This Is` paragraph (currently line 5): "Voss is an AI-native coding harness and programming language…". Only this paragraph is rewritten; Core Value (line 9) and the milestone sections below stay unchanged.
- Brand preservation is a hard constraint: both reframed docs must STILL name the `.voss` language and the harness as substrate — do not delete the language/harness identity.
</critical_path_note>
</context>

<tasks>

<task type="auto">
  <name>Task 1: PRD.md SUPERSEDED banner (VRFM-01 satellite side)</name>
  <files>PRD.md</files>
  <read_first>
    - PRD.md (lines 1-15: title `# Voss Language — Product Requirements Document` + version/status block + §1 Overview)
    - .planning/phases/V0-reframe-consolidate/V0-SPEC.md (REQ 1 acceptance)
    - .planning/phases/V0-reframe-consolidate/V0-CONTEXT.md (REQ 1 banner decision + canonical-path correction)
  </read_first>
  <action>
    Prepend a SUPERSEDED banner to root `PRD.md` as the first content block on the first screen — either above the line-1 `# Voss Language — Product Requirements Document` title or immediately under it. Use a blockquote banner beginning with `> ⊘ **SUPERSEDED**`. The banner MUST: (a) contain the literal token "SUPERSEDED"; (b) state this doc is retained as the historical language-PRD; (c) state the canonical PRD is now the org-layer doc and include a WORKING relative markdown link whose target is `.planning/docs/ORCHESTRATION_LAYERS.md` (PRD.md is at repo root, so the relative path is exactly `.planning/docs/ORCHESTRATION_LAYERS.md`). Do NOT delete, rewrite, or reorder any existing PRD.md body content — banner only.
    Touch no file other than `PRD.md` in this task.
  </action>
  <acceptance_criteria>
    - `grep -n "SUPERSEDED" PRD.md` returns a line within the first 12 lines of the file.
    - The banner links to the canonical doc with the correct relative path: `grep -n "\.planning/docs/ORCHESTRATION_LAYERS\.md" PRD.md` returns at least one line.
    - The link target resolves on disk from repo root: `test -f .planning/docs/ORCHESTRATION_LAYERS.md` succeeds (path correctness guard).
    - Existing PRD body preserved: `grep -q "AI-native programming language that compiles to Python" PRD.md` still succeeds (the §1 Overview line is intact — banner did not overwrite body).
    - `git diff --name-only` shows ONLY `PRD.md` changed by this task.
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && head -12 PRD.md | grep -q "SUPERSEDED" && grep -q "\.planning/docs/ORCHESTRATION_LAYERS\.md" PRD.md && test -f .planning/docs/ORCHESTRATION_LAYERS.md && grep -q "compiles to Python" PRD.md && echo OK</automated>
  </verify>
  <done>PRD.md first screen carries a `⊘ SUPERSEDED` blockquote banner linking (correct relative path) to `.planning/docs/ORCHESTRATION_LAYERS.md`; original PRD body content untouched.</done>
</task>

<task type="auto">
  <name>Task 2: PROJECT.md lead reframe (VRFM-02) + scope guard</name>
  <files>.planning/PROJECT.md</files>
  <read_first>
    - .planning/PROJECT.md (lines 1-22: `# Voss`, `## What This Is` lead paragraph, `## Core Value`, milestone section)
    - .planning/phases/V0-reframe-consolidate/V0-SPEC.md (REQ 2 acceptance + scope-guard acceptance criteria)
    - .planning/phases/V0-reframe-consolidate/V0-CONTEXT.md (REQ 2 decision: rewrite only the `## What This Is` lead; required literal phrase; brand-preservation constraint)
  </read_first>
  <action>
    Rewrite ONLY the `## What This Is` lead paragraph of `.planning/PROJECT.md` (the current line-5 paragraph). The new lead MUST: (a) frame Voss FIRST as an "agent engineering organization layer" — the paragraph must contain the literal phrase "agent engineering organization"; (b) explicitly name BOTH the `.voss` language AND the harness as the substrate beneath that layer (brand preserved, not erased); (c) optionally point to the canonical PRD `.planning/docs/ORCHESTRATION_LAYERS.md` for the full org-layer model (single-source — do not duplicate the primitives/glossary here). Leave `## Core Value` (line 9) and everything below it unchanged.
    Scope guard (enforced in acceptance): do NOT modify `README.md`, any npm `@vosslang` package copy, or any source/CLI/grammar file. Touch only `.planning/PROJECT.md` in this task.
  </action>
  <acceptance_criteria>
    - `grep -n "agent engineering organization" .planning/PROJECT.md` returns a line in the `## What This Is` section (first ~8 lines).
    - Brand preserved: `grep -q "\.voss" .planning/PROJECT.md` AND `grep -qi "harness" .planning/PROJECT.md` both succeed in the lead region (language + harness still named as substrate).
    - `## Core Value` line is byte-unchanged: `grep -q "bounded, inspectable, resumable AI coding work" .planning/PROJECT.md` still succeeds.
    - Scope guard — README untouched across the whole phase: `git diff --name-only` (and `git status --porcelain`) shows `README.md` NOT in the changed set.
    - Scope guard — docs-only: the full phase diff contains only `.md` documentation files. `git diff --name-only $(git merge-base HEAD HEAD) 2>/dev/null; git status --porcelain | awk '{print $2}'` — every listed path ends in `.md` and sits under `PRD.md`, `.planning/PROJECT.md`, or `.planning/docs/ORCHESTRATION_LAYERS.md` (plus `.planning/phases/V0-*` plan/summary docs). No non-`.md` path appears.
    - `git diff --name-only` shows ONLY `.planning/PROJECT.md` changed by this task.
  </acceptance_criteria>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q "agent engineering organization" .planning/PROJECT.md && grep -q "\.voss" .planning/PROJECT.md && grep -qi "harness" .planning/PROJECT.md && grep -q "bounded, inspectable, resumable AI coding work" .planning/PROJECT.md && ! git status --porcelain | awk '{print $2}' | grep -qx "README.md" && ! git status --porcelain | awk '{print $2}' | grep -qvE '\.md$' && echo OK</automated>
  </verify>
  <done>PROJECT.md `## What This Is` lead leads with "agent engineering organization" and still names `.voss` + harness as substrate; Core Value and below unchanged; README.md and all non-`.md` files absent from the phase diff.</done>
</task>

</tasks>

<verification>
- `PRD.md` and `.planning/PROJECT.md` are the only files changed by this plan.
- PRD.md carries a first-screen ⊘ SUPERSEDED banner linking to the canonical doc with a correct relative path that resolves on disk.
- PROJECT.md lead contains "agent engineering organization" and still names `.voss` + harness.
- Scope guard holds: `README.md` byte-unchanged; every file in the phase diff is a `.md` documentation file (no source/CLI/grammar).
</verification>

<success_criteria>
- VRFM-01 (satellite side: PRD.md superseded banner) and VRFM-02 (PROJECT.md identity reframe) satisfied.
- README.md and npm copy untouched; zero non-documentation files in the phase diff.
</success_criteria>

<output>
Create `.planning/phases/V0-reframe-consolidate/V0-02-SUMMARY.md` when done.
</output>
