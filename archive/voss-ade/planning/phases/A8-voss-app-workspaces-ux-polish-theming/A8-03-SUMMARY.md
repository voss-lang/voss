# A8-03 Summary

**Self-Check: PASSED**

Workspace tab bar, new-workspace picker, shortcuts, and command registry integration shipped.

## Tasks

| Task | Status | Verification |
|------|--------|--------------|
| 1 — WorkspaceTabBar + context menu (TDD) | PASS | 12 tab bar tests |
| 2 — NewWorkspacePicker + App wiring | PASS | NewWorkspacePicker + App tests |
| 3 — Shortcuts + registry/native menu | PASS | 471 tests (workspaces, command-palette, components/workspace, App) |

## Deliverables

### UI (`apps/voss-app/src/components/workspace/`)

- **WorkspaceTabBar** — 28px bar, 24px tabs, 8-color fixed dot palette, context menu (rename/color/close), drag reorder, last-workspace guard, running-process confirm
- **NewWorkspacePicker** — centered overlay: name, folder, shell, layout, color dots; Create workspace / Start empty
- **workspace.css** — Variant B tokens; stable tab dimensions on hover/close reveal

### Shortcuts + commands

- **workspaceShortcuts.ts** — Ctrl+1..9, Ctrl+Tab, Ctrl+Shift+Tab (does not steal Cmd+1..9 pane focus)
- **registry.ts** — `workspace.new/close/next/prev/focus1..9/rename/color`, `profile.switch`; Workspace category
- **nativeMenu.ts** — Workspace menu group
- **App.tsx** — tab bar between titlebar and grid; picker overlay; shortcut routing before palette dispatch

### Store

- **workspaceStore.remove()** — close workspace tab

## Requirements covered

UXP-01, UXP-03, UXP-04, UXP-05, UXP-07, UXP-08, UXP-26, UXP-27

## Next

**A8-04** — appearance polish (font picker, cursor, bell, reduced motion, transitions).

---

*Completed: 2026-05-21 | Plan: A8-03 | Phase: A8-voss-app-workspaces-ux-polish-theming*
