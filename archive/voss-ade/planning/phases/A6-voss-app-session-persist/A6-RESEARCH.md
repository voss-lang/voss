---
phase: A6
slug: voss-app-session-persist
status: complete
confidence: high
created: 2026-05-20
---

# Phase A6 - Research

## RESEARCH COMPLETE

Question: what do we need to know to plan Phase A6 well?

Phase A6 persists the L1 terminal session across restart. It extends the A3 grid tree, A4 layout serialization, and A5 project lifecycle without relaunching live processes.

## Current Substrate

- `crates/voss-app-core/src/grid.rs` owns the serde-compatible Rust mirror of the Solid grid tree. The JSON keys already match the TypeScript shape: `focusedId`, `kind`, `orientation`, `ratio`, `cwd`, `shell`, `index`.
- `crates/voss-app-core/src/layouts.rs` is the closest Rust file-I/O analog: a versioned wrapper around `GridState`, fail-safe parsing, lazy `.voss/` creation on write, and typed errors whose Display strings can surface through Tauri.
- `crates/voss-app-core/src/project.rs` already contains the A5 project helpers and `~/.config/voss-app/recents.json` path idiom. A6 should reuse that home-dir path convention for `global-session.json`.
- `apps/voss-app/src/grid/sync.ts` has the structural-change signal A6 needs. Today `markStructuralChange(state)` immediately mirrors to Rust; A6 can add a debounced session auto-save alongside that sync call.
- `apps/voss-app/src/grid/GridRoot.tsx` owns the Solid grid store and exposes a controller with `applyLoadedLayout` and `snapshot`. A6 needs to extend the controller with session restore/apply hooks rather than lifting the store into `App.tsx`.
- `apps/voss-app/src/pane/PaneComponent.tsx` owns the xterm `Terminal` instance. It currently does not expose scrollback or a restore-writing hook. A6 needs a narrow registry/callback seam so the grid layer can ask each pane for the last 2,000 normal-buffer lines on quit and seed restored text on mount.
- `apps/voss-app/src/grid/SplitNode.tsx` is the pane chrome mount point. A6 should add `RestoreBanner` next to the existing `CloseConfirmBanner` seam, above terminal content and below `PaneHeader`.
- `apps/voss-app/src/App.tsx` is still the composition root for `activeLayout`. It has A4 save/load closures but no visible project signal in the current inspected source. A6 therefore needs a Wave 0 gate that refuses execution until the A5 project-open app lifecycle is present.

## Tauri Close Event

Tauri v2 exposes `getCurrentWindow().onCloseRequested(handler)` from `@tauri-apps/api/window`. The handler receives an event with `preventDefault()`, and registration returns an unlisten function. A6 should register in `App.tsx` or a session lifecycle module, call `preventDefault()` immediately, run the full save with scrollback, then close the window after the save completes.

Implementation note: guard against reentry. Calling `close()` after a successful save emits another close request, so the handler needs an `isClosingAfterSave` flag that lets the second request pass.

## Recommended Architecture

1. Rust core session module:
   - Add `crates/voss-app-core/src/session.rs`.
   - Define `CURRENT_SESSION_VERSION: u32 = 1`.
   - Define `SessionFile { version, active_preset, grid, panes, project_less_accepted }`.
   - Store per-pane scrollback outside `GridState`, keyed by pane id: `SessionPane { id, scrollback: Option<Vec<String>> }`.
   - Implement project path `.voss/session.json` and global path `~/.config/voss-app/global-session.json`.
   - Use tmp write plus rename, and add an exclusive file lock around writes with `fs2::FileExt` or equivalent. There is no existing file-lock helper in the repo.

2. Frontend storage bridge:
   - Add `apps/voss-app/src/grid/sessionStorage.ts`.
   - Mirror `layoutStorage.ts`: typed `SessionFile`, `saveSession`, `loadSession`, `saveGlobalSession`, `loadGlobalSession`, and copy constants for known failures.
   - Keep this module thin. It should not know xterm internals.

3. Pane scrollback seam:
   - Add a registry module such as `apps/voss-app/src/pane/scrollbackRegistry.ts`.
   - Each `PaneComponent` registers by pane id on mount and unregisters on cleanup.
   - Registry callback returns last N lines from `term.buffer.normal`, stripped to plain text with `translateToString(true)`.
   - Restored scrollback is injected into a fresh terminal before shell interaction, then the pane spawns a new shell. No old PTY/session id persists.

4. Grid session orchestration:
   - Add `apps/voss-app/src/grid/sessionPersist.ts`.
   - Build snapshots from `GridController.snapshot()`, `activeLayout`, project path/project-less flag, and registry scrollback callbacks.
   - Add debounced tree-only save from structural changes. The existing `markStructuralChange` signal is the hook, but it needs a pluggable listener so A6 avoids baking app-specific persistence into the low-level sync module.
   - Full quit save calls the same serializer with scrollback included.

5. Restore path:
   - Session wins over default layout. Project mode: `session.json` -> `default.json` -> fresh pane. Global mode: `global-session.json` can bypass the setup window when `projectLessAccepted` is true.
   - Corrupt or unsupported session must fail closed and log to stderr, then fall through.
   - Restored panes show `RestoreBanner` with `Session restored - N lines`; banner dismisses on the first keystroke in that pane.

## Landmines

- A5 is a hard dependency. If `App.tsx` does not own project/project-less state yet, A6 cannot correctly choose `.voss/session.json` vs `global-session.json`.
- `PaneComponent` currently has no `id` prop. The A6 scrollback registry needs pane id to match saved scrollback to leaves after restore.
- xterm has both active and normal buffers. A6 is explicitly locked to `buffer.normal`; do not use `buffer.active` or the serialize addon.
- `translateToString(true)` gives text, not ANSI. That matches D-02.
- Structural auto-save must not read xterm buffers. It should write scrollback as null/empty and preserve any previously stored scrollback only if the schema deliberately supports that. Simpler L1 behavior: tree-only writes `scrollback: null`; full quit writes arrays.
- Blocking quit save must avoid an infinite close loop.
- Layout restore code remaps panes to avoid killing live panes. A6 session restore happens on launch before live user panes exist, so it can apply the saved ids directly.
- Do not add SQLite. PER-05 locks JSON for L1.

## Open Questions

All planning-blocking questions are resolved in A6-CONTEXT.md:

- Scrollback capture trigger: on quit only for scrollback, structural auto-save for tree.
- Scrollback encoding: plain text only.
- Buffer source: `buffer.normal`.
- Restore priority: session over default layout.
- Global project-less persistence: `global-session.json`.

## Plan Implications

- A6-00 should block execution until A5 project-open lifecycle exists in the app composition root.
- A6-01 owns Rust schema, path resolution, locking, save/load/fail-safe behavior, and Tauri command registration.
- A6-02 owns frontend session bridge types plus pure snapshot/restore transforms.
- A6-03 owns scrollback registry and `PaneComponent` extraction/restore seed.
- A6-04 owns structural auto-save, quit close interception, and restore priority in `App.tsx`.
- A6-05 owns restore banner UX, app-level acceptance, and restart/e2e coverage.

