---
phase: A8
slug: voss-app-workspaces-ux-polish-theming
status: complete
created: 2026-05-20
---

# Phase A8 Research - Workspaces, UX Polish, and Theming

## RESEARCH COMPLETE

Objective: identify what must be true to plan A8 safely against the current
voss-app codebase.

## Scope Resolution

A8-CONTEXT.md is the authority for planning where it conflicts with the older
ROADMAP wording.

- ROADMAP UXP-09 and success criterion 2 still mention a VSCode theme import
  engine. A8 discussion explicitly removed that import engine. D-05 locks A8
  to 12 curated bundled themes plus custom themes in the same JSON schema.
- Plan coverage should still name UXP-09, but implement it as "curated theme
  mappings and schema-compatible custom theme loading," not automated VSCode
  token import.
- A8 depends on A7 command registry/toast/profile switch commands by context,
  but this checkout has A7 plans and no A7 SUMMARY files. A8 execution needs a
  Wave 0 preflight that proves A7 is actually implemented, or clearly records
  that A8 cannot wire palette/profile commands yet.

## Current Substrate

Graphify was attempted first per project rule, but
`graphify-out/graph.json` is absent. This research uses phase context and
targeted source reads.

### App Composition

- `apps/voss-app/src/App.tsx` owns global app state today: `activeLayout`,
  `project`, `projectLessAccepted`, `recents`, `projectLessCwd`, and one
  `GridController`.
- `App.tsx` renders either `SetupWindow` or one `GridRoot`.
- A8 D-01 requires rendering one `GridRoot` per mounted workspace with CSS
  visibility toggles. That pushes `App.tsx` from single-project state into
  workspace orchestration.
- The least disruptive model is "workspace as mini-App state": each workspace
  holds project info, active layout, initial/restored session, project-less
  flag, and controller. A top-level `activeWorkspaceId` selects which mounted
  subtree is visible.

### GridRoot Hazards Under Multi-Workspace Mounting

`GridRoot.tsx` currently installs global listeners:

- `window.addEventListener('keydown', onKey)`
- `window.addEventListener('resize', onResize)`

If A8 mounts hidden `GridRoot` instances without changing this, every hidden
workspace can receive the same keydown and mutate its own tree. A8 must either:

- pass `active={workspace.id === activeWorkspaceId()}` into `GridRoot` and
  early-return from `onKey` for inactive workspaces, or
- move keyboard dispatch above `GridRoot` after A7 command registry lands.

The first option is smaller and works even if A7 remains incomplete.

### Session Persistence Hazards

A6 session lifecycle is single-workspace:

- `installStructuralSessionAutosave(ctx)` subscribes to global structural
  changes through `subscribeStructuralChange`.
- `installCloseSessionSave(ctx)` registers a Tauri close-request handler for
  one `SessionContext`.
- `saveSession(workspacePath, session)` targets `<workspace>/.voss/session.json`.
- `saveGlobalSession(session)` targets `~/.config/voss-app/global-session.json`.

A8 must not install one close-request handler per workspace. Multiple handlers
can race, block close repeatedly, or save only one workspace. Centralize close
save in `App.tsx` or a new `workspaceSessionPersist.ts` service:

1. collect snapshots from every mounted workspace controller,
2. write each project workspace to `<workspace>/.voss/session.json`,
3. write each project-less workspace to
   `~/.config/voss-app/sessions/<workspace-id>.json`,
4. update `~/.config/voss-app/workspaces.json`,
5. then allow the window to close.

Structural autosave should also be workspace-aware. The current global
`markStructuralChange` signal is not sufficient by itself because a structural
change in one active grid can wake subscribers for all hidden grids. Preferred
A8 approach: expose a per-GridRoot `onStructuralChange` callback or include a
workspace-scoped autosave callback in the mutating paths.

### Theme Engine

The theme seam already exists:

- `apps/voss-app/src/theme/applyTheme.ts` applies CSS variables to `:root`.
- `apps/voss-app/src/index.tsx` calls Tauri `get_theme_overrides` before first
  render and silently falls back to Variant B.
- `apps/voss-app/src/styles/variant-b.css` defines the token names A8 should
  keep stable: `--bg-0..3`, `--fg-0..3`, `--border`, `--border-bright`,
  `--focus`, `--focus-glow`, and semantic accents.

Recommended A8 shape:

- `apps/voss-app/src/themes/schema.ts`: TS schema/types for theme metadata,
  CSS variable map, and 16 ANSI colors.
- `apps/voss-app/src/themes/bundled/*.json`: Variant B plus the 11 locked
  popular themes.
- `apps/voss-app/src/themes/themeCatalog.ts`: list bundled themes, load custom
  workspace themes, apply previews, commit selected theme.
- `crates/voss-app-core/src/themes.rs`: Rust IO for custom theme listing,
  validation, and settings persistence.

Hot-swap is a cheap CSS variable update. The higher-risk work is making every
pane and xterm theme consume the same theme object, including ANSI colors,
without remounting terminal instances.

### Platform Effects

Current Tauri docs confirm:

- `windowEffects` requires a transparent window and is not supported on Linux.
  Linux must use a CSS opacity fallback. [CITED:
  https://v2.tauri.app/reference/config]
- Tauri v2 window effects include macOS semantic effects such as
  `underWindowBackground` and Windows 11 effects such as `tabbed`,
  `tabbedDark`, and `tabbedLight`. [CITED:
  https://v2.tauri.app/reference/javascript/api/namespacewindow]
- The JS `WebviewWindow.setEffects(effects)` API can set effects at runtime.
  [CITED: https://v2.tauri.app/reference/javascript/api/namespacewebviewwindow]

Planning implication: A8 should keep platform effects isolated behind one
small Tauri/window adapter. Do not scatter platform checks through components.
Linux acceptance should assert graceful no-op plus CSS alpha, not native blur.

### Solid Rendering

Solid docs support `<For each={...}>` list rendering and signal/store-based
reactivity. [CITED: https://docs.solidjs.com/reference/components/for]
Component tests should use `@solidjs/testing-library` render helpers. [CITED:
https://docs.solidjs.com/guides/testing]

Planning implication: workspace tabs and mounted workspace panes are ordinary
Solid keyed list rendering. The critical behavior to test is instance
preservation: switching active workspace must not recreate GridRoot or clear
pane state.

## Recommended Plan Slices

### Wave 0 - Dependency and substrate preflight

Verify A1/A3/A4/A5/A6 substrate and A7 status. If A7 artifacts are still only
plans, A8 must either stop before palette/native-menu/profile commands or
degrade those tasks into documented deferred wiring.

### Wave 1 - Theme/profile/settings substrate

Implement pure schema and IO before UI:

- theme schema and 12 bundled JSON themes,
- high-contrast overlay function,
- profile schema as full settings snapshot,
- Rust settings/theme/profile commands with atomic writes and fail-safe loads,
- tests for invalid custom themes and partial fallbacks.

### Wave 2 - Workspace state and persistence

Implement workspaces as mounted mini-App state:

- `WorkspaceRecord` metadata and color hash,
- `workspaces.json` index,
- per-workspace session path resolution,
- central all-workspace close save,
- active-only keydown routing for `GridRoot`,
- restore all workspaces on launch.

### Wave 3 - Workspace tab bar UI and shortcuts

Add `WorkspaceTabBar` between titlebar and pane area:

- tab add/picker,
- rename,
- fixed dot color palette,
- close confirmation for running panes,
- reorder,
- Ctrl+1..9 and Ctrl+Tab/Ctrl+Shift+Tab.

### Wave 4 - Appearance polish and accessibility

Add font/cursor/bell settings engine, CSS transitions, reduced-motion global
kill switch, pane chrome polish, high-contrast overlay, and visual/a11y tests.

### Wave 5 - Platform native polish and acceptance

Wire platform effects, desktop metadata/tray if supported by current app
structure, and final manual acceptance across macOS/Windows/Linux. At minimum,
macOS gets runtime verification in this development environment; Windows and
Linux need either CI/manual checklist or explicit not-run status.

## Validation Architecture

A8 needs four validation layers:

1. Pure TypeScript/Rust unit tests for schemas, color hashing, theme overlay,
   profile snapshot load/save, and workspace metadata path resolution.
2. Solid component tests for tab rendering, active workspace switching,
   focus/key isolation, rename/color/close controls, reduced-motion classes,
   and theme application.
3. Rust tests for `workspaces.json`, project-less session paths, settings and
   profile IO, fail-safe corrupt loads, and atomic writes.
4. Runtime/manual verification for platform effects, native window behavior,
   mounted hidden PTYs staying alive, and restore of three workspaces.

Critical regression tests:

- Hidden workspace does not receive split/close/layout key events.
- Switching workspace preserves GridRoot instance and pane tree.
- Quit saves all workspace sessions exactly once.
- One corrupt workspace/session/theme/profile file does not prevent app boot.
- Theme switch updates `:root` CSS vars and xterm ANSI colors without remount.
- High-contrast overlay reaches 7:1 contrast for core foreground/background
  pairs.
- `prefers-reduced-motion` disables all transitions and animations globally.

## Risks and Planning Constraints

- A8 is too broad to implement as one horizontal sweep. Plan in dependency
  waves and keep Wave 0 non-autonomous.
- A7 dependency is real for command palette/profile/theme shortcuts. If A7 is
  not complete, A8 should not pretend those commands can be wired.
- Existing A6 close-save and structural autosave are single-workspace. Treat
  multi-workspace save as a refactor, not a small extension.
- Native effects are platform-specific. The plan must encode per-platform
  fallbacks and manual verification instead of one universal assertion.
- Theme curation is product work. Tests can validate schema and contrast, but
  final quality needs visual inspection against the UI-SPEC.

