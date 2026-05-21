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
requirements: [BAR-01, BAR-02, BAR-06, BAR-07]
must_haves:
  truths:
    - "Rust can read .git/HEAD and return the branch name"
    - "Rust can poll .git/HEAD and emit branch-changed events on change"
    - "Rust can save/load notifications.json to ~/.config/voss-app/"
    - "Git watcher cancels cleanly when a new project is opened"
    - "Rust can return the PID of a running PTY session"
  artifacts:
    - path: "crates/voss-app-core/src/git.rs"
      provides: "read_branch_from_head + git_head_path pure helpers"
      exports: ["read_branch_from_head", "git_head_path"]
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "watch_git_head, stop_git_watch, save_notifications, load_notifications, get_pty_pid commands"
      contains: "GitWatchState"
  key_links:
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "crates/voss-app-core/src/git.rs"
      via: "use voss_app_core::git"
      pattern: "git::read_branch_from_head"
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "crates/voss-app-core/src/pty/mod.rs"
      via: "PtyRegistry::get(id) -> PtySession.child.lock().process_id()"
      pattern: "get_pty_pid"
---

<objective>
Rust backend for git HEAD watching, notification persistence, and PTY PID lookup.

Purpose: Provide the Tauri command surface that the frontend git watcher bridge and
notification store will call. This is the foundation for BAR-01 (branch display),
BAR-02 (PID in pane detail), BAR-06 (500ms branch update latency), and BAR-07
(notification persistence).

Output: New `git.rs` module in voss-app-core with pure helpers; five new Tauri
commands in lib.rs (`watch_git_head`, `stop_git_watch`, `save_notifications`,
`load_notifications`, `get_pty_pid`); `GitWatchState` managed state.
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

From apps/voss-app/src-tauri/src/lib.rs (PTY command pattern, line 71-97):
```rust
type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;

#[tauri::command]
async fn pty_write(session_id: String, data: Vec<u8>, state: Reg<'_>) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.write(&data).map_err(|e| e.to_string())
}
```

From crates/voss-app-core/src/pty/mod.rs (PtySession struct, line 27-38):
```rust
pub struct PtySession {
    pub id: uuid::Uuid,
    // ...
    child: Mutex<Box<dyn portable_pty::Child + Send + Sync>>,
    // ...
}
```
Note: `portable_pty::Child` trait exposes `process_id() -> Option<u32>`.
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
  <name>Task 2: Add git watcher + notification + PID commands to lib.rs</name>
  <files>apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs (full file — watcher pattern at lines 256-399, invoke_handler at 369-396, PTY command pattern at lines 71-97)
    - crates/voss-app-core/src/pty/mod.rs (PtySession struct at line 27, child field at line 32, PtyRegistry::get at line 188)
    - .planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md (Pattern 1: polling watcher, Pattern 5: notifications persistence)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (lib.rs section)
  </read_first>
  <action>
    Add seven items to lib.rs, following the established keymap watcher pattern verbatim per D-10:

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
    - Spawn `std::thread::spawn` polling loop: 200ms sleep (not 500ms like keymap — D-10 requirement), compare `git_file_stamp`, on change -> 50ms settle delay -> `git::read_branch_from_head` -> `app.emit("voss://branch-changed", branch_option)`. Loop until stop flag.
    - Return `Ok(initial)`.

    **4. `stop_git_watch` command** — signature: `fn stop_git_watch(state: tauri::State<'_, GitWatchState>, project_path: String) -> Result<(), String>`.
    - Look up stop flag in state.stops by project path, set to true if found.

    **5. notifications_path() helper** — same pattern as `settings_path()`: `dirs::home_dir().unwrap_or_default().join(".config").join("voss-app").join("notifications.json")`.

    **6. save_notifications / load_notifications commands** per D-07:
    - `save_notifications(entries: Vec<serde_json::Value>) -> Result<(), String>` — truncate the entries vec to the last 50 items before writing (MAX_PERSISTED = 50). Create parent dir, write `serde_json::to_string_pretty`, write file. The frontend in-memory buffer may hold up to 100 entries (per BAR-07), but only the last 50 are persisted to disk (per D-07/SC4). Define `const MAX_PERSISTED: usize = 50;` at the top of the function or as a module constant.
    - `load_notifications() -> Vec<serde_json::Value>` — read file, parse, return empty vec on any error. Returns whatever is in the file (up to 50 entries from the previous save).

    **7. `get_pty_pid` command** (new, for BAR-02 PID display) — signature: `async fn get_pty_pid(session_id: String, state: Reg<'_>) -> Result<Option<u32>, String>`.
    - Follows the exact same pattern as `pty_write`/`pty_resize`: `state.get(&session_id).ok_or("unknown session")?`.
    - On the returned `Arc<PtySession>`, lock the `child` Mutex and call `process_id()` which returns `Option<u32>`.
    - PtySession.child is `Mutex<Box<dyn portable_pty::Child + Send + Sync>>` (line 32 of pty/mod.rs). The `portable_pty::Child` trait exposes `process_id() -> Option<u32>`.
    - NOTE: PtySession's `child` field is private. Add a public method `pub fn process_id(&self) -> Option<u32>` to the `impl PtySession` block in `crates/voss-app-core/src/pty/mod.rs` that locks child and calls `process_id()`. Then in lib.rs: `session.process_id()`.

    **Registration:** Add `use voss_app_core::git;` to imports. Add `.manage(GitWatchState::default())` before `.invoke_handler(...)`. Register all five commands in `generate_handler!`: `watch_git_head, stop_git_watch, save_notifications, load_notifications, get_pty_pid`.

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
    - lib.rs contains `fn get_pty_pid` returning `Result<Option<u32>, String>`
    - save_notifications truncates entries to last 50 before writing (MAX_PERSISTED = 50)
    - pty/mod.rs has `pub fn process_id(&self) -> Option<u32>` on PtySession
    - `generate_handler!` macro includes all five new commands
    - `.manage(GitWatchState::default())` is present before `.invoke_handler`
    - `use voss_app_core::git;` import is present
    - `cargo build --package voss-app` exits 0
  </acceptance_criteria>
  <done>Five new Tauri commands registered and compiling; git watcher follows keymap watcher pattern with 200ms poll interval; notification persistence follows session save pattern with 50-entry disk cap; get_pty_pid exposes child process ID</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| project_path -> Rust | User-chosen project path crosses into file system operations |
| notification entries -> disk | Frontend-originated JSON written to local filesystem |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A10-01 | Tampering | watch_git_head | mitigate | Only watches `<project_path>/.git/HEAD` — project path already validated by open_project (A5); no arbitrary file read |
| T-A10-02 | DoS | watch_git_head poll loop | mitigate | 200ms sleep prevents CPU burn; stop flag prevents orphan threads; HashMap dedup prevents multiple watchers per path |
| T-A10-03 | Tampering | save_notifications | mitigate | Writes only to `~/.config/voss-app/notifications.json` (hardcoded path via notifications_path()); no path injection; truncates to MAX_PERSISTED=50 |
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
- Five new Tauri commands are registered in generate_handler! (watch_git_head, stop_git_watch, save_notifications, load_notifications, get_pty_pid)
- save_notifications truncates to 50 entries on disk
- get_pty_pid returns Option<u32> from portable_pty Child
- No new Rust crate dependencies
</success_criteria>

<output>
Create `.planning/phases/A10-voss-app-status-bar/A10-01-SUMMARY.md` when done
</output>
