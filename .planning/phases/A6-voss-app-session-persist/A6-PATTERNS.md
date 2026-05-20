---
phase: A6
slug: voss-app-session-persist
status: complete
created: 2026-05-20
---

# Phase A6 - Pattern Map

## PATTERN MAPPING COMPLETE

Graphify was attempted through the project rule, but no usable graph response was available in this run. This map is source-inspected from the current repo.

## Files and Analogs

| A6 Area | Files To Touch | Closest Existing Pattern | Notes |
|---|---|---|---|
| Rust session schema and IO | `crates/voss-app-core/src/session.rs`, `lib.rs`, `Cargo.toml` | `crates/voss-app-core/src/layouts.rs`, `project.rs` | Versioned serde wrapper, fail-safe load, home config path, tmp write and rename. Add explicit file locking for PER-06. |
| App Tauri wrappers | `apps/voss-app/src-tauri/src/lib.rs` | Existing layout and project wrapper blocks | Commands live in app crate because `tauri::generate_handler!` helper macros must be in the same crate. |
| Frontend invoke wrappers | `apps/voss-app/src/grid/sessionStorage.ts` | `apps/voss-app/src/grid/layoutStorage.ts` | Thin `invoke()` layer with exact command names and payload keys. |
| Pure session transforms | `apps/voss-app/src/grid/sessionCommands.ts` | `layoutCommands.ts` | No DOM/Tauri; build and apply session snapshots using canonical tree fields. |
| Structural auto-save hook | `apps/voss-app/src/grid/sync.ts`, `sessionPersist.ts` | `markStructuralChange` and A4 `GridController.snapshot()` | Add listener/subscription seam; avoid importing app persistence into sync module. |
| Quit close lifecycle | `apps/voss-app/src/App.tsx`, maybe `sessionPersist.ts` | Tauri v2 `getCurrentWindow().onCloseRequested` API | Prevent close, save with scrollback, then close with reentry guard. |
| Scrollback extraction | `PaneComponent.tsx`, new `scrollbackRegistry.ts` | Existing `buffer.active.getLine()` link detection | Use `buffer.normal.getLine()` and `translateToString(true)` for plain text. |
| Restore banner | `RestoreBanner.tsx`, `SplitNode.tsx`, tests | `CloseConfirmBanner.tsx`, `ExitBanner.tsx`, `PaneHeader.tsx` | 22px chrome row, Variant B tokens, no rounded card, auto-dismiss via first keystroke. |
| Acceptance tests | grid/pane vitest and Playwright | A4 `a4-acceptance.test.tsx`, A3 grid tests | Mock Tauri invokes and pane stubs for unit tests; e2e can remain skipped on Linux with source assertions if mac-only. |

## Landmines

- `PaneComponent` renders its own internal A2 header, while `SplitNode` renders the A3 header above it. A6 should not fix duplicate-header polish unless required for `RestoreBanner`; mount the restore banner in the A3 chrome seam.
- A6 cannot choose the correct session target without the A5 project state. Do not fake this with cwd heuristics.
- Do not serialize PTY session ids, process names, foreground process state, or environment mutations.
- The A4 layout load path remaps existing live panes. Session restore should run at app startup and can preserve saved pane ids directly.
- Every write path that can create `.voss/` must be a user/session write path. Loading a session or opening a project must not create `.voss/`.
- `global-session.json` must follow the same `~/.config/voss-app/` path lock used by settings and recents, not macOS Application Support.

## Recommended Plan Slices

- Wave 0: substrate gate for completed A5/A4/A3 app state.
- Wave 1: Rust session persistence surface.
- Wave 2: frontend session bridge and pure transforms.
- Wave 3: xterm scrollback registry and pane restore seeding.
- Wave 4: app lifecycle wiring for restore, autosave, and quit.
- Wave 5: banner and acceptance verification.

