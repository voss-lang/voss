---
phase: A4
slug: voss-app-layout-presets
status: complete
date: 2026-05-20
plans:
  - A4-00
  - A4-01
  - A4-02
  - A4-03
  - A4-04
  - A4-05
---

# Phase A4 - voss-app Layout Presets Phase Summary

Phase deliverable: pure-visual layout presets on top of the A3 binary-split pane tree, with a controlled Variant B titlebar switcher, `Cmd+G` cycling, pane-preserving layout save/load, and versioned `.voss/layouts/<name>.json` persistence.

## Wave Map

| Plan | Outcome |
|------|---------|
| A4-00 | Verified A3 grid mount and Rust grid mirror substrate. |
| A4-01 | Implemented pure preset transforms for `fanout`, `pipeline`, `swarm`, and `watchers`. |
| A4-02 | Wired controlled titlebar switcher, `Cmd+G`, and `custom` state. |
| A4-03 | Added Rust layout schema, validation, lazy save, safe load, and Tauri commands. |
| A4-04 | Added frontend invoke wrappers, serialization, load remap/spawn/spill, and A7 callable seams. |
| A4-05 | Added LAY-01..LAY-08 acceptance coverage and closed current verification. |

## Requirements Completed

- **LAY-01:** Four presets exist as pure visual transforms.
- **LAY-02:** Titlebar switcher reflects and sets active preset.
- **LAY-03:** `Cmd+G` cycles `custom -> fanout -> pipeline -> swarm -> watchers -> fanout`.
- **LAY-04:** Preset switches and layout loads preserve existing pane ids.
- **LAY-05:** Capacity mismatches use no fillers, spawn only missing saved slots, and spill extras.
- **LAY-06:** Save layout writes versioned layout data through Rust-owned I/O.
- **LAY-07:** Load/default layout path handles missing/corrupt/unsupported files safely.
- **LAY-08:** A4 remains L1 visual-only; no L2 agent/worktree semantics were added.

## Key Files

- `apps/voss-app/src/grid/layoutPresets.ts`
- `apps/voss-app/src/grid/layoutCommands.ts`
- `apps/voss-app/src/grid/layoutStorage.ts`
- `apps/voss-app/src/grid/GridRoot.tsx`
- `apps/voss-app/src/grid/keymap.ts`
- `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx`
- `apps/voss-app/src/App.tsx`
- `crates/voss-app-core/src/layouts.rs`
- `apps/voss-app/src-tauri/src/lib.rs`
- `apps/voss-app/src/grid/__tests__/a4-acceptance.test.tsx`

## Final Test Snapshot

```
pnpm install --frozen-lockfile
Done in 2s

pnpm --dir apps/voss-app test
Test Files 15 passed
Tests      174 passed

pnpm --dir apps/voss-app build
vite built successfully

cargo test -p voss-app-core
22 passed

cargo test -p voss-app-core layouts
16 passed
```

## Carry-Forward

- Live Tauri e2e remains deferred; `apps/voss-app/e2e/layout-presets.spec.ts` records skipped smoke contracts.
- A5 must provide the project-open workspace path before `default.json` can auto-apply in the real project-open flow.
- A7 must expose the real command palette UI for save/load. A4 only ships the callable seam.

## Phase Outcome

A4 is complete. The voss-app now has L1 visual layout presets, controlled preset state, pane-preserving save/load behavior, and versioned layout persistence ready for A5/A7 integration.
