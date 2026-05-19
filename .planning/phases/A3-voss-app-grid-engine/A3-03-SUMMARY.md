---
phase: A3-voss-app-grid-engine
plan: 03
subsystem: ui
tags: [grid, focus, resize, i3, edge-midpoint, floor-clamp, keybinds]

requires:
  - phase: A3-01
    provides: tree.ts (types, collectLeaves inorder, findLeaf, recomputeIndices, equalizeRatios), sync.ts (markStructuralChange, markDragSettled)
provides:
  - apps/voss-app/src/grid/focus.ts — focusByIndex / focusByClick / cycleFocus / focusByDirection (i3 edge-midpoint, GRD-03)
  - apps/voss-app/src/grid/resize.ts — resizeByDrag / resizeByKeyboard / equalizeAllRatios + splitPath (GRD-04, GRD-05 resize half)
affects: [A3-04, A3-05, A3-06]

tech-stack:
  added: []
  patterns:
    - "focusByDirection = i3/sway edge-midpoint (D-03): local pure rectsOf walker; candidate must be strictly on the dir side AND share an overlapping perpendicular span (true adjacency, not a shared corner); winner = min axis-gap then min perpendicular distance of the clamped projected midpoint. Deterministic from layout alone, no focus history."
    - "Splits carry NO id (A3-01 wire shape round-trips with the Rust mirror — adding one breaks GRD-08). Splits are addressed by a deterministic PATH string from root: \"\"=root, \"L\"/\"R\" appended per descent. Exported splitPath(root,leafId,axis) so the A3-04 DragHandle computes the identical path."
    - "20×5 resize clamp is a snap-toward-0.5 search (0.005 steps, bounded) on a local rectsOf+violatesFloor — never overshoots, cursor stays, no toast (A3-UI-SPEC silent reject)."
    - "Cadence: resizeByKeyboard fires markStructuralChange per 5% step (and NOT when clamped — no-op); resizeByDrag never syncs (A3-04 drag-end fires markDragSettled once)."

key-files:
  created:
    - apps/voss-app/src/grid/focus.ts
    - apps/voss-app/src/grid/resize.ts
    - apps/voss-app/src/grid/__tests__/focus.test.ts
    - apps/voss-app/src/grid/__tests__/resize.test.ts
  modified: []

key-decisions:
  - "Split addressing = path string (not a new SplitNode.id field). A3-01's TreeNode is the GRD-08 wire contract round-tripped by crates/voss-app-core/src/grid.rs; adding an id would break the round-trip. splitPath is exported as the shared scheme for A3-04's DragHandle."
  - "focus.ts/resize.ts each carry a private rectsOf (pure ratio split, no 1px border) — they deliberately do NOT import A3-02's geometry.ts (same-wave file-ownership isolation, enforced by the verify `! grep` gate)."
  - "resizeByKeyboard sign convention: right/down = +5%, left/up = −5% on the nearest bounding split of the matching axis (H for left/right, V for up/down); no-op if none. Matches the plan action verbatim; SPEC acceptance only constrains 5% step + floor-stop + equalize."

requirements-completed: [GRD-03, GRD-04, GRD-05]

duration: ~15min
completed: 2026-05-19
---

# Phase A3, Plan 03: Focus + Resize Summary

**Implemented numeric/click/cycle/i3-directional focus and drag/keyboard/equalize resize as pure tree logic over the A3-01 model, every resize path clamped at the 20×5 floor — unit-proven green, zero regression.**

## Performance
- **Tasks:** 2 (both auto, TDD) | **Files created:** 4 | **Wave:** 2 (parallel-safe with A3-02 — no shared files)

## Accomplishments
- `pnpm vitest run focus resize` → **15/15 green** (focus 7: index select, index>count no-op, click + unknown-id no-op, cycle wrap both ends, 2×2 corner right/down + bottom-right left/up, no-candidate no-op; resize 8: floor-snap clamp, siblings byte-identical, drag-no-sync + markDragSettled-once, keyboard 5% + per-step sync, repeated-stop-no-overshoot, single-pane/wrong-axis no-op, splitPath nearest-axis, equalizeAllRatios).
- Full `src/grid` suite **38/38** (tree 11 + operations 12 + focus 7 + resize 8) — A3-01/02 no regression.
- `pnpm exec tsc --noEmit` → 0. Verify gate `FOCUS_RESIZE_OK` (greps + no-`geometry`-import + cadence) passed.
- GRD-03 + GRD-04 + GRD-05 (resize half) satisfied.

## Verify Output
```
vitest run focus resize → Test Files 2 passed; Tests 15 passed
src/grid regression      → Test Files 4 passed; Tests 38 passed
tsc --noEmit             → tsc=0
greps + ownership        → FOCUS_RESIZE_OK
```

## Carry-Forward (A3-04 must honor)
- **Split addressing = path string.** A3-04 DragHandle MUST call `splitPath` / pass the same "L"/"R" path to `resizeByDrag` — splits have no id by design.
- **Drag-end sync is the caller's job.** `resizeByDrag` never syncs; A3-04 pointer-up handler calls `markDragSettled(store)` exactly once.
- **Equalize double-bind hazard.** Both `operations.equalizeAll` (A3-02) and `resize.equalizeAllRatios` exist. A3-04 binds ⌘= to **exactly one** (prefer `operations.equalizeAll`).
- `focusByDirection` takes `(store, dir, winW, winH)` — A3-04/06 supplies live window dims (per plan action signature; A3-PATTERNS' 2-arg sketch is superseded).

## Deferred (next A3 waves)
- A3-04 resize.ts/focus.ts render wiring: GridRoot/SplitNode/DragHandle, global keymap (⌘1-9, ⌘[/], ⌘⌥arrow, ⌘⌥⇧arrow, ⌘=) + **backlog 999.2 ⌘+/- folds here**.
- A3-05 22px header + ⋯ menu + CloseConfirmBanner (gates closeFocused on A2 D-07).
- A3-06 App.tsx grid mount + **wire sync_grid app-level** (carry-forward from A3-01) + 9-pane perf human-verify.
