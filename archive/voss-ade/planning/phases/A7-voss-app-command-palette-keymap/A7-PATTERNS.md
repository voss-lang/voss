---
phase: A7
slug: voss-app-command-palette-keymap
status: complete
created: 2026-05-20
---

# Phase A7 - Pattern Map

## PATTERN MAPPING COMPLETE

Graphify was attempted through the project rule during A7 planning, but no graph existed at `graphify-out/graph.json`. This map is source-inspected from the current repo.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `apps/voss-app/src/command-palette/registry.ts` | service/registry | event-driven | `apps/voss-app/src/grid/keymap.ts` | role-match |
| `apps/voss-app/src/command-palette/chords.ts` | utility | transform | `apps/voss-app/src/grid/keymap.ts` | role-match |
| `apps/voss-app/src/command-palette/fuzzy.ts` | utility | transform | `apps/voss-app/src/grid/layoutPresets.ts` | partial |
| `apps/voss-app/src/command-palette/CommandPalette.tsx` | component | event-driven | `apps/voss-app/src/grid/DotMenu.tsx` | role-match |
| `apps/voss-app/src/command-palette/toast.tsx` | component/provider | event-driven | `apps/voss-app/src/grid/CloseConfirmBanner.tsx` | role-match |
| `apps/voss-app/src/command-palette/nativeMenu.ts` | bridge | event-driven | `apps/voss-app/src/grid/layoutStorage.ts` | partial |
| `apps/voss-app/src/App.tsx` | composition root | state orchestration | existing `App.tsx` A4/A5 seams | exact |
| `apps/voss-app/src/grid/GridRoot.tsx` | component host | keyboard event | existing `GridRoot.tsx` keydown listener | exact |
| `apps/voss-app/src/grid/PaneHeader.tsx` | chrome component | state display | existing `PaneHeader.tsx` | exact |
| `crates/voss-app-core/src/keymap.rs` | Rust model/IO | file IO | `crates/voss-app-core/src/project.rs`, `layouts.rs` | role-match |
| `apps/voss-app/src-tauri/src/lib.rs` | Tauri command wrapper | request-response/event | existing layout/project wrapper blocks | exact |

## Pattern Assignments

### Command Registry / Chord Dispatch

**Analog:** `apps/voss-app/src/grid/keymap.ts`

Copy these behavioral invariants:

- unmatched keys return false without `preventDefault()`
- all currently handled A3/A4 chords remain handled
- structural commands call the active-layout-to-custom seam before split/close/equalize/resize
- Cmd+G layout cycling is not treated as structural

The registry replaces the switch, but the pass-through behavior is the compatibility contract.

### Palette Overlay and Row Menus

**Analog:** `apps/voss-app/src/grid/DotMenu.tsx`

Use the same Solid patterns:

- document-level Escape/outside-click listeners with `onMount`/`onCleanup`
- fixed dimensions for dense command rows
- `role="menu"`/button-style rows or an equivalent tested ARIA model
- token-only colors (`bg-bg-*`, `text-fg-*`, `text-accent-red`)
- no radius and no animated layout shift

### Toast / Inline Feedback

**Analog:** `apps/voss-app/src/grid/CloseConfirmBanner.tsx`

Use the same chrome rules:

- 22px/32px dense single-line surfaces
- semantic accent only for severity rail/text
- no modal for non-blocking validation warnings
- Escape/keyboard handling must not leak into PTY when the UI surface owns focus

### App Composition

**Analog:** `apps/voss-app/src/App.tsx`

A7 should extend the existing A4/A5 composition root:

- `project`, `recents`, `activeLayout`, and `projectLessAccepted` stay in `App.tsx`
- `saveCurrentLayout`, `loadLayoutByName`, and `applyDefaultLayout` become AppContext methods
- palette and toast providers render once near the root, above `GridRoot`
- no global `window.__voss` registration

### Rust Keymap and Settings IO

**Analogs:** `crates/voss-app-core/src/project.rs`, `crates/voss-app-core/src/layouts.rs`

Use the existing persistence conventions:

- `~/.config/voss-app/settings.json` path is built manually from `dirs::home_dir()`
- workspace override path is `<workspace>/.voss/keymap.json`
- loads fail closed
- writes create parent directories only on write
- typed errors expose user-facing Display strings
- app crate has thin `#[tauri::command]` wrappers in `apps/voss-app/src-tauri/src/lib.rs`

## Shared Patterns

- **Token usage:** A7 components use Variant B CSS variables and Tailwind v4 token utilities only.
- **No source drift:** command label/category/keybinding metadata must be read from one registry, then reused by keyboard, palette, and native menus.
- **Testing:** mirror existing Vitest patterns under `src/**/__tests__`, mock Tauri `invoke`/event/menu APIs at module boundaries, and keep Rust IO tests hermetic with temp dirs or thread-local path overrides.
- **Safety:** `.voss/keymap.json` errors toast and partially apply; one bad override cannot break the default keymap.

