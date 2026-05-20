---
phase: A4-voss-app-layout-presets
plan: 01
subsystem: preset-model
status: complete
completed: 2026-05-20
---

# Phase A4, Plan 01: Pure Layout Preset Model Summary

Implemented the pure visual preset model over the A3 pane tree.

## Accomplishments

- Added `LayoutPreset` and `ActiveLayout` types.
- Added fixed cycle order: `fanout -> pipeline -> swarm -> watchers -> fanout`.
- Added `nextPreset`, `applyPreset`, and `applyPresetFromLeaves`.
- Implemented pane-preserving preset builders:
  - `fanout`: primary pane left, receivers stacked right.
  - `pipeline`: equal left-to-right row.
  - `swarm`: near-square grid up to 4x4, with overflow spill.
  - `watchers`: primary pane top, watchers along bottom.
- Preset transforms preserve pane ids, cwd, shell, and leaf count. They do not touch DOM, Solid, Tauri, PTY sessions, or L2 semantics.

## Key Files

- `apps/voss-app/src/grid/layoutPresets.ts`
- `apps/voss-app/src/grid/__tests__/layoutPresets.test.ts`

## Verify

```
pnpm --dir apps/voss-app test -- --run src/grid src/components/titlebar
Test Files 15 passed
Tests      174 passed
```

## Outcome

LAY-01, LAY-03, LAY-04, LAY-05, and LAY-08 model requirements are implemented.
