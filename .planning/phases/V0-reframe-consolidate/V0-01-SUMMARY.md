---
phase: V0-reframe-consolidate
plan: 01
subsystem: docs
tags: [prd, canonical-doc, glossary, primitives, roadmap-mapping]

requires: []
provides:
  - "ORCHESTRATION_LAYERS.md declared the canonical PRD + architecture doc (status line, first screen)"
  - "Normalized six-primitive table (verified exactly six populated rows)"
  - "§4.3 Phase→Primitive map covering all six track prefixes M/T/A/O/F/V (O noted as folded into V)"
  - "## Glossary defining 11 org-layer terms (capability, role, agent, subagent, EM, card, board, gate, verifier, reviewer, audit)"
affects: [V0-02, V0-03, downstream V-track phases referencing the canonical PRD]

tech-stack:
  added: []
  patterns:
    - "Single-source-of-truth: glossary + phase→primitive map live only in the canonical PRD; other docs reference, never duplicate"

key-files:
  created:
    - .planning/phases/V0-reframe-consolidate/V0-01-SUMMARY.md
  modified:
    - .planning/docs/ORCHESTRATION_LAYERS.md

key-decisions:
  - "Status line placed directly above the existing roadmap-status banner (first screen); title + banner left intact"
  - "§4.1 already had six populated rows — verified, not rewritten (no thin cells)"
  - "§1 'not a rigid automation pipeline' thesis already clear — confirmed, left unchanged"
  - "§4.3 mapped at track-prefix granularity (one row per prefix), sourced from ROADMAP.md track defs + reused the banner's V↔O supersession mapping"

patterns-established:
  - "Phase→primitive map: track prefix → ≥1 of the six primitives, prefix-granular"

requirements-completed: [VRFM-01, VRFM-03, VRFM-04, VRFM-05]

duration: 12min
completed: 2026-06-06
---

# Phase V0-01: Reframe & Consolidate — Canonical PRD Promotion Summary

**`.planning/docs/ORCHESTRATION_LAYERS.md` now self-declares as Voss's canonical PRD + architecture doc and carries the complete org-layer content: normalized primitives, a track→primitive map, and an 11-term glossary.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2 / 2 completed
- **Files modified:** 1 (`.planning/docs/ORCHESTRATION_LAYERS.md`)

## Accomplishments

### Task 1 — Status line + thesis confirm + primitives normalize (VRFM-01, VRFM-03)
- Added a `> **Status:**` line above the roadmap-status banner asserting **canonical PRD and architecture doc** status (first screen, line 3). Title (line 1) and existing roadmap-status banner untouched.
- Confirmed §1 thesis preserves the "not a rigid automation pipeline" framing — already clear, left unchanged.
- Verified §4.1 "Six Product Primitives" has exactly six rows (Capabilities, Principles, Orchestration, Roles, Memory, Verification), each with populated Product Meaning + Implementation Surface cells. No rewrite needed.

### Task 2 — Phase→primitive map + glossary (VRFM-04, VRFM-05)
- Added **§4.3 Phase to Primitive Map** between §4.2 and §5 (inside Core Product Model): one row per ROADMAP track prefix — M, T, A, O, F, V — each mapped to ≥1 primitive name. O-track row marked **⊘ superseded / folded into the V-track**, reusing the banner's V↔O supersession mapping (not re-derived).
- Added a top-level **## Glossary** at end-of-file defining the 11 required terms (capability, role, agent, subagent, EM, card, board, gate, verifier, reviewer, audit), one concise definition each, consistent with PRD usage.

## Verification

- Task 1 automated verify: `canonical PRD` + `architecture doc` (first 40 lines) + `not a rigid` present; all six primitive rows present; title unchanged → **OK**.
- Task 2 automated verify: `## Glossary` (exactly one) + phase→primitive heading present; all 11 terms grep-found; O-row `supersed/fold` note present; all six prefix rows (M/T/A/O/F/V) present → **OK**.
- Docs-only constraint: `git status --short` shows only `.planning/docs/ORCHESTRATION_LAYERS.md` modified. Zero source/CLI/grammar files in the diff.

## Notes

- This plan (V0-01) is scoped to `ORCHESTRATION_LAYERS.md` only. REQ 2 (PROJECT.md lead) and the `PRD.md` SUPERSEDED banner mentioned in V0-CONTEXT belong to sibling plans, not this one.
- Used the corrected canonical path `.planning/docs/ORCHESTRATION_LAYERS.md` throughout (the SPEC's `docs/...` path is wrong, per CONTEXT correction).
