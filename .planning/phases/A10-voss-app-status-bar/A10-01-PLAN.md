---
phase: A10-voss-app-status-bar
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - crates/voss-app-core/src/git.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src-tauri/src/lib.rs
autonomous: true
requirements: [BAR-01, BAR-06, BAR-07]
must_haves:
  truths:
    - "Rust can read .git/HEAD and return the branch name"
    - "Rust can poll .git/HEAD and emit branch-changed events on change"
    - "Rust can save/load notifications.json to ~/.config/voss-app/"
    - "Git watcher cancels cleanly when a new project is opened"
  artifacts:
    - path: "crates/voss-app-core/src/git.rs"
      provides: "read_branch_from_head + git_head_path pure helpers"
      exports: ["read_branch_from_head", "git_head_path"]
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "watch_git_head, stop_git_watch, save_notifications, load_notifications commands"
      contains: "GitWatchState"
  key_links:
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "crates/voss-app-core/src/git.rs"
      via: "use voss_app_core::git"
      pattern: "git::read_branch_from_head"
---

<objective>
Rust backend for git HEAD watching and notification persistence.

Purpose: Provide the Tauri command surface that the frontend git watcher bridge and
notification store will call. This is the foundation for BAR-01 (branch display),
BAR-06 (500ms branch update latency), and BAR-07 (notification persistence).

Output: New `git.rs` module in voss-app-core with pure helpers; four new Tauri
commands in lib.rs (`watch_git_head`, `stop_git_watch`, `save_notifications`,
`load_notifications`); `GitWatchState` managed state.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A10-voss-app-status-bar/A10-CONTEXT.md
@.planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md
@.planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From crates/voss-app-core/src/lib.rs (current pub mod list):
```rust
pub mod grid;
pub mod keymap;
pub mod layouts;
pub mod project;
pub mod pty;
pub mod session;
// A10 adds: pub mod git;
```

From apps/voss-app/src-tauri/src/lib.rs (imports pattern):
```rust
use voss_app_core::grid::{self, GridState};
use voss_app_core::keymap::{self, KeymapOverrideFile, KeymapProfile, KeymapValidationResult};
// ...etc. A10 adds: use voss_app_core::git;
```

From apps/voss-app/src-tauri/src/lib.rs (existing watcher pattern):
```rust
#[derive(Default)]
struct KeymapWatchState {
    stops: Mutex<HashMap<PathBuf, Arc<AtomicBool>>>,
}

struct KeymapFileStamp { exists: bool, modified: Option<SystemTime>, len: Option<u64> }
fn keymap_file_stamp(path: &Path) -> KeymapFileStamp { ... }
```

From apps/voss-app/src-tauri/src/lib.rs (settings_path helper pattern, line 26):
```rust
fn settings_path() -> PathBuf {
    dirs::home_dir().unwrap_or_default()
        .join(".config").join("voss-app").join("settings.json")
}
```

From apps/voss-app/src-tauri/src/lib.rs (managed state + invoke_handler, line 365):
```rust
.manage(KeymapWatchState::default())
.invoke_handler(tauri::generate_handler![ ...existing..., watch_keymap_overrides ])
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create git.rs pure helpers in voss-app-core</name>
  <files>crates/voss-app-core/src/git.rs, crates/voss-app-core/src/lib.rs</files>
  <read_first>
    - crates/voss-app-core/src/project.rs (lines 92-98 for existing read_git_branch via git2)
    - crates/voss-app-core/src/lib.rs (for pub mod list)
    - .planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md (Pattern 1: read_branch_from_head)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (git.rs section)
  </read_first>
  <action>
    Create `crates/voss-app-core/src/git.rs` with two public functions per D-10 and RESEARCH Pattern 1:

    1. `pub fn read_branch_from_head(head_path: &Path) -> Option<String>` — reads `.git/HEAD` via `std::fs::read_to_string`, trims, checks `strip_prefix("ref: refs/heads/")`. Returns `Some(branch_name)` for normal branches, `None` for detached HEAD (SHA content). This is the fast path for the polling loop (NOT git2, per RESEARCH anti-pattern).

    2. `pub fn git_head_path(project_path: &Path) -> Option<PathBuf>` — constructs `project_path.join(".git").join("HEAD")`, returns `Some(path)` if it exists, `None` otherwise. This is the D-11 guard (hide branch when no git repo, Pitfall 1).

    Add `pub mod git;` to `crates/voss-app-core/src/lib.rs` after the existing `pub mod grid;` line.

    Include a `#[cfg(test)] mod tests` block in git.rs with at least two tests:
    - `test_read_branch_normal`: create a temp file containing `ref: refs/heads/main\n`, assert returns `Some("main")`.
    - `test_read_branch_detached`: create a temp file containing a 40-char SHA, assert returns `None`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core git -- --nocapture 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - crates/voss-app-core/src/git.rs exists and contains `pub fn read_branch_from_head`
    - crates/voss-app-core/src/git.rs contains `pub fn git_head_path`
    - crates/voss-app-core/src/lib.rs contains `pub mod git;`
    - `cargo test -p voss-app-core git` shows at least 2 tests passing
    - `cargo build -p voss-app-core` exits 0
  </acceptance_criteria>
  <done>git.rs module compiles, exports two public helpers, tests pass for normal branch and detached HEAD</done>
</task>

<task type="auto">
  <name>Task 2: Add git watcher + notification commands to lib.rs</name>
  <files>apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs (full file — watcher pattern at lines 256-399, invoke_handler at 369-396)
    - .planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md (Pattern 1: polling watcher, Pattern 5: notifications persistence)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (lib.rs section)
  </read_first>
  <action>
    Add six items to lib.rs, following the established keymap watcher pattern verbatim per D-10:

    **1. GitWatchState struct** (parallel to `KeymapWatchState`):
    `#[derive(Default)] struct GitWatchState { stops: Mutex<HashMap<PathBuf, Arc<AtomicBool>>> }`

    **2. GitFileStamp struct** (parallel to `KeymapFileStamp`):
    `#[derive(Debug, PartialEq)] struct GitFileStamp { exists: bool, modified: Option<SystemTime>, len: Option<u64> }`
    Plus `fn git_file_stamp(path: &Path) -> GitFileStamp` helper mirroring `keymap_file_stamp`.

    **3. `watch_git_head` command** — signature: `fn watch_git_head(app: tauri::AppHandle, state: tauri::State<'_, GitWatchState>, project_path: String) -> Result<Option<String>, String>`.
    - Construct head_path via `git::git_head_path(Path::new(&project_path))`.
    - If `None` (no git repo, D-11/Pitfall 1), return `Ok(None)` immediately — no thread spawned.
    - Read initial branch via `git::read_branch_from_head(&head_path)`.
    - Create `Arc<AtomicBool>` stop flag; insert into state.stops HashMap keyed by project PathBuf (cancel previous watcher if exists, same as keymap pattern — Pitfall 2).
    - Spawn `std::thread::spawn` polling loop: 200ms sleep (not 500ms like keymap — D-10 requirement), compare `git_file_stamp`, on change → 50ms settle delay → `git::read_branch_from_head` → `app.emit("voss://branch-changed", branch_option)`. Loop until stop flag.
    - Return `Ok(initial)`.

    **4. `stop_git_watch` command** — signature: `fn stop_git_watch(state: tauri::State<'_, GitWatchState>, project_path: String) -> Result<(), String>`.
    - Look up stop flag in state.stops by project path, set to true if found.

    **5. notifications_path() helper** — same pattern as `settings_path()`: `dirs::home_dir().unwrap_or_default().join(".config").join("voss-app").join("notifications.json")`.

    **6. save_notifications / load_notifications commands** per D-07:
    - `save_notifications(entries: Vec<serde_json::Value>) -> Result<(), String>` — create parent dir, write `serde_json::to_string_pretty`, write file.
    - `load_notifications() -> Vec<serde_json::Value>` — read file, parse, return empty vec on any error.

    **Registration:** Add `use voss_app_core::git;` to imports. Add `.manage(GitWatchState::default())` before `.invoke_handler(...)`. Register all four commands in `generate_handler!`: `watch_git_head, stop_git_watch, save_notifications, load_notifications`.

    Event constant: `const GIT_BRANCH_CHANGED_EVENT: &str = "voss://branch-changed";`
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo build --package voss-app 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - lib.rs contains `struct GitWatchState` with `stops: Mutex<HashMap<PathBuf, Arc<AtomicBool>>>`
    - lib.rs contains `fn watch_git_head` returning `Result<Option<String>, String>`
    - lib.rs contains `fn stop_git_watch`
    - lib.rs contains `fn save_notifications` and `fn load_notifications`
    - lib.rs contains `fn notifications_path() -> PathBuf` using `dirs::home_dir()`
    - `generate_handler!` macro includes all four new commands
    - `.manage(GitWatchState::default())` is present before `.invoke_handler`
    - `use voss_app_core::git;` import is present
    - `cargo build --package voss-app` exits 0
  </acceptance_criteria>
  <done>Four new Tauri commands registered and compiling; git watcher follows keymap watcher pattern with 200ms poll interval; notification persistence follows session save pattern</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| project_path → Rust | User-chosen project path crosses into file system operations |
| notification entries → disk | Frontend-originated JSON written to local filesystem |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A10-01 | Tampering | watch_git_head | mitigate | Only watches `<project_path>/.git/HEAD` — project path already validated by open_project (A5); no arbitrary file read |
| T-A10-02 | DoS | watch_git_head poll loop | mitigate | 200ms sleep prevents CPU burn; stop flag prevents orphan threads; HashMap dedup prevents multiple watchers per path |
| T-A10-03 | Tampering | save_notifications | mitigate | Writes only to `~/.config/voss-app/notifications.json` (hardcoded path via notifications_path()); no path injection |
| T-A10-04 | Information Disclosure | load_notifications | accept | Reads user-local file; no PII beyond user's own notification history; no cross-user risk |
| T-A10-SC | Tampering | npm/pip/cargo installs | accept | No new dependencies added in A10 — all crates already present in workspace |
</threat_model>

<verification>
```bash
# Rust compilation (both crates)
cargo build -p voss-app-core && cargo build --package voss-app

# git.rs unit tests
cargo test -p voss-app-core git

# No new dependencies
diff <(git show HEAD:Cargo.lock | head -5) <(head -5 Cargo.lock) 2>/dev/null || echo "Cargo.lock unchanged check"
```
</verification>

<success_criteria>
- cargo build for both voss-app-core and voss-app exits 0
- git.rs tests pass (branch read + detached HEAD)
- Four new Tauri commands are registered in generate_handler!
- No new Rust crate dependencies
</success_criteria>

<output>
Create `.planning/phases/A10-voss-app-status-bar/A10-01-SUMMARY.md` when done
</output>
