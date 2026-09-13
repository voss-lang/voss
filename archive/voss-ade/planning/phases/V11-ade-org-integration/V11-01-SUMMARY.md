---
phase: V11-ade-org-integration
plan: 01
subsystem: ui
tags: [typescript, solidjs, tauri, contract-types, replay-reducer, fixtures, vitest]

# Dependency graph
requires:
  - phase: V4-V9
    provides: verified SessionTreeNode / AuditReport / ReviewSidecar / RunFinal CLI-JSON schemas
provides:
  - Hand-authored TS contract types for every CLI-JSON shape V11 consumes (types.ts, V13.1-REPLACE marked)
  - Runtime validation guard (isRunData/assertRunData) rejecting malformed RunData at the Tauri boundary
  - Pure client-side replay reducer (computeBoardAtStep) reconstructing board/card state at step N
  - 5 golden JSON fixtures (node-root, node-child, review-sidecar, run-final, audit-report) as the V11 test corpus
affects: [orgStore, OrgViewShell, BoardPanel, ReplayPanel, AuditPanel, lib.rs load_run, V13.1]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hand-authored stopgap contract types with V13.1-REPLACE marker (codegen replacement later)"
    - "Structural runtime guard at Tauri boundary: drift surfaces as explicit Error, not silent render miss"
    - "Pure reducer with plain spreads only — no produce()/structuredClone() (DATA_CLONE_ERR on Solid proxies)"
    - "Fixture-driven panel tests authored from RESEARCH contracts (no real .voss/sessions in dev env)"

key-files:
  created:
    - apps/voss-app/src/org/types.ts
    - apps/voss-app/src/org/guards.ts
    - apps/voss-app/src/org/replayReducer.ts
    - apps/voss-app/src/org/__tests__/guards.test.ts
    - apps/voss-app/src/org/__tests__/replayReducer.test.ts
    - apps/voss-app/src/org/__tests__/fixtures/{node-root,node-child,review-sidecar,run-final,audit-report}.json
  modified: []

key-decisions:
  - "CardSnapshot.budget typed as {limit,spent} (from node.envelope) rather than a bare number"
  - "Reducer slice semantics: step N applies transitions 0..N inclusive (matches PATTERNS code), so step 0 lands the card in the column implied by the 0th transition"
  - "terminal_state override applied only once step >= node's last board.transition index"
  - "Transition union includes RunFinal (em.run_final) per SessionTreeNode contract"

patterns-established:
  - "V13.1-REPLACE marker convention for hand-authored contract stopgaps"
  - "assertRunData throws Error naming the failing field (run_id / session_tree.nodes)"
  - "computeBoardAtStep returns plain object literals; immutability asserted via JSON round-trip in tests"

requirements-completed: [VADE-02, VADE-10]

# Metrics
duration: 12min
completed: 2026-06-07
---

# Phase V11 Plan 01: Contract Foundation Summary

**Hand-authored TS contract types + runtime drift guard + pure replay reducer, driven by 5 golden JSON fixtures captured from the verified V4–V9 schemas.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-06-07
- **Tasks:** 3 (all auto)
- **Files created:** 10 (3 source, 2 tests, 5 fixtures)

## Accomplishments
- `types.ts` — full RunData contract surface (SessionTreeNode, Transition union, VerdictSnapshot, RunFinal, ReviewSidecar, AuditReport/Snapshot/Card, RunEntry, DecisionResult, BoardFrame, CardSnapshot) with the `V13.1-REPLACE` marker.
- `guards.ts` — `isRunData` / `assertRunData` structural boundary; malformed payloads throw an Error naming the failing field (D-02).
- `replayReducer.ts` — `computeBoardAtStep(nodes, step)` folds board.transition entries into the 6 canonical columns + terminal_state override; plain spreads only, zero `produce`/`structuredClone`.
- 5 schema-faithful golden fixtures = the authoritative test corpus for all downstream panel tests.

## Files Created/Modified
- `src/org/types.ts` — RunData + all sub-type interfaces (D-02), V13.1-REPLACE marked
- `src/org/guards.ts` — runtime validation of load_run output (isRunData/assertRunData)
- `src/org/replayReducer.ts` — computeBoardAtStep pure reducer (D-05/D-06)
- `src/org/__tests__/guards.test.ts` — 3 behavior tests incl. drift→error
- `src/org/__tests__/replayReducer.test.ts` — 6 behavior tests incl. immutability + Blocked override
- `src/org/__tests__/fixtures/*.json` — node-root, node-child, review-sidecar, run-final, audit-report

## Decisions Made
- See `key-decisions` frontmatter. All within plan scope; reducer slice semantics follow the PATTERNS reference code (the plan's behavior bullet explicitly allows the "column implied by the 0th transition" reading).

## Deviations from Plan
None - plan executed exactly as written. No new dependencies (threat T-V11-SC: nothing to install).

## Issues Encountered
None. JSON-import union widening handled with `as unknown as SessionTreeNode[]` casts at test call sites (expected with resolveJsonModule + discriminated unions).

## Verification
- `npx vitest run src/org/__tests__/` → 2 files, **9 tests passed**
- `npx tsc --noEmit` → **exit 0**
- `grep V13.1-REPLACE src/org/types.ts` → present
- reducer non-comment lines contain no `produce(` / `structuredClone(`

## Next Phase Readiness
- Contract types + fixtures ready for Rust `load_run`/`enumerate_runs`/`run_decision` (lib.rs), `orgStore`, and all org panels to import.
- `computeBoardAtStep` ready to power ReplayPanel (VADE-10).

---
*Phase: V11-ade-org-integration*
*Completed: 2026-06-07*
