# Phase F1: Durable Session Persistence - Pattern Map

**Mapped:** 2026-05-20
**Files analyzed:** 8 (new/modified)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `crates/voss-app-core/src/agent_registry.rs` | service | CRUD | `crates/voss-app-core/src/session.rs` | role-match |
| `crates/voss-app-core/src/pty/mod.rs` | service | request-response | (self — extend `spawn_session`) | exact |
| `crates/voss-app-core/src/lib.rs` | config | request-response | (self — extend plugin init) | exact |
| `apps/voss-app/src-tauri/src/lib.rs` | controller | request-response | (self — `spawn_pty` wrapper at lines 78-92) | exact |
| `apps/voss-app/src/pane/PaneComponent.tsx` | component | request-response | (self — `doSpawn` at lines 207-210) | exact |
| `apps/voss-app/src/workspaces/workspaceSessionPersist.ts` | middleware | event-driven | (self — `installAllWorkspacesCloseSave` lines 86-118) | exact |
| `apps/voss-app/src/grid/GridRoot.tsx` | component | request-response | (self — `initialSession` + `applySessionFile` pattern at lines 134-152) | exact |
| `apps/voss-app/src/command-palette/registry.ts` | config | event-driven | (self — `workspaceCommands()` at lines 269-323) | exact |

## Pattern Assignments

### `crates/voss-app-core/src/agent_registry.rs` (NEW — service, CRUD)

**Analog:** `crates/voss-app-core/src/session.rs`

**Imports pattern** (lines 17-21):
```rust
use std::path::{Path, PathBuf};

use fs2::FileExt;
use serde::{Deserialize, Serialize};

use crate::grid::GridState;
```

F1 equivalent: replace `fs2`/`serde`/`crate::grid` with `rusqlite` + `serde_json` + `std::time`.

**Error type pattern** (lines 68-74):
```rust
/// Typed errors for session save/load. Display strings are safe for UI
/// passthrough — no Rust internals leak.
#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    #[error("could not save session")]
    SaveFailed,
    #[error("could not load session")]
    LoadFailed,
}
```

F1: define `AgentRegistryError` with `thiserror::Error` derive, UI-safe Display strings. Variants: `OpenFailed`, `QueryFailed`, `WriteFailed`.

**Path resolution pattern** (lines 79-88):
```rust
/// `<workspace>/.voss/session.json`
pub fn session_path(workspace: &Path) -> PathBuf {
    workspace.join(".voss").join("session.json")
}

/// `~/.config/voss-app/global-session.json`
#[cfg(not(test))]
pub fn global_session_path() -> PathBuf {
    config_voss_app_dir().join("global-session.json")
}
```

F1: `registry_path(workspace)` returns `workspace.join(".voss").join("agent-registry.sqlite")`; `global_registry_path()` returns `config_voss_app_dir().join("agent-registry.sqlite")`. Use `#[cfg(test)]` overrides same as session.rs.

**Fail-safe load pattern** (lines 241-259):
```rust
fn fail_safe_load(path: &Path) -> Result<Option<SessionFile>, SessionError> {
    if !path.exists() {
        return Ok(None);
    }
    let raw = match std::fs::read_to_string(path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] could not read session: {e}");
            return Ok(None);
        }
    };
    match parse_session(&raw) {
        Ok(s) => Ok(Some(s)),
        Err(reason) => {
            eprintln!("[voss-app] session ignored: {reason}");
            Ok(None)
        }
    }
}
```

F1: `open_registry(path)` should follow fail-closed to `Ok(None)` or create-if-missing pattern. Log to stderr with `[voss-app]` prefix. Never crash startup.

**Test pattern** (lines 286-596):
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::{tempdir, TempDir};

    // ... sample helpers, then grouped #[test] fns ...
}
```

F1: use `tempdir()` for in-memory SQLite via `:memory:` or temp file path. Group tests by schema, CRUD, and lifecycle.

---

### `crates/voss-app-core/src/pty/mod.rs` (MODIFY — add `spawn_command_session`)

**Analog:** `spawn_session()` in same file (lines 116-170)

**Core spawn pattern** (lines 116-170):
```rust
pub fn spawn_session(
    rows: u16,
    cols: u16,
    cwd: Option<String>,
) -> anyhow::Result<(
    Arc<PtySession>,
    Box<dyn Read + Send>,
    tokio::sync::mpsc::Receiver<bool>,
)> {
    let pair = native_pty_system()
        .openpty(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .context("openpty")?;

    let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".to_string());
    let shell_name = std::path::Path::new(&shell)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("sh")
        .to_string();

    let mut cmd = CommandBuilder::new(&shell);
    cmd.env("TERM", "xterm-256color");
    cmd.env("COLORTERM", "truecolor");
    let cwd_path = match cwd {
        Some(c) => {
            cmd.cwd(&c);
            PathBuf::from(c)
        }
        None => std::env::current_dir().unwrap_or_else(|_| PathBuf::from("/")),
    };

    let child = pair.slave.spawn_command(cmd).context("spawn_command")?;
    let reader = pair.master.try_clone_reader().context("try_clone_reader")?;
    let writer = pair.master.take_writer().context("take_writer")?;

    let (pause_tx, pause_rx) = tokio::sync::mpsc::channel::<bool>(8);

    let session = Arc::new(PtySession {
        id: uuid::Uuid::new_v4(),
        master: Mutex::new(pair.master),
        writer: Mutex::new(writer),
        _slave: Mutex::new(pair.slave),
        child: Mutex::new(child),
        pause_tx,
        shell_name,
        cwd: cwd_path,
    });

    Ok((session, reader, pause_rx))
}
```

F1: create `spawn_command_session(cmd_binary, cmd_args, rows, cols, cwd)` that replaces the `$SHELL` lookup (lines 134-139) with `CommandBuilder::new(&cmd_binary)` + `cmd.args(cmd_args)`. The rest of the body (openpty, env, cwd, child spawn, reader/writer, session construction) is identical. The `shell_name` field stores `cmd_binary` basename.

---

### `crates/voss-app-core/src/lib.rs` (MODIFY — add module + state + handler)

**Analog:** self (lines 1-74)

**Module registration pattern** (lines 3-11):
```rust
pub mod appearance;
pub mod fonts;
pub mod grid;
pub mod keymap;
pub mod layouts;
pub mod profiles;
pub mod project;
pub mod pty;
pub mod session;
pub mod themes;
pub mod workspaces;
```

F1: add `pub mod agent_registry;` to this list.

**State management + plugin init pattern** (lines 58-74):
```rust
pub fn init<R: tauri::Runtime>() -> tauri::plugin::TauriPlugin<R> {
    tauri::plugin::Builder::new("voss-app-core")
        .invoke_handler(tauri::generate_handler![
            spawn_pty,
            pty_write,
            pty_resize,
            pty_pause,
            pty_resume,
            pty_kill,
            get_fg_process,
        ])
        .setup(|app, _api| {
            app.manage(Arc::new(PtyRegistry::default()));
            Ok(())
        })
        .build()
}
```

F1: add `Mutex<Option<rusqlite::Connection>>` to `app.manage(...)` in setup closure. Use `Option` because the DB opens lazily when a project path is known (Pitfall 2). Add `spawn_agent`, `get_active_agents`, `mark_agent_stopped`, `update_agents_last_seen`, `sweep_orphan_agents` to `generate_handler!`.

**Re-export pattern** (lines 15-51):
```rust
pub use pty::commands::{
    get_fg_process, pty_kill, pty_pause, pty_resize, pty_resume, pty_write, spawn_pty, PtyEvent,
};
pub use pty::{PtyRegistry, PtySession};
```

F1: add `pub use agent_registry::{...}` for types and functions the app crate needs.

---

### `apps/voss-app/src-tauri/src/lib.rs` (MODIFY — add spawn_agent wrapper)

**Analog:** `spawn_pty` wrapper in same file (lines 78-92)

**Cross-crate Tauri command wrapper pattern** (lines 68-92):
```rust
// Thin app-level #[tauri::command] wrappers over the voss-app-core `pty`
// public API. They live in the APP crate (not voss-app-core) because
// `tauri::generate_handler!` can only resolve the hidden command helper
// macros generated in the SAME crate ...

type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;

#[tauri::command]
async fn spawn_pty(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    cwd: Option<String>,
    state: Reg<'_>,
) -> Result<String, String> {
    let (session, reader, pause_rx) =
        spawn_session(rows, cols, cwd).map_err(|e| e.to_string())?;
    let registry: Arc<PtyRegistry> = Arc::clone(state.inner());
    let id = registry.insert(session);
    start_reader(id.clone(), reader, pause_rx, on_data, registry);
    Ok(id)
}
```

F1: create `spawn_agent` that mirrors this pattern but calls `spawn_command_session(cli_binary, cli_args, ...)` instead of `spawn_session(...)`, then writes a registry row via `agent_registry::register_agent(...)` before starting the reader. Takes additional params: `cli_binary: String, cli_args: Vec<String>, session_id: String, pane_id: String, registry_conn: tauri::State<'_, Mutex<Option<Connection>>>`.

**Managed state registration pattern** (lines 488-489):
```rust
.manage(Arc::new(PtyRegistry::default()))
.manage(Mutex::new(GridState::default()))
```

F1: add `.manage(Mutex::new(None::<rusqlite::Connection>))` (or `Arc<Mutex<Option<Connection>>>`) alongside the existing managed state.

**Command handler list pattern** (lines 491-536):
```rust
.invoke_handler(tauri::generate_handler![
    get_theme_overrides,
    spawn_pty,
    // ... 35+ commands ...
    list_system_fonts,
])
```

F1: add `spawn_agent`, `get_active_agents`, `mark_agent_stopped`, `update_agents_last_seen`, `sweep_orphan_agents` to this list.

---

### `apps/voss-app/src/pane/PaneComponent.tsx` (MODIFY — add agentConfig prop)

**Analog:** self — `PaneProps` interface (lines 31-44) and `doSpawn` (lines 207-210)

**Props pattern** (lines 31-44):
```typescript
export interface PaneProps {
  /** Pane id for scrollback registry and restore keying (A6). */
  id?: string;
  /** Working directory for the spawned shell; header shows its basename. */
  cwd?: string;
  /** $SHELL basename for the header shell slot (A2 = static; A8 wires real). */
  shell?: string;
  /** Pane index — A2 is always 1; A3 assigns real indices. */
  index?: number;
  /** Session-restored scrollback lines to seed before shell interaction (A6 D-09). */
  restoredScrollback?: string[];
  /** Called once on first user input in a restored pane (dismiss RestoreBanner). */
  onFirstInput?: () => void;
}
```

F1: add optional `agentConfig?: { cliBinary: string; cliArgs: string[]; sessionId: string }` to `PaneProps`.

**Spawn invocation pattern** (lines 207-210):
```typescript
const doSpawn = async (t: Terminal) => {
    await transport!.spawn({ rows: t.rows, cols: t.cols, cwd: props.cwd });
    setDot('running');
};
```

F1: branch on `props.agentConfig`: if present, call a new `transport.spawnAgent({...agentConfig, rows, cols, cwd})` instead of `transport.spawn(...)`. The PtyTransport needs a corresponding `spawnAgent` method.

**PtyTransport.spawn analog** (`apps/voss-app/src/pane/pty-ipc.ts` lines 96-104):
```typescript
async spawn(o: { rows: number; cols: number; cwd?: string }): Promise<string> {
    this.sessionId = await invoke<string>('spawn_pty', {
      onData: this.channel,
      rows: o.rows,
      cols: o.cols,
      cwd: o.cwd,
    });
    return this.sessionId;
}
```

F1: add `spawnAgent` method that invokes `'spawn_agent'` with additional `cliBinary`, `cliArgs`, `sessionId`, `paneId` params.

---

### `apps/voss-app/src/workspaces/workspaceSessionPersist.ts` (MODIFY — extend close handler)

**Analog:** self — `installAllWorkspacesCloseSave` (lines 86-118)

**Close-requested handler with reentry guard pattern** (lines 86-118):
```typescript
export async function installAllWorkspacesCloseSave(
  getContexts: () => WorkspaceSessionContext[],
  getIndex: () => WorkspacesIndex,
  saveIndex: (index: WorkspacesIndex) => Promise<void>,
): Promise<() => void> {
  let isClosingAfterSave = false;

  const unlisten = await getCurrentWindow().onCloseRequested(async (event) => {
    if (isClosingAfterSave) return;
    event.preventDefault();

    try {
      const scrollback = getScrollbackSnapshot(2000);
      const contexts = getContexts();

      for (const ctx of contexts) {
        await saveWorkspaceSession(ctx, scrollback);
      }

      await saveIndex(getIndex());

      isClosingAfterSave = true;
      await getCurrentWindow().close();
    } catch (e) {
      console.error(
        '[voss-app] all-workspace quit save failed — window kept open:',
        e,
      );
    }
  });

  return unlisten;
}
```

F1 (D-09): insert `await invoke('update_agents_last_seen', {...}).catch(...)` between `await saveIndex(getIndex())` (line 105) and `isClosingAfterSave = true` (line 107). The registry update MUST be best-effort (wrapped in `.catch()`) and MUST NOT prevent `window.close()`. This is the exact insertion point described in CONTEXT D-09.

---

### `apps/voss-app/src/grid/GridRoot.tsx` (MODIFY — boot restore registry query)

**Analog:** self — `initialSession` initialization pattern (lines 134-152)

**Session restore initialization pattern** (lines 134-152):
```typescript
// A6: initialize from restored session when available so no throwaway PTY spawns.
const initResult = props.initialSession
    ? applySessionFile(props.initialSession)
    : null;

const [store, setStore] = initResult
    ? createStore<GridStore>({
        root: initResult.root,
        focusedId: initResult.focusedId,
      })
    : createGridStore({ cwd: props.projectCwd });

// A6: restored scrollback map — keyed by saved pane id, cleared on first input.
const [restoredScrollbackByPaneId, setRestoredScrollbackByPaneId] =
    createSignal<Record<string, string[]>>(
      initResult
        ? Object.fromEntries(initResult.restoredScrollbackByPaneId)
        : {},
    );
```

F1: add a new prop `agentConfigByPaneId?: Map<string, AgentConfig>` to GridRoot. This is populated by the caller (App.tsx or workspace manager) BEFORE mounting GridRoot — the registry query completes before GridRoot renders. GridRoot passes agent configs through to SplitNodeView, which passes to PaneComponent via the new `agentConfig` prop. This follows the same pattern as `restoredScrollbackByPaneId`.

**SplitNode PaneComponent rendering** (`SplitNode.tsx` lines 125-132):
```typescript
<PaneComponent
  id={asLeaf().id}
  cwd={asLeaf().cwd}
  shell={asLeaf().shell}
  index={asLeaf().index}
  restoredScrollback={props.restoredScrollbackByPaneId?.[asLeaf().id]}
  onFirstInput={() => props.onPaneFirstInput?.(asLeaf().id)}
/>
```

F1: add `agentConfig={props.agentConfigByPaneId?.get?.(asLeaf().id)}` to the PaneComponent render.

---

### `apps/voss-app/src/command-palette/registry.ts` (MODIFY — add "Start Agent" command)

**Analog:** self — `workspaceCommands()` function (lines 269-323)

**Command catalog function pattern** (lines 269-282):
```typescript
export function workspaceCommands(): CommandDefinition[] {
  return [
    {
      id: 'workspace.new',
      label: 'New workspace',
      category: 'Workspace',
      handler: (ctx) => ctx.newWorkspace?.(),
    },
    // ...
  ];
}
```

F1: add a new `agentCommands()` export function returning a `CommandDefinition[]` with a single "Start Agent" command. Category can be `'Pane'` or a new `'Agent'` category (if the `CommandCategory` union is extended). The handler calls a new `ctx.startAgent?.()` method on `AppContext`.

**AppContext interface pattern** (lines 42-70):
```typescript
export interface AppContext {
  splitFocused: (orientation: 'H' | 'V') => void;
  closeFocused: () => void;
  // ...
  newWorkspace?: () => void;
  closeWorkspace?: () => void;
  // ...
}
```

F1: add `startAgent?: () => void` to `AppContext`. Optional (`?`) follows the established pattern for features added incrementally.

---

## Shared Patterns

### Cross-crate Tauri Command Wrappers
**Source:** `apps/voss-app/src-tauri/src/lib.rs` lines 68-92
**Apply to:** All new Tauri commands (`spawn_agent`, `get_active_agents`, `mark_agent_stopped`, `update_agents_last_seen`, `sweep_orphan_agents`)

Every Tauri command exposed from `voss-app-core` needs a thin app-level `#[tauri::command]` wrapper in `src-tauri/src/lib.rs` because `tauri::generate_handler!` only resolves macros from the same crate. Pattern: delegate to `voss_app_core::agent_registry::*` public functions, `.map_err(|e| e.to_string())` for error conversion.

### Mutex State Management
**Source:** `apps/voss-app/src-tauri/src/lib.rs` lines 488-489, `crates/voss-app-core/src/grid.rs` lines 78-84
**Apply to:** `agent_registry.rs` (Connection ownership), `lib.rs` plugin init

```rust
// grid.rs pattern — Mutex<T> managed as Tauri state
.manage(Mutex::new(GridState::default()))

// grid.rs lock-and-operate pattern (lines 78-84)
pub fn overwrite(slot: &Mutex<GridState>, new_state: GridState) -> Result<(), String> {
    let mut guard = slot
        .lock()
        .map_err(|e| format!("grid state mutex poisoned: {e}"))?;
    *guard = new_state;
    Ok(())
}
```

F1: `Mutex<Option<Connection>>` for lazy init; lock briefly, operate, drop guard before any async work.

### Error Handling — Rust Side
**Source:** `crates/voss-app-core/src/session.rs` lines 68-74
**Apply to:** `agent_registry.rs`

`thiserror::Error` derive with UI-safe Display strings. `eprintln!("[voss-app] ...")` for internal diagnostics. Fail-closed to `Ok(None)` or `Ok(())` where appropriate — never crash startup.

### Error Handling — Frontend Side
**Source:** `apps/voss-app/src/workspaces/workspaceSessionPersist.ts` line 109
**Apply to:** All F1 frontend IPC calls (registry query, last_seen update, orphan sweep)

```typescript
console.error('[voss-app] all-workspace quit save failed — window kept open:', e);
```

Pattern: `.catch((e) => console.error('[voss-app] ...', e))` for best-effort IPC. Never block window close or pane mount on registry failure.

### PTY Reader Exit Hook
**Source:** `crates/voss-app-core/src/pty/reader.rs` lines 47-57
**Apply to:** D-10 agent exit lifecycle

```rust
let code = registry
    .get(&session_id)
    .and_then(|s| {
        let c = s.try_exit_code();
        let _ = s.kill();
        c
    })
    .unwrap_or(0);
let _ = on_data.send(PtyEvent::Exit { code });
registry.remove(&session_id);
```

F1: before `registry.remove(&session_id)`, check if this session has an agent registry entry and call `agent_registry::mark_stopped(conn, pane_id)`. Requires passing `Arc<Mutex<Option<Connection>>>` to `start_reader` (or a callback).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | -- | -- | All files have analogs in the existing codebase |

Every F1 file either extends an existing module or follows an established crate pattern. No greenfield patterns are needed.

## Metadata

**Analog search scope:** `crates/voss-app-core/src/`, `apps/voss-app/src-tauri/src/`, `apps/voss-app/src/`
**Files scanned:** 14 analog files read
**Pattern extraction date:** 2026-05-20
