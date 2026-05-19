---
phase: A4
slug: voss-app-layout-presets
status: complete
created: 2026-05-19
---

# Phase A4 - Research: voss-app Layout Presets

## RESEARCH COMPLETE

Question answered: What do we need to know to plan A4 well?

## Executive Findings

A4 should be planned as an additive layer over the A3 pane tree, but the planner must account for current A3 integration drift:

- `apps/voss-app/src/grid/tree.ts` already has the right pure model primitives: `SplitNode`, `PaneLeaf`, `GridStore`, `collectLeaves()`, `recomputeIndices()`, `findLeaf()`, and `equalizeRatios()`.
- `apps/voss-app/src/grid/operations.ts` already preserves pane ids and only mutates structure, which is the right behavior for "never destroy panes."
- `apps/voss-app/src/grid/GridRoot.tsx` owns the global keydown listener and should receive the new `Cmd+G` dispatch path plus a way to surface active preset state to the titlebar.
- `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx` is currently A1 visual-only local state. A4 needs to convert it into a controlled component wired to grid layout state, including the `custom` state.
- `apps/voss-app/src/App.tsx` still renders one `PaneComponent` directly instead of `<GridRoot />`. The A4 plan should either depend on completing A3-06 integration first or include a blocking preflight task that wires the app body to `GridRoot`; do not assume the app runtime currently exercises the grid.
- `crates/voss-app-core/src/grid.rs` defines `GridState` and `sync_grid`, but `apps/voss-app/src-tauri/src/lib.rs` does not currently manage `Mutex<GridState>` or register `sync_grid` in `generate_handler!`. A4 layout persistence depends on this mirror working, so the plan needs a blocking Rust mirror registration check before adding layout I/O.
- Tauri 2's documented command pattern matches the existing seam: register Rust commands with `tauri::generate_handler!`, manage shared state through `.manage(...)`, and call commands from the frontend with `invoke(...)` from `@tauri-apps/api/core`. File I/O should stay in Rust commands, not the Solid webview.

## Implementation Research

### Preset transforms

Recommended shape: add a pure module under `apps/voss-app/src/grid/layoutPresets.ts` or equivalent. Keep it free of DOM, Tauri, and Solid imports so Vitest can cover all geometry cases.

Core API candidates:

- `type LayoutPreset = 'fanout' | 'pipeline' | 'swarm' | 'watchers'`
- `type ActiveLayout = LayoutPreset | 'custom'`
- `applyPreset(root: TreeNode, preset: LayoutPreset): TreeNode`
- `nextPreset(active: ActiveLayout): LayoutPreset`
- `detectPreset(root: TreeNode): ActiveLayout` if cheap and deterministic; otherwise mark manual edits as `custom` in the mutation layer.

The transform should preserve pane ids, cwd, shell, and index-order mapping:

1. Read panes with `collectLeaves(root)` after `recomputeIndices(root)`.
2. Build a new binary split tree that places the existing leaf objects into preset slots in stable index order.
3. Use pane #1 as the primary slot for fanout/watchers/swarm/pipeline.
4. Call `recomputeIndices(newRoot)` after construction.
5. Preserve `focusedId` unchanged if the focused pane still exists, which it should because panes are reused.
6. Call the existing sync path once after the transformed root is committed.

Do not create filler panes for under-capacity presets. If the saved layout has more slots than currently open panes, spawn new panes only during explicit load, and only for net-new slots.

### Preset-specific tree construction

Binary split tree constraints matter because A3 is not CSS grid. The plan should specify concrete construction helpers:

- `pipeline`: fold panes into an H-split row with equal ratios. For N panes, recursively split with ratios that approximate equal widths, not always 0.5 at every level.
- `swarm`: compute columns and rows from pane count, defaulting toward 2x2 and growing up to 4x4. Build rows with H splits, then stack rows with V splits. For counts above 16, spill extras by splitting the last cell/subtree.
- `fanout`: pane 1 left; all remaining panes in a right-side vertical column. For only one pane, return the pane unchanged.
- `watchers`: pane 1 top; watchers bottom as an H row. Natural watcher count is 2-3, but D-03 allows the watcher region to grow and D-04 spills beyond hard cap by splitting the last region cell.

Important planning point: equal visual widths/heights in a binary tree require ratios based on subtree leaf counts. A helper like `splitByCounts(leftCount, rightCount)` should set `ratio = leftCount / (leftCount + rightCount)` instead of relying on `makeSplit()`'s default 0.5 for every internal split.

### Keyboard and state routing

`dispatchKey()` currently owns A3 chords. A4 can add `Cmd+G` there, but applying a preset also needs titlebar state. Two low-risk patterns:

- Move grid state ownership up into an app-level component that renders both `Titlebar` and `GridRoot`, passing `activeLayout` plus `onPresetSelect`.
- Or keep `GridRoot` as owner and expose a context provider consumed by `PresetSwitcher`.

The first pattern is simpler to plan and test: `App.tsx` becomes the composition point, and titlebar remains mostly presentational.

Any manual structural operation that is not a preset switch or saved-layout load should set active layout to `custom`. This includes split, fork, close, drag resize, keyboard resize, and equalize. If this is too invasive for A4, the plan can scope custom-state updates to A4-owned layout operations plus preset switcher display after explicit preset/load.

### Layout persistence

Recommended schema:

```json
{
  "version": 1,
  "activePreset": "fanout",
  "root": { "kind": "split" },
  "focusedId": "pane-id",
  "panes": [
    { "id": "pane-id", "cwd": "/repo", "shell": "zsh" }
  ]
}
```

The exact shape can reuse `GridState` directly for `root` and `focusedId`, because Rust already mirrors the TypeScript discriminated union with serde. The plan should require a version wrapper around that state, not a parallel model.

Rust/Tauri work should include:

- A layout path resolver for workspace `.voss/layouts/<name>.json`.
- Name validation that rejects path separators, `..`, empty names, and non-`.json` suffix confusion.
- Lazy `.voss/layouts` creation only on save.
- `save_layout(name, layout)` writes pretty JSON atomically enough for local app use.
- `load_layout(name)` returns `Option<LayoutFile>` or a typed error string.
- `load_default_layout()` returns no-op when missing, ignores/logs corrupt or unmigratable files, and never panics.

A5 owns real project-open plumbing. A4 should expose the default-load function and a callable hook, but should not implement the folder picker or recent-workspace system.

### Testing targets

Vitest should carry most A4 behavior:

- Pure preset transform tests for 1, 2, 3, 4, 6, 9, 16, and 17 panes.
- Focus preservation test: focused pane id before transform equals after transform.
- No-destroy test: set of pane ids before and after preset switch is equal.
- `Cmd+G` order: custom -> fanout -> pipeline -> swarm -> watchers -> fanout.
- Titlebar controlled switcher: clicking a preset calls the grid action and renders active/custom states without local-only drift.
- Save/load mapping: loading a bigger saved layout spawns only missing panes; loading a smaller saved layout preserves extras through overflow/spill instead of killing them.

Rust tests should cover:

- Layout schema serde round-trip.
- Lazy directory creation only on save.
- Missing `default.json` returns no layout.
- Corrupt/unknown layout returns a non-fatal error/no-op.
- Path traversal is rejected.

Runtime smoke should include:

- `pnpm --dir apps/voss-app test -- --run src/grid`
- `pnpm --dir apps/voss-app build`
- `cargo test -p voss-app-core`

## Validation Architecture

Use a two-layer validation strategy:

1. Pure model tests prove the hard safety invariant: preset switches and layout loads never destroy existing pane ids and always preserve the focused pane id when that pane still exists.
2. UI/Rust integration tests prove command routing and persistence seams: `Cmd+G`, controlled switcher state, Tauri command registration, and layout file read/write behavior.

The highest-risk false positive is a plan that tests pure transforms but never verifies that `App.tsx` actually renders `GridRoot` or that `sync_grid` is registered in the Tauri handler. Treat both as blocking preflight checks in the plan.

## Planning Implications

Recommended plan shape:

1. Blocking preflight: finish/verify A3 app-body and Rust mirror registration if still incomplete.
2. Pure preset model: layout state type, transform helpers, `Cmd+G` order, no-destroy/focus-preserve tests.
3. UI wiring: controlled `PresetSwitcher`, titlebar state, custom state, grid action routing.
4. Persistence: Rust layout file schema/commands, frontend invoke wrappers, save/load/default-load behavior.
5. Integration acceptance: full A4 smoke covering preset cycling, save/load, corrupt default fail-safe, and build/test commands.

Do not add L2 semantics, agent behavior, scrollback/session restore, command palette UI, project picker, or status bar work. Those remain owned by later A phases.

