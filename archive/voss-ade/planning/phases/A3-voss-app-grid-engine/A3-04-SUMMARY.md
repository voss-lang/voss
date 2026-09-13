---
phase: A3-voss-app-grid-engine
plan: 04
subsystem: ui
tags: [grid, render, keymap, drag, focus-paint, solid, variant-b]

requires:
  - phase: A3-01
    provides: tree.ts (createGridStore Solid store, types), sync.ts (markDragSettled)
  - phase: A3-02
    provides: operations.ts (splitFocused/forkFocused/closeFocused/equalizeAll), geometry.ts (simulateSplitViolates)
  - phase: A3-03
    provides: focus.ts (focusByClick/Index/Direction, cycleFocus), resize.ts (resizeByDrag/Keyboard)
provides:
  - apps/voss-app/src/grid/keymap.ts — dispatchKey chord table (GRD-02/03/04), ⌘W via injected onCloseRequest
  - apps/voss-app/src/grid/SplitNode.tsx — recursive H/V renderer, inset-shadow focus paint (GRD-01, GRD-07)
  - apps/voss-app/src/grid/DragHandle.tsx — 6px transparent pointer-capture overlay → resizeByDrag + drag-end markDragSettled
  - apps/voss-app/src/grid/GridRoot.tsx — container + window keymap mount + minGridSize GRD-05 shrink clamp + closeFocused default
affects: [A3-05, A3-06]

tech-stack:
  added: []
  patterns:
    - "Solid reactivity seam: operations/focus/resize are pure GridStore mutators; the render layer runs them inside `setStore(produce(s => fn(s)))`. GridRoot owns setStore; SplitNode click + DragHandle move call it. markDragSettled reads the store proxy (serialize only — no produce needed)."
    - "Splits have no id (A3-01 wire shape) — addressed by the A3-03 path string ('', +L/+R per descent). GridRoot passes path='' to SplitNode; recursion appends; DragHandle forwards it to resizeByDrag. splitPath/findSplitByPath stay internal to resize.ts."
    - "GRD-05 window-shrink: minGridSize(root,cw,ch) (pure, exported) = smallest window keeping every leaf ≥20×5 at current ratios; GridRoot tiles the inner div at max(window,minGridSize) inside overflow-hidden — panes keep the floor, --bg-0 is never sub-floored (no DOM-layout dependency, unit-tested)."
    - "A2 PaneComponent is a locked black box: PaneProps = {cwd,shell,index} only (no focused/size prop). The focus visual + pixel sizing live on the SplitNode wrapper; A2's own ResizeObserver picks up the wrapper resize and fits xterm. No A2 edit (A2-CONTEXT additive-only honored)."

key-files:
  created:
    - apps/voss-app/src/grid/keymap.ts
    - apps/voss-app/src/grid/SplitNode.tsx
    - apps/voss-app/src/grid/DragHandle.tsx
    - apps/voss-app/src/grid/GridRoot.tsx
    - apps/voss-app/src/grid/__tests__/keymap.test.ts
    - apps/voss-app/src/grid/__tests__/GridRoot.test.tsx
  modified:
    - apps/voss-app/src/grid/geometry.ts  # structuredClone → pure cloneTree (proxy-safe; see deviation)

key-decisions:
  - "DEVIATION (A2 reality vs plan): plan Task 2 says 'pass a focused prop + pixel size to PaneComponent'. A2's PaneProps exposes none (cwd/shell/index only) and A2 is a locked black box (render-as-is, no A2 edit). Resolved: focus paint + sizing on the wrapper container; A2's ResizeObserver drives xterm fit. GRD-07 fully satisfied at the wrapper. Not a defect — plan also said 'render PaneComponent as-is, DO NOT modify A2 internals'."
  - "DEFECT FIX (cross-plan, surgical): geometry.ts simulateSplitViolates used structuredClone(root). At the render layer `root` is a Solid produce-draft Proxy → structuredClone throws DATA_CLONE_ERR (surfaced by the ⌘\\ GridRoot test). Replaced with a pure recursive cloneTree (tiny discriminated union). No API change; all 12 A3-02 operations/geometry tests still green within the 49. A3-02's pure unit path never hit this because it never wraps in produce."
  - "PLAN-DEFECT (verify gate over-broad, NOT a code violation): Task 2 verify `! grep -nE 'outline|border-.*focus|ring' src/grid/SplitNode.tsx` — the bare `ring` alternative matches the substring inside `string` (every typed .tsx has `: string`). The true GRD-07 contract (no outline, no Tailwind ring- utility, no focus-driven border color, only the inset focus shadow) was verified with a corrected gate. Recommend the plan author tighten to `\\bring-|outline:`."

requirements-completed: [GRD-01, GRD-03, GRD-04, GRD-07]

duration: ~30min
completed: 2026-05-19
---

# Phase A3, Plan 04: Recursive Renderer + Keymap + Focus Paint Summary

**The binary-split tree is now an interactive multi-pane grid: recursive H/V render wrapping the A2 pane, the full ⌘ keymap dispatching to A3-02/03 ops, draggable borders with single drag-end mirror sync, and the locked Variant B inset-shadow focus — unit-proven green, zero regression.**

## Performance
- **Tasks:** 3 (keymap auto-TDD, renderer+drag auto-TDD, GridRoot auto) | **Files created:** 6, modified: 1 | **Wave:** 3

## Accomplishments
- `pnpm vitest run keymap` → **5/5** (all chords + ⌘W→onCloseRequest + ⌘0/unmatched/non-⌘ pass-through no preventDefault).
- `pnpm vitest run GridRoot` → **6/6** (2×2 = 4 panes, exactly-one inset-shadow focus, click-to-focus moves shadow + syncs, 6-pane no-error + no rounded/transition, .grid-root.bg-bg-0 default 1 pane, ⌘\\ keydown→dispatch→2 panes, minGridSize narrow-window floor).
- Full `src/grid` suite **49/49** (tree 11 + operations 12 + focus 7 + resize 8 + keymap 5 + GridRoot 6) — A3-01/02/03 no regression after the geometry.ts cloneTree fix.
- `pnpm exec tsc --noEmit` → 0. True GRD-07 gate (no outline / ring- util / focus border-color / non-inset shadow) + all positive greps + KEYMAP_OK pass.
- GRD-01 (recursive render) + GRD-03/04 (keymap+click+drag wired) + GRD-07 (inset-shadow, no boundary stroke, instant repaint) satisfied.

## Verify Output
```
vitest keymap   → 5 passed
vitest GridRoot → 6 passed
src/grid full   → Test Files 6 passed; Tests 49 passed
tsc --noEmit    → 0
greps           → KEYMAP_OK + TRUE_CONTRACT_OK (corrected GRD-07 gate)
```

## Carry-Forward (A3-05 / A3-06 must honor)
- **A3-05 mount seam:** the `{/* A3-05 mount: PaneHeader index + ⋯ menu + CloseConfirmBanner overlay here */}` comment in SplitNode's leaf wrapper is the chrome insertion point. A3-05 also swaps `GridRoot` `onCloseRequest` to the A2-D-07 foreground-gated close (currently defaults to `closeFocused`, so ⌘W works now).
- **A3-06 integration (carry-forward chain A3-01 → here):** App.tsx must render `<GridRoot />` below the A1 titlebar (A1 owns App.tsx — NOT edited here) AND wire `sync_grid` app-level (thin `#[tauri::command]` wrapper + `.manage(Mutex<GridState>)` in src-tauri/src/lib.rs — same cross-crate `generate_handler!` constraint A2-05 hit for PTY). Until then `invoke('sync_grid')` rejects at runtime (mocked green in tests).
- **Cell metrics TODO:** GridRoot `DEFAULT_CW=8 / DEFAULT_CH=20` placeholder for the floor math — A3-06 must read live xterm cell px from the A2 pane (A2 owns it; PaneComponent does not expose it yet).
- **Equalize double-bind resolved:** keymap binds ⌘= to `operations.equalizeAll` only (`resize.equalizeAllRatios` deliberately NOT imported) — no double-bind.

## Deferred (next A3 waves)
- A3-05 22px Variant B header + ⋯ DotMenu + CloseConfirmBanner (foreground-gated close).
- A3-06 App.tsx mount + sync_grid app-level wiring + real cell metrics + 9-pane Canvas perf blocking human-verify.
