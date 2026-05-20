# Phase A5: voss-app Project Open - Specification

**Created:** 2026-05-19
**Ambiguity score:** 0.15 (gate: <= 0.20)
**Requirements:** 8 locked

## Goal

voss-app can open with a setup window, select a project folder, track the last 5 project folders, expose project metadata, and still run in project-less mode without creating `.voss/` until a later write needs it.

## Background

A1-A4 made the desktop shell, PTY pane, grid engine, and layout persistence real. Today `apps/voss-app/src/App.tsx` mounts `Titlebar` and `GridRoot` directly, while `Titlebar.tsx` still hardcodes `Voss ADE` with an A5 placeholder comment. `apps/voss-app/src-tauri/src/lib.rs` already has A4 layout commands that accept a `workspace_path`, but the comment explicitly says A5 must provide the project-open seam. `crates/voss-app-core/src/layouts.rs` already preserves the lazy `.voss/layouts/` creation rule for layout writes, but no project selection, recents, project metadata, or project-less setup flow exists yet.

## Requirements

1. **Setup window on launch**: When voss-app starts without an active project, it must show a setup window instead of silently starting a project-less PTY.
   - Current: `App.tsx` immediately renders the titlebar and grid; the titlebar hardcodes `Voss ADE`.
   - Target: Startup with no project renders a setup surface with actions to select a folder or start without a project.
   - Acceptance: A frontend test can render startup state and assert that the setup surface is visible and no project path is required before interaction.

2. **Folder selection**: The user can select any local directory from their computer as the current project, including the same directory again or a different directory later.
   - Current: No frontend or Tauri project-open command exists.
   - Target: A folder picker/open-project path accepts a selected directory, stores it as the active project root, and treats repeated same-folder selection as a no-op success.
   - Acceptance: Tests cover opening a temp directory, reopening the same directory, and opening a second temp directory with the active project root updated each time.

3. **Project metadata**: Opening a project must expose folder basename as the project name and read the current git branch when the folder is a git repository.
   - Current: `Titlebar.tsx` always displays `Voss ADE`; no branch metadata is read.
   - Target: Project state includes `name`, `path`, and nullable `gitBranch`; git branch is read-only metadata for L1.
   - Acceptance: Tests cover a non-git directory returning `gitBranch = null` and a git repository returning the checked-out branch name.

4. **Project-less mode**: The user can intentionally start without a project, and project-less panes inherit the user's home directory as their cwd.
   - Current: There is no explicit project-less state; A4 comments mention falling back to home until A5 lands.
   - Target: Setup can enter project-less mode, with no active project path and a resolved home-directory cwd for pane creation and layout command fallbacks.
   - Acceptance: Tests assert project-less state has no project path, uses home as cwd, and does not write project files.

5. **Recents capped at 5**: voss-app must remember the last 5 opened project folders, newest first, deduplicated by path.
   - Current: No recent project storage exists.
   - Target: Opening a folder updates global app recents; selecting an existing recent moves it to the front; only 5 entries are retained.
   - Acceptance: Tests open 6 directories and assert the oldest is dropped; reopening an existing path moves it to index 0 without duplication.

6. **Lazy `.voss/` creation**: Opening a project or entering project-less mode must not create `.voss/`; only later actions that write project data may create it.
   - Current: A4 layout save already lazily creates `.voss/layouts/`, but no A5 project-open path exists to enforce the read-only open behavior.
   - Target: Project open, same-project reopen, recent selection, metadata read, and branch read are filesystem read-only with respect to `.voss/`.
   - Acceptance: A test opens a temp project with no `.voss/`, reads metadata and recents, and verifies `.voss/` still does not exist.

7. **A4 default layout hook**: When a project opens, A5 must invoke the existing default-layout load path so `.voss/layouts/default.json` can auto-apply without making A4 own project selection.
   - Current: `load_default_layout(workspace_path)` exists, but there is no project-open hook to call it.
   - Target: Project open attempts to load `default.json`; missing or invalid defaults do not block opening the project.
   - Acceptance: Tests cover no default layout, a valid default layout, and an invalid default layout; all three cases leave the project open successful.

8. **No pane destruction on project change**: Selecting a folder while panes already exist must not kill running PTYs as part of A5.
   - Current: Grid panes and PTY sessions exist independently of project state.
   - Target: Changing the active project updates project metadata and default cwd for future pane creation/restart, without closing existing PTY sessions.
   - Acceptance: A test with an existing pane/session changes project and asserts the existing pane identity remains present while the active project path changes.

## Boundaries

**In scope:**
- Setup window for no-project launch with select-folder and start-without-project actions.
- Folder selection/open-project flow for any local directory.
- Active project state containing path, display name, nullable git branch, and default cwd.
- Project-less mode with home-directory cwd.
- Last 5 recent project folders, newest first and deduplicated.
- Read-only git branch metadata.
- Lazy `.voss/` creation guarantee on project open.
- A4 default-layout load hook on project open.

**Out of scope:**
- Full onboarding wizard - A11 owns onboarding.
- Command palette entries for open folder/open recent - A7 owns command palette.
- Workspace tab bar, pinned favorites, workspace colors, and multiple simultaneous workspaces - A8 owns workspaces and polish.
- Session restore, scrollback restore, and `global-session.json` persistence - A6 owns session persistence.
- Settings UI and workspace settings editing - A9 owns settings.
- Status bar project/branch rendering - A10 owns status bar, though A5 must expose the data.
- Drag-drop folder onto app icon - useful later, not required for the A5 folder-picker contract.
- File tree, SCM operations, semantic project detection, and Voss harness integration - outside L1 Project Open.

## Constraints

- L1 remains zero-Voss-exposure in UI. Do not mention `.voss` to the user except in developer-facing tests/docs.
- Project open must be read-only with respect to `.voss/`; no `.voss/` directory may be created until a write action such as layout save or settings save.
- Recents are global app state, not project-local `.voss/` state.
- Git branch detection is read-only and best-effort; non-git directories are valid projects.
- Existing running PTYs must not be killed merely because project state changes.
- No new command-palette dependency is required in A5.

## Acceptance Criteria

- [ ] Startup with no active project shows the setup window before any required project path exists.
- [ ] User can select a local directory and the active project path becomes that directory.
- [ ] Re-selecting the same directory succeeds without duplicate recents.
- [ ] Selecting a different directory updates active project metadata.
- [ ] Project name is derived from folder basename.
- [ ] Git repositories expose the current branch; non-git folders expose no branch.
- [ ] Starting without a project uses home directory as default cwd and no project path.
- [ ] Recents retain only the last 5 unique project folders, newest first.
- [ ] Project open and recents reads do not create `.voss/`.
- [ ] Opening a project attempts `default.json` layout load and ignores missing/invalid defaults without blocking open.
- [ ] Changing project while panes exist does not destroy existing pane/session identities.

## Ambiguity Report

| Dimension           | Score | Min   | Status | Notes |
|---------------------|-------|-------|--------|-------|
| Goal Clarity        | 0.90  | 0.75  | PASS   | Project-open outcomes are concrete. |
| Boundary Clarity    | 0.84  | 0.70  | PASS   | A6/A7/A8/A9/A10/A11 boundaries are explicit. |
| Constraint Clarity  | 0.78  | 0.65  | PASS   | Lazy `.voss/`, project-less cwd, recents cap, and no PTY kill are locked. |
| Acceptance Criteria | 0.86  | 0.70  | PASS   | Criteria are pass/fail and testable. |
| **Ambiguity**       | 0.15  | <=0.20 | PASS  | Gate passed after round 1. |

Status: PASS = met minimum; WARN = below minimum, planner treats as assumption.

## Interview Log

| Round | Perspective | Question summary | Decision locked |
|-------|-------------|------------------|-----------------|
| 1 | Researcher | What should no-project startup do? | Immediately show the setup window; do not silently start a project-less shell first. |
| 1 | Researcher | What happens when the user opens a folder? | User selects any directory from their computer; same or different directories are valid selections. |
| 1 | Simplifier | What is the minimum recents scope? | Keep the last 5 recent folders; pinned favorites and richer recents are out of A5. |

---

*Phase: A5-voss-app-project-open*
*Spec created: 2026-05-19*
*Next step: /gsd:discuss-phase A5 - implementation decisions only*
