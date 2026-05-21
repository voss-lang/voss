---
phase: A8-voss-app-workspaces-ux-polish-theming
plan: 02
type: execute
wave: 2
depends_on: [A8-00, A8-01]
files_modified:
  - crates/voss-app-core/src/workspaces.rs
  - crates/voss-app-core/src/session.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src/workspaces/workspaceStorage.ts
  - apps/voss-app/src/workspaces/workspaceStore.ts
  - apps/voss-app/src/workspaces/workspaceSessionPersist.ts
  - apps/voss-app/src/workspaces/__tests__/workspaceStorage.test.ts
  - apps/voss-app/src/workspaces/__tests__/workspaceStore.test.ts
  - apps/voss-app/src/workspaces/__tests__/workspaceSessionPersist.test.ts
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/grid/__tests__/GridRoot.test.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/__tests__/App.test.tsx
  - apps/voss-app/src-tauri/src/lib.rs
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-02-SUMMARY.md
autonomous: true
requirements: [UXP-01, UXP-02, UXP-06, UXP-08]
must_haves:
  truths:
    - "All workspaces stay mounted and hidden via CSS"
    - "Hidden workspace GridRoots do not receive keyboard commands"
    - "Quit save is centralized and saves all workspaces once"
    - "Project-less workspaces use ~/.config/voss-app/sessions/<id>.json"
---

<objective>
Implement workspace state, persistence, restore, and active-only grid behavior without shipping the tab UI yet.
</objective>

<context>
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-VALIDATION.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PATTERNS.md
</context>

<threat_model>
T-A8-03 Hidden workspaces mutate from global keydown. Mitigation: active-workspace gate in GridRoot or app-level routing plus regression test.
T-A8-04 Multiple close handlers race. Mitigation: one central all-workspace close handler with reentry guard and tests proving every workspace saves once.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Add Rust workspace index and project-less session paths</name>
  <files>crates/voss-app-core/src/workspaces.rs, crates/voss-app-core/src/session.rs, crates/voss-app-core/src/lib.rs, apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - crates/voss-app-core/src/session.rs - existing global/project session schema
    - crates/voss-app-core/src/project.rs - config path and recents pattern
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md - D-04
  </read_first>
  <action>
    Implement `workspaces.json` index schema with id, name, projectPath, accentColor, order, activeLayoutPreset, pinnedProfile, and session target metadata. Add project-less session helpers for `~/.config/voss-app/sessions/<id>.json`. Register thin Tauri wrappers for load/save/list workspace index and project-less workspace session save/load.
  </action>
  <verify>
    <automated>cargo test -p voss-app-core workspaces session && cargo build -p voss-app</automated>
  </verify>
  <acceptance_criteria>
    - `workspaces.json` missing/corrupt loads fail safe to a single default workspace.
    - Workspace ids are stable and safe as filenames.
    - Project sessions still resolve to `<workspace>/.voss/session.json`.
    - Project-less sessions resolve to `~/.config/voss-app/sessions/<id>.json`.
  </acceptance_criteria>
  <done>Rust storage can represent all A8 workspaces.</done>
</task>

<task type="execute">
  <name>Task 2: Add frontend workspace store and active-only GridRoot</name>
  <files>apps/voss-app/src/workspaces/workspaceStorage.ts, apps/voss-app/src/workspaces/workspaceStore.ts, apps/voss-app/src/workspaces/__tests__/workspaceStorage.test.ts, apps/voss-app/src/workspaces/__tests__/workspaceStore.test.ts, apps/voss-app/src/grid/GridRoot.tsx, apps/voss-app/src/grid/__tests__/GridRoot.test.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx - current singular state
    - apps/voss-app/src/grid/GridRoot.tsx - keydown and controller surface
    - apps/voss-app/src/grid/sessionStorage.ts - invoke wrapper style
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md - GridRoot hazard
  </read_first>
  <action>
    Create typed frontend workspace records and storage wrappers. Add an active predicate to `GridRoot` so inactive mounted grids ignore keydown but keep resize and terminal state alive. Add tests proving only the active grid responds to split/close/layout key events.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/workspaces src/grid/__tests__/GridRoot.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Workspace store supports add, activate, rename, color, reorder, close guard metadata, and pinned profile field.
    - Inactive GridRoot instances ignore keyboard commands.
    - Active GridRoot keeps existing A3/A4 behavior.
  </acceptance_criteria>
  <done>Workspace state can mount multiple safe GridRoots.</done>
</task>

<task type="execute">
  <name>Task 3: Refactor App to restore and save all mounted workspaces</name>
  <files>apps/voss-app/src/workspaces/workspaceSessionPersist.ts, apps/voss-app/src/workspaces/__tests__/workspaceSessionPersist.test.ts, apps/voss-app/src/App.tsx, apps/voss-app/src/__tests__/App.test.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/sessionPersist.ts - close save and autosave pattern
    - apps/voss-app/src/grid/sessionCommands.ts - session builder
    - apps/voss-app/src/grid/sessionStorage.ts - session bridges
    - apps/voss-app/src/project/projectStorage.ts - project open flow
  </read_first>
  <action>
    Replace singular `project`/`activeLayout`/`gridController` orchestration with mounted workspace records. Render one `GridRoot` per workspace and hide inactive workspaces via CSS. Install one all-workspace close-save handler that snapshots each controller, writes each session and the workspace index, then closes with a reentry guard. Keep project-less first launch behavior by creating/restoring a default workspace.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/workspaces src/__tests__/App.test.tsx src/grid && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - App renders multiple mounted workspace containers and hides inactive ones.
    - Switching active workspace does not remount the hidden GridRoot.
    - Close save writes all workspace sessions exactly once.
    - Existing single-workspace setup/project-less flows still work.
  </acceptance_criteria>
  <done>Workspace persistence and mounted switching exist behind minimal controls.</done>
</task>
</tasks>

<verification>
Run focused workspace/grid/App tests plus frontend build and Rust workspace/session tests.
</verification>

<success_criteria>
- UXP-01/02/06 persistence and mounted-isolation substrate works before tab chrome lands.
- UXP-08 last-workspace and close-guard data is represented for UI wiring.
</success_criteria>

