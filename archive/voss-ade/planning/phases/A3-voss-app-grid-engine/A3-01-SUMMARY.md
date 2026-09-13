---
phase: A3-voss-app-grid-engine
plan: 01
subsystem: ui
tags: [grid, binary-split-tree, solid-store, rust-mirror, tauri-sync, contracts]

requires:
  - phase: A2
    provides: PaneComponent (consumed as black box by later A3 render plans), voss-app-core crate (PTY) + app-level command wiring pattern
  - phase: A1
    provides: voss-app-core workspace member + src-tauri path-dep; Solid=SSOT / Rust-owns-state seam (D-09)
provides:
  - apps/voss-app/src/grid/tree.ts — binary-split tree model (SplitNode/PaneLeaf/TreeNode/GridStore), createGridStore (Solid store), recomputeIndices (geometric inorder, no gaps), equalizeRatios, makeSplit (ratio 0.5), makePane, findLeaf, collectLeaves
  - apps/voss-app/src/grid/sync.ts — syncGridToRust + markStructuralChange (immediate) + markDragMove/markDragSettled (drag coalescer, 1 sync on pointer-up)
  - crates/voss-app-core/src/grid.rs — Rust mirror (TreeNode/SplitNode/Orientation/PaneLeaf/GridState) + #[tauri::command] sync_grid (in-memory Mutex, zero disk I/O), serde camelCase round-trip with tree.ts
  - the A3 contracts every downstream plan (operations/focus/resize/render/chrome) builds against
affects: [A3-02, A3-03, A3-04, A3-05, A3-06, A4, A6]

tech-stack:
  added: []
  patterns:
    - "serde wire alignment: rename_all=camelCase on TreeNode/SplitNode/PaneLeaf/GridState so JSON keys == tree.ts field names (focusedId, kind, etc); Orientation deliberately NOT renamed so variants serialize literal \"H\"/\"V\" matching the TS union."
    - "Geometric index = inorder traversal (left/top then right/bottom), 1-based, recomputed every structural change — never sparse IDs."
    - "Mirror sync cadence: structural changes sync immediately; drag-resize coalesces via pendingDrag (markDragMove records, markDragSettled flushes one sync)."

key-files:
  created:
    - apps/voss-app/src/grid/tree.ts
    - apps/voss-app/src/grid/sync.ts
    - apps/voss-app/src/grid/__tests__/tree.test.ts
    - crates/voss-app-core/src/grid.rs
  modified:
    - crates/voss-app-core/src/lib.rs (added pub mod grid + pub use grid::{GridState, sync_grid})

key-decisions:
  - "rename_all=camelCase chosen over PATTERNS' snake_case example, per A3-01 plan's explicit instruction — required for clean JSON round-trip with tree.ts (focusedId etc). Documented in grid.rs top comment. Orientation left unrenamed (H/V literals)."
  - "tree.ts model is pure (no invoke/DOM/JSX) — recomputeIndices/equalizeRatios mutate plain TreeNode objects; Solid store reactivity for live mutation is a later-plan concern. createGridStore returns the createStore tuple [Store, SetStore]."
  - "sync.ts adds markDragMove (records pendingDrag, no invoke) + markDragSettled (flushes one sync) to realize the A3-CONTEXT drag-coalesce cadence as a testable unit; tests assert N drag-moves + 1 settle = exactly 1 invoke."
  - "**Carry-forward (NOT a defect — A3-01 is contracts-only):** sync_grid is a voss-app-core #[tauri::command]. Same cross-crate generate_handler! constraint as A2's PTY commands — it is NOT yet registered in apps/voss-app/src-tauri/src/lib.rs and Mutex<GridState> is not yet .manage()'d. invoke('sync_grid') will not route until a later A3 plan (the integration/render wave) adds an app-level wrapper + managed state, mirroring the A2-05 PTY fix. Flagged so the A3 integration plan lists src-tauri/src/lib.rs."

patterns-established:
  - "voss-app-core command + app registration is a two-step contract: define+test in the crate (this plan), then app-level wrapper + .manage() in apps/voss-app/src-tauri/src/lib.rs (integration plan). A3 integration wave MUST wire sync_grid like A2-05 wired the PTY commands."

requirements-completed: [GRD-01, GRD-08]

duration: ~25min
completed: 2026-05-19
---

# Phase A3, Plan 01: Grid Tree Model + Rust Mirror + Sync Seam Summary

**Established the A3 binary-split pane-tree contracts — a pure typed Solid tree model with deterministic geometric indexing (tree.ts), an in-memory zero-disk Rust mirror with a serde-camelCase round-tripping `sync_grid` command (grid.rs), and a structural-immediate / drag-coalesced Solid→Rust bridge (sync.ts) — all unit-proven green for every downstream A3 plan to build against.**

## Performance

- **Tasks:** 3 (all auto, TDD; autonomous plan, no human gate)
- **Files created:** 4 | modified: 1
- **Wave:** 1 (foundation)

## Accomplishments

- `pnpm vitest run tree` → **11/11 green** (8 tree-model: index recompute, 2×2 [1,2,3,4], mid-tree removal contiguous renumber, ≥6-pane asymmetric, equalize-all-depths, makeSplit ratio 0.5, findLeaf/collectLeaves inorder; 3 sync-bridge: structural=1 invoke, N drag-move+settle=1 invoke, payload `{newState:{root,focusedId}}`).
- `cargo test -p voss-app-core grid` → **2/2 green** (2×2 serde round-trip; JSON keys match TS — `focusedId`, `kind:pane/split`, `orientation:"H"`).
- `cargo build -p voss-app-core` 0 warnings; `pnpm exec tsc --noEmit` 0 errors.
- GRD-08 disk-I/O gate: grid.rs has zero `std::fs`/`File::`/`fs::write`/`.voss`.

## Verify Output

```
cargo test -p voss-app-core grid → test result: ok. 2 passed (4 pty filtered)
cargo build -p voss-app-core     → Finished (0 warnings)
grid.rs no-disk gate             → NO_DISK_OK
sync_grid + mod grid wired       → MIRROR_WIRED_OK
pnpm vitest run tree             → Test Files 1 passed; Tests 11 passed
pnpm exec tsc --noEmit           → tsc=0
TS contract greps                → TS_GREPS_OK
```

## Carry-Forward (for the A3 integration wave — NOT an A3-01 defect)

`sync_grid` is defined + tested in voss-app-core but NOT yet registered in the Tauri app (`apps/voss-app/src-tauri/src/lib.rs`) and `Mutex<GridState>` is not `.manage()`'d. This is identical to the A2 PTY pattern: cross-crate `tauri::generate_handler!` cannot resolve another crate's command macros via `pub use`, so the app needs a thin app-level `sync_grid` wrapper + managed state. A3-01 is contracts-only (its verify is crate-level + unit, no live app) so this is correctly out of scope — but the A3 plan that mounts the grid into App.tsx MUST also wire sync_grid + `.manage(Mutex::new(GridState{...}))`, exactly as A2-05 did for the PTY commands. Patterns-established + this note ensure the A3 integration plan lists src-tauri/src/lib.rs.

## Deferred (next A3 waves)

- A3-02: operations.ts (splitFocused/forkFocused/closeFocused/equalizeAll) + 20×5 floor guard.
- A3-03: focus.ts (numeric/directional/i3 edge-midpoint/cycle).
- A3-04: resize.ts + drag handles (markDragMove/Settled consumers) + recursive renderer.
- A3-05: 22px header + ⋯ menu + close-confirm banner.
- A3-06: App.tsx grid integration (mount + **wire sync_grid app-level** per carry-forward) + 9-pane perf/flood blocking human-verify.
