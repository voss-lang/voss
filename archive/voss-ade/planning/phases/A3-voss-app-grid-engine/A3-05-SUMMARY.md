---
phase: A3-voss-app-grid-engine
plan: 05
subsystem: ui
tags: [grid, pane-header, dot-menu, close-confirm, variant-b, foreground-gate]

requires:
  - phase: A3-02
    provides: operations.ts (forkFocused/splitFocused/closeFocused)
  - phase: A3-04
    provides: SplitNode.tsx leaf seam comment, GridRoot onCloseRequest injection point, keymap ⌘W
provides:
  - apps/voss-app/src/grid/PaneHeader.tsx — 22px Variant B header (● index cwd shell process ⋯), focus bg-lift (GRD-06/07)
  - apps/voss-app/src/grid/DotMenu.tsx — 128px 5-item ⋯ popup → forkFocused/splitFocused/gated close (GRD-06)
  - apps/voss-app/src/grid/CloseConfirmBanner.tsx — 22px char-exact confirm banner + requestCloseGated single close entry (GRD-02)
  - SplitNode.tsx leaf seam filled; GridRoot onCloseRequest swapped to the gated path
affects: [A3-06]

tech-stack:
  added: []
  patterns:
    - "requestCloseGated(store,_paneId,isForegroundRunning,showBanner) is the SINGLE close entry (T-A3-13): ⌘W (GridRoot onCloseRequest default) and ⋯ 'Close pane' both route through it. Idle ⇒ closeFocused now; fg ⇒ showBanner. isForegroundRunning is INJECTED (CloseUI.isFg) — A3 never reimplements A2 D-07 detection."
    - "Chrome state is per-leaf-local in SplitNodeView (menuOpen, banner signals); the close commit runs inside setStore(produce(...)) so pure closeFocused stays reactive (same Solid render-seam rule as A3-04 / [[voss-app-solid-produce-no-structuredclone]])."
    - "Established Solid component-test pattern reused: render() from solid-js/web + fireEvent from @testing-library/dom, jsdom. NO @solidjs/testing-library (plan mentioned it; A3-04 precedent — zero new deps, honors T-A3-SC)."

key-files:
  created:
    - apps/voss-app/src/grid/PaneHeader.tsx
    - apps/voss-app/src/grid/DotMenu.tsx
    - apps/voss-app/src/grid/CloseConfirmBanner.tsx
    - apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx
  modified:
    - apps/voss-app/src/grid/SplitNode.tsx  # leaf seam: PaneHeader + DotMenu + CloseConfirmBanner + CloseUI prop
    - apps/voss-app/src/grid/GridRoot.tsx   # onCloseRequest default → requestCloseGated; +closeUI prop/threading; dropped now-orphan closeFocused import

key-decisions:
  - "DEVIATION (A2 reality vs plan, same class as A3-04): plan Task 1 says PaneHeader consumes A2's surfaced dot/cwd/shell/process props. A2 `PaneComponent` surfaces NONE — it renders its OWN internal header and keeps dot/proc/fg as private signals (verified). Resolved: PaneHeader is the canonical Variant B GRD-06 header rendered in the leaf seam ABOVE PaneComponent; cwd/shell/index come from the leaf (real), dotState/process are props defaulting (● 'running', process hidden) until A2 surfaces them. CONSEQUENCE: in the live app a leaf shows the A3 header AND A2's own internal header (duplicate) — reconciling needs an A2-touching change OUT OF A3-05 scope → A3-06/A8 carry-forward. No A2 file modified (A2-CONTEXT additive-only honored)."
  - "DEVIATION: requestCloseGated `isForegroundRunning` narrowed to sync `() => boolean` (plan signature said `Promise<boolean> | boolean`). An awaited detector would leave the Solid produce draft stale at commit; the realistic A2 source is a cached fg signal (sync). Minor narrowing, same class as A3-03 CopyMode."
  - "SCOPE: ⌘W cross-pane banner is deferred. The ⋯-menu 'Close pane' path is fully wired to the per-leaf banner + tested. ⌘W (GridRoot.onCloseRequest default) routes through requestCloseGated with isFg defaulting false ⇒ closes immediately (UNCHANGED from A3-04, zero regression); the cross-pane ⌘W→banner plumbing needs the real A2 fg signal → A3-06/A8."
  - "PLAN-DEFECT (carried from A3-04, NOT a code violation): Task1 verify `! grep -nE '...|ring' PaneHeader.tsx` false-positives on the substring in `string` (every typed .tsx). True GRD-07 intent verified with a corrected gate: no outline/rounded/transition, no ring- utility, PaneHeader carries NO boundary stroke (the inset focus shadow lives on the SplitNode wrapper, not the header). Recommend the plan author tighten to `\\bring-|outline:`."

requirements-completed: [GRD-02, GRD-06, GRD-07]

duration: ~35min
completed: 2026-05-19
---

# Phase A3, Plan 05: Per-Pane Variant B Chrome Summary

**The 22px Variant B header (A2 segments + added index + ⋯), the locked 5-item ⋯ menu, and the foreground-gated close-confirm banner are built and mounted in the A3-04 leaf seam; ⌘W + Close pane both flow through the single requestCloseGated entry — unit-proven green, zero regression, no A2 file touched.**

## Performance
- **Tasks:** 3 (Task1/2 auto-TDD, Task3 auto) | **Files created:** 4, modified: 2 | **Wave:** 4

## Accomplishments
- `pnpm vitest run PaneChrome` → **7/7**: header segment order + index + aria-labels + focus bg-lift + empty-process-hidden; DotMenu exactly 5 items (4 + sep, no 6th) wired to fork/split/gated-close; banner char-exact copy + Close anyway/Enter→closeFocused + Keep/Esc→keep; requestCloseGated idle-vs-fg; 2-pane seam per-pane index + ⋯Fork→forkFocused; ⋯Close idle→close / fg→banner.
- Full `src/grid` suite **56/56** (49 prior + 7) — A3-01..04 zero regression after the SplitNode/GridRoot edits.
- `pnpm exec tsc --noEmit` → 0. HEADER_OK + MENU_OK + SEAM_OK (corrected GRD-07 gate). No `src/pane/` file modified.
- GRD-06 (header + ⋯ menu) + GRD-02 close-confirm half + GRD-07 header bg-lift satisfied.

## Verify Output
```
vitest PaneChrome → 7 passed
src/grid full     → Test Files 7 passed; Tests 56 passed
tsc --noEmit      → 0
greps             → HEADER_OK + MENU_OK + SEAM_OK (true-intent GRD-07 gate)
```

## Carry-Forward (A3-06 must honor)
- **Duplicate-header reconciliation (A2-touching, NOT A3-05 scope):** A2 `PaneComponent` renders its own internal header; the A3 PaneHeader is the canonical Variant B one. A3-06/A8 must either hide A2's internal header or surface A2's dot/proc/fg so PaneHeader shows live values — this is the A2-touching integration step.
- **Real fg gate:** wire `closeUI={{ isFg, fgName }}` on `<GridRoot>` to A2's foreground signal (A2 D-07: `get_fg_process` / `fg_process` channel) and finish the ⌘W cross-pane banner. Currently injected idle ⇒ ⌘W/Close close immediately.
- **A3-06 chain (A3-01→04→here):** mount `<GridRoot/>` in App.tsx (A1-owned, NOT edited here) + wire `sync_grid` app-level (thin `#[tauri::command]` + `.manage(Mutex<GridState>)`, same cross-crate `generate_handler!` pattern as A2-05 PTY) + real xterm cell metrics (GridRoot DEFAULT_CW/CH TODO) + 9-pane Canvas perf blocking human-verify.

## Deferred (next A3 wave)
- A3-06 app integration + sync_grid app-level + cell metrics + 9-pane perf human-verify + duplicate-header + real fg-gate reconciliation.
