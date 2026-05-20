---
phase: A6-voss-app-session-persist
plan: 01
type: execute
wave: 1
depends_on: [A6-00]
files_modified:
  - crates/voss-app-core/Cargo.toml
  - crates/voss-app-core/src/session.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src-tauri/src/lib.rs
autonomous: true
requirements: [PER-01, PER-03, PER-04, PER-05, PER-06]
must_haves:
  truths:
    - "Rust/Tauri owns persisted session file IO"
    - "Session JSON is versioned with integer version 1"
    - "Project sessions write to <workspace>/.voss/session.json; project-less sessions write to ~/.config/voss-app/global-session.json"
    - "Every session write uses an exclusive file lock or equivalent flock"
    - "Corrupt or unsupported session files fail closed and never crash startup"
    - "D-04/D-06: tree-only structural autosave and quit full-save both target the same session file shape"
    - "D-11: invalid or unsupported sessions return no session so the frontend can fall through to default layout"
  artifacts:
    - path: "crates/voss-app-core/src/session.rs"
      provides: "SessionFile schema plus save/load helpers"
      contains: "CURRENT_SESSION_VERSION"
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "Tauri command wrappers for session persistence"
      contains: "save_session"
---

<objective>
Add the Rust session persistence surface: versioned `session.json` / `global-session.json`, locked writes, fail-safe loads, and app-level Tauri commands.
</objective>

<context>
@.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md
@.planning/phases/A6-voss-app-session-persist/A6-RESEARCH.md
@.planning/phases/A6-voss-app-session-persist/A6-PATTERNS.md
@crates/voss-app-core/src/layouts.rs
@crates/voss-app-core/src/project.rs
@crates/voss-app-core/src/grid.rs
@apps/voss-app/src-tauri/src/lib.rs
</context>

<threat_model>
T-A6-01 Path traversal or wrong target file. Mitigation: project session path is derived only from the trusted workspace path plus `.voss/session.json`; global path is derived from `dirs::home_dir()/.config/voss-app/global-session.json`. No user-supplied session filename.
T-A6-02 Concurrent write corruption. Mitigation: use an exclusive file lock around every write and tmp-file rename on the same filesystem.
T-A6-03 Corrupt or future session bricks startup. Mitigation: parse version first and return `Ok(None)` for missing/corrupt/unsupported load paths, with stderr logging.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add versioned SessionFile schema and serde tests</name>
  <files>crates/voss-app-core/src/session.rs, crates/voss-app-core/src/lib.rs</files>
  <read_first>
    - crates/voss-app-core/src/grid.rs - `GridState` serde contract
    - crates/voss-app-core/src/layouts.rs - `LayoutFile` versioned wrapper pattern
    - .planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md - PER-01..PER-05 and D-01..D-12
  </read_first>
  <action>
    Create `crates/voss-app-core/src/session.rs` with `pub const CURRENT_SESSION_VERSION: u32 = 1`. Define serde camelCase structs for `SessionFile`, `SessionPane`, and any small enums/helpers needed. The schema must wrap `GridState`, include `active_preset: Option<String>`, include `project_less_accepted: bool`, and store scrollback as `Vec<SessionPane>` where each pane has `id: String` and `scrollback: Option<Vec<String>>`. Add `SessionFile::new(grid, active_preset, panes, project_less_accepted)`. Export the module and public types from `crates/voss-app-core/src/lib.rs`. Add tests proving JSON contains `"version":1`, `"focusedId"`, `"activePreset"`, `"projectLessAccepted"`, and one pane scrollback array.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core session -- --nocapture && grep -q 'pub const CURRENT_SESSION_VERSION: u32 = 1' crates/voss-app-core/src/session.rs && grep -q 'pub struct SessionFile' crates/voss-app-core/src/session.rs && grep -q 'pub mod session' crates/voss-app-core/src/lib.rs && echo SESSION_SCHEMA_OK</automated>
  </verify>
  <acceptance_criteria>
    - `SessionFile` serializes and deserializes with integer `version: 1`.
    - `SessionFile` wraps `GridState` rather than duplicating grid structs.
    - `projectLessAccepted` is present in JSON.
    - Per-pane `scrollback` accepts `null` and arrays.
    - `SESSION_SCHEMA_OK` prints.
  </acceptance_criteria>
  <done>Session schema is defined and exported.</done>
</task>

<task type="tdd">
  <name>Task 2: Add locked save/load helpers for project and global sessions</name>
  <files>crates/voss-app-core/Cargo.toml, crates/voss-app-core/src/session.rs</files>
  <read_first>
    - crates/voss-app-core/src/layouts.rs - fail-safe load and lazy write pattern
    - crates/voss-app-core/src/project.rs - `~/.config/voss-app/` path idiom
    - .planning/phases/A6-voss-app-session-persist/A6-RESEARCH.md - locking and load-fallback constraints
  </read_first>
  <action>
    Add a Rust file-lock dependency such as `fs2 = "0.4"` to `crates/voss-app-core/Cargo.toml`. Implement `session_path(workspace: &Path) -> PathBuf`, `global_session_path() -> PathBuf`, `save_session(workspace: &Path, session: &SessionFile)`, `load_session(workspace: &Path) -> Result<Option<SessionFile>, SessionError>`, `save_global_session(session: &SessionFile)`, and `load_global_session()`. Writes must create the parent directory only on save, lock a lock file or the destination file exclusively, write pretty JSON to a tmp file, then rename. Loads must not create directories. Missing, invalid JSON, and unsupported versions return `Ok(None)` and log to stderr. Define `SessionError` Display strings for save/load failures without leaking Rust internals.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core session -- --nocapture && grep -q 'lock_exclusive\\|try_lock_exclusive' crates/voss-app-core/src/session.rs && grep -q 'global-session.json' crates/voss-app-core/src/session.rs && grep -q '.voss.*session.json' crates/voss-app-core/src/session.rs && echo SESSION_IO_OK</automated>
  </verify>
  <acceptance_criteria>
    - Save creates `.voss/` only on session write.
    - Load does not create `.voss/`.
    - Project path resolves to `<workspace>/.voss/session.json`.
    - Global path resolves to `~/.config/voss-app/global-session.json`.
    - Corrupt and unsupported versions return `Ok(None)`.
    - A source assertion finds exclusive locking in `session.rs`.
    - `SESSION_IO_OK` prints.
  </acceptance_criteria>
  <done>Rust session save/load helpers are safe and tested.</done>
</task>

<task type="execute">
  <name>Task 3: Register app-level Tauri session commands</name>
  <files>apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs - existing layout/project command wrapper pattern
    - crates/voss-app-core/src/session.rs - function names and types from Tasks 1-2
  </read_first>
  <action>
    Import `voss_app_core::session::{self, SessionFile}` in `apps/voss-app/src-tauri/src/lib.rs`. Add app-level `#[tauri::command]` wrappers named `save_session`, `load_session`, `save_global_session`, and `load_global_session`. Payload keys must be camelCase-compatible from TypeScript: project save/load use `workspacePath`; global commands take no path. Register all four in `tauri::generate_handler!`. Keep wrappers thin and map errors with `to_string()`, matching A4 layout wrappers.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo build -p voss-app 2>&1 | tail -30 && grep -q 'fn save_session' apps/voss-app/src-tauri/src/lib.rs && grep -q 'fn load_session' apps/voss-app/src-tauri/src/lib.rs && grep -q 'fn save_global_session' apps/voss-app/src-tauri/src/lib.rs && grep -q 'fn load_global_session' apps/voss-app/src-tauri/src/lib.rs && echo SESSION_TAURI_OK</automated>
  </verify>
  <acceptance_criteria>
    - Tauri command names are exactly `save_session`, `load_session`, `save_global_session`, `load_global_session`.
    - Commands are registered in `generate_handler!`.
    - `cargo build -p voss-app` exits 0.
    - `SESSION_TAURI_OK` prints.
  </acceptance_criteria>
  <done>Session persistence is callable from the webview.</done>
</task>
</tasks>

<verification>
Run `cargo test -p voss-app-core session -- --nocapture` and `cargo build -p voss-app`.
</verification>

<success_criteria>
- Versioned project and global session files can be saved and loaded.
- Writes are locked and fail safely.
- Corrupt or future-version sessions fall through without crashing startup.
</success_criteria>
