# Phase V0: Reframe & Consolidate - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct from V0-SPEC.md (discuss-phase skipped — ambiguity 0.151, decisions locked in spec)

<domain>
## Phase Boundary

Docs-only identity reframe. Make `ORCHESTRATION_LAYERS.md` the canonical PRD + architecture
doc; lead all identity docs with "agent engineering organization layer" atop the `.voss`
language + harness substrate (brand preserved, not erased). Add a glossary and a
phase→primitive map to the canonical PRD; normalize the six-primitive section; archive the
old root `PRD.md` as superseded; reframe `.planning/PROJECT.md` lead.

No runtime/code/CLI/grammar change. Public `README.md` and npm `@vosslang` copy untouched.
The phase diff must contain only documentation files.
</domain>

<decisions>
## Implementation Decisions

### Canonical doc path (CORRECTION — read carefully)
- **The canonical PRD lives at `.planning/docs/ORCHESTRATION_LAYERS.md`, NOT `docs/ORCHESTRATION_LAYERS.md`.**
  The SPEC repeatedly writes `docs/ORCHESTRATION_LAYERS.md`; that path does not exist in the repo.
  Verified actual path: `.planning/docs/ORCHESTRATION_LAYERS.md`. All plan tasks MUST target the
  real path. SUPERSEDED-banner and PROJECT.md links MUST use a correct relative path to the real file.

### Current state of the canonical doc (verified 2026-06-06)
- Title is already `# Voss PRD: Agent Engineering Organization Layer` (line 1).
- §1 Product Thesis already contains the "not a rigid automation pipeline" framing — V0 confirms/strengthens, does not author from scratch.
- §4.1 "Six Product Primitives" table already exists.
- §4.2 "Recursive Architecture" (L0–L4) table already exists.
- §6 already contains "Phase 0: Reframe And Consolidate" (this phase, as P0).
- NO glossary section exists. NO phase→primitive map exists. Both are net-new in V0.

### REQ 1 — Canonical PRD promotion
- Add an explicit status declaration near the top of `.planning/docs/ORCHESTRATION_LAYERS.md`
  (immediately under the existing title or beside the existing roadmap-status banner) stating it
  is the **canonical PRD + architecture doc** for Voss. One line is sufficient; do not restructure the doc.
- Root `PRD.md`: prepend a `> ⊘ **SUPERSEDED**` banner as the first content block (above the existing
  `# Voss Language — Product Requirements Document` title or immediately under it on the first screen).
  Banner text: states this doc is retained as the historical language-PRD and that the canonical PRD is
  now `.planning/docs/ORCHESTRATION_LAYERS.md`, with a working relative link. Do not delete or rewrite
  PRD.md body content — banner only.

### REQ 2 — PROJECT.md identity reframe
- Rewrite only the `## What This Is` lead paragraph of `.planning/PROJECT.md`.
- New lead names "agent engineering organization layer" as the primary framing AND explicitly keeps
  both the `.voss` language and the harness named as the substrate beneath it.
- Required literal phrase in the lead: **"agent engineering organization"** (acceptance grep target).
- Must still reference `.voss` language AND harness. Leave the rest of PROJECT.md (Core Value,
  milestone sections) unchanged.

### REQ 3 — Six primitives normalized
- Normalize the existing §4.1 table so each of the six — capabilities, principles, orchestration,
  roles, memory, verification — has both a one-line product meaning AND a named implementation-surface
  cell. Confirm exactly these six, no more/fewer. Edit in place; do not duplicate the table elsewhere.

### REQ 4 — Phase→primitive map (net-new section)
- Add a new section to `.planning/docs/ORCHESTRATION_LAYERS.md` (suggested placement: §4.3, right
  after the Recursive Architecture table, so the map sits inside the Core Product Model).
- Table maps every roadmap track prefix — M, T, A, O, F, V — to ≥1 of the six primitive names.
- O-track row must note it is folded into / superseded by V (the doc's existing banner already states
  the V↔O supersession — reuse that mapping, don't re-derive).
- Map at the track-prefix granularity (one row per prefix), not per-phase — per-phase rewrites are out of scope.

### REQ 5 — Terminology glossary (net-new section)
- Add a glossary section to `.planning/docs/ORCHESTRATION_LAYERS.md` (suggested placement: a top-level
  `## Glossary` near the end, before any roadmap appendix).
- Define at least these 11 terms: capability, role, agent, subagent, EM, card, board, gate, verifier,
  reviewer, audit. One concise definition each, consistent with how the PRD already uses them.

### "Not a rigid pipeline" framing
- Already present in §1 thesis. Confirm it reads clearly; strengthen only if a one-line edit helps.
  No new section required for this — it is REQ-adjacent, satisfied by §1.

### Claude's Discretion
- Exact wording of the canonical-PRD status line, the SUPERSEDED banner prose, glossary definitions,
  and phase→primitive map cell contents.
- Exact section numbering/anchors for the two net-new sections (suggestions above are non-binding).
- Whether glossary terms beyond the required 11 are added (allowed, not required).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Identity docs in scope
- `.planning/docs/ORCHESTRATION_LAYERS.md` — the canonical PRD being promoted/extended (six-primitive table §4.1, L0–L4 §4.2, thesis §1, P0 def §6). PRIMARY edit target.
- `PRD.md` (repo root) — old language-PRD; gets a SUPERSEDED banner only.
- `.planning/PROJECT.md` — planning entry doc; lead paragraph reframed.
- `.planning/ROADMAP.md` — source for the M/T/A/O/F/V track prefixes used in the phase→primitive map.

### Spec
- `.planning/phases/V0-reframe-consolidate/V0-SPEC.md` — the 5 locked requirements + acceptance criteria this phase delivers. NOTE its `docs/...` path is wrong; use `.planning/docs/...`.

### Scope guards (must NOT change)
- `README.md` — out of scope; must be byte-identical in the phase diff.
- npm `@vosslang` package copy — out of scope.
- Any source/CLI/grammar file — out of scope (docs-only).
</canonical_refs>

<specifics>
## Specific Ideas

- Acceptance is grep-checkable: `ORCHESTRATION_LAYERS.md` contains a canonical-PRD declaration line;
  `PRD.md` first screen contains "SUPERSEDED" + relative link; `PROJECT.md` lead contains
  "agent engineering organization" + names `.voss`/harness; canonical PRD contains the six primitive
  names, a map covering all six prefixes M/T/A/O/F/V, and a glossary with the 11 terms.
- Scope-guard acceptance: phase diff contains zero non-documentation files; `README.md` unchanged.
- Reuse-not-recreate: glossary + phase map exist ONLY in the canonical PRD; other docs link, never duplicate.
</specifics>

<deferred>
## Deferred Ideas

- Public `README.md` / npm `@vosslang` rebrand — separate higher-stakes decision (out of scope).
- `.voss` grammar work — V10.
- Per-phase detail rewrites of M/O/F/A phases — only the cross-track primitive map is added.
</deferred>

---

*Phase: V0-reframe-consolidate*
*Context derived 2026-06-06 directly from V0-SPEC.md (discuss-phase skipped per low ambiguity)*
