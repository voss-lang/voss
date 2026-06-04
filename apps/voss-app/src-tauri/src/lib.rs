use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use std::time::{Duration, SystemTime};

use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use tauri::Emitter;
use voss_app_core::agent_registry::{
    get_active_agents as registry_get_active_agents, global_registry_path, mark_stopped,
    open_registry, register_agent, registry_path, sweep_orphans, update_last_seen_all, AgentEntry,
};
use voss_app_core::appearance::{self, AppearanceSettings};
use voss_app_core::fonts;
use voss_app_core::grid::{self, GridState};
use voss_app_core::keymap::{self, KeymapOverrideFile, KeymapProfile, KeymapValidationResult};
use voss_app_core::layouts::{self, LayoutFile};
use voss_app_core::profiles::{self, ProfileFile};
use voss_app_core::project::{self, ProjectInfo};
use voss_app_core::pty::reader::start_reader;
use voss_app_core::pty::writer::validate_write;
use voss_app_core::pty::{foreground, spawn_command_session_with_env, spawn_session};
use voss_app_core::session::{self, SessionFile};
use voss_app_core::themes::{self, CustomThemeFile};
use voss_app_core::workspaces::{self, WorkspacesIndex};
use voss_app_core::{PtyEvent, PtyRegistry};

#[derive(Debug, Deserialize, Serialize, Clone)]
struct CustomAgent {
    name: String,
    command: String,
}

#[derive(Debug, Deserialize, Serialize, Default)]
struct SettingsFile {
    theme: Option<HashMap<String, String>>,
    custom_agents: Option<Vec<CustomAgent>>,
}

fn settings_path() -> PathBuf {
    // NOTE: build the path manually from home_dir() so it resolves to
    // ~/.config/voss-app/settings.json on every platform (CONTEXT D-08/D-09).
    // The `dirs` crate's platform-native config helper is intentionally NOT
    // used: on macOS it resolves to ~/Library/Application Support, which
    // diverges from the user-facing ~/.config path locked by D-08.
    // See A1-RESEARCH.md Pitfall 8 and A1-UI-SPEC.md Theme Override System Contract.
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("settings.json")
}

#[tauri::command]
fn get_theme_overrides() -> HashMap<String, String> {
    let path = settings_path();
    if !path.exists() {
        return HashMap::new();
    }
    let raw = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] failed to read settings: {e}");
            return HashMap::new();
        }
    };
    let settings: SettingsFile = match serde_json::from_str(&raw) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] failed to parse settings: {e}");
            return HashMap::new();
        }
    };
    settings.theme.unwrap_or_default()
}

#[tauri::command]
fn load_custom_agents() -> Vec<CustomAgent> {
    let path = settings_path();
    if !path.exists() {
        return Vec::new();
    }
    let raw = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(_) => return Vec::new(),
    };
    let settings: SettingsFile = match serde_json::from_str(&raw) {
        Ok(s) => s,
        Err(_) => return Vec::new(),
    };
    settings.custom_agents.unwrap_or_default()
}

#[tauri::command]
fn save_custom_agents(agents: Vec<CustomAgent>) -> Result<(), String> {
    let path = settings_path();
    let mut settings: SettingsFile = if path.exists() {
        std::fs::read_to_string(&path)
            .ok()
            .and_then(|raw| serde_json::from_str(&raw).ok())
            .unwrap_or_default()
    } else {
        SettingsFile::default()
    };
    settings.custom_agents = Some(agents);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())?;
    Ok(())
}

// ---- PTY commands ---------------------------------------------------------
// Thin app-level #[tauri::command] wrappers over the voss-app-core `pty`
// public API. They live in the APP crate (not voss-app-core) because
// `tauri::generate_handler!` can only resolve the hidden command helper
// macros generated in the SAME crate — a `pub use` of cross-crate commands
// does not bring those macros into scope. This keeps the frontend's bare
// `invoke('spawn_pty', …)` contract and app-managed `Arc<PtyRegistry>` state.

type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;
type AgentDb<'a> = tauri::State<'a, Mutex<Option<Connection>>>;

fn ensure_registry<'a>(
    db: &'a Mutex<Option<Connection>>,
    workspace_path: Option<&str>,
) -> Result<std::sync::MutexGuard<'a, Option<Connection>>, String> {
    let mut guard = db
        .lock()
        .map_err(|_| "agent registry lock poisoned".to_string())?;
    if guard.is_none() {
        let path = match workspace_path {
            Some(ws) => registry_path(Path::new(ws)),
            None => global_registry_path(),
        };
        let conn = open_registry(&path).map_err(|e| e.to_string())?;
        *guard = Some(conn);
    }
    Ok(guard)
}

fn is_voss_cli_binary(cli_binary: &str) -> bool {
    Path::new(cli_binary)
        .file_name()
        .and_then(|s| s.to_str())
        .is_some_and(|name| name == "voss" || name == "voss.exe")
}

/// Classify whether a Voss CLI invocation is interactive (→ full Textual TUI)
/// or one-shot (→ compact renderer).
///
/// Interactive commands that enter the REPL: `chat`, `resume`, `edit`, and bare
/// `voss` (no subcommand — click group defaults to `chat`).
fn is_interactive_voss_command(cli_args: &[String]) -> bool {
    match cli_args.first().map(|s| s.as_str()) {
        None => true, // bare `voss` → defaults to chat
        Some("chat" | "resume" | "edit") => true,
        _ => false,
    }
}

fn env_for_embedded_cli(
    cli_binary: &str,
    cli_args: &[String],
) -> Vec<(&'static str, &'static str)> {
    if !is_voss_cli_binary(cli_binary) {
        return Vec::new();
    }

    if is_interactive_voss_command(cli_args) {
        return vec![("VOSS_EMBEDDED", "1"), ("VOSS_FORCE_TUI", "1")];
    }

    vec![("VOSS_EMBEDDED", "1"), ("VOSS_RENDERER", "compact")]
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
async fn spawn_agent(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    cwd: Option<String>,
    cli_binary: String,
    cli_args: Vec<String>,
    session_id: String,
    pane_id: String,
    workspace_path: Option<String>,
    db: AgentDb<'_>,
    pty_state: Reg<'_>,
) -> Result<String, String> {
    let mut guard = ensure_registry(db.inner(), workspace_path.as_deref())?;
    let conn = guard
        .as_mut()
        .ok_or_else(|| "agent registry unavailable".to_string())?;

    let embedded_env = env_for_embedded_cli(&cli_binary, &cli_args);
    let (session, reader, pause_rx) = spawn_command_session_with_env(
        &cli_binary,
        &cli_args,
        &embedded_env,
        rows,
        cols,
        cwd.clone(),
    )
    .map_err(|e| e.to_string())?;
    let registry: Arc<PtyRegistry> = Arc::clone(pty_state.inner());
    let pty_id = registry.insert(session);
    start_reader(pty_id.clone(), reader, pause_rx, on_data, registry);

    let cwd_str = cwd.as_deref().unwrap_or("");
    register_agent(conn, &pane_id, &session_id, &cli_binary, &cli_args, cwd_str)
        .map_err(|e| e.to_string())?;

    Ok(pty_id)
}

#[cfg(test)]
mod tests {
    use super::{env_for_embedded_cli, is_interactive_voss_command};

    const TUI_ENV: [(&str, &str); 2] = [("VOSS_EMBEDDED", "1"), ("VOSS_FORCE_TUI", "1")];
    const COMPACT_ENV: [(&str, &str); 2] = [("VOSS_EMBEDDED", "1"), ("VOSS_RENDERER", "compact")];

    #[test]
    fn interactive_commands_classified_correctly() {
        // Bare voss (no subcommand) defaults to chat
        assert!(is_interactive_voss_command(&[]));
        assert!(is_interactive_voss_command(&["chat".into()]));
        assert!(is_interactive_voss_command(&[
            "chat".into(),
            "--model".into(),
            "gpt-4o".into()
        ]));
        assert!(is_interactive_voss_command(&[
            "resume".into(),
            "session-123".into()
        ]));
        assert!(is_interactive_voss_command(&[
            "edit".into(),
            "file.py".into()
        ]));

        // Non-interactive
        assert!(!is_interactive_voss_command(&["do".into(), "task".into()]));
        assert!(!is_interactive_voss_command(&["doctor".into()]));
        assert!(!is_interactive_voss_command(&[
            "agent".into(),
            "spawn".into()
        ]));
        assert!(!is_interactive_voss_command(&["sessions".into()]));
        assert!(!is_interactive_voss_command(&["config".into()]));
    }

    #[test]
    fn voss_chat_command_gets_embedded_tui_env() {
        let args = vec!["chat".to_string()];
        assert_eq!(env_for_embedded_cli("voss", &args), TUI_ENV);
    }

    #[test]
    fn bare_voss_gets_embedded_tui_env() {
        assert_eq!(env_for_embedded_cli("voss", &[]), TUI_ENV);
    }

    #[test]
    fn voss_resume_gets_embedded_tui_env() {
        let args = vec!["resume".to_string(), "sess-abc".to_string()];
        assert_eq!(env_for_embedded_cli("voss", &args), TUI_ENV);
    }

    #[test]
    fn voss_edit_gets_embedded_tui_env() {
        let args = vec!["edit".to_string(), "main.py".to_string()];
        assert_eq!(env_for_embedded_cli("voss", &args), TUI_ENV);
    }

    #[test]
    fn voss_non_interactive_command_gets_compact_env() {
        let args = vec!["do".to_string(), "task".to_string()];
        assert_eq!(env_for_embedded_cli("voss", &args), COMPACT_ENV);
    }

    #[test]
    fn path_voss_binary_gets_env_but_other_agents_do_not() {
        let chat_args = vec!["chat".to_string()];
        let claude_args = vec!["--model=opus".to_string()];
        assert_eq!(env_for_embedded_cli("/opt/bin/voss", &chat_args), TUI_ENV);
        assert_eq!(env_for_embedded_cli("voss.exe", &chat_args), TUI_ENV);
        assert!(env_for_embedded_cli("claude", &claude_args).is_empty());
    }
}

#[tauri::command]
fn get_active_agents(
    workspace_path: Option<String>,
    db: AgentDb<'_>,
) -> Result<Vec<AgentEntry>, String> {
    let Ok(mut guard) = ensure_registry(db.inner(), workspace_path.as_deref()) else {
        return Ok(Vec::new());
    };
    let Some(conn) = guard.as_mut() else {
        return Ok(Vec::new());
    };
    Ok(registry_get_active_agents(conn).unwrap_or_else(|e| {
        eprintln!("[voss-app] get_active_agents failed: {e}");
        Vec::new()
    }))
}

#[tauri::command]
fn mark_agent_stopped(
    pane_id: String,
    workspace_path: Option<String>,
    db: AgentDb<'_>,
) -> Result<(), String> {
    let mut guard = ensure_registry(db.inner(), workspace_path.as_deref())?;
    let conn = guard
        .as_mut()
        .ok_or_else(|| "agent registry unavailable".to_string())?;
    mark_stopped(conn, &pane_id).map_err(|e| e.to_string())
}

#[tauri::command]
fn update_agents_last_seen(workspace_path: Option<String>, db: AgentDb<'_>) -> Result<(), String> {
    let mut guard = ensure_registry(db.inner(), workspace_path.as_deref())?;
    let conn = guard
        .as_mut()
        .ok_or_else(|| "agent registry unavailable".to_string())?;
    update_last_seen_all(conn).map_err(|e| e.to_string())
}

#[tauri::command]
fn sweep_orphan_agents(
    valid_pane_ids: Vec<String>,
    workspace_path: Option<String>,
    db: AgentDb<'_>,
) -> Result<usize, String> {
    let mut guard = ensure_registry(db.inner(), workspace_path.as_deref())?;
    let conn = guard
        .as_mut()
        .ok_or_else(|| "agent registry unavailable".to_string())?;
    sweep_orphans(conn, &valid_pane_ids).map_err(|e| e.to_string())
}

#[tauri::command]
async fn spawn_pty(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    cwd: Option<String>,
    state: Reg<'_>,
) -> Result<String, String> {
    let (session, reader, pause_rx) = spawn_session(rows, cols, cwd).map_err(|e| e.to_string())?;
    let registry: Arc<PtyRegistry> = Arc::clone(state.inner());
    let id = registry.insert(session);
    start_reader(id.clone(), reader, pause_rx, on_data, registry);
    Ok(id)
}

#[tauri::command]
async fn pty_write(session_id: String, data: Vec<u8>, state: Reg<'_>) -> Result<(), String> {
    validate_write(&data)?;
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.write(&data).map_err(|e| e.to_string())
}

#[tauri::command]
async fn pty_resize(
    session_id: String,
    rows: u16,
    cols: u16,
    state: Reg<'_>,
) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.resize(rows, cols).map_err(|e| e.to_string())
}

#[tauri::command]
async fn pty_pause(session_id: String, state: Reg<'_>) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.set_paused(true).await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn pty_resume(session_id: String, state: Reg<'_>) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.set_paused(false).await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn pty_kill(session_id: String, state: Reg<'_>) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.kill().map_err(|e| e.to_string())?;
    state.remove(&session_id);
    Ok(())
}

#[tauri::command]
async fn get_fg_process(session_id: String, state: Reg<'_>) -> Result<Option<String>, String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    let fd = match session.master_raw_fd() {
        Some(fd) => fd,
        None => return Ok(None),
    };
    Ok(foreground::get_foreground_name(fd))
}

// ---- Appearance settings + fonts (A8-04) ------------------------------------

#[tauri::command]
fn load_appearance_settings() -> AppearanceSettings {
    appearance::load_appearance_settings()
}

#[tauri::command]
fn save_appearance_settings(settings: AppearanceSettings) -> Result<(), String> {
    appearance::save_appearance_settings(&settings).map_err(|e| e.to_string())
}

#[tauri::command]
fn list_system_fonts() -> Vec<String> {
    fonts::list_system_fonts()
}

// ---- Grid mirror commands (GRD-08) ----------------------------------------
// Thin app-level wrappers delegating to voss-app-core's plain `grid::overwrite`
// / `grid::snapshot` — same cross-crate `generate_handler!` constraint as the
// PTY commands above (the core's own `#[tauri::command]` macros are not in
// scope here). In-memory mirror only; zero disk I/O.

type GridSlot<'a> = tauri::State<'a, Mutex<GridState>>;

#[tauri::command]
fn sync_grid(state: GridSlot<'_>, new_state: GridState) -> Result<(), String> {
    grid::overwrite(state.inner(), new_state)
}

#[tauri::command]
fn get_grid(state: GridSlot<'_>) -> Result<GridState, String> {
    grid::snapshot(state.inner())
}

// ---- Layout persistence commands (A4-03, LAY-06/07) -----------------------
// Thin app-level wrappers over `voss_app_core::layouts`. Same cross-crate
// `generate_handler!` constraint as the PTY and grid commands above — the
// core's own `#[tauri::command]` macros are not in scope here.
//
// `workspace_path` is the absolute path to the open project root; the
// frontend resolves it via the A5 project-open seam (until A5 lands the
// frontend passes the CWD of the focused pane or the user's home).
// Errors propagate as `LayoutError`'s Display strings — those match the
// A4-UI-SPEC error copy exactly, so the renderer can surface them
// verbatim.

#[tauri::command]
fn save_layout(workspace_path: String, name: String, layout: LayoutFile) -> Result<(), String> {
    layouts::save_layout(Path::new(&workspace_path), &name, &layout).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_layout(workspace_path: String, name: String) -> Result<LayoutFile, String> {
    layouts::load_layout(Path::new(&workspace_path), &name).map_err(|e| e.to_string())
}

#[tauri::command]
fn list_layouts(workspace_path: String) -> Result<Vec<String>, String> {
    layouts::list_layouts(Path::new(&workspace_path)).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_default_layout(workspace_path: String) -> Result<Option<LayoutFile>, String> {
    layouts::load_default_layout(Path::new(&workspace_path)).map_err(|e| e.to_string())
}

// ---- Context pin commands (F4-04) -------------------------------------------
// Write .voss/context-pins.json atomically (write-then-rename). The harness
// reads this file at iteration start (F4 D-20). ADE is the sole writer.

#[tauri::command]
fn write_context_pins(workspace_path: String, pinned_paths: Vec<String>) -> Result<(), String> {
    let voss_dir = Path::new(&workspace_path).join(".voss");
    std::fs::create_dir_all(&voss_dir).map_err(|e| e.to_string())?;
    let target = voss_dir.join("context-pins.json");
    let tmp = voss_dir.join("context-pins.json.tmp");
    let payload = serde_json::json!({ "pinned": pinned_paths });
    std::fs::write(&tmp, payload.to_string()).map_err(|e| e.to_string())?;
    std::fs::rename(&tmp, &target).map_err(|e| e.to_string())?;
    Ok(())
}

// ---- Swarm orchestration commands (A13) -------------------------------------

const SWARM_RESULT_EVENT: &str = "voss://swarm-result-added";

#[derive(Default)]
struct SwarmWatchState {
    stops: Mutex<HashMap<String, Arc<AtomicBool>>>,
}

fn emit_new_swarm_results(
    app: &tauri::AppHandle,
    swarm_id: &str,
    results_path: &Path,
    known: &mut HashSet<String>,
) {
    let entries = match std::fs::read_dir(results_path) {
        Ok(entries) => entries,
        Err(_) => return,
    };
    for entry in entries.filter_map(|entry| entry.ok()) {
        let is_file = entry
            .file_type()
            .map(|file_type| file_type.is_file())
            .unwrap_or(false);
        if !is_file {
            continue;
        }
        let filename = entry.file_name().to_string_lossy().into_owned();
        if !filename.ends_with(".result.md") || !known.insert(filename.clone()) {
            continue;
        }
        let payload = serde_json::json!({
            "swarmId": swarm_id,
            "resultFile": filename,
        });
        if let Err(e) = app.emit(SWARM_RESULT_EVENT, payload) {
            eprintln!("[voss-app] swarm result event failed: {e}");
        }
    }
}

#[tauri::command]
fn get_env_var(name: String) -> Result<String, String> {
    std::env::var(&name).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_swarm_files(
    workspace_path: String,
    manifest_json: String,
    tasks: Vec<(String, String)>,
    shared_context: String,
) -> Result<(), String> {
    if workspace_path.trim().is_empty() {
        return Err("workspace_path must not be empty".to_string());
    }

    let swarm_dir = Path::new(&workspace_path).join(".voss").join("swarm");
    let tasks_dir = swarm_dir.join("tasks");
    let results_dir = swarm_dir.join("results");
    let shared_dir = swarm_dir.join("shared");
    std::fs::create_dir_all(&tasks_dir).map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&results_dir).map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&shared_dir).map_err(|e| e.to_string())?;

    let manifest_target = swarm_dir.join("manifest.json");
    let manifest_tmp = swarm_dir.join("manifest.json.tmp");
    std::fs::write(&manifest_tmp, manifest_json).map_err(|e| e.to_string())?;
    std::fs::rename(&manifest_tmp, &manifest_target).map_err(|e| e.to_string())?;

    for (filename, content) in tasks {
        std::fs::write(tasks_dir.join(filename), content).map_err(|e| e.to_string())?;
    }

    std::fs::write(shared_dir.join("context.md"), shared_context).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn watch_swarm_results(
    app: tauri::AppHandle,
    state: tauri::State<'_, SwarmWatchState>,
    swarm_id: String,
    results_dir: String,
) -> Result<(), String> {
    let stop = Arc::new(AtomicBool::new(false));
    let previous = state
        .stops
        .lock()
        .map_err(|_| "could not watch swarm results".to_string())?
        .insert(swarm_id.clone(), Arc::clone(&stop));
    if let Some(previous) = previous {
        previous.store(true, Ordering::Relaxed);
    }

    let results_path = PathBuf::from(results_dir);
    std::thread::spawn(move || {
        let mut known = HashSet::new();
        emit_new_swarm_results(&app, &swarm_id, &results_path, &mut known);

        while !stop.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(500));
            emit_new_swarm_results(&app, &swarm_id, &results_path, &mut known);
        }
    });

    Ok(())
}

#[tauri::command]
fn stop_swarm_watcher(
    state: tauri::State<'_, SwarmWatchState>,
    swarm_id: String,
) -> Result<(), String> {
    if let Some(stop) = state
        .stops
        .lock()
        .map_err(|_| "could not stop swarm watcher".to_string())?
        .remove(&swarm_id)
    {
        stop.store(true, Ordering::Relaxed);
    }
    Ok(())
}

// ---- Project open commands (A5-02) ----------------------------------------
// Thin app-level wrappers over `voss_app_core::project`. Same cross-crate
// `generate_handler!` constraint as the PTY, grid, and layout commands above.

#[tauri::command]
fn open_project(path: String) -> Result<ProjectInfo, String> {
    project::open_project(Path::new(&path)).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_recents() -> Vec<String> {
    project::list_recents()
}

#[tauri::command]
fn default_cwd(project_path: Option<String>) -> String {
    project::default_cwd(project_path.as_deref().map(Path::new))
}

// ---- Session persistence commands (A6-01) -----------------------------------
// Thin app-level wrappers over `voss_app_core::session`. Same cross-crate
// `generate_handler!` constraint as the PTY, grid, layout, and project
// commands above. Project commands take `workspace_path`; global commands
// take no path argument.

#[tauri::command]
fn save_session(workspace_path: String, session: SessionFile) -> Result<(), String> {
    session::save_session(Path::new(&workspace_path), &session).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_session(workspace_path: String) -> Result<Option<SessionFile>, String> {
    session::load_session(Path::new(&workspace_path)).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_global_session(session: SessionFile) -> Result<(), String> {
    session::save_global_session(&session).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_global_session() -> Result<Option<SessionFile>, String> {
    session::load_global_session().map_err(|e| e.to_string())
}

// ---- Workspace index + project-less sessions (A8-02) ------------------------
// Thin wrappers over `voss_app_core::workspaces` and extended session paths.

#[tauri::command]
fn load_workspaces_index() -> WorkspacesIndex {
    workspaces::load_workspaces_index()
}

#[tauri::command]
fn save_workspaces_index(index: WorkspacesIndex) -> Result<(), String> {
    workspaces::save_workspaces_index(&index).map_err(|e| e.to_string())
}

#[tauri::command]
fn list_workspaces() -> Vec<workspaces::WorkspaceEntry> {
    workspaces::list_workspaces()
}

#[tauri::command]
fn save_project_less_session(workspace_id: String, session: SessionFile) -> Result<(), String> {
    session::save_project_less_session(&workspace_id, &session).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_project_less_session(workspace_id: String) -> Result<Option<SessionFile>, String> {
    session::load_project_less_session(&workspace_id).map_err(|e| e.to_string())
}

// ---- Keymap commands (A7-03) ------------------------------------------------
// Thin wrappers over `voss_app_core::keymap`. Profile persistence uses
// `settings.json`; workspace overrides use `.voss/keymap.json`.

const KEYMAP_UPDATED_EVENT: &str = "voss://keymap-updated";

#[derive(Default)]
struct KeymapWatchState {
    stops: Mutex<HashMap<PathBuf, Arc<AtomicBool>>>,
}

#[derive(Debug, PartialEq)]
struct KeymapFileStamp {
    exists: bool,
    modified: Option<SystemTime>,
    len: Option<u64>,
}

fn keymap_file_stamp(path: &Path) -> KeymapFileStamp {
    match std::fs::metadata(path) {
        Ok(metadata) => KeymapFileStamp {
            exists: true,
            modified: metadata.modified().ok(),
            len: Some(metadata.len()),
        },
        Err(_) => KeymapFileStamp {
            exists: false,
            modified: None,
            len: None,
        },
    }
}

#[tauri::command]
fn load_keymap_profile() -> String {
    let profile = keymap::load_keymap_profile();
    serde_json::to_string(&profile).unwrap_or_else(|_| "\"vscode\"".into())
}

#[tauri::command]
fn save_keymap_profile(profile: KeymapProfile) -> Result<(), String> {
    keymap::save_keymap_profile(&profile).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_keymap_overrides(workspace_path: String) -> Option<KeymapOverrideFile> {
    keymap::load_keymap_overrides(Path::new(&workspace_path))
}

#[tauri::command]
fn validate_keymap_overrides(
    overrides: KeymapOverrideFile,
    known_command_ids: Vec<String>,
    known_chords: Vec<String>,
) -> KeymapValidationResult {
    keymap::validate_keymap_overrides(&overrides, &known_command_ids, &known_chords)
}

#[tauri::command]
fn watch_keymap_overrides(
    app: tauri::AppHandle,
    state: tauri::State<'_, KeymapWatchState>,
    workspace_path: String,
    known_command_ids: Vec<String>,
    known_chords: Vec<String>,
) -> Result<KeymapValidationResult, String> {
    let workspace = PathBuf::from(workspace_path);
    let keymap_path = keymap::keymap_override_path(&workspace);
    let initial =
        keymap::validate_workspace_keymap_overrides(&workspace, &known_command_ids, &known_chords);

    let stop = Arc::new(AtomicBool::new(false));
    let previous = state
        .stops
        .lock()
        .map_err(|_| "could not watch keymap settings".to_string())?
        .insert(workspace.clone(), Arc::clone(&stop));
    if let Some(previous) = previous {
        previous.store(true, Ordering::Relaxed);
    }

    std::thread::spawn(move || {
        let mut last = keymap_file_stamp(&keymap_path);
        while !stop.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(500));
            let next = keymap_file_stamp(&keymap_path);
            if next == last {
                continue;
            }
            last = next;
            std::thread::sleep(Duration::from_millis(75));
            let payload = keymap::validate_workspace_keymap_overrides(
                &workspace,
                &known_command_ids,
                &known_chords,
            );
            if let Err(e) = app.emit(KEYMAP_UPDATED_EVENT, payload) {
                eprintln!("[voss-app] keymap update event failed: {e}");
            }
        }
    });

    Ok(initial)
}

// ---- Theme persistence commands (A8-01) -------------------------------------
// Thin wrappers over `voss_app_core::themes`. Custom themes live under
// `<workspace>/.voss/themes/`; active theme id is in `settings.json`.

#[tauri::command]
fn list_custom_themes(workspace_path: String) -> Vec<String> {
    themes::list_custom_themes(Path::new(&workspace_path))
}

#[tauri::command]
fn load_custom_theme(workspace_path: String, name: String) -> Option<CustomThemeFile> {
    themes::load_custom_theme(Path::new(&workspace_path), &name)
}

#[tauri::command]
fn save_custom_theme(
    workspace_path: String,
    name: String,
    theme: CustomThemeFile,
) -> Result<(), String> {
    themes::save_custom_theme(Path::new(&workspace_path), &name, &theme).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_active_theme_id() -> Option<String> {
    themes::load_active_theme_id()
}

#[tauri::command]
fn save_active_theme_id(id: Option<String>) -> Result<(), String> {
    themes::save_active_theme_id(id.as_deref()).map_err(|e| e.to_string())
}

// ---- Profile persistence commands (A8-01) -----------------------------------
// Thin wrappers over `voss_app_core::profiles`. Snapshots live at
// `~/.config/voss-app/profiles/`; active profile id is in `settings.json`.

#[tauri::command]
fn list_profiles() -> Vec<String> {
    profiles::list_profiles()
}

#[tauri::command]
fn load_profile(name: String) -> Option<ProfileFile> {
    profiles::load_profile(&name)
}

#[tauri::command]
fn save_profile(name: String, profile: ProfileFile) -> Result<(), String> {
    profiles::save_profile(&name, &profile).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_active_profile_id() -> Option<String> {
    profiles::load_active_profile_id()
}

#[tauri::command]
fn save_active_profile_id(id: Option<String>) -> Result<(), String> {
    profiles::save_active_profile_id(id.as_deref()).map_err(|e| e.to_string())
}

// ---- File tree commands (A12-07) -------------------------------------------

#[derive(Debug, serde::Serialize)]
struct DirEntry {
    name: String,
    is_dir: bool,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    children: Vec<DirEntry>,
}

const SKIP_DIRS: &[&str] = &[
    "node_modules",
    "target",
    ".git",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".venv",
    ".tox",
    ".mypy_cache",
];

fn read_dir_shallow(path: &std::path::Path, depth: u32) -> Vec<DirEntry> {
    if depth == 0 {
        return Vec::new();
    }
    let rd = match std::fs::read_dir(path) {
        Ok(rd) => rd,
        Err(_) => return Vec::new(),
    };
    let mut entries: Vec<DirEntry> = rd
        .filter_map(|e| e.ok())
        .filter_map(|e| {
            let name = e.file_name().to_string_lossy().into_owned();
            // Skip hidden files/dirs
            if name.starts_with('.') {
                return None;
            }
            let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
            // Skip noise directories
            if is_dir && SKIP_DIRS.contains(&name.as_str()) {
                return None;
            }
            let children = if is_dir && depth > 1 {
                read_dir_shallow(&e.path(), depth - 1)
            } else {
                Vec::new()
            };
            Some(DirEntry {
                name,
                is_dir,
                children,
            })
        })
        .collect();
    // Sort: dirs first, then alphabetical
    entries.sort_by(|a, b| b.is_dir.cmp(&a.is_dir).then(a.name.cmp(&b.name)));
    entries
}

#[tauri::command]
fn list_dir(path: String) -> Result<Vec<DirEntry>, String> {
    let canonical = std::fs::canonicalize(&path).map_err(|e| e.to_string())?;
    Ok(read_dir_shallow(&canonical, 2))
}

#[derive(Debug, serde::Serialize)]
struct GitCommit {
    hash: String,
    message: String,
    timestamp_secs: i64,
}

#[tauri::command]
fn git_log(workspace_path: String, limit: usize) -> Result<Vec<GitCommit>, String> {
    let output = std::process::Command::new("git")
        .args([
            "-C",
            &workspace_path,
            "log",
            &format!("-{}", limit),
            "--format=%H %ct %s",
        ])
        .output()
        .map_err(|e| e.to_string())?;

    if !output.status.success() {
        // Not a git repo or other git error — return empty gracefully
        return Ok(Vec::new());
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let commits: Vec<GitCommit> = stdout
        .lines()
        .filter(|line| !line.is_empty())
        .filter_map(|line| {
            let mut parts = line.splitn(3, ' ');
            let hash = parts.next()?.to_string();
            let ts: i64 = parts.next()?.parse().ok()?;
            let message = parts.next().unwrap_or("").to_string();
            Some(GitCommit {
                hash,
                message,
                timestamp_secs: ts,
            })
        })
        .collect();

    Ok(commits)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Arc::new(PtyRegistry::default()))
        .manage(Mutex::new(GridState::default()))
        .manage(Mutex::new(None::<Connection>))
        .manage(SwarmWatchState::default())
        .manage(KeymapWatchState::default())
        .invoke_handler(tauri::generate_handler![
            get_theme_overrides,
            spawn_pty,
            pty_write,
            pty_resize,
            pty_pause,
            pty_resume,
            pty_kill,
            get_fg_process,
            spawn_agent,
            get_active_agents,
            mark_agent_stopped,
            update_agents_last_seen,
            sweep_orphan_agents,
            sync_grid,
            get_grid,
            save_layout,
            load_layout,
            list_layouts,
            load_default_layout,
            open_project,
            load_recents,
            default_cwd,
            save_session,
            load_session,
            save_global_session,
            load_global_session,
            get_env_var,
            write_swarm_files,
            watch_swarm_results,
            stop_swarm_watcher,
            load_workspaces_index,
            save_workspaces_index,
            list_workspaces,
            save_project_less_session,
            load_project_less_session,
            load_keymap_profile,
            save_keymap_profile,
            load_keymap_overrides,
            validate_keymap_overrides,
            watch_keymap_overrides,
            list_custom_themes,
            load_custom_theme,
            save_custom_theme,
            load_active_theme_id,
            save_active_theme_id,
            list_profiles,
            load_profile,
            save_profile,
            load_active_profile_id,
            save_active_profile_id,
            load_appearance_settings,
            save_appearance_settings,
            list_system_fonts,
            write_context_pins,
            load_custom_agents,
            save_custom_agents,
            list_dir,
            git_log,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
