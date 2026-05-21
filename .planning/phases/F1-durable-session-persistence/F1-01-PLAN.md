---
phase: F1-durable-session-persistence
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - crates/voss-app-core/Cargo.toml
  - crates/voss-app-core/src/agent_registry.rs
  - crates/voss-app-core/src/pty/mod.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src-tauri/src/lib.rs
autonomous: true
requirements: [FPRS-01, FPRS-02, FPRS-03, FPRS-05]

must_haves:
  truths:
    - "rusqlite 0.39 with bundled feature compiles clean in voss-app-core"
    - "agent_registry.rs CRUD operations work against an in-memory SQLite DB"
    - "spawn_command_session spawns an arbitrary CLI binary on a PTY"
    - "spawn_agent Tauri command creates PTY + registry row"
    - "get_active_agents returns rows with status active"
    - "mark_agent_stopped transitions a row to stopped"
    - "update_agents_last_seen touches all active rows"
    - "sweep_orphan_agents marks unmatched active rows as stopped"
  artifacts:
    - path: "crates/voss-app-core/src/agent_registry.rs"
      provides: "SQLite registry module — Connection open, schema create, CRUD, path resolution"
      exports: ["open_registry", "create_schema", "register_agent", "mark_stopped", "update_last_seen_all", "get_active_agents", "sweep_orphans", "registry_path", "global_registry_path", "AgentEntry", "AgentRegistryError"]
    - path: "crates/voss-app-core/src/pty/mod.rs"
      provides: "spawn_command_session for arbitrary CLI binaries"
      exports: ["spawn_command_session"]
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "5 new Tauri command wrappers + managed Mutex<Option<Connection>>"
  key_links:
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "crates/voss-app-core/src/agent_registry.rs"
      via: "pub use + #[tauri::command] wrappers"
      pattern: "agent_registry::"
    - from: "crates/voss-app-core/src/agent_registry.rs"
      to: "rusqlite"
      via: "Cargo.toml dependency"
      pattern: "rusqlite::Connection"
---

<objective>
Build the Rust agent registry layer: a new `agent_registry.rs` module in `voss-app-core` that owns a SQLite `Connection` behind `Mutex`, plus `spawn_command_session` in the PTY module for arbitrary CLI binary spawning, plus 5 thin Tauri command wrappers in the app crate.

Purpose: This is the data backbone of F1. Every other plan depends on these Rust functions existing and being callable from the frontend.

Output: `agent_registry.rs` with full CRUD, `spawn_command_session` in `pty/mod.rs`, 5 new Tauri commands registered in the app crate, `rusqlite` dep added, all `cargo test` green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/F1-durable-session-persistence/F1-SPEC.md
@.planning/phases/F1-durable-session-persistence/F1-CONTEXT.md
@.planning/phases/F1-durable-session-persistence/F1-RESEARCH.md
@.planning/phases/F1-durable-session-persistence/F1-PATTERNS.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From crates/voss-app-core/src/session.rs (error pattern analog):
```rust
#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    #[error("could not save session")]
    SaveFailed,
    #[error("could not load session")]
    LoadFailed,
}

pub fn session_path(workspace: &Path) -> PathBuf {
    workspace.join(".voss").join("session.json")
}
```

From crates/voss-app-core/src/pty/mod.rs (spawn_session signature):
```rust
pub fn spawn_session(
    rows: u16, cols: u16, cwd: Option<String>,
) -> anyhow::Result<(Arc<PtySession>, Box<dyn Read + Send>, tokio::sync::mpsc::Receiver<bool>)>
```

From crates/voss-app-core/src/pty/commands.rs (PtyEvent):
```rust
pub enum PtyEvent {
    Data { bytes: Vec<u8> },
    Exit { code: i32 },
    FgProcess { name: String },
    TitleChange { title: String },
}
```

From apps/voss-app/src-tauri/src/lib.rs (command wrapper pattern):
```rust
type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;

#[tauri::command]
async fn spawn_pty(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16, cols: u16, cwd: Option<String>,
    state: Reg<'_>,
) -> Result<String, String> { ... }
```

From crates/voss-app-core/src/lib.rs (plugin init pattern):
```rust
pub fn init<R: tauri::Runtime>() -> tauri::plugin::TauriPlugin<R> {
    tauri::plugin::Builder::new("voss-app-core")
        .invoke_handler(tauri::generate_handler![...])
        .setup(|app, _api| {
            app.manage(Arc::new(PtyRegistry::default()));
            Ok(())
        })
        .build()
}
```
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 0: rusqlite package legitimacy gate</name>
  <what-built>
    rusqlite 0.39 is tagged [ASSUMED] in the Package Legitimacy Audit (slopcheck unavailable).
    It is the de facto Rust SQLite binding (~10 years old, github.com/rusqlite/rusqlite).
    This is the ONLY new external dependency in F1.
  </what-built>
  <how-to-verify>
    1. Verify at https://crates.io/crates/rusqlite — confirm publisher, download count, repo link
    2. Verify at https://github.com/rusqlite/rusqlite — confirm active maintenance, no security advisories
    3. Confirm the `bundled` feature compiles SQLite from source (no system libsqlite3 dependency)
  </how-to-verify>
  <resume-signal>Type "approved" to proceed with rusqlite 0.39 bundled, or raise concerns</resume-signal>
</task>

<task type="auto">
  <name>Task 1: agent_registry.rs module + rusqlite dep + spawn_command_session</name>
  <files>
    crates/voss-app-core/Cargo.toml
    crates/voss-app-core/src/agent_registry.rs
    crates/voss-app-core/src/pty/mod.rs
    crates/voss-app-core/src/lib.rs
  </files>
  <read_first>
    crates/voss-app-core/Cargo.toml
    crates/voss-app-core/src/session.rs
    crates/voss-app-core/src/pty/mod.rs
    crates/voss-app-core/src/lib.rs
    crates/voss-app-core/src/pty/reader.rs
  </read_first>
  <action>
    **Cargo.toml:** Add `rusqlite = { version = "0.39", features = ["bundled"] }` to `[dependencies]` (per D-01, FPRS-01).

    **agent_registry.rs** (NEW, per D-01 — same level as session.rs):

    1. Imports: `rusqlite::{Connection, params}`, `serde::{Deserialize, Serialize}`, `std::path::{Path, PathBuf}`, `std::time::{SystemTime, UNIX_EPOCH}`.

    2. `AgentRegistryError` enum with `thiserror::Error` derive — variants: `OpenFailed`, `QueryFailed`, `WriteFailed`. UI-safe Display strings matching session.rs pattern (per D-01).

    3. `AgentEntry` struct (Serialize, Deserialize): fields `pane_id: String`, `session_id: String`, `cli_binary: String`, `cli_args: String` (JSON text), `cwd: String`, `status: String`, `last_seen: i64`. This is the row type returned by queries.

    4. `epoch_seconds() -> i64` helper: `SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() as i64`.

    5. Path resolution functions (per FPRS-02):
       - `registry_path(workspace: &Path) -> PathBuf`: returns `workspace.join(".voss").join("agent-registry.sqlite")`
       - `global_registry_path() -> PathBuf`: returns `config_voss_app_dir().join("agent-registry.sqlite")` (reuse the same `config_voss_app_dir()` helper from session.rs — it returns `~/.config/voss-app/`)
       - Add `#[cfg(test)]` override for `global_registry_path` using a thread_local pattern matching session.rs

    6. `open_registry(path: &Path) -> Result<Connection, AgentRegistryError>`:
       - Create parent dirs with `std::fs::create_dir_all`
       - `Connection::open(path)` mapped to `OpenFailed`
       - Call `create_schema(&conn)?`
       - Return `Ok(conn)`

    7. `create_schema(conn: &Connection) -> Result<(), AgentRegistryError>`:
       - Execute `CREATE TABLE IF NOT EXISTS agent_sessions (pane_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, cli_binary TEXT NOT NULL, cli_args TEXT NOT NULL DEFAULT '[]', cwd TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'stopped')), last_seen INTEGER NOT NULL)`
       - Map error to `WriteFailed`

    8. CRUD functions (per D-01, FPRS-01):
       - `register_agent(conn, pane_id, session_id, cli_binary, cli_args: &[String], cwd) -> Result<(), AgentRegistryError>`: INSERT OR REPLACE with `serde_json::to_string(cli_args)`, status='active', last_seen=epoch_seconds()
       - `mark_stopped(conn, pane_id) -> Result<(), AgentRegistryError>`: UPDATE status='stopped', last_seen=now WHERE pane_id=?
       - `update_last_seen_all(conn) -> Result<(), AgentRegistryError>`: UPDATE last_seen=now WHERE status='active' (per D-09, FPRS-05)
       - `get_active_agents(conn) -> Result<Vec<AgentEntry>, AgentRegistryError>`: SELECT * WHERE status='active', query_map into AgentEntry vec
       - `sweep_orphans(conn, valid_pane_ids: &[String]) -> Result<usize, AgentRegistryError>`: UPDATE status='stopped' WHERE status='active' AND pane_id NOT IN (...). If valid_pane_ids empty, mark ALL active as stopped (per D-11). Use rusqlite params_from_iter for the dynamic IN clause.

    9. `#[cfg(test)] mod tests` using `tempfile::tempdir()` for file-backed SQLite (not :memory:, to test path creation). Tests:
       - `test_schema_creation`: open_registry on temp path, verify table exists
       - `test_register_and_get_active`: register 2 agents, get_active returns 2
       - `test_mark_stopped`: register, mark_stopped, get_active returns 0
       - `test_update_last_seen`: register, sleep 1ms, update_last_seen_all, verify last_seen changed
       - `test_sweep_orphans`: register 3 agents (a, b, c), sweep with valid=[a], verify b and c are stopped, a is still active
       - `test_sweep_empty_valid`: register 2, sweep with empty valid list, both stopped
       - `test_registry_path_resolution`: verify registry_path joins correctly
       - `test_insert_or_replace`: register same pane_id twice, get_active returns 1 (not 2)

    **pty/mod.rs** (per D-02, FPRS-03 — PTY layer stays generic, new function alongside spawn_session):

    Add `spawn_command_session(cmd_binary: &str, cmd_args: &[String], rows: u16, cols: u16, cwd: Option<String>)` with the same return type as `spawn_session`. Body is identical to `spawn_session` except:
    - Replace the `$SHELL` env lookup (lines 134-139) with `CommandBuilder::new(cmd_binary)` + `for arg in cmd_args { cmd.arg(arg); }`
    - `shell_name` = basename of `cmd_binary` (use the same `Path::new(cmd_binary).file_name()...` pattern)
    - Keep TERM, COLORTERM, cwd, openpty, child spawn, reader/writer, pause channel, PtySession construction identical

    **lib.rs** (crate root):
    - Add `pub mod agent_registry;` to the module list
    - Add `pub use agent_registry::{...}` re-exports for: `open_registry`, `register_agent`, `mark_stopped`, `update_last_seen_all`, `get_active_agents`, `sweep_orphans`, `registry_path`, `global_registry_path`, `AgentEntry`, `AgentRegistryError`
    - Add `pub use pty::spawn_command_session;` alongside existing `pub use pty::spawn_session` (implicit — spawn_session is not currently re-exported from lib.rs, but spawn_command_session should be accessible for the app crate)
    - Do NOT add commands to the plugin `init()` invoke_handler — the commands live in the app crate per the cross-crate pattern
    - Do NOT add managed state in plugin init — the app crate manages `Mutex<Option<Connection>>` (per Pitfall 2, connection opens lazily)
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core -- agent_registry -x && cargo build -p voss-app-core 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `crates/voss-app-core/Cargo.toml` contains `rusqlite = { version = "0.39", features = ["bundled"] }`
    - `crates/voss-app-core/src/agent_registry.rs` exists with `pub fn open_registry`, `pub fn register_agent`, `pub fn mark_stopped`, `pub fn get_active_agents`, `pub fn update_last_seen_all`, `pub fn sweep_orphans`, `pub fn registry_path`, `pub fn global_registry_path`
    - `AgentEntry` struct has fields: pane_id, session_id, cli_binary, cli_args, cwd, status, last_seen
    - `agent_sessions` table schema has CHECK(status IN ('active', 'stopped'))
    - `crates/voss-app-core/src/pty/mod.rs` contains `pub fn spawn_command_session` accepting `cmd_binary: &str, cmd_args: &[String]`
    - `crates/voss-app-core/src/lib.rs` contains `pub mod agent_registry` and re-exports
    - `cargo test -p voss-app-core -- agent_registry` runs 8+ tests, all pass
    - `cargo build -p voss-app-core` succeeds with 0 errors
  </acceptance_criteria>
  <done>
    agent_registry.rs module with full CRUD operations, spawn_command_session in pty/mod.rs, rusqlite 0.39 bundled compiles clean, 8+ unit tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Tauri command wrappers + managed registry state</name>
  <files>
    apps/voss-app/src-tauri/src/lib.rs
  </files>
  <read_first>
    apps/voss-app/src-tauri/src/lib.rs
    crates/voss-app-core/src/agent_registry.rs
    crates/voss-app-core/src/pty/mod.rs
    crates/voss-app-core/src/pty/reader.rs
  </read_first>
  <action>
    Add 5 new `#[tauri::command]` wrappers in `apps/voss-app/src-tauri/src/lib.rs` following the established cross-crate pattern (per D-01, D-02, D-03). Also add `Mutex<Option<rusqlite::Connection>>` as managed Tauri state (per D-03, Pitfall 2 — starts as None, lazily opened).

    **Imports:** Add `use voss_app_core::agent_registry;` and `use voss_app_core::pty::spawn_command_session;`. Add `use rusqlite::Connection;` (rusqlite is a transitive dep via voss-app-core).

    **Type alias:** `type AgentDb<'a> = tauri::State<'a, Mutex<Option<Connection>>>;`

    **Helper:** `fn ensure_registry(db: &Mutex<Option<Connection>>, workspace_path: Option<&str>) -> Result<std::sync::MutexGuard<'_, Option<Connection>>, String>` that:
    - Locks the mutex
    - If the Option is None, opens the registry at the appropriate path (workspace_path -> registry_path, or global_registry_path as fallback), stores in the Option, returns the guard
    - If already Some, returns the guard
    - Errors map to String

    **5 commands:**

    1. `spawn_agent(on_data: Channel<PtyEvent>, rows: u16, cols: u16, cwd: Option<String>, cli_binary: String, cli_args: Vec<String>, session_id: String, pane_id: String, workspace_path: Option<String>, db: AgentDb, pty_state: Reg) -> Result<String, String>`:
       - Call `ensure_registry(&db, workspace_path.as_deref())?`
       - Call `spawn_command_session(&cli_binary, &cli_args, rows, cols, cwd.clone())` to create PTY (per D-02)
       - Insert into PtyRegistry, start_reader (same as spawn_pty)
       - Lock db, call `agent_registry::register_agent(conn, &pane_id, &session_id, &cli_binary, &cli_args, cwd_str)` (per FPRS-03)
       - Return pty_id

    2. `get_active_agents(workspace_path: Option<String>, db: AgentDb) -> Result<Vec<agent_registry::AgentEntry>, String>`:
       - ensure_registry, call get_active_agents on the unwrapped connection
       - On error (including None connection), return empty vec (best-effort, per Pitfall 3)

    3. `mark_agent_stopped(pane_id: String, workspace_path: Option<String>, db: AgentDb) -> Result<(), String>`:
       - ensure_registry, call mark_stopped

    4. `update_agents_last_seen(workspace_path: Option<String>, db: AgentDb) -> Result<(), String>`:
       - ensure_registry, call update_last_seen_all (per D-09, FPRS-05)

    5. `sweep_orphan_agents(valid_pane_ids: Vec<String>, workspace_path: Option<String>, db: AgentDb) -> Result<usize, String>`:
       - ensure_registry, call sweep_orphans (per D-11)

    **Managed state:** Add `.manage(Mutex::new(None::<Connection>))` in the `run()` function alongside existing `.manage(Arc::new(PtyRegistry::default()))` and `.manage(Mutex::new(GridState::default()))`.

    **Handler registration:** Add `spawn_agent`, `get_active_agents`, `mark_agent_stopped`, `update_agents_last_seen`, `sweep_orphan_agents` to the `tauri::generate_handler![...]` list.

    **Note on rusqlite in app crate:** The app crate does not directly depend on rusqlite. The `Connection` type comes through `voss_app_core`. If the compiler cannot resolve `rusqlite::Connection`, add `rusqlite = { version = "0.39", features = ["bundled"] }` to `apps/voss-app/src-tauri/Cargo.toml` as well (same version pin).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo build -p voss-app 2>&1 | tail -10 && cargo test -p voss-app-core -- agent_registry -x 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/src-tauri/src/lib.rs` contains `#[tauri::command] async fn spawn_agent(...)` with params: on_data, rows, cols, cwd, cli_binary, cli_args, session_id, pane_id, workspace_path, db, pty_state
    - `apps/voss-app/src-tauri/src/lib.rs` contains `#[tauri::command]` for get_active_agents, mark_agent_stopped, update_agents_last_seen, sweep_orphan_agents
    - `.manage(Mutex::new(None::<Connection>))` or equivalent appears in the `run()` function
    - All 5 new commands appear in the `generate_handler![...]` macro invocation
    - `cargo build -p voss-app` (or the src-tauri crate) succeeds with 0 errors
    - Existing PTY commands (spawn_pty, pty_write, etc.) still compile and are still registered
  </acceptance_criteria>
  <done>
    5 Tauri command wrappers registered, Mutex<Option<Connection>> managed, app crate builds clean, existing commands unaffected
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Frontend -> Rust IPC | cli_binary and cli_args cross from untrusted frontend input |
| SQLite file -> registry queries | File on disk could be tampered with |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F1-01 | Tampering | agent_registry.rs SQL | mitigate | All queries use rusqlite `params![]` parameterized queries — zero string interpolation |
| T-F1-02 | Elevation of Privilege | spawn_agent cli_binary | accept | cli_binary is user-provided from command palette — same trust boundary as typing in a terminal; no restriction needed |
| T-F1-03 | Tampering | registry .sqlite file | accept | Local-only single-user desktop app; no additional protection needed |
| T-F1-04 | Information Disclosure | cli_args in registry | accept | Local SQLite file, same security as session.json; no secrets expected in CLI args |
| T-F1-SC | Tampering | rusqlite crate install | mitigate | Blocking human checkpoint (Task 0) for [ASSUMED] package legitimacy |
</threat_model>

<verification>
```bash
cargo test -p voss-app-core -- agent_registry -x
cargo build -p voss-app
```
</verification>

<success_criteria>
- rusqlite 0.39 bundled compiles clean on macOS
- agent_registry.rs has 8+ passing unit tests covering schema, CRUD, sweep
- spawn_command_session works for arbitrary CLI binary
- 5 Tauri command wrappers build clean
- No regression in existing PTY/grid/session/layout commands
</success_criteria>

<output>
Create `.planning/phases/F1-durable-session-persistence/F1-01-SUMMARY.md` when done
</output>
