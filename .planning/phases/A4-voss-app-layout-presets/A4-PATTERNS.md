---
phase: A4
slug: voss-app-layout-presets
status: complete
created: 2026-05-19
---

# Phase A4 - Pattern Map

## Pattern Mapping Complete

A4 builds on the A3 grid engine and A1 titlebar. The codebase graph is unavailable (`graphify-out/graph.json` missing), so this map is source-inspected.

## Files and Analogs

| A4 Area | Files To Touch | Closest Existing Pattern | Notes |
|---------|----------------|--------------------------|-------|
| Preset transform model | `apps/voss-app/src/grid/layoutPresets.ts`, `apps/voss-app/src/grid/__tests__/layoutPresets.test.ts` | `apps/voss-app/src/grid/tree.ts`, `operations.ts`, `resize.ts` | Pure TypeScript functions, no DOM/Tauri/Solid imports. Mutators preserve pane ids and call `recomputeIndices()`. |
| Keyboard cycle | `apps/voss-app/src/grid/keymap.ts`, keymap tests | Existing `dispatchKey()` in `keymap.ts` | Add `Cmd+G` as an injected callback, like `onCloseRequest`, so keymap remains pure and titlebar state stays outside the module. |
| Grid/titlebar state | `apps/voss-app/src/App.tsx`, `GridRoot.tsx`, `Titlebar.tsx`, `PresetSwitcher.tsx` | A1 `Titlebar` + A3 `GridRoot` composition | Move active layout state to the app/grid composition layer. Convert `PresetSwitcher` from local state to controlled props. |
| Save/load UI copy | `apps/voss-app/src/grid/layoutCommands.ts`, tests | A4 UI-SPEC copy table | A7 owns the palette. A4 exposes callable stubs/handlers and exact copy only. |
| Rust layout schema/I/O | `crates/voss-app-core/src/layouts.rs`, `crates/voss-app-core/src/grid.rs`, `apps/voss-app/src-tauri/src/lib.rs` | `settings_path()` in app `lib.rs`; `GridState` serde in `grid.rs` | Rust/Tauri owns file I/O. Use versioned wrapper around `GridState`; lazy-create `.voss/layouts` only on save. |
| Frontend persistence bridge | `apps/voss-app/src/grid/layoutStorage.ts`, load/save tests | `src/grid/sync.ts` invoke wrapper | Thin `invoke()` wrappers. Keep schema validation in Rust and remap behavior in TypeScript. |

## Landmines

- `App.tsx` currently still renders one `PaneComponent`; A4 execution must not proceed until A3-06 mounts `GridRoot`.
- `sync_grid` exists in `voss-app-core` but is not registered/managed in `src-tauri/src/lib.rs` in the inspected tree. Layout persistence depends on A3-06 fixing this.
- A3-05 adds a canonical `PaneHeader` above the A2 pane, while A2 still renders its own internal header. A4 must not attempt duplicate-header reconciliation unless A3-06 already resolved it.
- Equal-looking rows/columns in a binary tree require ratios based on subtree leaf counts, not blindly nested 0.5 splits.
- Saved layout load must never remove existing pane ids. Smaller saved layouts remap and spill extras; bigger saved layouts may spawn net-new panes with saved cwd/shell.

## Plan Implications

- A4-00 is a blocking substrate gate over A3-06.
- A4-01 owns pure preset math and no UI.
- A4-02 owns titlebar/key routing and no disk I/O.
- A4-03 owns Rust schema/path/file I/O and no Solid layout transforms.
- A4-04 owns frontend save/load remapping and invokes A4-03 commands.
- A4-05 is final acceptance and visual/manual verification.

