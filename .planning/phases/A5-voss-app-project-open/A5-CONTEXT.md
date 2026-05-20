# Phase A5: voss-app Project Open - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning
**Source:** Derived direct from A5-SPEC.md (per project memory `gsd-spec-then-context-direct` — SPEC was the discussion).

<domain>
## Phase Boundary

A5 turns the standalone Tauri shell + grid (A1-A4) into a project-aware app: an explicit setup window on no-project launch, an `open project` folder picker for any local directory, project metadata (name + best-effort git branch), a capped-5 recents list at `~/.config/voss-app/recents.json`, first-class project-less mode that uses `$HOME` as pane cwd, and a lazy `.voss/` rule that survives project open (no `.voss/` written until a later phase saves layout/settings).

A5 ships the **project-open seam** A4 already wired against (`save_layout`/`load_layout`/`load_default_layout` all accept `workspace_path`) and invokes `load_default_layout` on every successful project open. A5 does NOT touch existing PTYs when the project changes — running grids stay alive.

**Out of scope** (delegated by SPEC): drag-drop onto app icon, command-palette open/close-recent entries (A7), session/scrollback restore (A6), settings UI (A9), status-bar branch rendering (A10 — A5 must EXPOSE the data), tab-bar workspaces / pinned recents / workspace colors (A8), onboarding wizard (A11), `⌘O` keybinding (folder picker is the contract; binding may be added but is not the locked surface).

</domain>

<decisions>
## Implementation Decisions

Scope (WHAT) is fixed by A5-SPEC requirements 1–8 and roadmap WS-01..WS-07. These are HOW decisions derived from SPEC + CONCEPT §10 Q5 (project-less first-class) + Q7 (`.voss/` lazy creation).

### Project state shape & ownership
- **D-01:** Project state is a single Solid signal owned by `App.tsx`, parallel to the existing `activeLayout` signal. Shape: `Project = { path: string; name: string; gitBranch: string | null }` for an open project, or `null` for project-less. Replaces the A1 hardcoded `Voss ADE` titlebar text once a project opens.
- **D-02:** `App.tsx` lifts a small `ProjectStore` (signal + setters) — not a separate module, just a closure — so the titlebar, GridRoot fallback cwds, and the A4 layout-save closures all read from one source. Same ownership pattern A4-02 introduced for `activeLayout`.

### Setup window vs. live app
- **D-03:** Setup window is a conditional top-level branch inside `App.tsx`: when `project === null AND projectLessAccepted === false`, render `<SetupWindow />` in the body slot INSTEAD of `<GridRoot />`. Once the user clicks "Open project" (and a folder is selected) OR "Start without project", `projectLessAccepted` flips to true and the grid mounts. Titlebar always renders.
- **D-04:** `projectLessAccepted` is intentionally session-only — not persisted. Quitting in project-less mode and relaunching shows the setup window again, matching SPEC requirement 1 ("startup with no active project shows the setup window before any required project path exists"). Persisting it is A6's session-restore concern.

### Folder picker
- **D-05:** Folder picker uses `tauri-plugin-dialog` (`open({ directory: true, multiple: false })`) — first-party Tauri 2 plugin; no shell-out to native dialogs. Add to `apps/voss-app/src-tauri/Cargo.toml` and register on the plugin builder alongside `tauri_plugin_os`.
- **D-06:** Folder selection flows through ONE Rust command (`open_project(path: String) -> ProjectInfo`) that resolves the canonical absolute path, derives `name` from the basename, reads the git branch best-effort, updates the in-process recents list, persists `recents.json`, and returns the `ProjectInfo` to the frontend. Re-opening the same path is a no-op success (returns the same `ProjectInfo`, recents-list dedup keeps the entry at index 0).
- **D-07:** Project open is filesystem read-only with respect to `.voss/` (SPEC requirement 6 / CONCEPT Q7). The `open_project` command MUST NOT touch `<workspace>/.voss/` at any point; lazy creation stays inside A4's `save_layout` and any future settings writer.

### Git branch detection
- **D-08:** Branch read via the `git2` crate (workspace dep) — not by shelling out. Open the repo with `git2::Repository::discover(path)`; on success read `HEAD` and resolve to a branch name (`shorthand()`); on any error return `None`. Non-git directories, detached HEADs, and bare repos all surface as `gitBranch = null`. No global gitconfig writes.

### Recents storage
- **D-09:** Recents persisted at `~/.config/voss-app/recents.json` (parallel to A1's `settings.json`; matches CONCEPT §10 D-08/D-09's user-facing-config path lock). Schema: `{ version: 1, recents: string[] }` where `recents` is at most 5 absolute paths, newest first, deduplicated by exact string equality (after canonicalization in D-06). Bump `version` on any schema change.
- **D-10:** Recents writes are best-effort and atomic-ish: write to `recents.json.tmp` then rename; failures are logged to stderr but never bubble to the UI (recents is a convenience, not a contract). Read failures (missing or corrupt file) silently return an empty list.

### Project-less mode + default cwd
- **D-11:** Project-less default cwd resolves to `dirs::home_dir()` Rust-side. The frontend never assembles the path. A new `default_cwd()` Tauri command returns the active project path (when `project !== null`) or the home dir (otherwise) so `splitFocused`/`forkFocused` can stop hardcoding `''`. Falls back to `'/'` if `home_dir()` returns `None` (extreme edge case — sandbox without HOME).

### A4 default-layout hook
- **D-12:** After every successful `open_project`, the frontend (NOT the Rust command) invokes `applyDefaultLayout(workspacePath)` — the A4-04 callable seam. Failures (missing default, invalid file, unsupported version) leave the project open successful — A4 already returns `Ok(None)` on those branches. The hook is intentionally frontend-side so the project-open Rust command stays pure-data.

### Existing PTY preservation
- **D-13:** Project-change reuses the running `GridRoot` and grid store as-is. No `closeFocused` cascade. Project metadata updates only affect future pane creation (D-11) and the titlebar display. SPEC requirement 8 is satisfied by NOT writing any pane-cleanup logic in A5.

### Claude's / Planner's Discretion
- Setup window visual layout (button arrangement, copy beyond "Open project" / "Start without project", recents row vs. column) — planner's call within the locked Variant B token system (A1 D-01/02).
- Whether `open_project` is one Tauri command or a small cluster (e.g. separate `pick_folder` for the dialog and `open_project` for the canonicalization + recents update) — planner's call. The acceptance contract is end-to-end, not per-command.
- Drag-drop folder onto app icon (roadmap WS-01 second clause) — explicitly deferred by SPEC; planner may stub the OS file-association entrypoint as a TODO but does not need to ship it.
- `⌘O` accelerator binding — planner may add it on top of the folder-picker contract; the SPEC contract is the picker itself.
- `dirs` crate version pin — workspace dep already exists; planner reuses unless a version bump is needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & cross-A constraints
- `.planning/phases/A5-voss-app-project-open/A5-SPEC.md` — 8 locked requirements + acceptance criteria + boundaries. Ambiguity 0.15 (gate ≤0.20).
- `.planning/ROADMAP.md` Phase A5 — WS-01..WS-07. Note SPEC narrowed recents from 10 to 5 and dropped drag-drop; SPEC takes precedence.

### Product concept (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §10 Q5 — **project-less is first-class**, panes inherit `$HOME`. Q7 — **`.voss/` lazy**, project open alone touches no files.
- `apps/voss-app/CONCEPT.md` §10 Q1 — `Voss ADE` titlebar branding stays as the **fallback** when no project is open; project name replaces it when a project opens.

### Prior-phase decisions A5 builds on
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-08/D-09 (`~/.config/voss-app/settings.json` config path lock — `recents.json` lives in the same directory; Rust/Tauri owns persisted IO).
- `.planning/phases/A4-voss-app-layout-presets/A4-04-PLAN.md` — `saveLayout`/`loadLayout`/`loadDefaultLayout` all accept `workspacePath`. The A4 callable seam in `apps/voss-app/src/App.tsx` (`saveCurrentLayout`, `loadLayoutByName`, `applyDefaultLayout`) is the integration target.
- `crates/voss-app-core/src/layouts.rs` D-09 — `load_default_layout` returns `Ok(None)` for missing/corrupt/unsupported files. A5's hook can call it unconditionally.

### Source code (A5 substrate)
- `apps/voss-app/src/App.tsx` — current composition root with `activeLayout` signal + GridController seam. A5 adds `project` signal + setup branch + project-open closure.
- `apps/voss-app/src/components/titlebar/Titlebar.tsx` — hardcoded `Voss ADE` text. A5 wires `project.name` (fallback `Voss ADE`).
- `apps/voss-app/src-tauri/src/lib.rs` — `settings_path()` pattern at `~/.config/voss-app/settings.json`; `tauri::generate_handler!` registry. A5 adds the dialog plugin + project commands + `default_cwd` command.
- `crates/voss-app-core/src/pty.rs` — `spawn_session(rows, cols, cwd: Option<String>)`. A5 ensures the cwd that ends up here is the resolved D-11 value.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/voss-app/src-tauri/src/lib.rs::settings_path` — same shape as the new `recents_path` should follow: `dirs::home_dir().join(".config").join("voss-app")`. Reuse the path-building idiom verbatim (CONCEPT D-08 lock).
- A4 layout commands (`save_layout`, `load_default_layout`) — accept `workspace_path` already. A5's project-open Rust command can write a TS-side wrapper that calls them with the new resolved path.
- A4-04 App.tsx closures (`saveCurrentLayout`, `loadLayoutByName`, `applyDefaultLayout`) — A5 calls `applyDefaultLayout(project.path)` on every successful open (D-12).
- `crates/voss-app-core` workspace dep `dirs` — already a workspace dep; reuse for home + config dir resolution.

### Established Patterns
- **Solid signals = UI SSOT; Rust owns persisted IO** (A1 D-09). `recents.json` reads/writes live in Rust; the frontend never touches the path.
- **Cross-crate `tauri::generate_handler!` constraint** (A2-05, A4-03 pattern) — app-level `#[tauri::command]` wrappers in `apps/voss-app/src-tauri/src/lib.rs` delegate to plain helpers in `voss-app-core`. New project-open helpers go in `voss-app-core` (new module `project.rs`); thin app wrappers register them.
- **Errors as user-facing strings** (A4-03 `LayoutError::Display`) — `ProjectError` Display strings match any A5-UI-SPEC copy verbatim so the renderer can pass them through.
- **Lazy creation** — A4's `save_layout` creates `.voss/layouts/` only on write. A5 inherits the rule globally for project open.

### Integration Points
- `App.tsx` — owns the `project` signal; conditionally renders `<SetupWindow />` vs `<GridRoot />`; calls `applyDefaultLayout(project.path)` on successful open.
- `Titlebar.tsx` — accepts `projectName` prop (defaults to `Voss ADE`) so it stays usable in pre-A5 tests.
- `GridRoot` / `operations.ts` — `splitFocused`/`forkFocused` need the resolved D-11 cwd. Either thread it via prop (simplest) or have a Tauri command return it on demand.
- New Rust module `crates/voss-app-core/src/project.rs` — `ProjectInfo`, `RecentsFile`, `open_project`, `list_recents`, `load_recents`, `default_cwd`, `read_git_branch`. App-level Tauri wrappers in `apps/voss-app/src-tauri/src/lib.rs` register them.
- New frontend file `apps/voss-app/src/project/projectStorage.ts` (or under `src/grid/` for proximity) — thin `invoke()` wrappers matching the A4 `layoutStorage.ts` style.
- New frontend file `apps/voss-app/src/components/setup/SetupWindow.tsx` — Variant B token-only setup surface. No shadcn, no new icons.

</code_context>

<specifics>
## Specific Ideas

- **One-shot project state change.** Opening a different project replaces the entire `project` signal value in one assignment — no partial states, no race between branch read and metadata update. The Rust `open_project` returns the full populated `ProjectInfo` (path/name/branch) in one round-trip.
- **Recents survive a corrupt file.** Read errors return an empty list silently; the next successful `open_project` writes a fresh `recents.json` over the corruption. This matches A4-03's `load_default_layout` fail-safe-by-default posture.
- **No `.voss/` ever touched on open.** The boundary is asserted by a Rust test: open a temp dir, read metadata, verify `<temp>/.voss/` does not exist. Same test pattern A4-03 used for lazy `.voss/layouts/` creation.
- **Project-less default cwd is Rust-resolved.** The frontend never builds a path string. Eliminates platform branching in JS.

</specifics>

<deferred>
## Deferred Ideas

None — A5 scope landed clean from SPEC. Adjacent capabilities are fenced to their owning phases:
- Drag-drop folder onto app icon → not required by SPEC; revisit in A11 (onboarding) or as a small follow-up.
- Command-palette "Open recent" / "Close project" → A7 (palette).
- Tab-bar workspaces / pinned recents / workspace colors → A8 (workspaces).
- Session/scrollback restore → A6 (`session.json`).
- Settings UI → A9.
- Status-bar branch display → A10 (A5 exposes the data; A10 renders it).
- L2 agent/worktree/cost semantics → post-A11.

</deferred>

---

*Phase: A5-voss-app-project-open*
*Context derived: 2026-05-19*
