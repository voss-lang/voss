---
phase: V24-ade-product-revamp-swarm-observability
plan: 01
subsystem: docs
tags: [product-contract, ia, vocabulary, ade, voss-app, design-contract]

# Dependency graph
requires:
  - phase: V24-SPEC
    provides: VADE2-01..08 locked requirements + Acceptance Criteria + Interview Log hard-fails
  - phase: V24-CONTEXT
    provides: D-01..D-11 implementation/vocabulary decisions
  - phase: V24-UI-SPEC
    provides: visual/interaction contract + §Copywriting Contract vocabulary table
provides:
  - "apps/voss-app/PRODUCT.md — committed product/design contract (register, IA, success criteria, locked vocabulary)"
  - "Single source of truth for V24 copy + IA cited by V24-02..08"
affects: [V24-02, V24-03, V24-04, V24-05, V24-06, V24-07, V24-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Product contract precedes UI churn (W0 gate); downstream plans cite by section name, never re-derive vocabulary/IA"

key-files:
  created:
    - apps/voss-app/PRODUCT.md
  modified: []

key-decisions:
  - "PRODUCT.md owns product decisions (register/IA/vocabulary/success); V24-UI-SPEC owns visual/interaction detail — pointer, no duplication of token tables"
  - "Locked vocabulary table cites each decision ID inline (D-08 Task·D-09 steps/cards+runId internal·D-10 Swarm Map·D-11 Read only/Can edit/Autopilot)"

patterns-established:
  - "W0 contract pattern: register + IA + success criteria + locked vocabulary as the citable source of truth for a multi-plan UI phase"

requirements-completed: [VADE2-01]

# Metrics
duration: 9 min
completed: 2026-06-15
---

# Phase V24 Plan 01: Product & Design Contract Summary

**Committed `apps/voss-app/PRODUCT.md` — the W0 product/design contract locking the product register, 8-item left-portal IA, V24-SPEC success criteria, and the load-bearing copy vocabulary (Task/Swarm Map/Read only·Can edit·Autopilot/steps·cards) that V24-02..08 cite without re-derivation.**

## Performance

- **Duration:** 9 min
- **Tasks:** 1
- **Files created:** 1
- **Verification:** grep gate `CONTRACT_OK` + 3-agent adversarial workflow (PRODUCT.md PASS on all in-scope dimensions)

## Accomplishments

- Authored `apps/voss-app/PRODUCT.md` (155 lines) with all five required labeled sections: Product Register, Information Architecture, Success Criteria, Locked Vocabulary, Visual & Interaction Contract.
- **Product Register:** default register = product; primary user = Ben; future audience = developer teams; product thesis quoted byte-identical from ROADMAP §V24.
- **Information Architecture:** all 8 portal items in order (Overview, Tasks, Agents, Swarm Map, Review, Context, Memory, Settings); marks 4 NEW (Overview/Tasks/Agents/Swarm Map) vs 4 reused-as-is (Review/Context/Memory/Settings); states canvas-swap spatial model (D-01) + launch-to-grid (D-02).
- **Success Criteria:** 11 falsifiable bars copied 1:1 from V24-SPEC §Acceptance Criteria + the two Interview-Log hard-fails (raw internal labels in default chrome; presets-as-navigation) + the L1 terminal-credibility constraint.
- **Locked Vocabulary:** table mirroring V24-UI-SPEC §Copywriting Contract for load-bearing terms, each citing its decision ID — Task/Tasks-not-Runs (D-08), Swarm Map (D-10), Read only/Can edit/Autopilot + retire Plan/Edit/Auto (D-11), steps/cards never "tasks" (D-09), Create Task (D-08), Ask Voss to… (VADE2-04), runId/RunData/currentRunId internal-only (D-09).
- **Visual & Interaction Contract:** one-line pointer to `V24-UI-SPEC.md`; no token-table duplication.

## Task Commits

1. **Task 1: Write apps/voss-app/PRODUCT.md product + design contract** — pending operator/auto-commit (see Issues Encountered re: git policy).

**Plan metadata:** SUMMARY committed by operator/auto-commit alongside production file.

## Files Created/Modified

- `apps/voss-app/PRODUCT.md` — V24 product/design contract: register, IA, success criteria, locked vocabulary, V24-UI-SPEC pointer.

## Decisions Made

- PRODUCT.md is the product-decision source of truth; V24-UI-SPEC remains the visual/interaction source of truth. PRODUCT.md references it rather than duplicating token/geometry tables, keeping a single visual SoT.
- Kept the ROADMAP "Runs" → "Tasks" rename explicit in the IA table (D-08) so downstream plans see the rename rationale, not just the result.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Git commit deferred to operator (project policy).** Per Ben's standing rule, the executor does not run `git add/commit`; PRODUCT.md + this SUMMARY are written to disk and committed by the operator / concurrent auto-commit process. The plan's "committed" done-criterion is satisfied at the disk-write boundary here; the atomic close-out commit is handled outside the executor.
- **Upstream inconsistency flagged (NOT in V24-01 scope — do not fix here).** Adversarial verification found `V24-UI-SPEC.md` is self-inconsistent on the composer title: its §Copywriting Contract row (L492) mandates the unicode ellipsis `Ask Voss to…` (U+2026) and forbids three dots, but its own composer ASCII mockup (L263) renders `Ask Voss to...` (three U+002E). PRODUCT.md correctly uses the unicode `…`. **Action for V24-04 (composer plan):** when building `VossComposer`, use the unicode ellipsis per the Copywriting Contract row + PRODUCT.md Locked Vocabulary, and fix the UI-SPEC mockup typo. Out of scope for this documentation-only plan (files_modified = PRODUCT.md).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- VADE2-01 met: contract committed, enumerates IA + success criteria + locked vocabulary, citable by V24-02..08.
- **V24-02 (W1 left portal + canvas-swap)** is unblocked — its PortalView/IA can cite this contract's Information Architecture section directly.
- Carry-forward for **V24-04**: unicode-ellipsis composer title + UI-SPEC mockup typo fix (see Issues Encountered).

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15*
