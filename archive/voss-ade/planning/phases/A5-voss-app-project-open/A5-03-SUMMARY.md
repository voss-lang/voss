---
phase: A5-voss-app-project-open
plan: 03
subsystem: frontend-project-storage
status: complete
completed: 2026-05-20
---

# Phase A5, Plan 03: Project Storage Wrapper Summary

Added the typed frontend seam for project open, recents, default cwd, and native folder picking.

## Shipped

- Created `apps/voss-app/src/project/projectStorage.ts`.
- Created `apps/voss-app/src/project/__tests__/projectStorage.test.ts`.
- Exported:
  - `ProjectInfo`
  - `RecentsFile`
  - `OPEN_PROJECT_LABEL`
  - `START_PROJECT_LESS_LABEL`
  - `RECENTS_HEADING`
  - `pickFolder()`
  - `openProject(path)`
  - `listRecents()`
  - `defaultCwd(projectPath)`

## Contract Notes

- `pickFolder` is the only wrapper that imports `@tauri-apps/plugin-dialog`.
- `pickFolder` returns `null` for dialog cancel and for any non-string dialog result.
- `openProject`, `listRecents`, and `defaultCwd` use `@tauri-apps/api/core` `invoke`.
- `defaultCwd` sends the camelCase payload key `{ projectPath }`, which maps to Rust `project_path` through Tauri's parameter conversion.
- `openProject` rethrows Rust error strings unchanged.

## Test Counts

- `projectStorage.test.ts`: 9 tests passed
- `pnpm --filter voss-app test -- src/project`: 16 files passed, 183 tests passed

## Wrapper Size

- `projectStorage.ts`: 60 lines
- `layoutStorage.ts` analog: 67 lines

The new wrapper stayed close to the A4 layout storage pattern; the size difference is expected because A5 has fewer copy constants but includes the dialog picker.

## Verification

- `pnpm vitest run src/project/__tests__/projectStorage.test.ts --reporter=dot`: passed, 9 tests
- `pnpm exec tsc --noEmit -p .`: passed
- `pnpm --filter voss-app exec tsc --noEmit -p .`: passed
- `pnpm --filter voss-app test -- src/project`: passed, 16 files / 183 tests
- Plan grep gate printed `PROJECT_STORAGE_OK`

## Dependency Note

All four wrappers depend on the A5-02 IPC surface being live. Unit tests mock `invoke` and the dialog plugin, so they prove command names and payload shapes; they do not prove the live Tauri runtime has registered the commands. A5-02 covered that with the app build and `generate_handler!` verification.
