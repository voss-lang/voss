---
phase: V0-reframe-consolidate
plan: 02
subsystem: docs
tags: [prd, superseded-banner, identity, project-md, brand]

requires:
  - phase: V0-01
    provides: "canonical PRD at .planning/docs/ORCHESTRATION_LAYERS.md (banner/link target)"
provides:
  - "PRD.md first-screen ⊘ SUPERSEDED banner linking to the canonical PRD"
  - "PROJECT.md '## What This Is' lead reframed: org-layer-first, .voss + harness named as substrate"
affects: [downstream V-track phases, anyone arriving via old PRD.md or PROJECT.md]

tech-stack:
  added: []
  patterns:
    - "Satellite identity docs point to (don't duplicate) the canonical PRD; brand (.voss + harness) preserved, not erased"

key-files:
  created:
    - .planning/phases/V0-reframe-consolidate/V0-02-SUMMARY.md
  modified:
    - PRD.md
    - .planning/PROJECT.md

key-decisions:
  - "PRD.md banner placed immediately under the line-1 title (first screen, line 3); body untouched"
  - "PRD.md link uses repo-root-relative path .planning/docs/ORCHESTRATION_LAYERS.md"
  - "PROJECT.md link uses .planning-relative path docs/ORCHESTRATION_LAYERS.md (resolves to same file)"
  - "Only the '## What This Is' paragraph rewritten; Core Value + milestone sections byte-unchanged"

patterns-established:
  - "Org-layer-atop-substrate framing: agent engineering organization layer over the harness + .voss substrates"

requirements-completed: [VRFM-01, VRFM-02]

duration: 8min
completed: 2026-06-06
---

# Phase V0-02: Reframe & Consolidate — Satellite Doc Reframe Summary

**Old root `PRD.md` now self-declares SUPERSEDED and routes to the canonical PRD; `.planning/PROJECT.md` leads with the agent-engineering-organization-layer identity atop the named `.voss` + harness substrate.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2 / 2 completed
- **Files modified:** 2 (`PRD.md`, `.planning/PROJECT.md`)

## Accomplishments

### Task 1 — PRD.md SUPERSEDED banner (VRFM-01, satellite side)
- Prepended a `> ⊘ **SUPERSEDED**` blockquote immediately under the line-1 title (first screen). It marks the doc as the retained historical **language PRD**, points to the canonical PRD with a working repo-root-relative link `[.planning/docs/ORCHESTRATION_LAYERS.md](.planning/docs/ORCHESTRATION_LAYERS.md)`, and notes the `.voss` spec below remains accurate. No existing body content touched.

### Task 2 — PROJECT.md lead reframe (VRFM-02) + scope guard
- Rewrote only the `## What This Is` paragraph: Voss framed first as an **agent engineering organization layer**, explicitly naming the **harness** (`voss` CLI/TUI) and the **`.voss` language** as the two substrates beneath it, with a pointer to the canonical PRD. `## Core Value` and milestone sections left byte-unchanged.

## Verification

- Task 1 automated verify: `SUPERSEDED` in first 12 lines; canonical relative link present; link target resolves on disk; `compiles to Python` body line intact → **OK**.
- Task 2 automated verify: `agent engineering organization` present; `.voss` + `harness` still named; `bounded, inspectable, resumable AI coding work` Core Value intact → **OK**.
- Scope guards: `README.md` absent from the changed set; every changed path ends in `.md` (no source/CLI/grammar files); PROJECT.md→canonical link resolves.

## Notes

- Phase working tree also still holds V0-01's uncommitted `.md` edits (ORCHESTRATION_LAYERS.md + V0-01-SUMMARY.md) — the auto-commit hook has not fired; all changes remain documentation-only, so the phase-level docs-only / README-unchanged guard holds.
- VRFM-01 is now satisfied on both sides: doc side (V0-01 status line in the canonical PRD) + satellite side (this plan's PRD.md banner).
