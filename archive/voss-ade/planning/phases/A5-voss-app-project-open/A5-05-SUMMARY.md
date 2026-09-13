# A5-05 Summary

**Date:** 2026-05-20

## Result

Composed the A5 project-open substrate into the app shell.

- `App.tsx` now owns `project`, `projectLessAccepted`, `recents`, and the project-less cwd cache.
- `Titlebar` renders `projectName` when present and falls back to `Voss ADE` for undefined or empty names.
- The body slot uses Solid `<Show>`: `SetupWindow` is the no-project fallback and `GridRoot` mounts once after project-open or project-less acceptance.
- Successful project opens refresh recents, yield one microtask, and then attempt the A4 default-layout hook without blocking the open.
- `GridRoot` accepts an optional `projectCwd` seam for later pane-spawn cwd wiring.

## App.tsx Diff Line Count

From implementation commit `a724c02`:

| File | Added | Deleted |
|---|---:|---:|
| `apps/voss-app/src/App.tsx` | 78 | 12 |

## Open-Project Ordering Trace

Happy path in `apps/voss-app/src/App.tsx`:

1. `handleOpenFolder` gets the selected path from `pickFolder()` at lines 113-116.
2. `openSelectedProject` calls `openProject(path)` at line 100.
3. Project state is committed with `setProject(info)` at line 101.
4. The one-way grid predicate is latched with `setProjectLessAccepted(true)` at line 102.
5. Recents refresh with `setRecents(await listRecents())` at line 103.
6. `await Promise.resolve()` at line 104 yields so the `<Show>` branch can mount `GridRoot`.
7. `applyDefaultLayout(info.path)` runs at line 105 and catches failures with `console.warn` at lines 105-107.

The App integration test `flushes project state and GridRoot mount before default-layout load begins` asserts the titlebar project text and grid DOM are visible before `loadDefaultLayout` starts.

## Pane Preservation

Passed. `apps/voss-app/src/__tests__/App.test.tsx` includes `updates project from an existing open-grid state without remounting GridRoot`, which opens one project, captures the `GridRoot` DOM node, opens a second project through the same retained handler, and asserts:

- the `GridRoot` node identity is unchanged;
- the GridRoot mock mount count remains `1`.

This covers D-13 / SPEC Req-8 at the App composition layer.

## Void Suppression Lines

Before A5-05, `App.tsx` suppressed three A7 seams:

- line 82: `void saveCurrentLayout;`
- line 83: `void loadLayoutByName;`
- line 84: `void applyDefaultLayout;`

After A5-05, `applyDefaultLayout` is live and no longer suppressed:

- line 133: `void saveCurrentLayout;`
- line 134: `void loadLayoutByName;`

## Verification

Passed:

```bash
cd /Users/benjaminmarks/Projects/Voss/apps/voss-app
pnpm vitest run src/components/titlebar/__tests__/Titlebar.test.tsx src/__tests__/App.test.tsx --reporter=dot
pnpm vitest run src/__tests__/App.test.tsx --reporter=dot
pnpm exec tsc --noEmit -p .
```

Passed phase gates from repo root:

```bash
pnpm --filter voss-app test
pnpm --filter voss-app exec tsc --noEmit -p .
pnpm --filter voss-app build
```

Sentinel checks:

```bash
TITLEBAR_PROJECT_OK
APP_COMPOSITION_OK
```
