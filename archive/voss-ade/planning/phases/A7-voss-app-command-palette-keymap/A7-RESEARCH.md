---
phase: A7
slug: voss-app-command-palette-keymap
status: complete
confidence: high
created: 2026-05-20
---

# Phase A7 - Research

## User Constraints

Locked A7 decisions from `A7-CONTEXT.md`:

- D-01: Create a central typed `CommandRegistry` at `apps/voss-app/src/command-palette/registry.ts` with command id, label, category, optional keybinding, and handler.
- D-02: Retire the A3 pure-switch `grid/keymap.ts` dispatch path and migrate all existing A3/A4 chords to registry dispatch with zero regression.
- D-03: Build a single `AppContext` object in `App.tsx` and thread it into registry handlers.
- D-04: Native OS menus are generated from the same command registry and dispatch back to the same handlers.
- D-05: Cmd+P quick-open lists saved layouts and recent projects in L1; file search is deferred to L4.
- D-06: One `CommandPalette` component supports `quick` and `full` modes.
- D-07: Fuzzy matching is simple case-insensitive substring scoring with recency boost; no external fuzzy dependency.
- D-08: Palette is a centered overlay; Esc/click-outside dismiss; while open, keystrokes do not reach the PTY.
- D-09: Palette rows show right-aligned chord hints sourced from registry entries.
- D-10: Tmux profile uses a timed 1.5s Cmd+B prefix window with the mapped `%`, `"`, `o`, `x`, and `c` keys; timeout/Esc cancels, unrecognized keys cancel and pass through to PTY.
- D-11: Named keymap profiles are `vscode` default and `tmux`; tmux inherits vscode and adds prefix chords.
- D-12: Active profile persists in `~/.config/voss-app/settings.json` under `keymap.profile`.
- D-13: `.voss/keymap.json` merges additively over the active profile; a command id set to `null` unbinds it.
- D-14: `.voss/keymap.json` hot-reloads through a Rust-side watcher and pushes updated bindings to the frontend.
- D-15: Keymap validation is per entry with partial apply; invalid entries are skipped and surfaced as toasts.
- D-16: A7 ships the minimal toast component.

Deferred by context: workspace tabs, theme engine, settings UI, status bar, file-open in Cmd+P, agent pane semantics, cost meter, tmux zoom, and tmux scroll mode.

## RESEARCH COMPLETE

Question: what do we need to know to plan Phase A7 well?

A7 should be planned as a registry-first frontend integration with two small Rust support surfaces: settings/keymap persistence and keymap override watching. The highest-risk edge is keeping one command source of truth across keyboard dispatch, palette search, and native menu dispatch without duplicating command behavior.

## Current Substrate

- `apps/voss-app/src/grid/keymap.ts` is a pure function that maps Cmd chords to grid operations and returns `true` only when it consumes the key. This behavior is the non-regression contract for the new registry dispatch.
- `apps/voss-app/src/grid/GridRoot.tsx` owns the single `window` keydown listener. It currently prefilters on `metaKey`, calls `dispatchKey` inside a Solid `produce`, and handles Cmd+G after the draft closes. A7 should move keydown ownership up or pass a registry dispatcher down, but it must preserve PTY pass-through for unmatched keys.
- `apps/voss-app/src/App.tsx` already owns project state, recents, `activeLayout`, and the A4 callable seams: `saveCurrentLayout`, `loadLayoutByName`, and `applyDefaultLayout`. This is the right place to build `AppContext`, render the palette/toast providers, and install native menus after registry initialization.
- `apps/voss-app/src/grid/layoutStorage.ts` exposes `listLayouts`, `loadLayout`, `saveLayout`, and `loadDefaultLayout` Tauri wrappers. Cmd+P saved-layout entries should call these through `AppContext` rather than duplicating `invoke()` calls.
- `apps/voss-app/src/project/projectStorage.ts` exposes `openProject`, `listRecents`, and `pickFolder`. Cmd+P recent-project entries should reuse `openProject` flow and then refresh recents.
- `apps/voss-app/src/grid/PaneHeader.tsx` is the 22px Variant B header where the tmux prefix indicator belongs. It currently accepts no prefix prop, so A7 needs a narrow additive prop such as `prefixActive?: boolean`.
- `crates/voss-app-core/src/project.rs` is the best path/persistence analog for `~/.config/voss-app/*.json`: hand-built `~/.config/voss-app` path, versioned JSON, fail-closed reads, and temp-write-plus-rename.
- `crates/voss-app-core/src/layouts.rs` is the best workspace-file analog for `.voss/*.json`: validate names/shape, lazy-create only on write, typed error Display strings passed through Tauri.
- `apps/voss-app/src-tauri/src/lib.rs` already uses thin app-level command wrappers because `tauri::generate_handler!` command helper macros must be in the same crate. A7 Tauri commands should follow this pattern.

## Standard Stack

- Keep frontend logic in Solid + TypeScript; no new fuzzy-search package. This is locked by D-07 and appropriate for the small v0 command catalog.
- Use `@tauri-apps/api/menu` for native menu construction from frontend registry metadata, or use Rust `tauri::menu::*` only if a serializable command catalog is mirrored into Rust. Tauri v2 docs show JS `Menu.new(...).setAsAppMenu()` and Rust `MenuBuilder`/`MenuItemBuilder` with `app.set_menu(...)` plus `app.on_menu_event(...)` as supported paths. [CITED: v2.tauri.app/learn/window-menu]
- Use `@tauri-apps/api/event` for Rust-to-frontend keymap update events if the watcher is Rust-side. Tauri v2 docs show frontend `listen()` and Rust `AppHandle::emit(...)` for global events. [CITED: v2.tauri.app/develop/calling-frontend]
- For file watching, prefer the smallest Rust-side mechanism that satisfies D-14. Tauri's official FS plugin supports watch via `tauri-plugin-fs` with the `watch` feature, but that is primarily exposed as a plugin watch API. If the implementation needs a backend-owned watcher that emits typed validation results, a direct Rust watcher module wrapping the same underlying capability is cleaner. [CITED: v2.tauri.app/plugin/file-system]

## Architecture Patterns

### Registry Shape

Split commands into metadata plus handlers:

- `CommandDefinition`: serializable metadata (`id`, `label`, `category`, `defaultBinding`, optional `palette`, optional `menu`, optional `when` key).
- `Command`: definition plus `handler(ctx: AppContext)`.
- `CommandRegistry`: owns command list, current keymap profile, override map, recency store, and `dispatchChord(chord, ctx)`.

This split lets palette, keyboard dispatch, and menu generation read the same command list without requiring Rust to understand frontend closures.

### Keyboard Dispatch

The registry should preserve the current `dispatchKey` contract:

- Return `true` only when a command is actually handled.
- Call `preventDefault()` only for handled chords or palette-owned input.
- Let unmatched keys fall through to the PTY.
- Keep structural-edit hooks (`activeLayout` -> `custom`) attached to split/close/equalize/resize commands.
- Keep Cmd+G layout cycling outside nested Solid drafts, mirroring the current `GridRoot` pattern.

### Palette UI

Use one `CommandPalette` component with:

- `mode: "quick" | "full"`
- local query signal
- derived rows from registry/search providers
- global modal behavior: focus input on open, Esc/click-outside close, restore previous focus on close
- no card-in-card styling; use centered overlay with Variant B variables from `variant-b.css`

Quick mode rows are not only commands: they are command-like action rows for saved layouts and recent projects. Full mode rows are registry commands.

### Native Menus

The cleanest no-drift plan is frontend-installed native menus:

- Add `installNativeMenu(registry, ctx)` that builds menu groups from `registry.menuItems()`.
- Use command IDs as menu item IDs.
- Menu actions call `registry.execute(id, ctx)` or dispatch an app-level command event.
- Re-run the installer when profile/keymap changes if accelerators need to update.

If the executor chooses Rust menus instead, the plan must include a generated/shared catalog file so labels/categories/bindings do not drift from the TypeScript registry.

### Keymap Profiles and Overrides

Use three layers:

1. Built-in profile defaults (`vscode`, `tmux`).
2. Active profile from `~/.config/voss-app/settings.json` at `keymap.profile`.
3. Workspace override from `.voss/keymap.json`.

Validation should produce a result like:

- `effectiveBindings: Record<CommandId, Chord | null>`
- `errors: KeymapValidationIssue[]`

Apply all valid entries and toast each invalid entry. Conflicts should be deterministic: if two commands resolve to the same chord, keep the profile/default binding and reject the later override entry with a toast.

### Tmux Prefix Mode

Prefix mode is stateful keyboard dispatch, not a normal chord:

- Cmd+B enters prefix mode and consumes the key.
- Store `prefixActive` with a 1.5s timer.
- Esc cancels and consumes.
- `%`, `"`, `o`, `x`, and `c` dispatch mapped commands with no Cmd modifier.
- Unknown key cancels and returns `false` so the PTY receives the original key.

The header indicator should be a focused-pane-only prop so unrelated pane headers do not show stale prefix state.

## Common Pitfalls

- Native menu duplication: a Rust-only menu catalog can drift from the TypeScript registry. Prefer frontend menu installation or generated shared metadata.
- Solid draft nesting: current Cmd+G avoids nested `setStore` calls by deferring preset application. Registry handlers must preserve that separation.
- PTY input capture: palette open state must be checked before PTY/keymap dispatch. Any non-palette keydown while palette is open should belong to the input/overlay, not the terminal.
- Chord normalization: `KeyboardEvent.key`, `code`, `metaKey`, `ctrlKey`, `altKey`, and `shiftKey` vary by symbol keys. Build and test a normalizer that preserves current Cmd+Backslash, Cmd+Shift+Backslash, Cmd+[ and Cmd+] behavior.
- Settings shape: existing Rust `SettingsFile` only has `theme`. A7 must extend it compatibly rather than replacing existing settings.
- `.voss/keymap.json` load must not create `.voss/`. Only user writes should create workspace files.
- Toast scope creep: A7 needs a minimal stack for keymap validation only, not a full notification center.

## Validation Architecture

Use existing Vitest, TypeScript build, Cargo tests, and targeted Playwright smoke where practical.

Required automated surfaces:

- Unit tests for chord normalization, substring/recency fuzzy scoring, registry dispatch, profile merge, override validation, and tmux prefix timeout/cancel/pass-through.
- Component tests for `CommandPalette` quick/full modes, overlay dismissal, focus capture, chord hints, and toast rendering.
- Integration tests around `App.tsx` showing Cmd+P and Cmd+Shift+P open the correct modes, quick rows invoke saved layout/recent project handlers, and palette-open keystrokes do not reach the grid/PTX dispatch path.
- Rust unit tests for settings keymap profile round-trip and `.voss/keymap.json` parse/validation behavior.
- Source/build checks for native menu installation and Tauri command/event registration.

Suggested commands:

- `pnpm --dir apps/voss-app test -- --run src/command-palette src/grid src/__tests__/App.test.tsx`
- `pnpm --dir apps/voss-app build`
- `cargo test -p voss-app-core keymap`
- `cargo build -p voss-app`

Manual checks remain needed for real native menu accelerator behavior and file-watch hot reload inside the packaged Tauri shell.

## Plan Implications

- A7-00 should be a blocking substrate/UI-spec preflight if planning proceeds after the UI gate.
- A7-01 should create the command registry, chord normalizer, fuzzy scoring, built-in command catalog, and migrate A3/A4 chord tests to registry behavior.
- A7-02 should wire `AppContext`, keyboard dispatch, palette open state, and `CommandPalette` quick/full UI.
- A7-03 should implement settings/profile persistence plus `.voss/keymap.json` schema, validation, merge, and Rust-to-frontend hot reload.
- A7-04 should implement tmux prefix mode, focused header indicator, and pass-through semantics.
- A7-05 should implement native menu generation from registry metadata plus final acceptance/e2e coverage.
- A7-06, if needed, should be a final acceptance-only plan for CMD-01..07, especially native menus and watcher hot reload.
