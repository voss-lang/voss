---
phase: A8
slug: voss-app-workspaces-ux-polish-theming
status: complete
created: 2026-05-20
---

# Phase A8 - Pattern Map

## PATTERN MAPPING COMPLETE

Graphify was attempted during A8 research, but no graph existed at
`graphify-out/graph.json`. This map is source-inspected from the current repo.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `apps/voss-app/src/workspaces/workspaceStore.ts` | state/service | UI orchestration | `apps/voss-app/src/App.tsx` | role-match |
| `apps/voss-app/src/workspaces/workspaceStorage.ts` | Tauri bridge | request-response | `apps/voss-app/src/grid/sessionStorage.ts` | exact |
| `apps/voss-app/src/workspaces/workspaceSessionPersist.ts` | lifecycle service | event + IO | `apps/voss-app/src/grid/sessionPersist.ts` | role-match |
| `apps/voss-app/src/components/workspace/WorkspaceTabBar.tsx` | chrome component | event-driven | `components/titlebar/Titlebar.tsx`, `grid/DotMenu.tsx` | role-match |
| `apps/voss-app/src/components/workspace/NewWorkspacePicker.tsx` | overlay component | event-driven | `command-palette/CommandPalette.tsx` | role-match |
| `apps/voss-app/src/themes/schema.ts` | model/schema | validation | `grid/layoutStorage.ts`, `command-palette/keymapStorage.ts` | partial |
| `apps/voss-app/src/themes/themeCatalog.ts` | service/catalog | transform + IO | `theme/applyTheme.ts`, `command-palette/quickOpen.ts` | role-match |
| `apps/voss-app/src/themes/bundled/*.json` | data | static bundled assets | `styles/variant-b.css` | role-match |
| `apps/voss-app/src/appearance/*` | service/UI helpers | settings transform | `command-palette/keymapStorage.ts` | role-match |
| `crates/voss-app-core/src/workspaces.rs` | Rust model/IO | file IO | `session.rs`, `project.rs` | exact |
| `crates/voss-app-core/src/themes.rs` | Rust model/IO | file IO | `layouts.rs`, `keymap.rs` | exact |
| `crates/voss-app-core/src/profiles.rs` | Rust model/IO | file IO | `keymap.rs`, `session.rs` | exact |
| `crates/voss-app-core/src/fonts.rs` | Rust command helper | platform query | `project.rs::default_cwd` | partial |
| `apps/voss-app/src-tauri/src/lib.rs` | Tauri wrapper | command registry | existing layout/project/session/keymap wrappers | exact |

## Pattern Assignments

## Decision Coverage Map

| Decision | Plan Coverage |
|---|---|
| D-01 all workspaces stay mounted hidden | A8-02, A8-03 |
| D-02 workspace state structure planner discretion | A8-02 chooses mounted mini-App workspace records |
| D-03 fixed workspace accent dot palette | A8-03 |
| D-04 workspaces.json plus per-workspace sessions | A8-02 |
| D-05 12 curated bundled themes, no VSCode import | A8-01 |
| D-06 static JSON theme files in repo | A8-01 |
| D-07 custom themes via same JSON schema | A8-01 |
| D-08 native vibrancy per platform with Linux CSS fallback | A8-05 |
| D-09 full platform polish across macOS, Windows, Linux | A8-05, A8-06 |
| D-10 OS-native window chrome | A8-05 |
| D-11 CSS transitions only and reduced-motion kill switch | A8-04 |
| D-12 high-contrast token override layer | A8-01, A8-04 |
| D-13 font dropdown and live preview | A8-04 |
| D-14 full settings snapshot profiles | A8-01, A8-03 |

### App Composition and Workspaces

**Analog:** `apps/voss-app/src/App.tsx`

A8 should refactor from one app-wide project/grid state into mounted workspace
records. Each workspace should own the state that is currently singular:

- project or project-less cwd
- active layout
- initial/restored session
- grid controller
- project-less accepted flag

`App.tsx` remains the orchestration root. Do not move all behavior into
global singletons.

### Active-Only Grid Input

**Analog:** `apps/voss-app/src/grid/GridRoot.tsx`

`GridRoot` currently installs window keydown listeners per instance. A8 must
add an active-workspace gate before mounting hidden GridRoots:

- `active?: () => boolean` prop, or equivalent active id check
- inactive grids ignore global keydown
- active grids keep existing A3/A4 key behavior
- palette-open suppression from A7 remains above grid handling

### Workspace Session Persistence

**Analog:** `apps/voss-app/src/grid/sessionPersist.ts`

A6 close save is single-grid. A8 must centralize all-workspace close save:

- one close-request handler in `App.tsx` or `workspaceSessionPersist.ts`
- iterate mounted workspace controllers
- save project workspaces to `.voss/session.json`
- save project-less workspaces to `~/.config/voss-app/sessions/<id>.json`
- write `~/.config/voss-app/workspaces.json`
- then re-issue close with the existing reentry guard pattern

Avoid one close handler per workspace.

### Rust IO Modules

**Analogs:** `crates/voss-app-core/src/session.rs`, `layouts.rs`, `keymap.rs`

Use the existing conventions:

- manual `~/.config/voss-app` path from `dirs::home_dir()`
- typed schema structs with `#[serde(rename_all = "camelCase")]`
- integer `version`
- missing/corrupt/unsupported load fails safe where possible
- writes create parent directories only on write
- atomic tmp write + rename for user files
- typed errors expose stable user-facing Display strings
- app crate has thin `#[tauri::command]` wrappers

### Theme Runtime

**Analog:** `apps/voss-app/src/theme/applyTheme.ts`

Keep the runtime simple:

- validated theme JSON becomes a CSS variable map plus xterm ANSI palette
- `applyThemeOverrides()` remains the CSS-var seam
- pane terminal instances consume a theme update without remount
- high contrast is applied after the selected theme
- reduced motion is global CSS, not component-by-component JS

### Compact UI Surfaces

**Analogs:** `command-palette/CommandPalette.tsx`, `grid/DotMenu.tsx`

A8 uses dense operational chrome:

- 28px workspace tabbar
- 24px tabs inside the bar
- 32px picker rows
- 28px context menu rows
- 0px radius
- no nested cards
- Escape/outside-click cleanup with `onMount`/`onCleanup`
- stable dimensions so hover/active/drag states do not shift layout

### A7 Registry and Toast

**Analogs:** `command-palette/registry.ts`, `toast.tsx`, `nativeMenu.ts`

A8 should extend A7 rather than duplicate it:

- add `workspace.*`, `theme.*`, `profile.*`, `appearance.*` commands to the registry
- use existing `ToastStack` for feedback
- native menus wrap registry commands when menu support is active
- if A7 command handlers remain placeholders, Wave 0 must flag that before A8 wires dependent commands

## Verification Patterns

- Frontend: Vitest + Solid Testing Library under `src/**/__tests__`.
- Rust: `cargo test -p voss-app-core <module>`.
- Build: `pnpm --dir apps/voss-app build` and `cargo build -p voss-app`.
- Manual: Tauri runtime for native vibrancy, hidden PTY liveness, and cross-platform metadata.
