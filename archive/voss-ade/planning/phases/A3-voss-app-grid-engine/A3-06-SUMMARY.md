---
phase: A3-voss-app-grid-engine
plan: 06
subsystem: integration
tags: [grid, app-mount, sync-grid, mirror-parity, perf, d-01, warp-parity]

requires:
  - phase: A3-04
    provides: GridRoot.tsx
  - phase: A3-05
    provides: PaneHeader/DotMenu/CloseConfirmBanner + onCloseRequest gate
provides:
  - apps/voss-app/src/App.tsx — <GridRoot/> mounted below the A1 titlebar (A2 single-pane region swapped)
  - apps/voss-app/src-tauri/src/lib.rs — app-level sync_grid/get_grid commands + Mutex<GridState> manage + handler registration
  - crates/voss-app-core/src/grid.rs — Default for GridState, plain overwrite/snapshot helpers, get_grid command
  - apps/voss-app/src/grid/__tests__/mirror-parity.test.ts — Solid↔Rust structural parity + no-disk-IO payload assertion
  - apps/voss-app/e2e/grid-integration.spec.ts — 13 A3-SPEC acceptance criteria (Linux-CI-deferred)
  - apps/voss-app/e2e/grid-perf.spec.ts — 9-pane Canvas perf/flood benchmark (Linux-CI-deferred)
  - **In-flight Warp-parity correction (memory voss-app-grid-warp-parity):**
    - tree.ts +leafCount +balanceRatios (ratio = leaves(left)/leaves(node) ⇒ every leaf equal-area)
    - operations.ts: split/fork/close call balanceRatios; equalizeAll → balance (Warp ⌘=)
    - resize.ts equalizeAllRatios → balance
    - geometry.ts simulateSplitViolates balances the post-swap clone (floor pre-flight reflects post-equalize geometry)
    - keymap.ts ⌘D = split right, ⌘⇧D = split below (Warp parity); ⌘\/⌘⇧\ kept as aliases; forkFocused unbound
affects: []  # closes Phase A3

tech-stack:
  added: []
  patterns:
    - "Cross-crate generate_handler! constraint (same as A2-05 PTY): voss-app-core exposes plain helpers (grid::overwrite/snapshot) + its own #[tauri::command] (for core tests), app's src-tauri/src/lib.rs defines thin #[tauri::command] wrappers delegating to them and registers those in the app's invoke_handler! — webview invoke('sync_grid'|'get_grid') hits the app wrappers."
    - "Warp locked-tiling auto-equalize via balanceRatios (every split node's ratio = leaves(left)/leaves(node)) — opening a pane shrinks the others EVENLY instead of geometrically halving the focused one; floor pre-flight tests this balanced geometry so N panes fit until the real 20×5 floor."
    - "GRD-08 mirror parity validated WITHOUT disk: fake in-memory Rust store in the unit suite (sync_grid overwrites; get_grid clones) + .voss/ snapshot in the e2e contract."

key-files:
  created:
    - apps/voss-app/src/grid/__tests__/mirror-parity.test.ts
    - apps/voss-app/e2e/grid-integration.spec.ts
    - apps/voss-app/e2e/grid-perf.spec.ts
  modified:
    - apps/voss-app/src/App.tsx                  # PaneComponent region → <GridRoot/>
    - apps/voss-app/src-tauri/src/lib.rs         # sync_grid/get_grid wrappers + Mutex<GridState> manage + handler register
    - crates/voss-app-core/src/grid.rs           # Default for GridState, plain overwrite/snapshot, get_grid command
    - apps/voss-app/src/grid/tree.ts             # +leafCount +balanceRatios (Warp parity)
    - apps/voss-app/src/grid/operations.ts       # split/fork/close balance; equalizeAll → balance
    - apps/voss-app/src/grid/resize.ts           # equalizeAllRatios → balance
    - apps/voss-app/src/grid/geometry.ts         # simulate balances clone for floor pre-flight
    - apps/voss-app/src/grid/keymap.ts           # ⌘D/⌘⇧D split; forkFocused unbound
    - apps/voss-app/src/grid/__tests__/{tree,operations,resize,keymap}.test.ts  # updated for balanced semantics + ⌘D split

key-decisions:
  - "WARP-PARITY CORRECTION at the human-verify gate (memory voss-app-grid-warp-parity). User reported live: (a) ⌘D/⌘⇧D wrong — bound to fork / unbound; (b) only 4 panes max because the focused pane geometrically halved on each split, so the 5th hit the 20×5 floor. Both are real misses vs the locked Warp-style intent. Fixed in-plan: keymap rebound + balanceRatios applied on every structural change + floor pre-flight balanced too. Tests updated to assert the balanced ratios. This is a behavior change in A3-02/03/04 logic shipped under A3-06 because it's the system-level realization of the locked memory — without it the human-verify gate would have rejected."
  - "TASK 3 HUMAN SIGN-OFF: 9-pane Canvas perf bar HELD on the dev machine after the Warp fixes (user replied `approved`). D-01 Canvas-per-pane validated; WebGL stays UN-adopted (no fallback triggered)."
  - "INTEGRATION-DEBT documented (NOT regressions, A2-touching → out of A3 scope):
    (i) A2 PaneComponent renders its own internal header; A3 PaneHeader stacks on top (duplicate header visually). Reconcile = hide A2's internal header OR surface dot/proc to A3 PaneHeader (A2-touching). Carry to A3-06-followup / A8.
    (ii) ⌘W cross-pane confirm banner falls back to immediate close because A2's fg signal is not surfaced (closeUI.isFg defaults false). ⋯-menu 'Close pane' path is fully wired+tested with an injectable detector.
    (iii) GridRoot DEFAULT_CW=8/DEFAULT_CH=20 placeholder for the floor math — wire to A2's live xterm cell metrics."

requirements-completed: [GRD-01, GRD-02, GRD-03, GRD-04, GRD-05, GRD-06, GRD-07, GRD-08]

duration: ~50min (Tasks 1+2 autonomous, Task 3 human; mid-gate Warp correction included)
completed: 2026-05-19
---

# Phase A3, Plan 06: App Integration + Mirror Parity + Perf Sign-Off Summary

**The binary-split grid is mounted in the running app, the Rust mirror tracks the Solid tree with zero disk I/O, the 9-pane Canvas-per-pane perf bar is human-signed-off, and a Warp locked-tiling correction (⌘D split + balanceRatios auto-equalize) landed at the gate to realize the locked product intent — Phase A3 closed.**

## Performance
- **Tasks:** 3 (Tasks 1+2 auto, Task 3 blocking human-verify) | **Files created:** 3, modified: 9 | **Wave:** 5

## Accomplishments
- `pnpm vitest run mirror-parity` → 1/1 (scripted split-H/V/fork/focus/keyboard-resize/close all parity-clean; no `.voss`/fs path in any IPC payload).
- Full `src/grid` suite **59/59** (incl. new tree balanceRatios test + operations "N panes tile equal" test); `cargo test -p voss-app-core grid` **2/2**; `cargo build -p voss-app-core` + `-p voss-app` (src-tauri) both clean — `generate_handler!` resolves the cross-crate app wrappers.
- e2e specs (`grid-integration` + `grid-perf`) typecheck and contain every required scenario token; Playwright runs them as `test.skip` (Linux-CI-deferred per memory `voss-app-tauri-e2e-macos-blocked` — macOS WKWebView has no WebDriver).
- **Task 3 human sign-off: `approved`** — 9-pane Canvas-per-pane perf bar holds (idle ~60fps + one-pane `yes`-flood isolation) on the dev machine after the Warp correction; WebGL un-adopted; no `.voss/` created.
- GRD-01..08 closed at the system level.

## Verify Output
```
vitest mirror-parity → 1 passed
src/grid full        → Test Files 8 passed; Tests 59 passed
cargo test grid      → 2 passed
cargo build core+app → 0 errors (cross-crate handler resolves)
tsc --noEmit         → 0
greps                → INTEGRATION_OK + SPECS_PRESENT
human-verify (D-01)  → approved (9-pane Canvas perf bar holds; no .voss/)
```

## Carry-Forward (A3-06-followup / A8 — A2-touching, NOT regressions)
- **Duplicate header reconciliation:** A2 PaneComponent renders its own internal header beneath the A3 Variant B one. Either hide A2's internal header or surface A2's dot/proc/fg to PaneHeader. A2-touching → out of A3 scope.
- **Real A2 fg gate wiring:** thread `closeUI={{ isFg, fgName }}` on `<GridRoot>` to A2's foreground signal (`get_fg_process` / `fg_process` channel) so ⌘W shows the cross-pane banner on real fg processes. ⋯-menu Close path is fully wired+tested with the injectable detector today.
- **Live xterm cell metrics:** GridRoot `DEFAULT_CW=8 / DEFAULT_CH=20` placeholder → read from A2's xterm instance.
- **Linux-CI e2e un-skip:** `grid-integration` + `grid-perf` retain the assertion intent verbatim for the CI job that un-skips on Linux/Windows (A10 / future).

## Phase A3 — Complete (6/6)
All 8 GRD requirements satisfied. The voss-app desktop ADE has a Warp-style locked-tiling pane grid mounted, the Solid source-of-truth round-trips through the voss-app-core Rust mirror with zero disk I/O, and the Canvas-per-pane renderer holds the 9-pane perf bar. Next: A4 (Layout Presets) — already planned and context-gathered.
