---
phase: A3-voss-app-grid-engine
plan: 02
subsystem: ui
tags: [grid, operations, split, fork, close, floor-guard, geometry]

requires:
  - phase: A3-01
    provides: tree.ts (types, makePane/makeSplit, recomputeIndices, equalizeRatios, findLeaf, collectLeaves), sync.ts (markStructuralChange)
provides:
  - apps/voss-app/src/grid/geometry.ts — computePaneRects, paneColsRows, wouldViolateFloor, simulateSplitViolates (20×5 hard floor, GRD-05; pure)
  - apps/voss-app/src/grid/operations.ts — splitFocused/forkFocused/closeFocused/equalizeAll (GRD-02) with floor pre-flight + D-04 close (sibling expands+focus, last-pane respawn)
affects: [A3-03, A3-04, A3-05, A3-06]

tech-stack:
  added: []
  patterns:
    - "Floor guard is a clone-and-simulate pre-flight (simulateSplitViolates) run BEFORE mutation; violation = silent no-op (no change, no sync) per GRD-05 / A3-UI-SPEC 'Error state: silent no-op'."
    - "Operations are pure GridStore mutators (return void, reassign store.root/focusedId, fire markStructuralChange on success only); render layer wraps in setStore(produce(...))."
    - "closeLeaf returns {root,focus}: sibling subtree promoted to the removed leaf's slot, focus = first inorder leaf of the expanded sibling (D-04); root===null ⇒ last pane ⇒ fresh makePane respawn."

key-files:
  created:
    - apps/voss-app/src/grid/geometry.ts
    - apps/voss-app/src/grid/operations.ts
    - apps/voss-app/src/grid/__tests__/operations.test.ts
  modified: []

key-decisions:
  - "operations signatures take optional `geom?: GridGeom` — when supplied, split/fork run the GRD-05 floor pre-flight; pure structural unit fixtures omit it. Reconciles the plan's `(store, orientation)` signature with simulateSplitViolates needing window+cell dims (the render layer always supplies geom; the render-layer integration is A3-04/06)."
  - "Mutators operate on a plain GridStore object (testable, matches `(store: GridStore)` signature). Solid produce/reconcile wrapping is the render-layer concern — operations stay pure."

requirements-completed: [GRD-02, GRD-05]

duration: ~20min
completed: 2026-05-19
---

# Phase A3, Plan 02: Tree Mutations + 20×5 Floor Guard Summary

**Implemented the four structural verbs (split-H/V, fork, close, equalize) with the GRD-05 20×5 hard-floor pre-flight (silent no-op) and the D-04 close behavior (sibling subtree expands + focus moves; last pane respawns) — all pure, unit-proven green.**

## Performance
- **Tasks:** 2 (both auto, TDD) | **Files created:** 3 | **Wave:** 2

## Accomplishments
- `pnpm vitest run operations` → **12/12 green** (4 geometry: full-tile rects, exact-20×5 not-violating, below-floor true, simulate 30-col split violates/wide ok; 8 operations: H/V 50/50 siblings, fork cwd+shell+fresh-id, under-floor silent no-op deep-equal+no-sync, close sibling-expand+focus, last-pane respawn, deep-target spine rebuild, equalize-all-depths).
- `pnpm exec tsc --noEmit` → 0. geometry.ts purity verified (no invoke/document/JSX).
- GRD-02 (split/fork/close) + GRD-05 (floor) satisfied; D-04 close behavior locked.

## Verify Output
```
vitest run operations → Test Files 1 passed; Tests 12 passed
tsc --noEmit          → tsc=0
greps + purity        → ALL_A3_02_OK
```

## Deferred (next A3 waves)
- A3-03 focus.ts (numeric/directional/i3 edge-midpoint/cycle).
- A3-04 resize.ts + drag handles (consumes markDragMove/Settled) — **backlog 999.2 ⌘+/- focused-pane resize folds here**.
- A3-05 22px header + ⋯ menu + CloseConfirmBanner (gates closeFocused on A2 D-07 foreground).
- A3-06 App.tsx grid mount + **wire sync_grid app-level** (carry-forward from A3-01) + 9-pane perf blocking human-verify.
