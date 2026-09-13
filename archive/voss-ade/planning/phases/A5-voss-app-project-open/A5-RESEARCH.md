# Phase A5: voss-app Project Open - Research

**Researched:** 2026-05-19
**Domain:** Tauri 2 plugin integration + native file dialogs + Rust filesystem/git probing + Solid conditional rendering
**Confidence:** HIGH (Tauri/Solid integration verified against codebase + official v2 docs; git2 / canonicalize / dirs verified against docs.rs)

## Summary

A5 grafts a project-open seam onto an A1-A4 app that already has: a working composition root (`App.tsx` owns the `activeLayout` signal + `GridController`), thin `#[tauri::command]` wrappers in `apps/voss-app/src-tauri/src/lib.rs` delegating to plain helpers in `voss-app-core`, a lazy `.voss/` rule already proven in `crates/voss-app-core/src/layouts.rs`, and a capabilities file (`apps/voss-app/src-tauri/capabilities/default.json`) that currently lists ONLY `core:*` permissions.

Three pieces of integration drift the planner must correct mid-flight:
1. **`git2` is NOT a workspace dependency** — A5-CONTEXT D-08 says "workspace dep" but `Cargo.toml` and `crates/voss-app-core/Cargo.toml` contain no `git2` line. A5 must add it.
2. **The dialog plugin is not registered** — only `tauri_plugin_os::init()` is on the builder; capabilities file has no `dialog:*` permissions; `@tauri-apps/plugin-dialog` is not in `package.json`. Three coordinated edits land together or the picker silently errors.
3. **`App.tsx` unconditionally renders `<GridRoot />`** — A5 must wrap it in a `<Show when={...}>` (Solid's established voss-app pattern — `PaneComponent.tsx` already uses `Show` four times) gated on a new `project` signal **plus** a `projectLessAccepted` signal (D-03/D-04).

**Primary recommendation:** Land the Rust scaffold first (workspace `git2` dep + `voss-app-core::project` module + `#[tauri::command]` wrappers + `tauri_plugin_dialog::init()` on the builder + `dialog:allow-open` in capabilities). Frontend wave second (typed `projectStorage.ts` invoke wrappers + `SetupWindow.tsx` + `App.tsx` conditional branch + `applyDefaultLayout(project.path)` hook). Tests run cleanly under the existing pure-unit + jsdom infra; no Playwright work (macOS-blocked, per project memory `voss-app-tauri-e2e-macos-blocked`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Native folder picker dialog | Tauri Runtime (OS shell via plugin) | Frontend Webview (invokes `open()`) | Webview cannot show native dialogs; `tauri-plugin-dialog` bridges. Frontend just calls `open({ directory: true, multiple: false })`. |
| Path canonicalization + existence check | Backend / Rust | — | `std::fs::canonicalize` is platform-specific; do it once in Rust, return canonical path to JS (D-06). Matches A1 D-09 "Solid signals = UI SSOT; Rust owns persisted IO." |
| Git branch read | Backend / Rust (via `git2`) | — | `libgit2` is a Rust dependency; reads are filesystem-bound and best-effort. JS never touches `.git/`. |
| Recents persistence (`~/.config/voss-app/recents.json`) | Backend / Rust | — | Same idiom as A1's `settings_path()`. Atomic-ish write (tmp+rename) is a Rust pattern. |
| Setup window UI / branching on no-project state | Frontend Webview (Solid) | — | Pure render branching using `<Show>`. Owns `project` + `projectLessAccepted` signals. |
| Default-cwd resolution for new panes | Backend / Rust (`dirs::home_dir`) | Frontend (passes through invoke) | D-11 forbids JS path assembly; one Tauri command returns the resolved string. |
| A4 default-layout auto-apply on open | Frontend Webview | Backend (existing `load_default_layout`) | Already wired through A4-04's `applyDefaultLayout` closure in `App.tsx`. A5 just calls it after every successful `open_project`. |
| Existing PTY preservation across project change | Frontend Webview (no-op) | — | D-13: NOT writing pane cleanup logic satisfies SPEC req 8. |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Project state = single Solid signal owned by `App.tsx` parallel to `activeLayout`. Shape: `Project = { path: string; name: string; gitBranch: string | null }` for open, or `null` for project-less. Replaces hardcoded `Voss ADE` titlebar text when project opens.
- **D-02:** `App.tsx` lifts a `ProjectStore` closure (signal + setters) — not a separate module. Titlebar, GridRoot fallback cwds, and A4 layout-save closures all read from it. Same pattern A4-02 used for `activeLayout`.
- **D-03:** Setup window = conditional top-level branch inside `App.tsx`. When `project === null AND projectLessAccepted === false`, render `<SetupWindow />` in body slot INSTEAD of `<GridRoot />`. Titlebar always renders.
- **D-04:** `projectLessAccepted` is session-only — not persisted. Quitting and relaunching in project-less mode shows setup window again. Persisting is A6's concern.
- **D-05:** Folder picker uses `tauri-plugin-dialog` (`open({ directory: true, multiple: false })`). Add to `apps/voss-app/src-tauri/Cargo.toml`; register on plugin builder alongside `tauri_plugin_os`.
- **D-06:** Folder selection flows through ONE Rust command `open_project(path: String) -> ProjectInfo` that canonicalizes, derives basename name, reads git branch best-effort, updates recents, persists `recents.json`, returns `ProjectInfo`. Re-opening same path = no-op success.
- **D-07:** Project open is filesystem read-only w.r.t. `.voss/`. `open_project` MUST NOT touch `<workspace>/.voss/`.
- **D-08:** Branch read via `git2`. `Repository::discover(path)` → `head()` → `shorthand()`. Any error → `None`. Non-git, detached HEAD, bare repos all surface as `gitBranch = null`.
- **D-09:** Recents at `~/.config/voss-app/recents.json`. Schema: `{ version: 1, recents: string[] }`. Max 5 absolute paths, newest first, dedup by exact string equality (after canonicalization).
- **D-10:** Recents writes best-effort atomic-ish: tmp+rename. Failures → stderr log, never bubble to UI. Read failures (missing/corrupt) → silent empty list.
- **D-11:** Project-less default cwd = `dirs::home_dir()` Rust-side. New `default_cwd()` Tauri command. Fallback `/` if `home_dir()` returns `None`.
- **D-12:** After successful `open_project`, **frontend** invokes `applyDefaultLayout(workspacePath)` (the A4-04 callable seam). Failures leave project open successful.
- **D-13:** Project-change reuses running `GridRoot` + grid store as-is. No `closeFocused` cascade. SPEC req 8 satisfied by NOT writing pane-cleanup logic.

### Claude's Discretion

- Setup window visual layout (button arrangement, copy beyond "Open project" / "Start without project", recents row vs. column).
- Whether `open_project` is ONE Tauri command or a small cluster (e.g. separate `pick_folder` + `open_project`). Acceptance contract is end-to-end.
- Drag-drop folder onto app icon — deferred; planner may stub TODO.
- `⌘O` accelerator binding — planner may add it; SPEC contract is the picker itself.
- `dirs` crate version pin — workspace dep already exists; reuse.

### Deferred Ideas (OUT OF SCOPE)

- Drag-drop folder onto app icon → not required.
- Command-palette "Open recent" / "Close project" → A7 (palette).
- Tab-bar workspaces / pinned recents / workspace colors → A8.
- Session/scrollback restore → A6 (`session.json`).
- Settings UI → A9.
- Status-bar branch display → A10 (A5 EXPOSES the data; A10 renders).
- L2 agent/worktree/cost semantics → post-A11.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| Req-1 | Setup window on launch when no active project | Solid `<Show>` pattern documented + already used in `PaneComponent.tsx`; conditional top-level branch in `App.tsx` (D-03) is straightforward additive change. |
| Req-2 | Folder selection (any local directory, repeated same dir = no-op) | `tauri-plugin-dialog` `open({ directory: true, multiple: false })` → `Promise<string \| null>`; Rust canonicalization via `std::fs::canonicalize`; dedup in recents handler (D-06/D-09). |
| Req-3 | Project metadata (basename + git branch) | `Path::file_name()` for basename; `git2::Repository::discover` → `head()` → `shorthand()` for branch (D-08). Best-effort: any error returns `None`. |
| Req-4 | Project-less mode + home-dir cwd | `dirs::home_dir() -> Option<PathBuf>`; new `default_cwd` Tauri command (D-11). |
| Req-5 | Recents capped at 5, newest first, deduplicated | Rust struct `RecentsFile { version: 1, recents: Vec<String> }` + helper that prepends + dedups + truncates to 5; persisted at `~/.config/voss-app/recents.json`. |
| Req-6 | Lazy `.voss/` creation | `open_project` Rust command performs ZERO writes to `<workspace>/.voss/`. Test pattern from `layouts.rs` (`save_lazily_creates_voss_layouts_only_on_first_write`) is the model. |
| Req-7 | A4 default-layout hook | Frontend calls `applyDefaultLayout(project.path)` (already exists in `App.tsx`, callable seam wired by A4-04). A4-03's `load_default_layout` already returns `Ok(None)` on all failure modes. |
| Req-8 | No pane destruction on project change | Pure non-action: don't call `closeFocused` or remount `GridRoot`. Test asserts pane id persistence across `setProject(...)` calls. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tauri-plugin-dialog` (Rust) | `2` (latest stable 2.4.2) | Native folder picker | [VERIFIED: crates.io] First-party Tauri 2 plugin; only supported way to show native dialogs from webview. |
| `@tauri-apps/plugin-dialog` (npm) | `^2` (slopcheck-resolved `^2.7.1` on 2026-05-19) | JS bindings for the plugin | [VERIFIED: npm + slopcheck OK] Must version-match the Rust crate's IPC surface. |
| `git2` (Rust) | `^0.20` (latest 0.20.4) | Read git branch from `<project>/.git/HEAD` | [VERIFIED: crates.io] Rust binding to `libgit2`; no shell-out to `git`. |
| `dirs` (Rust, workspace dep) | `5` (already pinned) | `home_dir()` + `~/.config/voss-app/` path | [VERIFIED: codebase] A1 already uses this for `settings_path()`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `serde` / `serde_json` (workspace) | already pinned | `ProjectInfo` and `RecentsFile` serde | Same idiom as `LayoutFile` in `layouts.rs`. |
| `thiserror` (workspace `1`) | already pinned | Typed `ProjectError` Display strings | Match `LayoutError` pattern in `layouts.rs`. |
| `tempfile` (workspace `3`, dev-only) | already pinned | `tempdir()` for Rust unit tests | Used in `layouts.rs` tests; reuse verbatim. |
| Solid `<Show>` | from `solid-js` 1.9.13 (pinned) | `App.tsx` conditional branch | Pattern already established in `PaneComponent.tsx`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `git2` | Shell-out to `git symbolic-ref --short HEAD` | Shell-out adds latency + cross-platform path concerns; CONTEXT D-08 locked `git2`. |
| `git2` | `gitoxide` (`gix`) crate | Pure-Rust, no libgit2 C dep; not yet workspace-known here, larger compile footprint. Skip for A5. |
| `tempfile::NamedTempFile::persist` | Hand-rolled `write tmp; rename` | NamedTempFile gives same-FS guarantee + cross-platform `persist`; hand-rolled is fine for D-10 (best-effort, not crash-durable). Either works. |
| Plain string equality dedup | Path-canonicalized dedup | Canonicalization already happens in `open_project` (D-06); string equality after canonicalization is sufficient. |

**Installation (cumulative diff plan):**
```toml
# apps/voss-app/src-tauri/Cargo.toml — append to [dependencies]
tauri-plugin-dialog = "2"
git2 = { version = "0.20", default-features = false, features = ["vendored-libgit2"] }
```

Note: `default-features = false` + `vendored-libgit2` removes the optional `https` / `ssh` features (uses bundled C `libgit2` source; no `OpenSSL`/`libssh2` system links). Branch-read uses only filesystem + zlib; this minimizes the link surface and keeps `cargo build` self-contained.

```jsonc
// apps/voss-app/package.json — append to dependencies
"@tauri-apps/plugin-dialog": "^2"
```

**Version verification (2026-05-19):**
- `tauri-plugin-dialog` 2.4.2 latest on crates.io [CITED: crates.io listing], compatible with `tauri = "2"` (≥2.11.2 in app + ≥2.x in core); minimum Rust 1.77.2 ≤ workspace `1.75` floor — **planner must verify rust-toolchain**; if floor is 1.75 the workspace MSRV needs bump or `tauri-plugin-dialog` pinned to a version compatible with 1.75 (likely an earlier 2.0.x). See Open Questions Q1.
- `@tauri-apps/plugin-dialog` ^2.7.1 (slopcheck-resolved on 2026-05-19).
- `git2` 0.20.4 latest on crates.io [CITED: crates.io listing].
- `dirs` already at workspace pin `5`.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `tauri-plugin-dialog` | crates.io | mature (Tauri 2 plugin family, v2 since 2024-10) | first-party Tauri | github.com/tauri-apps/plugins-workspace | [OK] | Approved |
| `@tauri-apps/plugin-dialog` | npm | mature (first-party) | first-party Tauri | github.com/tauri-apps/plugins-workspace | [OK] | Approved |
| `git2` | crates.io | mature (8+ yrs, 0.20.x current) | high (rust-lang org) | github.com/rust-lang/git2-rs | [OK] | Approved |
| `dirs` | crates.io | already in workspace (`5`) | — | — | [pre-existing] | Already approved (A1) |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

slopcheck run on 2026-05-19 against crates.io and npm registries — all 3 new packages returned `[OK]`. (slopcheck attempted `cargo add` and `npm install` as side effects; both were reverted from the working tree before this RESEARCH.md was written.)

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── voss-app (Tauri 2 webview) ────────────────────────────┐
│                                                                                   │
│  [App.tsx — composition root]                                                     │
│     project: Signal<Project|null>     projectLessAccepted: Signal<boolean>        │
│                                                                                   │
│     ┌───────────────┐                                                             │
│     │   Titlebar    │  ← project()?.name ?? "Voss ADE"                            │
│     └───────────────┘                                                             │
│                                                                                   │
│     <Show when={project()!==null || projectLessAccepted()}                        │
│           fallback={<SetupWindow onPick={…} onSkip={…} recents={…} />}>           │
│         <GridRoot … />                                                            │
│     </Show>                                                                       │
│                              │                                                    │
│                              │ pick "Open project" ─────────────────┐             │
│                              │                                      │             │
│                              ▼                                      ▼             │
│             projectStorage.ts (thin invoke wrappers)        loadDefaultLayout     │
│                              │                                      │             │
└──────────────────────────────┼──────────────────────────────────────┼─────────────┘
                               │ Tauri IPC                            │
┌──────────────────────────────┼──────────────────────────────────────┼─────────────┐
│  apps/voss-app/src-tauri/src/lib.rs  (thin #[tauri::command] wrappers)            │
│                              │                                      │             │
│   pick_project_folder()  ────┼──→  tauri-plugin-dialog::open()  (native dialog)   │
│   open_project(path)     ────┤                                                    │
│   list_recents()         ────┤                                                    │
│   default_cwd()          ────┤                                                    │
│                              ▼                                                    │
│  crates/voss-app-core/src/project.rs (new module)                                 │
│     fn open_project(path: &Path) -> Result<ProjectInfo, ProjectError>             │
│        1. canonicalize ──→ std::fs::canonicalize                                  │
│        2. basename     ──→ Path::file_name                                        │
│        3. git branch   ──→ git2::Repository::discover → head → shorthand          │
│        4. recents      ──→ load_recents() + prepend+dedup+truncate                │
│        5. persist      ──→ save_recents() at ~/.config/voss-app/recents.json      │
│        ── NEVER touches <workspace>/.voss/ (Req-6) ──                             │
│                                                                                   │
│     fn default_cwd(project_path: Option<&Path>) -> String                         │
│        project_path.map(…).unwrap_or_else(|| dirs::home_dir().or("/"))            │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
apps/voss-app/
├── src-tauri/
│   ├── Cargo.toml                          # + tauri-plugin-dialog, + git2 (vendored)
│   ├── capabilities/default.json           # + "dialog:allow-open"
│   └── src/lib.rs                          # + plugin init, + project commands
├── src/
│   ├── App.tsx                             # + project signal, + <Show> branch
│   ├── components/
│   │   ├── titlebar/Titlebar.tsx           # + projectName prop (default "Voss ADE")
│   │   └── setup/SetupWindow.tsx           # NEW — Variant B token-only setup surface
│   └── project/
│       └── projectStorage.ts               # NEW — invoke wrappers (open_project, list_recents, default_cwd)
crates/voss-app-core/src/
├── lib.rs                                  # + pub mod project; + pub use ...
└── project.rs                              # NEW — ProjectInfo, RecentsFile, open_project, …
```

### Pattern 1: Tauri Plugin Init + Capability
**What:** Plugins must be both initialized on the builder AND have their permissions whitelisted in the capability file. Forgetting either causes silent runtime denials.
**When to use:** Every external Tauri 2 plugin.
**Example (existing voss-app + dialog addition):**
```rust
// apps/voss-app/src-tauri/src/lib.rs (around line 200)
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_dialog::init())   // ← A5 adds this line
        .manage(Arc::new(PtyRegistry::default()))
        .manage(Mutex::new(GridState::default()))
        .invoke_handler(tauri::generate_handler![
            // … existing …
            open_project,
            list_recents,
            default_cwd,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```
```jsonc
// apps/voss-app/src-tauri/capabilities/default.json
{
  "identifier": "main-capability",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "core:window:allow-close",
    "core:window:allow-minimize",
    "core:window:allow-toggle-maximize",
    "core:window:allow-set-fullscreen",
    "core:window:allow-is-fullscreen",
    "core:window:allow-start-dragging",
    "dialog:allow-open"          // ← A5 adds this line (sufficient for open() only)
  ]
}
```
[CITED: v2.tauri.app/plugin/dialog/] Permissions enabled by `dialog:default` are `allow-message`, `allow-save`, `allow-open`. Since A5 needs *only* `open()`, the minimal addition is `dialog:allow-open` — adding the smaller permission keeps the surface tight. If the planner prefers, `dialog:default` is also valid and equivalent for `open()`.

### Pattern 2: Cross-Crate `#[tauri::command]` Wrappers
**What:** App-level wrappers in `apps/voss-app/src-tauri/src/lib.rs` delegate to plain helpers in `voss-app-core`. The core crate's `#[tauri::command]` macros are not in scope here (per the comment at `lib.rs:60` and A2-05 / A4-03 pattern).
**Why:** `tauri::generate_handler!` can only resolve hidden command helper macros generated in the SAME crate.
**Example:**
```rust
// apps/voss-app/src-tauri/src/lib.rs
use voss_app_core::project::{self, ProjectInfo};

#[tauri::command]
fn open_project(path: String) -> Result<ProjectInfo, String> {
    project::open_project(std::path::Path::new(&path)).map_err(|e| e.to_string())
}

#[tauri::command]
fn list_recents() -> Vec<String> {
    project::list_recents()
}

#[tauri::command]
fn default_cwd(project_path: Option<String>) -> String {
    project::default_cwd(project_path.as_deref().map(std::path::Path::new))
}
```

### Pattern 3: Lazy-`.voss/` Discipline
**What:** Open/read paths NEVER call `std::fs::create_dir_all` on `<workspace>/.voss/`. Only write paths do.
**Why:** SPEC Req-6 + CONCEPT §10 Q7 + the test pattern A4-03 already shipped (`save_lazily_creates_voss_layouts_only_on_first_write` in `layouts.rs`).
**Example (test that must pass):**
```rust
#[test]
fn open_project_does_not_create_voss_directory() {
    let dir = tempfile::tempdir().unwrap();
    let voss = dir.path().join(".voss");
    assert!(!voss.exists());
    let _info = project::open_project(dir.path()).unwrap();
    assert!(!voss.exists(), ".voss must NOT exist after read-only open");
}
```

### Pattern 4: Solid Conditional Branch via `<Show>`
**What:** Use `<Show when={…} fallback={…}>` rather than a ternary for large conditional blocks. Already used in `PaneComponent.tsx` four times — established voss-app idiom.
**Example:**
```tsx
// apps/voss-app/src/App.tsx (replace lines 100-110)
import { createSignal, Show } from 'solid-js';

const [project, setProject] = createSignal<Project | null>(null);
const [projectLessAccepted, setProjectLessAccepted] = createSignal(false);

const showGrid = () => project() !== null || projectLessAccepted();

return (
  <div style={{ /* … existing flex column … */ }}>
    <Titlebar
      projectName={project()?.name ?? 'Voss ADE'}
      activeLayout={activeLayout()}
      onLayoutSelect={onLayoutSelect}
    />
    <Show
      when={showGrid()}
      fallback={
        <SetupWindow
          recents={recents()}
          onOpenFolder={handleOpenFolder}
          onStartWithoutProject={() => setProjectLessAccepted(true)}
          onOpenRecent={handleOpenRecent}
        />
      }
    >
      <div style={{ flex: '1', 'min-height': '0', background: 'var(--bg-0)' }}>
        <GridRoot
          activeLayout={activeLayout}
          onLayoutChange={(next) => setActiveLayout(next)}
          controllerRef={(c) => { gridController = c; }}
        />
      </div>
    </Show>
  </div>
);
```
**Note on Solid + `<Show>`:** Solid's reactivity recreates the `<GridRoot />` subtree only when `showGrid()` *flips* truthiness. Flipping from project-less (true) to project-open (true) does NOT remount — which is exactly what SPEC Req-8 / D-13 require.

### Anti-Patterns to Avoid
- **Calling `tauri-plugin-dialog::open` directly from Rust on the main thread** — A5 needs the *frontend* to invoke `open()`; the Rust command receives the already-selected path. Trying to call the dialog API from a `#[tauri::command]` blocks the runtime.
- **Path normalization in JS** — D-11 forbids it; do all path math in Rust.
- **Eagerly creating `<workspace>/.voss/`** — would silently violate Req-6.
- **Calling `git2::Repository::open` instead of `discover`** — `open` requires the path to BE the repo root; `discover` walks up. Use `discover` (D-08).
- **Resetting `gridController` on project change** — would destroy panes (D-13 violation).
- **Persisting `projectLessAccepted` to `~/.config/voss-app/`** — D-04 locks it as session-only.
- **Threading `workspacePath` through `splitFocused`/`forkFocused` signatures** — D-11 says use a Tauri command (`default_cwd`) instead; keep grid ops pure.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Native folder dialog | Shell-out to `osascript`/`zenity`/PowerShell | `tauri-plugin-dialog` | Cross-platform; first-party; permission-gated. |
| Path canonicalization | Custom `..` stripper | `std::fs::canonicalize` | Resolves symlinks correctly; one platform-specific edge case (`/tmp` → `/private/tmp` on macOS — documented and consistent). |
| Home directory resolution | `std::env::var("HOME")` | `dirs::home_dir()` | Falls back to `getpwuid_r` when `$HOME` is unset; handles Windows `SHGetKnownFolderPath`. |
| Git branch read | Shell-out to `git symbolic-ref --short HEAD` or parsing `.git/HEAD` | `git2::Repository::discover + head + shorthand` | Handles detached HEAD, worktrees, packed refs, bare repos uniformly. |
| Atomic file write | Hand-rolled `write tmp; rename` (still fine — D-10 says best-effort) | `tempfile::NamedTempFile::persist` (optional) | Either works; NamedTempFile gives same-FS guarantee. D-10 explicitly says failures don't bubble, so hand-rolled `write_then_rename` is acceptable. |

**Key insight:** Every one of these has a well-tested library. The lazy `.voss/` rule is the only thing A5 owns end-to-end; the rest is integration glue.

## Runtime State Inventory

> A5 is greenfield with respect to runtime state — no rename, no migration. Included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `recents.json` is being created fresh; not migrating from any prior format. | None. |
| Live service config | None — Tauri capabilities config is repo-tracked; no external service. | None. |
| OS-registered state | None — no task scheduler / launchd / pm2 entry for voss-app at this phase. | None. |
| Secrets/env vars | None — no API keys or tokens read by A5 code paths. (Note: `HOME` env var IS read by `dirs::home_dir`, but that's runtime-resolved, not stored.) | None. |
| Build artifacts | `target/` already excluded by gitignore. New `git2` C dep (libgit2 vendored) extends initial `cargo build` time on a clean checkout. | Document in PR / CONTRIBUTING. |

**Nothing found in category:** All five — confirmed by grep `git log --diff-filter=A` style review of A1-A4 phase outputs. A5 introduces only new state, no rename of existing state.

## Common Pitfalls

### Pitfall 1: Forgetting to register the dialog plugin
**What goes wrong:** `invoke('plugin:dialog|open', …)` returns "command not allowed" or "plugin not registered."
**Why it happens:** The plugin requires THREE coordinated edits — `Cargo.toml`, `lib.rs` builder chain, and capabilities permissions. Missing any silently breaks runtime.
**How to avoid:** Land all three in one wave; add a smoke test that calls `open()` mocked via `vi.mock('@tauri-apps/plugin-dialog')` to confirm wiring shape.
**Warning signs:** `dialog.allow_open: not allowed` errors at runtime; webview console shows the IPC denial.

### Pitfall 2: `canonicalize` rejects non-existent paths
**What goes wrong:** `std::fs::canonicalize("/nonexistent")` returns an `io::Error`, not a path. If a user types a stale recent that no longer exists, `open_project` crashes.
**Why it happens:** `canonicalize` requires the path to exist on disk (verified at docs.rust-lang.org/std/fs/fn.canonicalize.html).
**How to avoid:** Treat a `canonicalize` error as a user-facing "project no longer exists" → return `ProjectError::NotFound`, prune from recents, surface to UI. Don't try to "fix" the path.
**Warning signs:** Test case: open a temp dir, drop it from disk, then attempt to re-open via recents list.

### Pitfall 3: `git2::Repository::discover` walks past the workspace
**What goes wrong:** If a user opens a directory deep inside a parent git repo, `discover` walks UP until it finds `.git`. The branch returned is the parent repo's branch, not the project's. Confusing UX.
**Why it happens:** `discover` is documented as "looks up the filesystem hierarchy until it finds a repository" — that's a feature, not a bug, for nested checkouts.
**How to avoid:** Document the behavior; SPEC Req-3 says "when the folder is a git repository" — interpreting "is" as "is contained in" matches `discover`'s contract and is what users mean 95% of the time. If stricter scoping is needed, gate on `repo.workdir() == Some(project_path)`. Recommendation: ship `discover` semantics; revisit if users complain.
**Warning signs:** Branch shows in titlebar for a non-repo subfolder of a repo. Note this in test cases.

### Pitfall 4: `home_dir()` returns `None` in sandboxed contexts
**What goes wrong:** CI containers / Tauri sandbox tests with no `HOME` env → `default_cwd()` returns `None` → frontend gets `""` and panes spawn in the binary's cwd.
**Why it happens:** [VERIFIED: docs.rs/dirs] `home_dir()` returns `None` when `$HOME` is empty AND `getpwuid_r` has no entry.
**How to avoid:** D-11 already locks the fallback: `"/"`. Encode it in the helper.
**Warning signs:** Test the explicit `None` branch with a mock or by overriding the env var.

### Pitfall 5: Tauri snake_case → camelCase parameter mapping silently fails
**What goes wrong:** A param named `projectPath` in JS won't bind to Rust `project_path` if the wrapper's serde rename is wrong (or `workspacePath` is sent as `workspace_path`).
**Why it happens:** Tauri auto-converts; mismatched casing → silent `null`/default values.
**How to avoid:** Mirror the A4-04 `layoutStorage.ts` style verbatim. JS sends camelCase keys; Rust receives snake_case params; Tauri bridges.
**Warning signs:** Rust receives default values; commands look like they "ran" but did nothing.

### Pitfall 6: macOS `/tmp` symlink resolves
**What goes wrong:** Tests using `tempfile::tempdir()` on macOS get paths under `/var/folders/…`; canonicalize might re-resolve via `/private/var/…`. Recents dedup uses string equality — same dir opened twice might appear as two different strings if one canonicalization happens at a different time.
**Why it happens:** `/var` on macOS is a symlink to `/private/var`.
**How to avoid:** ALWAYS canonicalize as the very first step in `open_project` (D-06). Compare AFTER canonicalization.
**Warning signs:** Recents grows past unique-path count when a test reopens the same dir.

### Pitfall 7: `tauri-plugin-dialog` MSRV vs workspace MSRV
**What goes wrong:** `tauri-plugin-dialog` 2.x requires Rust ≥ 1.77.2; workspace `rust-version` is `1.75`. Build may fail or warn.
**Why it happens:** Plugin tightened MSRV at some point in the 2.x series.
**How to avoid:** Bump workspace `rust-version` to `1.77.2` in `Cargo.toml`, OR pin `tauri-plugin-dialog` to a 2.0.x version compatible with 1.75. Verify in Wave 0 with `cargo build`.
**Warning signs:** `cargo build` reports MSRV violation. See Open Question Q1.

## Code Examples

Verified patterns from official sources + repo-local conventions:

### Folder picker (frontend)
```ts
// apps/voss-app/src/project/projectStorage.ts
import { invoke } from '@tauri-apps/api/core';
import { open as openDialog } from '@tauri-apps/plugin-dialog';

export type ProjectInfo = {
  path: string;        // canonical absolute path
  name: string;        // basename
  gitBranch: string | null;
};

/** Show the native folder picker. Returns the canonical project path, or null on cancel. */
export async function pickFolder(): Promise<string | null> {
  // open() returns Promise<string | null> when directory:true + multiple:false.
  // [CITED: v2.tauri.app/reference/javascript/dialog]
  const result = await openDialog({ directory: true, multiple: false });
  return typeof result === 'string' ? result : null;
}

export async function openProject(path: string): Promise<ProjectInfo> {
  return invoke<ProjectInfo>('open_project', { path });
}

export async function listRecents(): Promise<string[]> {
  return invoke<string[]>('list_recents');
}

export async function defaultCwd(projectPath: string | null): Promise<string> {
  return invoke<string>('default_cwd', { projectPath });
}
```

### Open-project handler (frontend)
```ts
// apps/voss-app/src/App.tsx — inside App() body
const handleOpenFolder = async () => {
  const picked = await pickFolder();
  if (!picked) return;                  // user cancelled
  try {
    const info = await openProject(picked);
    setProject(info);
    setProjectLessAccepted(true);       // open implies "no longer setup mode"
    // D-12: hook A4 default layout — failures non-blocking
    await applyDefaultLayout(info.path).catch((e) => {
      console.warn('default layout skipped:', e);
    });
  } catch (e) {
    console.error('open_project failed:', e);
    // Future: surface to UI via a toast. A5 SPEC is silent on the error UI;
    // log-only is acceptable for L1.
  }
};
```

### `open_project` Rust core (verified API shapes)
```rust
// crates/voss-app-core/src/project.rs
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectInfo {
    pub path: String,
    pub name: String,
    pub git_branch: Option<String>,
}

#[derive(Debug, thiserror::Error)]
pub enum ProjectError {
    #[error("project path does not exist")]
    NotFound,
    #[error("project path is not a directory")]
    NotADirectory,
    #[error("could not resolve project path")]
    InvalidPath,
}

pub fn open_project(path: &Path) -> Result<ProjectInfo, ProjectError> {
    // 1. Canonicalize. Errors on non-existent paths (intentional: stale recents
    //    must be surfaced as NotFound so the UI can prune them).
    let canonical = std::fs::canonicalize(path).map_err(|e| {
        eprintln!("[voss-app] open_project canonicalize: {e}");
        ProjectError::NotFound
    })?;
    if !canonical.is_dir() {
        return Err(ProjectError::NotADirectory);
    }
    // 2. Derive basename. Reject paths with no file_name (root /).
    let name = canonical
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or(ProjectError::InvalidPath)?
        .to_string();
    // 3. Best-effort git branch.
    let git_branch = read_git_branch(&canonical);
    // 4. Recents update (best-effort; logs on failure, never errors).
    update_recents(&canonical);
    Ok(ProjectInfo {
        path: canonical.to_string_lossy().into_owned(),
        name,
        git_branch,
    })
}

fn read_git_branch(path: &Path) -> Option<String> {
    // git2::Repository::discover walks up the filesystem to find `.git/`.
    // [CITED: docs.rs/git2 — Repository::discover signature]
    let repo = git2::Repository::discover(path).ok()?;
    let head = repo.head().ok()?;                       // None on unborn HEAD
    head.shorthand().map(|s| s.to_string())             // Option<&str> → Option<String>
}

pub fn default_cwd(project_path: Option<&Path>) -> String {
    if let Some(p) = project_path {
        return p.to_string_lossy().into_owned();
    }
    dirs::home_dir()
        .map(|h| h.to_string_lossy().into_owned())
        .unwrap_or_else(|| "/".to_string())             // D-11 fallback
}
```

### Recents storage (atomic-ish, best-effort)
```rust
// crates/voss-app-core/src/project.rs (continued)
const RECENTS_VERSION: u32 = 1;
const RECENTS_CAP: usize = 5;

#[derive(Serialize, Deserialize, Default)]
struct RecentsFile {
    version: u32,
    recents: Vec<String>,
}

fn recents_path() -> PathBuf {
    // SAME idiom as apps/voss-app/src-tauri/src/lib.rs::settings_path
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("recents.json")
}

pub fn list_recents() -> Vec<String> {
    load_recents().recents
}

fn load_recents() -> RecentsFile {
    let path = recents_path();
    if !path.exists() {
        return RecentsFile { version: RECENTS_VERSION, recents: vec![] };
    }
    match std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str::<RecentsFile>(&s).ok())
    {
        Some(f) if f.version == RECENTS_VERSION => f,
        _ => {
            eprintln!("[voss-app] recents.json missing or corrupt; using empty list");
            RecentsFile { version: RECENTS_VERSION, recents: vec![] }
        }
    }
}

fn update_recents(canonical: &Path) {
    let mut file = load_recents();
    let entry = canonical.to_string_lossy().into_owned();
    // Dedup: remove any existing occurrence, then prepend.
    file.recents.retain(|p| p != &entry);
    file.recents.insert(0, entry);
    // Cap at 5.
    file.recents.truncate(RECENTS_CAP);
    if let Err(e) = save_recents(&file) {
        eprintln!("[voss-app] recents save failed (non-fatal): {e}");
    }
}

fn save_recents(file: &RecentsFile) -> std::io::Result<()> {
    let path = recents_path();
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;          // ~/.config/voss-app is fine to create
    }
    let tmp = path.with_extension("json.tmp");
    let json = serde_json::to_string_pretty(file)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
    std::fs::write(&tmp, json)?;
    std::fs::rename(&tmp, &path)?;              // atomic on same FS
    Ok(())
}
```

### Test pattern — Rust unit (mirror `layouts.rs` exactly)
```rust
// crates/voss-app-core/src/project.rs — #[cfg(test)] mod tests
#[test]
fn open_project_returns_basename_as_name() {
    let dir = tempfile::tempdir().unwrap();
    let info = open_project(dir.path()).unwrap();
    assert_eq!(info.name, dir.path().file_name().unwrap().to_string_lossy());
}

#[test]
fn open_project_returns_none_branch_for_non_git_dir() {
    let dir = tempfile::tempdir().unwrap();
    let info = open_project(dir.path()).unwrap();
    assert!(info.git_branch.is_none());
}

#[test]
fn open_project_does_not_create_voss_directory() {
    let dir = tempfile::tempdir().unwrap();
    let voss = dir.path().join(".voss");
    let _ = open_project(dir.path()).unwrap();
    assert!(!voss.exists());
}

#[test]
fn default_cwd_falls_back_to_home_for_no_project() {
    let cwd = default_cwd(None);
    // home_dir() Some() in CI; if None (sandbox) fallback is "/"
    assert!(cwd == dirs::home_dir().map(|h| h.to_string_lossy().into_owned())
                     .unwrap_or_else(|| "/".to_string()));
}
```

### Test pattern — frontend (mirror `layoutStorage.test.ts`)
```ts
// apps/voss-app/src/project/__tests__/projectStorage.test.ts
import { describe, it, expect, vi } from 'vitest';

const h = vi.hoisted(() => ({ invoke: vi.fn(), openDialog: vi.fn() }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('@tauri-apps/plugin-dialog', () => ({ open: h.openDialog }));

import { openProject, pickFolder, defaultCwd } from '../projectStorage';

describe('projectStorage', () => {
  it('pickFolder returns null on cancel', async () => {
    h.openDialog.mockResolvedValueOnce(null);
    expect(await pickFolder()).toBeNull();
  });

  it('openProject sends camelCase path', async () => {
    h.invoke.mockResolvedValueOnce({ path: '/x', name: 'x', gitBranch: null });
    await openProject('/x');
    expect(h.invoke).toHaveBeenCalledWith('open_project', { path: '/x' });
  });

  it('defaultCwd null → invoked with projectPath:null', async () => {
    h.invoke.mockResolvedValueOnce('/home/u');
    await defaultCwd(null);
    expect(h.invoke).toHaveBeenCalledWith('default_cwd', { projectPath: null });
  });
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tauri v1 `dialog` API (`@tauri-apps/api/dialog`) | Tauri v2 first-party plugin `@tauri-apps/plugin-dialog` + `tauri-plugin-dialog` crate | Tauri 2.0 GA (2024-10) | All dialog/fs/os capabilities moved out of core into discoverable plugins; permission ACL is opt-in. Project is on Tauri 2.11.2 already. |
| `dirs-next` | `dirs` v5 | dirs-next archived 2023 | Workspace already pins `dirs = "5"`; no migration needed. |
| `git2` 0.18 (older docs you'll find on Stack Overflow) | `git2` 0.20.x | 2024-2025 | API stable; `Repository::discover` + `head().shorthand()` signatures unchanged. |

**Deprecated/outdated:**
- `dialog:allow-ask` / `dialog:allow-confirm` are marked deprecated [CITED: v2.tauri.app/plugin/dialog/]. A5 uses neither — only `dialog:allow-open`.
- Tauri v1 patterns (e.g. `tauri.conf.json` `allowlist`) are gone in v2; ignore any tutorial referencing them.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Frontend invocation of `tauri-plugin-dialog::open()` does not require any additional permission beyond `dialog:allow-open` (e.g. no `fs:allow-read` needed because the dialog plugin returns paths, not file handles). | Pattern 1, capabilities | If wrong, picker returns a path but downstream `invoke('open_project')` succeeds anyway — `fs` permissions only apply to the `fs` plugin's own commands. Low risk. [VERIFIED via doc reading; flagged as ASSUMED because no explicit acceptance test in repo yet.] |
| A2 | `git2` 0.20.4 builds on macOS arm64 with `vendored-libgit2` feature without any system C dependency. | Standard Stack | If wrong, planner adds `libgit2` to brew dependencies. Standard fallback. |
| A3 | Workspace MSRV (`1.75`) is sufficient for `tauri-plugin-dialog` 2.4.2 OR a 2.0.x version exists that supports 1.75. | Pitfall 7 / Open Question Q1 | If neither holds, planner bumps workspace `rust-version` to `1.77.2`. Cheap fix. |
| A4 | macOS `tempdir()` paths canonicalize consistently across two calls within one test run. | Pitfall 6 | If not, test will flake; refactor to a single canonicalize per assertion. |
| A5 | Solid's `<Show when={…}>` does NOT recreate child subtree when `when` flips from one truthy value to another. | Anti-Patterns / Pattern 4 | [CITED: docs.solidjs.com/concepts/control-flow/conditional-rendering] confirms truthy→truthy does not recreate. Risk: low. |

## Open Questions (RESOLVED)

> All three questions carry an inline Recommendation that A5-00 / A5-01 implement; this heading carries the `(RESOLVED)` suffix per the GSD checker Dimension 11 contract.

1. **`tauri-plugin-dialog` MSRV vs workspace MSRV**
   - What we know: workspace `rust-version = "1.75"`; latest `tauri-plugin-dialog` 2.4.2 needs ≥ 1.77.2 [CITED: docs.rs/tauri-plugin-dialog].
   - What's unclear: whether an earlier 2.x (2.0.x or 2.1.x) supports 1.75.
   - Recommendation: planner's Wave 0 runs `cargo add tauri-plugin-dialog@^2 --dry-run`; if MSRV breaks, either bump workspace MSRV (cheap — Rust 1.77 is stable for 18+ months) or pin to the highest 2.x version that compiles. Bumping MSRV is the cleaner answer; defer the decision to the planner.

2. **Recents file path on Linux/Windows**
   - What we know: D-09 locks `~/.config/voss-app/recents.json`. On macOS, that resolves to `/Users/<u>/.config/voss-app/recents.json` (A1 D-08 lock).
   - What's unclear: On Windows, `dirs::home_dir()` returns `C:\Users\<u>`, so the file becomes `C:\Users\<u>\.config\voss-app\recents.json`. Acceptable, but not XDG-standard for Windows.
   - Recommendation: ship as locked; revisit if A11 windows packaging cares. Matches A1 settings.json path exactly.

3. **`open_project` on a path inside a parent git repo**
   - What we know: `Repository::discover` walks up.
   - What's unclear: whether to scope branch read to project-root-or-tighter.
   - Recommendation: ship `discover` semantics (matches `git status` behavior); document; revisit if user feedback.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust toolchain | All Rust build/test | ✓ | 1.x (project uses workspace `1.75` floor) | — |
| `cargo` | Build | ✓ | bundled | — |
| `pnpm` | Frontend build/test | ✓ | from package.json (no explicit pin) | — |
| `node` | vitest | ✓ | — | — |
| C compiler (cc / clang) | `vendored-libgit2` build | ✓ on dev box | Xcode CLT clang on macOS | If missing: `brew install libgit2` + drop `vendored-libgit2` feature (system link). |
| Playwright | e2e — **macOS-blocked** | n/a | — | Per project memory: skip Tauri WebDriver e2e on macOS; gate on vitest + cargo test + tsc. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Playwright e2e is intentionally skipped — A5's acceptance lives in unit + integration layers per project memory `voss-app-tauri-e2e-macos-blocked`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Rust framework | `cargo test` (built-in), `tempfile = "3"` (workspace) |
| Rust config | `crates/voss-app-core/Cargo.toml` `[dev-dependencies]` already has `tempfile` |
| TS framework | Vitest 4.1.6 (already installed) |
| TS config | `apps/voss-app/vitest.config.ts` — `environment: 'jsdom'`, `include: ['src/**/__tests__/**/*.test.{ts,tsx}']` |
| Quick run (Rust) | `cargo test -p voss-app-core project::tests` |
| Quick run (TS) | `pnpm --filter voss-app test -- src/project/__tests__` |
| Full suite (Rust) | `cargo test --workspace` |
| Full suite (TS) | `pnpm --filter voss-app test` |
| Type check | `pnpm --filter voss-app exec tsc --noEmit` |
| Phase gate | Full suite green + `cargo build -p voss-app` clean |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| Req-1 | Setup window renders when project=null & !accepted | unit (jsdom) | `pnpm --filter voss-app test -- App.test.tsx` | ❌ Wave 0 |
| Req-2 | `open_project(path)` canonicalizes; same dir reopened = same result | unit (Rust) | `cargo test -p voss-app-core project::open_project_canonicalizes` | ❌ Wave 0 |
| Req-2 | Folder picker invokes `@tauri-apps/plugin-dialog::open` with directory:true | unit (jsdom) | `pnpm --filter voss-app test -- projectStorage.test.ts` | ❌ Wave 0 |
| Req-3 | Basename → name | unit (Rust) | `cargo test -p voss-app-core project::basename` | ❌ Wave 0 |
| Req-3 | Non-git → gitBranch=None | unit (Rust) | `cargo test -p voss-app-core project::no_git_means_none` | ❌ Wave 0 |
| Req-3 | git repo → gitBranch=shorthand | integration (Rust) | `cargo test -p voss-app-core project::git_init_then_branch` | ❌ Wave 0 |
| Req-4 | `default_cwd(None)` → home (or `/` fallback) | unit (Rust) | `cargo test -p voss-app-core project::default_cwd_no_project` | ❌ Wave 0 |
| Req-4 | Project-less state has path=null in App.tsx | unit (jsdom) | `pnpm --filter voss-app test -- App.test.tsx` | ❌ Wave 0 |
| Req-5 | Open 6 dirs → oldest dropped; reopen existing → moved to index 0 | unit (Rust) | `cargo test -p voss-app-core project::recents_cap_5_dedup` | ❌ Wave 0 |
| Req-6 | open_project leaves `.voss/` absent | unit (Rust) | `cargo test -p voss-app-core project::open_project_does_not_create_voss_directory` | ❌ Wave 0 |
| Req-7 | applyDefaultLayout called on successful open | unit (jsdom) | `pnpm --filter voss-app test -- App.test.tsx` | ❌ Wave 0 |
| Req-7 | applyDefaultLayout failure does not block | unit (jsdom) | (same file, additional case) | ❌ Wave 0 |
| Req-8 | Project change keeps existing pane id alive | unit (jsdom) | `pnpm --filter voss-app test -- App.test.tsx` (assert GridRoot mount survives) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cargo test -p voss-app-core project::tests` AND `pnpm --filter voss-app test -- src/project`
- **Per wave merge:** `cargo test --workspace && pnpm --filter voss-app test && pnpm --filter voss-app exec tsc --noEmit && cargo build -p voss-app`
- **Phase gate:** Full suite green before `/gsd:verify-work`. (Playwright e2e excluded per project memory.)

### Wave 0 Gaps
- [ ] `crates/voss-app-core/src/project.rs` — new module with `ProjectInfo`, `ProjectError`, `open_project`, `list_recents`, `default_cwd`, plus tests
- [ ] `crates/voss-app-core/src/lib.rs` — add `pub mod project;` and re-exports
- [ ] `apps/voss-app/src-tauri/Cargo.toml` — add `tauri-plugin-dialog`, `git2 = { version="0.20", default-features=false, features=["vendored-libgit2"] }`
- [ ] `apps/voss-app/src-tauri/src/lib.rs` — add 3 `#[tauri::command]` wrappers + register dialog plugin + extend `generate_handler!`
- [ ] `apps/voss-app/src-tauri/capabilities/default.json` — add `"dialog:allow-open"`
- [ ] `apps/voss-app/package.json` — add `"@tauri-apps/plugin-dialog": "^2"`
- [ ] `apps/voss-app/src/project/projectStorage.ts` — invoke wrappers + `pickFolder` (NEW file)
- [ ] `apps/voss-app/src/components/setup/SetupWindow.tsx` — Variant B token surface (NEW file)
- [ ] `apps/voss-app/src/components/setup/__tests__/SetupWindow.test.tsx` — render + interaction tests (NEW file)
- [ ] `apps/voss-app/src/project/__tests__/projectStorage.test.ts` — mock-based invoke contract (NEW file)
- [ ] `apps/voss-app/src/__tests__/App.test.tsx` — setup-vs-grid branching, applyDefaultLayout hook, pane preservation (NEW file)
- [ ] `apps/voss-app/src/App.tsx` — add `project` + `projectLessAccepted` signals, `<Show>` branch, handlers
- [ ] `apps/voss-app/src/components/titlebar/Titlebar.tsx` — add `projectName?: string` prop (default `"Voss ADE"`)
- [ ] **MSRV verification** in Wave 0: confirm `cargo build` clean before continuing; bump workspace `rust-version` if needed (Open Question Q1)

## Sources

### Primary (HIGH confidence)
- `v2.tauri.app/plugin/dialog/` — dialog plugin init pattern, permission list, frontend `open()` API.
- `v2.tauri.app/security/permissions/` — `dialog:default` validity + `${plugin-name}:${permission-name}` convention.
- `docs.rs/git2/0.20.4/git2/struct.Repository.html` — `Repository::discover` and `head` signatures.
- `docs.rs/git2/0.20.4/git2/struct.Reference.html` — `shorthand() -> Option<&str>`, `is_branch()`.
- `docs.rs/git2/0.20.4/git2/enum.ErrorCode.html` — `NotFound`, `UnbornBranch`, `BareRepo` variants.
- `docs.rs/dirs/latest/dirs/fn.home_dir.html` — `Option<PathBuf>` signature and platform behavior.
- `doc.rust-lang.org/std/fs/fn.canonicalize.html` — signature + Errors section + symlink behavior.
- `docs.solidjs.com/reference/components/show` — `<Show>` behavior (truthy→truthy no remount).
- Repo: `apps/voss-app/src-tauri/src/lib.rs` — current command + plugin + capabilities pattern.
- Repo: `crates/voss-app-core/src/layouts.rs` — A4-03 fail-safe + lazy `.voss/` test patterns.
- Repo: `apps/voss-app/src/grid/layoutStorage.ts` — A4-04 invoke wrapper style + UI-SPEC copy idiom.
- Repo: `apps/voss-app/src/pane/PaneComponent.tsx` — `<Show>` usage already established.

### Secondary (MEDIUM confidence)
- `crates.io/crates/tauri-plugin-dialog` — version 2.4.2 latest (publish date not pulled by fetch — verified via WebSearch result snippet).
- `crates.io/crates/git2` — version 0.20.4 latest.
- WebSearch results for atomic-write patterns / `<Show>` best practices — corroborated by multiple sources.

### Tertiary (LOW confidence)
- None — all decisions track to either docs or repo grep.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all three new deps verified against crates.io / npm + slopcheck OK; codebase grep confirmed deltas.
- Architecture: HIGH — patterns mirror A4-03 / A4-04 line-for-line; `<Show>` already used in repo.
- Pitfalls: MEDIUM-HIGH — MSRV concern (Q1) is the only unresolved item; all others verified.

**Research date:** 2026-05-19
**Valid until:** 2026-06-18 (30 days — Tauri 2 plugin family is stable; only watch is `tauri-plugin-dialog` version drift or a Tauri 2.x bump).

## Planning Implications (Task Ordering)

> Not required by the standard format, but the SPEC asked for ordering — surfacing it here for the planner.

**Recommended wave order:**

1. **Wave 0 — Scaffold + test infra.** Add deps (`tauri-plugin-dialog`, `git2`, `@tauri-apps/plugin-dialog`). Verify MSRV (Q1) with a `cargo build`. Create empty `voss-app-core/src/project.rs` stub + `apps/voss-app/src/project/` directory. Create test files with `it.todo` placeholders so Wave 1 lands tests + impl together.

2. **Wave 1 — Rust core (`voss-app-core::project`).** Land `ProjectInfo`, `ProjectError`, `open_project`, `read_git_branch`, `default_cwd`, `load_recents` / `update_recents` / `save_recents`. Mirror `layouts.rs` test style. No frontend yet.

3. **Wave 2 — Tauri wrappers + capability.** App-level `#[tauri::command]` wrappers in `apps/voss-app/src-tauri/src/lib.rs`. Add `tauri_plugin_dialog::init()` to the builder. Add `"dialog:allow-open"` to capabilities. No frontend impl yet — only the bridge is wired so Wave 3 can invoke real commands in jsdom-mocked tests.

4. **Wave 3 — Frontend wrappers + components.** `projectStorage.ts` invoke wrappers + `pickFolder`. `SetupWindow.tsx` Variant B surface. Wire `App.tsx` to use the new `project` + `projectLessAccepted` signals, the `<Show>` branch, and the `applyDefaultLayout(info.path)` hook on successful open. Update `Titlebar.tsx` to accept `projectName` prop.

5. **Wave 4 — Wire-through tests + acceptance.** `App.test.tsx` integration covering Req-1 / Req-4 / Req-7 / Req-8. Final acceptance: every SPEC checkbox green via test, `cargo build -p voss-app` green, `pnpm --filter voss-app exec tsc --noEmit` green.

**Critical dependency chain:** Wave 1 Rust signatures define the IPC contract — Wave 2 wrappers re-export the same names/casings — Wave 3 frontend `invoke()` uses camelCase matches. Any drift breaks silently (Pitfall 5). Lock signatures in Wave 1; do not edit them in Wave 2 / 3.

**Single-pane integration risk:** `applyDefaultLayout` is invoked in `App.tsx` from a closure that captures `gridController`. If a project is opened BEFORE the grid mounts (theoretically possible if setup-window flow is instant), `gridController` may be undefined. The existing closure already has an `if (!gridController) return false` guard — Wave 3 just needs to make sure the order of operations in `handleOpenFolder` runs `setProject(info)` BEFORE the `await applyDefaultLayout(info.path)`, so the conditional `<Show>` flips and `GridRoot` mounts (and assigns `gridController`) before the default-layout call lands. Best implementation: `await new Promise(r => queueMicrotask(r))` between `setProject` and `applyDefaultLayout`, OR move the default-layout hook into a Solid `createEffect` watching `project()`. Either works — planner's call.

---

*Phase: A5-voss-app-project-open*
*Research date: 2026-05-19*
*Next step: `/gsd:plan-phase A5`*
