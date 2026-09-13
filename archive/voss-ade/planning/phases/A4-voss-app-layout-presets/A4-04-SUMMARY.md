---
phase: A4-voss-app-layout-presets
plan: 04
subsystem: frontend-layout-commands
status: complete
completed: 2026-05-20
---

# Phase A4, Plan 04: Frontend Save and Load Summary

Wired frontend save/load helpers to the Rust layout persistence surface.

## Accomplishments

- Added thin Tauri invoke wrappers in `layoutStorage.ts`.
- Added exact A4 UI-SPEC copy constants for save/load outcomes.
- Added `serializeLayout` with canonical tree copying so runtime fields do not leak into layout files.
- Added `applyLoadedLayout` remapping:
  - Equal saved/current count substitutes existing panes into saved geometry.
  - Saved layouts with more slots spawn only net-new panes using saved cwd/shell.
  - Saved layouts with fewer slots preserve existing extras by spilling them into the last region.
- Added callable save/load/default seams in `App.tsx` for A7 command palette integration.

## Key Files

- `apps/voss-app/src/grid/layoutStorage.ts`
- `apps/voss-app/src/grid/layoutCommands.ts`
- `apps/voss-app/src/grid/__tests__/layoutStorage.test.ts`
- `apps/voss-app/src/grid/__tests__/layoutCommands.test.ts`
- `apps/voss-app/src/App.tsx`

## Verify

```
pnpm --dir apps/voss-app test -- --run src/grid src/components/titlebar
Test Files 15 passed
Tests      174 passed

cargo test -p voss-app-core layouts
16 passed
```

## Outcome

LAY-04, LAY-05, LAY-06, LAY-07, and LAY-08 frontend command behavior is implemented.
