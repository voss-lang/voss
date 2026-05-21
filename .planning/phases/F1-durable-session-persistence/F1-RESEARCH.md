# Phase F1: Durable Session Persistence - Research

**Researched:** 2026-05-20
**Domain:** Rust SQLite persistence (rusqlite) + Tauri command surface + SolidJS frontend orchestration
**Confidence:** HIGH

## Summary

F1 adds agent-awareness to the ADE: a SQLite registry tracks which panes run Voss agent sessions (vs generic shells), and a boot-time restore routine auto-restarts those agent subprocesses. A6 already handles pane geometry/scrollback/cwd; F1 adds a parallel data layer for agent identity and lifecycle.

The implementation surface is narrow and well-constrained. A new `agent_registry.rs` module in `voss-app-core` owns `rusqlite::Connection` behind `Mutex`, following the exact same state management pattern used by `grid.rs` (`Mutex<GridState>`) and `pty/mod.rs` (`Arc<PtyRegistry>`). The `spawn_agent` command wraps the existing `spawn_session()` PTY API, adding a registry row write. Frontend changes are minimal: the `PaneComponent` gets an optional `agentConfig` prop, and the boot restore path queries the registry after A6 tree rebuild but before panes mount.

**Primary recommendation:** Build `agent_registry.rs` as a standalone module with `Mutex<Connection>` opened once during plugin init. Use `rusqlite` 0.39.0 with the `bundled` feature (compiles SQLite from source, avoids system dependency). Follow the exact cross-crate command wrapper pattern from A2/A3/A4/A6 for the `spawn_agent` Tauri command.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** New standalone `agent_registry.rs` module in `voss-app-core` -- same level as `session.rs`, `layouts.rs`, `grid.rs`. Owns rusqlite Connection, schema creation, CRUD. PTY layer stays generic; registry is agent-specific.
- **D-02:** `spawn_agent` wraps `spawn_pty` internally -- calls existing `spawn_pty` to create the PTY session, then writes the registry row. PTY layer unchanged. Agent layer adds metadata.
- **D-03:** `Mutex<Connection>` for SQLite connection management -- same pattern as `grid.rs` `Mutex<GridState>`. Open once on plugin init, wrap in Mutex. Commands lock briefly for reads/writes.
- **D-04:** Frontend orchestration -- after A6 loads session.json and rebuilds the tree, but before PaneComponent mounts spawn generic shells, the frontend checks registry for each pane_id. If agent entry exists with `status = 'active'`, pass `cli_binary` + `cli_args` to PaneComponent instead of default shell. No Rust-side restore logic.
- **D-05:** Rely on A6 pane_id stability -- A6 already persists and restores pane IDs (UUIDs). Registry keys on `pane_id`. On boot, match `registry.pane_id` to restored tree `pane_id`. No extra mapping layer.
- **D-06:** `PaneComponent` gets optional `agentConfig` prop: `{ cliBinary: string, cliArgs: string[], sessionId: string }`. If present, spawn_agent instead of spawn_pty. Tree leaf stores this config for A6 persistence.
- **D-07:** Command palette entry point -- A7 command registry gets a "Start Voss Agent" (or "Start Agent") command that prompts for task description, then spawns agent in focused pane. Minimal UX, leverages existing A7 infrastructure.
- **D-08:** Any CLI binary from day one -- `spawn_agent` takes a generic `cli_binary` string. "voss", "claude", "codex", "opencode" all work. Registry stores whatever was passed. Future Agents launcher (F6 council) needs this anyway.
- **D-09:** Extend A6 close-requested handler -- add registry `last_seen` update AFTER session.json save but BEFORE `window.close()`. Same handler, sequential: scrollback -> session.json -> registry last_seen -> close. One close-request flow.
- **D-10:** Both events trigger status change -- agent exit (PTY EOF/exit event) -> immediate registry update to `status = 'stopped'`. App quit -> active rows stay `status = 'active'` (they're meant to restart on next boot). Clean distinction.
- **D-11:** Boot-time orphan sweep -- after A6 restore + F1 agent restart, scan registry for `status = 'active'` rows with no matching `pane_id` in the restored tree. Mark those `status = 'stopped'`. One pass, no background work.

### Claude's Discretion
No explicit discretion areas -- CONTEXT.md defers no design decisions to the planner.

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope. Future Agents launcher (F6 council) will consume the generic `spawn_agent` API designed here.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-1 (Agent Registry) | SQLite database tracks active agent sessions per pane | `rusqlite` 0.39 with `bundled` feature; `Mutex<Connection>` pattern; schema verified |
| REQ-2 (Registry Location) | Registry at `<project>/.voss/agent-registry.sqlite` or `~/.config/voss-app/` fallback | Path resolution follows `session.rs` patterns; `.voss/` already gitignored for `.voss-cache/` but `*.sqlite` needs entry |
| REQ-3 (Agent Spawn Registration) | `spawn_agent` creates PTY + registry row atomically | Wraps `spawn_session()` + `INSERT` in same function; cross-crate wrapper pattern documented |
| REQ-4 (Boot Restart) | Active registry entries trigger agent subprocess spawns on launch | Frontend orchestration between A6 tree rebuild and PaneComponent mount; `agentConfig` prop pattern |
| REQ-5 (Clean Shutdown) | Close-requested handler updates `last_seen` timestamps | Extends `installAllWorkspacesCloseSave()` in `workspaceSessionPersist.ts` |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SQLite registry (CRUD) | Rust / voss-app-core | -- | Persistent storage + thread-safe access via Mutex; Tauri async command wrapping |
| Agent spawn (PTY + registry) | Rust / voss-app-core | Frontend (IPC call) | Core spawns PTY + writes DB; frontend invokes via Tauri command |
| Boot restore orchestration | Frontend (SolidJS) | Rust (read query) | Frontend controls mount order; queries registry via IPC before spawning panes |
| Close-requested lifecycle | Frontend (SolidJS) | Rust (write query) | Frontend handler calls Rust command to update `last_seen` |
| Orphan sweep | Frontend (SolidJS) | Rust (query + update) | Frontend knows which pane_ids exist in restored tree; tells Rust to mark orphans |
| Command palette entry | Frontend (SolidJS) | -- | A7 CommandRegistry gets new "Start Agent" command definition |
| PTY exit -> registry update | Rust / voss-app-core | Frontend (callback) | Rust reader detects EOF; F1 hooks into exit path to update registry |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `rusqlite` | 0.39.0 | SQLite database access from Rust | De facto Rust SQLite binding; 550+ dependent crates; `bundled` feature compiles SQLite from source (no system dep) [ASSUMED -- version confirmed via `cargo search`; standard status based on training knowledge] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `serde` + `serde_json` | (workspace) | Serialize `cli_args` JSON array for registry column | Already a workspace dependency |
| `chrono` or `std::time` | N/A | `last_seen` timestamp column | Use `SystemTime` epoch seconds via `std::time` -- avoids new dep; SQLite stores as INTEGER |
| `uuid` | (workspace) | Generate session IDs for agent rows | Already a workspace dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `rusqlite` (sync) | `sqlx` (async) | SPEC constraint explicitly requires sync Mutex pattern matching existing crate conventions; `sqlx` adds complexity |
| `Mutex<Connection>` | Connection pool (`r2d2_sqlite`) | Overkill for single-app single-writer; existing codebase pattern is Mutex |
| `std::time` epoch seconds | `chrono` crate | New dependency not justified for a single timestamp column; epoch INTEGER is sufficient |

**Installation:**
```toml
# In crates/voss-app-core/Cargo.toml [dependencies]
rusqlite = { version = "0.39", features = ["bundled"] }
```

**Version verification:** `cargo search rusqlite` confirms 0.39.0 is latest stable (checked 2026-05-20). [ASSUMED -- registry existence verified but standard status from training data]

## Package Legitimacy Audit

> slopcheck was unavailable at research time. All packages tagged `[ASSUMED]`.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `rusqlite` | crates.io | ~10 yrs | High (well-known) | github.com/rusqlite/rusqlite | N/A | [ASSUMED] -- planner must add checkpoint |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time. The single new package (`rusqlite`) is tagged `[ASSUMED]` and the planner must gate its install behind a `checkpoint:human-verify` task.*

## Architecture Patterns

### System Architecture Diagram

```
App Boot
  |
  v
[A6 Session Restore]         [F1 Registry Open]
  |  (tree + scrollback)       |  (Mutex<Connection> init)
  v                            v
[Frontend: match pane_ids] <-- [Rust: query active agents]
  |                               (SELECT WHERE status='active')
  |
  +--- pane has agent entry ----> [spawn_agent IPC]
  |                                  |
  |                                  +-> spawn_session() (PTY)
  |                                  +-> INSERT registry row
  |
  +--- no agent entry ----------> [spawn_pty IPC] (normal shell)
  |
  v
[PaneComponent mounts]
  |
  +--- agent exit (EOF) -------> [Rust reader: UPDATE status='stopped']
  |
  +--- App quit ----------------> [close-requested handler]
                                    |-> save session.json (A6)
                                    |-> UPDATE last_seen (F1)
                                    |-> window.close()
```

### Recommended Project Structure
```
crates/voss-app-core/src/
  agent_registry.rs     # NEW: Connection, schema, CRUD, path resolution
  lib.rs                # ADD: pub mod agent_registry, Mutex<Connection> managed state
  pty/
    mod.rs              # UNCHANGED
    commands.rs         # UNCHANGED (spawn_pty stays generic)
  session.rs            # UNCHANGED

apps/voss-app/src-tauri/src/
  lib.rs                # ADD: spawn_agent + registry query wrappers

apps/voss-app/src/
  pane/
    PaneComponent.tsx   # MODIFY: optional agentConfig prop, branching spawn
    pty-ipc.ts          # ADD: spawnAgent() method (or modify spawn)
  grid/
    SplitNode.tsx        # MODIFY: pass agentConfig to PaneComponent
    tree.ts              # POSSIBLY: extend PaneLeaf with optional agentConfig
  workspaces/
    workspaceSessionPersist.ts  # MODIFY: add registry last_seen in close handler
  command-palette/
    registry.ts          # ADD: "Start Agent" command definition
```

### Pattern 1: Cross-crate Tauri Command Wrappers
**What:** App-level `#[tauri::command]` functions in `apps/voss-app/src-tauri/src/lib.rs` delegate to `voss-app-core` public functions. This is required because `tauri::generate_handler!` only resolves command macros from the same crate.
**When to use:** Every new Tauri command exposed from `voss-app-core`.
**Example:**
```rust
// apps/voss-app/src-tauri/src/lib.rs
// Source: A2/A3/A4/A6 established pattern (verified in codebase)
#[tauri::command]
async fn spawn_agent(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    cwd: Option<String>,
    cli_binary: String,
    cli_args: Vec<String>,
    session_id: String,
    pane_id: String,
    registry: tauri::State<'_, Mutex<rusqlite::Connection>>,
    pty_state: tauri::State<'_, Arc<PtyRegistry>>,
) -> Result<String, String> {
    // delegates to voss_app_core::agent_registry::spawn_agent(...)
}
```

### Pattern 2: Mutex State Management
**What:** Single-owner Mutex wrapping a stateful resource, managed via `app.manage()` in plugin setup.
**When to use:** Thread-safe shared state in Tauri.
**Example:**
```rust
// Source: grid.rs Mutex<GridState> pattern + pty Arc<PtyRegistry> pattern
// In lib.rs init():
.setup(|app, _api| {
    app.manage(Arc::new(PtyRegistry::default()));
    // F1 adds:
    let conn = agent_registry::open_registry(project_path)?;
    app.manage(Mutex::new(conn));
    Ok(())
})
```

### Pattern 3: Registry Path Resolution
**What:** Deterministic path for the SQLite file following the same `.voss/` convention as session.json.
**When to use:** Registry file location.
**Example:**
```rust
// Source: session.rs session_path() pattern (verified in codebase)
pub fn registry_path(workspace: &Path) -> PathBuf {
    workspace.join(".voss").join("agent-registry.sqlite")
}

pub fn global_registry_path() -> PathBuf {
    // ~/.config/voss-app/agent-registry.sqlite
    config_voss_app_dir().join("agent-registry.sqlite")
}
```

### Pattern 4: PTY Exit Hook for Registry Update
**What:** When the PTY reader detects EOF/exit, update the agent registry status to 'stopped' before removing the session from `PtyRegistry`.
**When to use:** D-10 agent exit lifecycle.
**Example:**
```rust
// Source: reader.rs exit path (verified in codebase, lines 47-57)
// Current: registry.remove(&session_id) on EOF
// F1: before remove, check if session has an agent registry entry and
// update status to 'stopped'. The agent_registry Connection is passed
// to start_reader or resolved from a shared reference.
```

### Anti-Patterns to Avoid
- **Do not modify `spawn_session()` or `PtySession`:** The PTY layer stays generic (D-02). Agent awareness lives in `agent_registry.rs` only.
- **Do not use WAL mode or fsync:** F1 is boot-only best-effort (SPEC boundary). Default SQLite journal mode is fine.
- **Do not add a background watchdog thread:** F1 is startup-path only. No runtime health monitoring (SPEC boundary).
- **Do not store agentConfig in session.json:** The registry is the single source of truth for agent metadata. A6's `session.json` stores tree geometry only.
- **Do not use `structuredClone` on Solid store proxies:** The codebase has a known issue where Solid produce-draft Proxies cannot be structuredCloned (memory: voss-app-solid-produce-no-structuredclone). Any tree data passed to helper functions must be spread-cloned first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQLite access | Raw FFI to libsqlite3 | `rusqlite` 0.39 with `bundled` | Ergonomic Rust bindings; bundled avoids system dep; well-maintained |
| UUID generation | Custom ID scheme | `uuid::Uuid::new_v4()` | Already used by PTY sessions (spawn_session in pty/mod.rs:159) |
| Thread-safe DB access | Custom locking | `std::sync::Mutex<Connection>` | Matches existing crate patterns; brief locks only |
| JSON array serialization | Custom format for cli_args | `serde_json::to_string(&args)` / `from_str` | Store cli_args as JSON TEXT column; deserialize on read |
| Timestamp | Custom epoch math | `std::time::SystemTime::now().duration_since(UNIX_EPOCH)` | Store as INTEGER epoch seconds in SQLite |
| File locking for registry | fs2 advisory locks | SQLite's built-in locking | SQLite handles concurrent access internally; no need for external locks |

**Key insight:** The registry is a simple CRUD layer with 7 columns. rusqlite + Mutex + existing Tauri patterns cover every need. No framework-level additions required.

## Common Pitfalls

### Pitfall 1: rusqlite Connection is not Send
**What goes wrong:** `rusqlite::Connection` is `!Send` by default. Wrapping it in `Mutex` and putting it in Tauri managed state requires `Send + Sync`.
**Why it happens:** SQLite connections are thread-local by design.
**How to avoid:** Use `rusqlite::Connection::open()` which creates a thread-safe connection when accessed through Mutex. Tauri's async command pattern with `spawn_blocking` ensures DB operations don't block the async executor. Alternative: use a dedicated DB thread with a channel, but Mutex is simpler and matches the codebase pattern. [ASSUMED -- verify rusqlite Send bounds at implementation time]
**Warning signs:** Compile error: "the trait `Send` is not implemented for `Connection`"

### Pitfall 2: Registry init timing vs project path availability
**What goes wrong:** The registry path depends on the project path, but the project path may not be known at plugin init time (project-less mode, or project opened after boot).
**Why it happens:** `init()` runs once at app startup; project selection happens later in the frontend.
**How to avoid:** Use a `Mutex<Option<Connection>>` that starts as `None` and is lazily opened on the first `spawn_agent` call when the project path becomes known. Or open the global registry at init and switch to the project-specific registry when a project opens. The global fallback path (`~/.config/voss-app/agent-registry.sqlite`) is always available.
**Warning signs:** Panic on `unwrap()` of `None` connection before project is set.

### Pitfall 3: Boot restore race with PaneComponent mount
**What goes wrong:** If PaneComponent mounts and calls `spawn_pty` before the registry query completes, agent panes get plain shells instead of agent sessions.
**Why it happens:** Solid reactive rendering is eager; the registry query is async IPC.
**How to avoid:** D-04 specifies frontend orchestration. The registry query must complete before PaneComponent mounts. Use the existing `initialSession` prop pattern: App.tsx already waits for session load before passing `initialSession` to GridRoot. F1 adds a parallel registry query that resolves alongside session load, and the results are merged into the PaneComponent props. The `agentConfig` prop on PaneComponent means no mount happens until the data is ready.
**Warning signs:** Agent panes show a plain shell prompt instead of the CLI agent on restart.

### Pitfall 4: Orphan sweep must run AFTER agent restart
**What goes wrong:** If orphan sweep runs before boot restart, it marks agents as stopped that should have been restarted.
**Why it happens:** Both happen at boot time; ordering matters.
**How to avoid:** D-11 specifies the order: A6 restore -> F1 agent restart -> orphan sweep. The frontend controls this sequence. Only after all matched agents have been spawned should the orphan sweep IPC call fire.
**Warning signs:** All agent entries get marked 'stopped' on boot; no agents restart.

### Pitfall 5: close-requested handler reentry after F1 addition
**What goes wrong:** The close-requested handler already has a reentry guard (`isClosingAfterSave`). Adding an F1 registry update step between session save and `window.close()` must not break this guard.
**Why it happens:** The handler calls `event.preventDefault()` then re-issues `close()` after save. If the registry update fails, the window could stay open or enter an infinite loop.
**How to avoid:** The registry update should be best-effort: wrap in try/catch, log errors, but do not prevent window close. The existing pattern in `workspaceSessionPersist.ts` lines 93-118 is the exact insertion point -- add the registry call between the session save loop and the `isClosingAfterSave = true` line.
**Warning signs:** App won't quit; close-requested fires repeatedly.

### Pitfall 6: PaneLeaf schema change breaks A6 session round-trip
**What goes wrong:** If `agentConfig` is stored on `PaneLeaf` in the tree and persisted through A6's `session.json`, the schema version must be bumped or the field made optional.
**Why it happens:** `buildSessionFile()` whitelist-copies tree fields (sessionCommands.ts:118-135 `cloneCanonical`). New fields not in the whitelist are dropped; fields in the whitelist but not in the Rust `GridState` serde will fail deserialization.
**How to avoid:** Do NOT add agentConfig to `PaneLeaf` or `GridState`. The registry is the sole source of truth. PaneComponent receives `agentConfig` via prop injection from the boot restore path, not from the serialized tree. The A6 session.json schema stays unchanged.
**Warning signs:** Existing session.json files fail to load after F1 deployment.

## Code Examples

### Registry Schema Creation
```rust
// Source: SPEC REQ-1 + CONTEXT D-01 (design decisions)
pub fn create_schema(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS agent_sessions (
            pane_id    TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            cli_binary TEXT NOT NULL,
            cli_args   TEXT NOT NULL DEFAULT '[]',
            cwd        TEXT NOT NULL,
            status     TEXT NOT NULL DEFAULT 'active'
                       CHECK(status IN ('active', 'stopped')),
            last_seen  INTEGER NOT NULL
        );"
    )?;
    Ok(())
}
```

### Registry CRUD Operations
```rust
// Source: CONTEXT D-01 CRUD operations pattern
pub fn register_agent(
    conn: &Connection,
    pane_id: &str,
    session_id: &str,
    cli_binary: &str,
    cli_args: &[String],
    cwd: &str,
) -> rusqlite::Result<()> {
    let args_json = serde_json::to_string(cli_args)
        .unwrap_or_else(|_| "[]".to_string());
    let now = epoch_seconds();
    conn.execute(
        "INSERT OR REPLACE INTO agent_sessions
         (pane_id, session_id, cli_binary, cli_args, cwd, status, last_seen)
         VALUES (?1, ?2, ?3, ?4, ?5, 'active', ?6)",
        rusqlite::params![pane_id, session_id, cli_binary, args_json, cwd, now],
    )?;
    Ok(())
}

pub fn mark_stopped(conn: &Connection, pane_id: &str) -> rusqlite::Result<()> {
    conn.execute(
        "UPDATE agent_sessions SET status = 'stopped', last_seen = ?1
         WHERE pane_id = ?2",
        rusqlite::params![epoch_seconds(), pane_id],
    )?;
    Ok(())
}

pub fn update_last_seen_all(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute(
        "UPDATE agent_sessions SET last_seen = ?1 WHERE status = 'active'",
        rusqlite::params![epoch_seconds()],
    )?;
    Ok(())
}

pub fn get_active_agents(conn: &Connection) -> rusqlite::Result<Vec<AgentEntry>> {
    let mut stmt = conn.prepare(
        "SELECT pane_id, session_id, cli_binary, cli_args, cwd, status, last_seen
         FROM agent_sessions WHERE status = 'active'"
    )?;
    let rows = stmt.query_map([], |row| {
        Ok(AgentEntry {
            pane_id: row.get(0)?,
            session_id: row.get(1)?,
            cli_binary: row.get(2)?,
            cli_args: row.get(3)?,
            cwd: row.get(4)?,
            status: row.get(5)?,
            last_seen: row.get(6)?,
        })
    })?;
    rows.collect()
}

pub fn sweep_orphans(
    conn: &Connection,
    valid_pane_ids: &[&str],
) -> rusqlite::Result<usize> {
    // Mark active rows whose pane_id is NOT in the restored tree
    if valid_pane_ids.is_empty() {
        return conn.execute(
            "UPDATE agent_sessions SET status = 'stopped'
             WHERE status = 'active'",
            [],
        );
    }
    let placeholders: String = valid_pane_ids.iter()
        .enumerate()
        .map(|(i, _)| format!("?{}", i + 2))
        .collect::<Vec<_>>()
        .join(",");
    let sql = format!(
        "UPDATE agent_sessions SET status = 'stopped', last_seen = ?1
         WHERE status = 'active' AND pane_id NOT IN ({})",
        placeholders
    );
    let mut params: Vec<Box<dyn rusqlite::types::ToSql>> = vec![
        Box::new(epoch_seconds())
    ];
    for id in valid_pane_ids {
        params.push(Box::new(id.to_string()));
    }
    conn.execute(&sql, rusqlite::params_from_iter(params.iter().map(|p| p.as_ref())))
}
```

### Frontend Boot Restore Integration
```typescript
// Source: App.tsx restoreWorkspaceFromRecord pattern (verified in codebase)
// After loadSession() and before GridRoot mounts:
const restoreWorkspaceFromRecord = async (ws, record) => {
  // ... existing session load ...
  
  // F1: query registry for active agents in parallel
  const activeAgents: AgentEntry[] = await invoke('get_active_agents', {
    workspacePath: record.projectPath ?? null,
  }).catch(() => []);
  
  // Build agentConfig map keyed by pane_id
  const agentConfigByPaneId = new Map<string, AgentConfig>();
  for (const agent of activeAgents) {
    agentConfigByPaneId.set(agent.paneId, {
      cliBinary: agent.cliBinary,
      cliArgs: JSON.parse(agent.cliArgs),
      sessionId: agent.sessionId,
    });
  }
  
  // Pass to GridRoot via new prop or merge into initial session
  ws.setAgentConfigs(agentConfigByPaneId);
};
```

### spawn_agent Command (Rust side)
```rust
// Source: pty/commands.rs spawn_pty pattern (verified in codebase)
pub async fn spawn_agent(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    cwd: Option<String>,
    cli_binary: String,
    cli_args: Vec<String>,
    session_id: String,
    pane_id: String,
    registry_conn: tauri::State<'_, Mutex<Connection>>,
    pty_state: tauri::State<'_, Arc<PtyRegistry>>,
) -> Result<String, String> {
    // Build the command: cli_binary + cli_args
    // spawn_session variant that runs cli_binary instead of $SHELL
    // ... (note: spawn_session currently hardcodes $SHELL; F1 needs
    //      a variant or extension that accepts an arbitrary command)
    
    // Register in SQLite
    let conn = registry_conn.lock().map_err(|e| e.to_string())?;
    agent_registry::register_agent(
        &conn, &pane_id, &session_id, &cli_binary, &cli_args,
        cwd.as_deref().unwrap_or("."),
    ).map_err(|e| e.to_string())?;
    drop(conn); // release lock before spawning
    
    // Spawn PTY with the agent command
    // ... PTY spawn + reader start ...
    Ok(pty_id)
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `rusqlite` 0.32 | `rusqlite` 0.39.0 | 2025 | API stable; `bundled` feature compiles SQLite 3.51.3 |
| `portable-pty` hardcoded $SHELL | F1 needs arbitrary command spawn | This phase | Must extend or wrap `spawn_session` to accept custom commands |

**Deprecated/outdated:**
- None relevant. `rusqlite` API is stable across recent versions.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rusqlite` 0.39 is the current latest and the standard Rust SQLite binding | Standard Stack | Low -- well-known crate, `cargo search` confirms 0.39.0 |
| A2 | `rusqlite::Connection` behind `Mutex` satisfies Tauri's `Send + Sync` requirement for managed state | Pitfall 1 | Medium -- if Connection is `!Send`, need a dedicated DB thread pattern instead |
| A3 | `bundled` feature compiles SQLite from source without additional system deps on macOS | Standard Stack | Low -- widely documented pattern |
| A4 | `spawn_session()` can be extended or wrapped to accept an arbitrary command instead of `$SHELL` | Architecture | Medium -- if `portable-pty` CommandBuilder cannot be customized, need a parallel spawn path |

## Open Questions (RESOLVED)

1. **spawn_session extension for arbitrary commands** — RESOLVED: New `spawn_command_session(cmd, args, rows, cols, cwd)` function alongside `spawn_session()`. No signature change to existing API. Plans F1-01 Task 1 implements this.

2. **Registry Connection lifecycle with project switching** — RESOLVED: `Mutex<Option<Connection>>` lazily opened on first `spawn_agent` call with the workspace path. Plans F1-01 Task 2 implements this.

3. **PTY exit callback plumbing for registry update (D-10)** — RESOLVED: Frontend approach chosen — PtyTransport `handle()` invokes `mark_agent_stopped` via IPC on exit event. Simpler than passing Connection to reader thread (no reader.rs signature change). Plans F1-03 Task 1 implements this.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust toolchain | All Rust code | Yes | 1.95.0-nightly | -- |
| `cargo` | Build | Yes | (bundled with rustc) | -- |
| `rusqlite` (crate) | REQ-1 | Yes (crates.io) | 0.39.0 | -- |
| SQLite (system) | N/A (bundled) | N/A | N/A | `bundled` feature compiles from source |
| `pnpm` | Frontend build | Yes | (assumed from monorepo) | -- |
| vitest | Frontend tests | Yes | (configured in vitest.config.ts) | -- |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (Rust) | `cargo test -p voss-app-core` |
| Framework (TS) | vitest (`pnpm vitest --run`) |
| Config file (Rust) | Cargo.toml (standard) |
| Config file (TS) | `apps/voss-app/vitest.config.ts` |
| Quick run command | `cargo test -p voss-app-core -- agent_registry && cd apps/voss-app && pnpm vitest --run src/**/*agent*` |
| Full suite command | `cargo test -p voss-app-core && cd apps/voss-app && pnpm vitest --run` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-1 | Registry schema + CRUD | unit (Rust) | `cargo test -p voss-app-core -- agent_registry -x` | Wave 0 |
| REQ-1 | Status transition active->stopped | unit (Rust) | same | Wave 0 |
| REQ-2 | Path resolution project vs global | unit (Rust) | same | Wave 0 |
| REQ-3 | spawn_agent creates PTY + row | integration (Rust) | `cargo test -p voss-app-core -- agent_registry::tests::spawn -x` | Wave 0 |
| REQ-4 | Boot restore loads active agents | unit (TS) | `cd apps/voss-app && pnpm vitest --run -t "agent restore"` | Wave 0 |
| REQ-5 | Close handler updates last_seen | unit (TS) | `cd apps/voss-app && pnpm vitest --run -t "close session"` | Wave 0 |
| REQ-5 (AC) | last_seen within 2s of quit | unit (Rust) | `cargo test -p voss-app-core -- agent_registry::tests::last_seen -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cargo test -p voss-app-core -- agent_registry && cd apps/voss-app && pnpm vitest --run`
- **Per wave merge:** Full suite: `cargo test -p voss-app-core && cd apps/voss-app && pnpm vitest --run && tsc --noEmit`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `crates/voss-app-core/src/agent_registry.rs` -- new module with tests
- [ ] `apps/voss-app/src/**/__tests__/*agent*.test.ts` -- frontend agent config / restore tests
- [ ] `rusqlite` dependency in Cargo.toml -- must build clean

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | -- |
| V3 Session Management | no | -- |
| V4 Access Control | no | -- |
| V5 Input Validation | yes | Validate `cli_binary` is a non-empty string; sanitize `pane_id` / `session_id` as UUIDs; `cli_args` stored as JSON array via serde (no SQL injection) |
| V6 Cryptography | no | -- |

### Known Threat Patterns for SQLite + CLI spawn

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via pane_id/session_id | Tampering | Parameterized queries (rusqlite `params![]`) -- never string interpolation |
| Arbitrary command execution via cli_binary | Elevation of Privilege | cli_binary is user-provided from command palette; same trust boundary as typing in a shell. No additional restriction needed for F1 (user explicitly chose the command). |
| Path traversal in registry path | Tampering | `workspace.join(".voss")` -- workspace path comes from A5 project open, already validated |
| SQLite file tampering | Tampering | Local-only, single-user app. No additional protection needed for F1. |

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `session.rs`, `pty/mod.rs`, `pty/commands.rs`, `pty/reader.rs`, `lib.rs` (both crates), `App.tsx`, `GridRoot.tsx`, `PaneComponent.tsx`, `SplitNode.tsx`, `sessionPersist.ts`, `workspaceSessionPersist.ts`, `sessionCommands.ts`, `sessionStorage.ts`, `registry.ts`, `pty-ipc.ts`, `tree.ts`
- `cargo search rusqlite` -- confirmed 0.39.0 latest
- F1-SPEC.md and F1-CONTEXT.md -- locked requirements and decisions

### Secondary (MEDIUM confidence)
- [docs.rs/rusqlite/0.39.0](https://docs.rs/rusqlite/0.39.0/rusqlite/) -- Connection API, params!, query_map patterns
- [crates.io/crates/rusqlite](https://crates.io/crates/rusqlite) -- version, bundled feature documentation

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- single new dependency (rusqlite), well-known, version-confirmed
- Architecture: HIGH -- all integration points verified in codebase; patterns established by A2/A3/A4/A6/A7/A8
- Pitfalls: HIGH -- all derived from verified codebase patterns and known Solid/Tauri constraints

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (stable domain -- rusqlite API unlikely to change)
