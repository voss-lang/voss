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
use voss_app_core::pty::{
    foreground, spawn_command_session_managed, spawn_command_session_with_env,
};
use voss_app_core::session::{self, SessionFile};
use voss_app_core::sidecar::{
    python_path, spawn_voss_serve, validate_workspace_cwd, ServeHandshake, VossServe,
};
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
    // Use ~/.config/voss-app/settings.json instead of dirs::config_dir() — on macOS that resolves to ~/Library/Application Support.
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

type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;
type AgentDb<'a> = tauri::State<'a, Mutex<Option<Connection>>>;
type VossServeMap<'a> = tauri::State<'a, Mutex<HashMap<String, VossServe>>>;

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

fn is_interactive_voss_command(cli_args: &[String]) -> bool {
    match cli_args.first().map(|s| s.as_str()) {
        None => true,
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

fn build_env_with_agent_id(
    base: Vec<(String, String)>,
    voss_agent_id: Option<String>,
) -> Vec<(String, String)> {
    let mut env = base;
    if let Some(slug) = voss_agent_id {
        if !slug.is_empty() {
            env.push(("VOSS_AGENT_ID".to_string(), slug));
        }
    }
    env
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
    voss_agent_id: Option<String>,
    db: AgentDb<'_>,
    pty_state: Reg<'_>,
) -> Result<String, String> {
    let mut guard = ensure_registry(db.inner(), workspace_path.as_deref())?;
    let conn = guard
        .as_mut()
        .ok_or_else(|| "agent registry unavailable".to_string())?;

    let embedded_env = env_for_embedded_cli(&cli_binary, &cli_args);
    let full_env = build_env_with_agent_id(
        embedded_env
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
        voss_agent_id,
    );
    let env_refs: Vec<(&str, &str)> = full_env
        .iter()
        .map(|(k, v)| (k.as_str(), v.as_str()))
        .collect();
    let (session, reader, pause_rx) = spawn_command_session_with_env(
        &cli_binary,
        &cli_args,
        &env_refs,
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

#[derive(Serialize, Clone)]
struct ManagedSpawnResult {
    pty_id: String,
    tier: String,
    sandboxed: bool,
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
async fn spawn_managed_agent(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    cwd: Option<String>,
    cli_binary: String,
    cli_args: Vec<String>,
    session_id: String,
    pane_id: String,
    workspace_path: Option<String>,
    scope: String,
    tier: String,
    voss_agent_id: Option<String>,
    db: AgentDb<'_>,
    pty_state: Reg<'_>,
) -> Result<ManagedSpawnResult, String> {
    let mut guard = ensure_registry(db.inner(), workspace_path.as_deref())?;
    let conn = guard
        .as_mut()
        .ok_or_else(|| "agent registry unavailable".to_string())?;

    let embedded_env = env_for_embedded_cli(&cli_binary, &cli_args);
    let full_env = build_env_with_agent_id(
        embedded_env
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
        voss_agent_id,
    );
    let env_refs: Vec<(&str, &str)> = full_env
        .iter()
        .map(|(k, v)| (k.as_str(), v.as_str()))
        .collect();
    let ((session, reader, pause_rx), sandboxed) = spawn_command_session_managed(
        &cli_binary,
        &cli_args,
        &env_refs,
        rows,
        cols,
        cwd.clone(),
        &scope,
    )
    .map_err(|e| e.to_string())?;
    let registry: Arc<PtyRegistry> = Arc::clone(pty_state.inner());
    let pty_id = registry.insert(session);
    start_reader(pty_id.clone(), reader, pause_rx, on_data, registry);

    // Roster shows the REAL CLI, not the sandbox launcher argv.
    let cwd_str = cwd.as_deref().unwrap_or("");
    register_agent(conn, &pane_id, &session_id, &cli_binary, &cli_args, cwd_str)
        .map_err(|e| e.to_string())?;

    // Honest tier: sandbox unavailable → downgrade to observe-only.
    let effective_tier = if sandboxed { tier } else { "C".to_string() };
    Ok(ManagedSpawnResult {
        pty_id,
        tier: effective_tier,
        sandboxed,
    })
}

#[cfg(test)]
mod tests {
    use super::{build_env_with_agent_id, env_for_embedded_cli, is_interactive_voss_command};

    #[test]
    fn agent_id_env_injected_when_some() {
        let base = vec![("VOSS_EMBEDDED".to_string(), "1".to_string())];
        let env = build_env_with_agent_id(base, Some("claude-1".to_string()));
        assert!(env.contains(&("VOSS_AGENT_ID".to_string(), "claude-1".to_string())));
        assert!(env.contains(&("VOSS_EMBEDDED".to_string(), "1".to_string())));
    }

    #[test]
    fn agent_id_env_absent_when_none_or_empty() {
        let env = build_env_with_agent_id(Vec::new(), None);
        assert!(!env.iter().any(|(k, _)| k == "VOSS_AGENT_ID"));
        let env = build_env_with_agent_id(Vec::new(), Some(String::new()));
        assert!(!env.iter().any(|(k, _)| k == "VOSS_AGENT_ID"));
    }

    const TUI_ENV: [(&str, &str); 2] = [("VOSS_EMBEDDED", "1"), ("VOSS_FORCE_TUI", "1")];
    const COMPACT_ENV: [(&str, &str); 2] = [("VOSS_EMBEDDED", "1"), ("VOSS_RENDERER", "compact")];

    #[test]
    fn interactive_commands_classified_correctly() {
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

    #[test]
    fn clipboard_image_extension_accepts_common_types_only() {
        assert_eq!(clipboard_image_extension("image/png"), Some("png"));
        assert_eq!(clipboard_image_extension("IMAGE/JPEG"), Some("jpg"));
        assert_eq!(clipboard_image_extension("image/webp"), Some("webp"));
        assert_eq!(clipboard_image_extension("text/plain"), None);
    }

    #[test]
    fn save_clipboard_image_writes_temp_file() {
        let path = super::save_clipboard_image(vec![1, 2, 3], "image/png".into()).unwrap();
        let path = PathBuf::from(path);
        assert_eq!(path.extension().and_then(|s| s.to_str()), Some("png"));
        assert_eq!(fs::read(&path).unwrap(), vec![1, 2, 3]);
        fs::remove_file(path).ok();
    }

    use std::fs;
    use std::path::PathBuf;
    use std::time::SystemTime;

    fn unique_tmp(tag: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("voss_test_{tag}_{}_{}", std::process::id(), nanos))
    }

    #[test]
    fn enumerate_runs_filters_flat_session_files() {
        let base = unique_tmp("enum");
        let sessions = base.join(".voss").join("sessions");
        let run_dir = sessions.join("abc123run456");
        fs::create_dir_all(&run_dir).unwrap();
        fs::write(run_dir.join("node1.json"), "{}").unwrap();
        fs::write(sessions.join("legacyflat999.json"), "{}").unwrap();

        let runs = super::enumerate_runs(base.to_string_lossy().into_owned());
        let ids: Vec<String> = runs.iter().map(|r| r.run_id.clone()).collect();
        assert_eq!(ids, vec!["abc123run456".to_string()]);

        fs::remove_dir_all(&base).ok();
    }

    #[test]
    fn load_run_rejects_traversal() {
        let res = super::load_run("../etc".into(), "/tmp".into(), "voss".into());
        assert!(res.is_err());
    }

    #[cfg(unix)]
    #[test]
    fn run_decision_captures_nonzero_exit() {
        use std::os::unix::fs::PermissionsExt;
        let base = unique_tmp("decision");
        fs::create_dir_all(&base).unwrap();
        let fake = base.join("voss");
        fs::write(&fake, "#!/bin/sh\nexit 3\n").unwrap();
        fs::set_permissions(&fake, fs::Permissions::from_mode(0o755)).unwrap();

        let res = super::run_decision(
            fake.to_string_lossy().into_owned(),
            base.to_string_lossy().into_owned(),
            vec!["audit".into(), "deadbeef1234".into(), "--approve".into()],
        )
        .unwrap();
        assert!(!res.success);
        assert_eq!(res.exit_code, 3);

        fs::remove_dir_all(&base).ok();
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
    voss_agent_id: Option<String>,
    state: Reg<'_>,
) -> Result<String, String> {
    // Plain-shell spawn routed through the env-carrying path so every pane
    // receives VOSS_AGENT_ID (VBUS-03 D-11). Mirrors spawn_session's
    // behavior: $SHELL + VOSS_EMBEDDED=1 (TERM/COLORTERM set by the callee).
    let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".to_string());
    let full_env = build_env_with_agent_id(
        vec![("VOSS_EMBEDDED".to_string(), "1".to_string())],
        voss_agent_id,
    );
    let env_refs: Vec<(&str, &str)> = full_env
        .iter()
        .map(|(k, v)| (k.as_str(), v.as_str()))
        .collect();
    let (session, reader, pause_rx) =
        spawn_command_session_with_env(&shell, &[], &env_refs, rows, cols, cwd)
            .map_err(|e| e.to_string())?;
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

type GridSlot<'a> = tauri::State<'a, Mutex<GridState>>;

#[tauri::command]
fn sync_grid(state: GridSlot<'_>, new_state: GridState) -> Result<(), String> {
    grid::overwrite(state.inner(), new_state)
}

#[tauri::command]
fn get_grid(state: GridSlot<'_>) -> Result<GridState, String> {
    grid::snapshot(state.inner())
}

type CanvasSlot<'a> = tauri::State<'a, Mutex<CanvasState>>;

#[tauri::command]
fn sync_canvas(state: CanvasSlot<'_>, new_state: CanvasState) -> Result<(), String> {
    canvas::overwrite(state.inner(), new_state)
}

#[tauri::command]
fn get_canvas(state: CanvasSlot<'_>) -> Result<CanvasState, String> {
    canvas::snapshot(state.inner())
}

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

fn registered_project_path(workspace_id: &str) -> Result<PathBuf, String> {
    workspaces::load_workspaces_index()
        .workspaces
        .into_iter()
        .find(|workspace| workspace.id == workspace_id)
        .and_then(|workspace| workspace.project_path)
        .map(PathBuf::from)
        .ok_or_else(|| "workspace is not a registered project".to_string())
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
            if name.starts_with('.') {
                return None;
            }
            let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
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

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct RunData {
    run_id: String,
    session_tree: serde_json::Value,
    review: serde_json::Value,
    audit: serde_json::Value,
    run_final: serde_json::Value,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct RunEntry {
    run_id: String,
    mtime_secs: u64,
    has_run_final: bool,
}

#[derive(Debug, serde::Serialize)]
struct DecisionResult {
    success: bool,
    stdout: String,
    stderr: String,
    exit_code: i32,
}

fn is_safe_run_id(run_id: &str) -> bool {
    !run_id.is_empty()
        && !run_id.contains('/')
        && !run_id.contains('\\')
        && !run_id.contains("..")
}

fn sessions_dir(cwd: &str) -> PathBuf {
    Path::new(cwd).join(".voss").join("sessions")
}

fn load_run_impl(run_id: String, cwd: String, cli_binary: String) -> Result<RunData, String> {
    if !is_safe_run_id(&run_id) {
        return Err(format!("invalid run_id: {run_id}"));
    }
    let run_dir = sessions_dir(&cwd).join(&run_id);
    if !run_dir.is_dir() {
        return Err(format!("run not found: {run_id}"));
    }

    let mut node_files: Vec<PathBuf> = Vec::new();
    let mut review = serde_json::Map::new();
    if let Ok(rd) = std::fs::read_dir(&run_dir) {
        for entry in rd.filter_map(|e| e.ok()) {
            let name = entry.file_name().to_string_lossy().into_owned();
            if !name.ends_with(".json") || name == "run-final.json" {
                continue;
            }
            if name.ends_with(".review.json") {
                if let Ok(raw) = std::fs::read_to_string(entry.path()) {
                    if let Ok(val) = serde_json::from_str::<serde_json::Value>(&raw) {
                        let node_id = name.trim_end_matches(".review.json").to_string();
                        review.insert(node_id, val);
                    }
                }
                continue;
            }
            node_files.push(entry.path());
        }
    }
    node_files.sort();
    let mut nodes: Vec<serde_json::Value> = Vec::new();
    for path in node_files {
        if let Ok(raw) = std::fs::read_to_string(&path) {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&raw) {
                nodes.push(val);
            }
        }
    }
    let session_tree = serde_json::json!({ "root_id": run_id, "nodes": nodes });

    let audit = match std::process::Command::new(&cli_binary)
        .args(["audit", run_id.as_str(), "--cwd", cwd.as_str(), "--format", "json"])
        .output()
    {
        Ok(out) if out.status.success() => {
            serde_json::from_slice::<serde_json::Value>(&out.stdout)
                .unwrap_or(serde_json::Value::Null)
        }
        _ => serde_json::Value::Null,
    };

    let run_final = std::fs::read_to_string(run_dir.join("run-final.json"))
        .ok()
        .and_then(|raw| serde_json::from_str::<serde_json::Value>(&raw).ok())
        .unwrap_or(serde_json::Value::Null);

    Ok(RunData {
        run_id,
        session_tree,
        review: serde_json::Value::Object(review),
        audit,
        run_final,
    })
}

#[tauri::command]
fn enumerate_runs(cwd: String) -> Vec<RunEntry> {
    let dir = sessions_dir(&cwd);
    let rd = match std::fs::read_dir(&dir) {
        Ok(rd) => rd,
        Err(_) => return Vec::new(),
    };
    let mut entries: Vec<RunEntry> = rd
        .filter_map(|e| e.ok())
        .filter_map(|e| {
            let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
            if !is_dir {
                return None;
            }
            let path = e.path();
            let has_node = std::fs::read_dir(&path)
                .ok()?
                .filter_map(|f| f.ok())
                .any(|f| {
                    let n = f.file_name().to_string_lossy().into_owned();
                    n.ends_with(".json") && n != "run-final.json"
                });
            if !has_node {
                return None;
            }
            let mtime_secs = e
                .metadata()
                .ok()
                .and_then(|m| m.modified().ok())
                .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
                .map(|d| d.as_secs())
                .unwrap_or(0);
            Some(RunEntry {
                run_id: e.file_name().to_string_lossy().into_owned(),
                mtime_secs,
                has_run_final: path.join("run-final.json").is_file(),
            })
        })
        .collect();
    entries.sort_by(|a, b| b.mtime_secs.cmp(&a.mtime_secs));
    entries
}

#[tauri::command]
fn run_decision(
    cli_binary: String,
    cwd: String,
    args: Vec<String>,
) -> Result<DecisionResult, String> {
    if !is_voss_cli_binary(&cli_binary) {
        return Err(format!("not a voss CLI binary: {cli_binary}"));
    }
    for arg in &args {
        if arg.starts_with('-') {
            continue;
        }
        if arg.contains('/') || arg.contains('\\') || arg.contains("..") {
            return Err(format!("invalid argument: {arg}"));
        }
    }
    let output = std::process::Command::new(&cli_binary)
        .args(&args)
        .current_dir(&cwd)
        .output()
        .map_err(|e| e.to_string())?;
    Ok(DecisionResult {
        success: output.status.success(),
        stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
        stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        exit_code: output.status.code().unwrap_or(-1),
    })
}

fn orchestration_root(
    window: &tauri::WebviewWindow,
    state: &OrchestrationWindowState,
) -> Result<String, String> {
    require_orchestration_window(window)?;
    state
        .context
        .lock()
        .map_err(|_| "could not read orchestration context".to_string())?
        .as_ref()
        .map(|context| context.cwd.clone())
        .ok_or_else(|| "orchestration context is unavailable".to_string())
}

#[tauri::command]
fn load_run(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OrchestrationWindowState>,
    run_id: String,
) -> Result<RunData, String> {
    load_run_impl(
        run_id,
        orchestration_root(&window, state.inner())?,
        "voss".to_string(),
    )
}

#[tauri::command]
fn enumerate_runs(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OrchestrationWindowState>,
) -> Result<Vec<RunEntry>, String> {
    Ok(enumerate_runs_impl(orchestration_root(
        &window,
        state.inner(),
    )?))
}

#[tauri::command]
fn run_decision(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OrchestrationWindowState>,
    args: Vec<String>,
) -> Result<DecisionResult, String> {
    run_decision_impl(
        "voss".to_string(),
        orchestration_root(&window, state.inner())?,
        args,
    )
}

fn authorize_sidecar_cwd(cwd: &str, index: &WorkspacesIndex) -> Result<PathBuf, String> {
    let canonical = validate_workspace_cwd(cwd, &[])?;
    let registered = index
        .workspaces
        .iter()
        .filter_map(|workspace| workspace.project_path.as_deref())
        .filter_map(|path| std::fs::canonicalize(path).ok())
        .any(|path| path == canonical);
    if !registered {
        return Err("workspace is not a registered project".to_string());
    }
    Ok(canonical)
}

fn normalize_orchestration_view(view: Option<String>) -> String {
    match view.as_deref() {
        Some("swarm-map" | "memory" | "review") => view.unwrap(),
        _ => "review".to_string(),
    }
}

#[tauri::command]
async fn open_orchestration_console(
    app: tauri::AppHandle,
    state: tauri::State<'_, OrchestrationWindowState>,
    cwd: String,
    initial_view: Option<String>,
    card_id: Option<String>,
) -> Result<(), String> {
    let root = authorize_sidecar_cwd(&cwd, &workspaces::load_workspaces_index())?;
    let context = OrchestrationContext {
        cwd: root.to_string_lossy().into_owned(),
        initial_view: normalize_orchestration_view(initial_view),
        card_id,
    };
    *state
        .context
        .lock()
        .map_err(|_| "could not open orchestration console".to_string())? = Some(context.clone());

    if let Some(window) = app.get_webview_window(ORCHESTRATION_WINDOW_LABEL) {
        window
            .show()
            .and_then(|_| window.set_focus())
            .map_err(|_| "could not focus orchestration console".to_string())?;
        app.emit_to(
            ORCHESTRATION_WINDOW_LABEL,
            ORCHESTRATION_CONTEXT_EVENT,
            context,
        )
        .map_err(|_| "could not update orchestration console".to_string())?;
        return Ok(());
    }

    tauri::WebviewWindowBuilder::new(
        &app,
        ORCHESTRATION_WINDOW_LABEL,
        tauri::WebviewUrl::App("index.html".into()),
    )
    .title("Voss Orchestration")
    .inner_size(1180.0, 760.0)
    .min_inner_size(800.0, 500.0)
    .decorations(false)
    .build()
    .map_err(|_| "could not open orchestration console".to_string())?;
    Ok(())
}

#[tauri::command]
fn get_orchestration_context(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, OrchestrationWindowState>,
) -> Result<OrchestrationContext, String> {
    let _ = orchestration_root(&window, state.inner())?;
    state
        .context
        .lock()
        .map_err(|_| "could not read orchestration context".to_string())?
        .clone()
        .ok_or_else(|| "orchestration context is unavailable".to_string())
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct SidecarHandle {
    sidecar_id: String,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
enum SidecarOperation {
    CreateSession,
    ListSessions,
    ListSaved,
    GetSession {
        session_id: String,
    },
    DeleteSession {
        session_id: String,
    },
    PostMessage {
        session_id: String,
        text: String,
        mode: String,
    },
    AbortSession {
        session_id: String,
    },
    GetCost {
        session_id: String,
    },
    Doctor,
    ReplyPermission {
        session_id: String,
        id: String,
        choice: String,
    },
    Memory {
        query: Option<String>,
        top_k: u32,
    },
    GetSwarm {
        swarm_id: String,
    },
    CreateSwarm {
        goal: String,
        builders: u32,
        roster: Option<Vec<serde_json::Value>>,
    },
    RunSwarm {
        swarm_id: String,
    },
    ObserveEvent {
        event: serde_json::Value,
        evidence: Vec<serde_json::Value>,
    },
    ObserveSettingsGet,
    ObserveSettingsPatch {
        repository_id: String,
        enrollment: serde_json::Value,
    },
}

#[derive(Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum SidecarStreamEvent {
    Event { event: serde_json::Value },
    End,
    Error { message: String },
}

fn sidecar_connection(
    sidecar_id: &str,
    state: &Mutex<HashMap<String, VossServeEntry>>,
) -> Result<(ServeHandshake, PathBuf), String> {
    let map = state.lock().map_err(|_| "lock poisoned".to_string())?;
    map.values()
        .find(|entry| entry.id == sidecar_id && entry.serve.pid().is_some())
        .map(|entry| (entry.serve.handshake.clone(), entry.root.clone()))
        .ok_or_else(|| "sidecar handle is unavailable".to_string())
}

fn sidecar_url(port: u16, segments: &[&str]) -> Result<reqwest::Url, String> {
    let mut url = reqwest::Url::parse(&format!("http://127.0.0.1:{port}"))
        .map_err(|_| "invalid sidecar endpoint".to_string())?;
    {
        let mut path = url
            .path_segments_mut()
            .map_err(|_| "invalid sidecar endpoint".to_string())?;
        path.clear();
        path.extend(segments);
    }
    Ok(url)
}

async fn send_sidecar_request(
    token: &str,
    request: reqwest::RequestBuilder,
) -> Result<serde_json::Value, String> {
    let response = request
        .bearer_auth(token)
        .send()
        .await
        .map_err(|_| "sidecar request failed".to_string())?;
    let status = response.status();
    if response
        .content_length()
        .is_some_and(|length| length > 4_194_304)
    {
        return Err("sidecar response exceeded limit".to_string());
    }
    let bytes = response
        .bytes()
        .await
        .map_err(|_| "sidecar response failed".to_string())?;
    if bytes.len() > 4_194_304 {
        return Err("sidecar response exceeded limit".to_string());
    }
    if !status.is_success() {
        let detail = serde_json::from_slice::<serde_json::Value>(&bytes)
            .ok()
            .and_then(|value| value.get("detail").cloned())
            .map(|value| value.to_string())
            .unwrap_or_else(|| status.to_string());
        return Err(format!("sidecar request failed: {detail}"));
    }
    if bytes.is_empty() {
        return Ok(serde_json::Value::Null);
    }
    serde_json::from_slice(&bytes).map_err(|_| "invalid sidecar response".to_string())
}

async fn send_observe_event(
    token: &str,
    request: reqwest::RequestBuilder,
) -> Result<serde_json::Value, String> {
    let response = request
        .bearer_auth(token)
        .send()
        .await
        .map_err(|_| "sidecar request failed".to_string())?;
    let status = response.status();
    if status == reqwest::StatusCode::FORBIDDEN {
        let reason = response
            .json::<serde_json::Value>()
            .await
            .ok()
            .and_then(|value| value.get("reason")?.as_str().map(String::from))
            .unwrap_or_else(|| "unknown".into());
        return Err(format!("observe_rejected:{reason}"));
    }
    if !status.is_success() {
        return Err(format!("sidecar request failed: {status}"));
    }
    response
        .json::<serde_json::Value>()
        .await
        .map_err(|_| "invalid sidecar response".to_string())
}

#[tauri::command]
async fn call_voss_sidecar(
    window: tauri::WebviewWindow,
    sidecar_id: String,
    operation: SidecarOperation,
    state: VossServeMap<'_>,
) -> Result<serde_json::Value, String> {
    require_orchestration_window(&window)?;
    let (handshake, root) = sidecar_connection(&sidecar_id, state.inner())?;
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .map_err(|_| "sidecar client unavailable".to_string())?;
    let root = root.to_string_lossy().into_owned();

    if let SidecarOperation::CreateSwarm { goal, builders, .. } = &operation {
        if goal.is_empty() || goal.len() > 1_048_576 || *builders == 0 || *builders > 32 {
            return Err("invalid swarm request".to_string());
        }
    }

    let is_observe = matches!(operation, SidecarOperation::ObserveEvent { .. });
    let request = match operation {
        SidecarOperation::CreateSession => client
            .post(sidecar_url(handshake.port, &["session"])?)
            .json(&serde_json::json!({"auth": "auto", "cwd": root})),
        SidecarOperation::ListSessions => client.get(sidecar_url(handshake.port, &["session"])?),
        SidecarOperation::ListSaved => {
            let mut url = sidecar_url(handshake.port, &["sessions", "saved"])?;
            url.query_pairs_mut().append_pair("cwd", &root);
            client.get(url)
        }
        SidecarOperation::GetSession { session_id } => {
            client.get(sidecar_url(handshake.port, &["session", &session_id])?)
        }
        SidecarOperation::DeleteSession { session_id } => {
            client.delete(sidecar_url(handshake.port, &["session", &session_id])?)
        }
        SidecarOperation::PostMessage {
            session_id,
            text,
            mode,
        } => {
            if !matches!(mode.as_str(), "plan" | "edit" | "auto") || text.len() > 1_048_576 {
                return Err("invalid sidecar message".to_string());
            }
            client
                .post(sidecar_url(
                    handshake.port,
                    &["session", &session_id, "message"],
                )?)
                .json(&serde_json::json!({
                    "mode": mode,
                    "parts": [{"type": "text", "text": text}],
                }))
        }
        SidecarOperation::AbortSession { session_id } => client.post(sidecar_url(
            handshake.port,
            &["session", &session_id, "abort"],
        )?),
        SidecarOperation::GetCost { session_id } => client.get(sidecar_url(
            handshake.port,
            &["session", &session_id, "cost"],
        )?),
        SidecarOperation::Doctor => {
            let mut url = sidecar_url(handshake.port, &["doctor"])?;
            url.query_pairs_mut().append_pair("cwd", &root);
            client.get(url)
        }
        SidecarOperation::ReplyPermission {
            session_id,
            id,
            choice,
        } => {
            if !matches!(choice.as_str(), "a" | "A" | "d" | "y" | "n") {
                return Err("invalid permission choice".to_string());
            }
            client
                .post(sidecar_url(
                    handshake.port,
                    &["session", &session_id, "permission"],
                )?)
                .json(&serde_json::json!({"v": 1, "id": id, "choice": choice}))
        }
        SidecarOperation::Memory { query, top_k } => {
            if top_k == 0 || top_k > 100 {
                return Err("invalid memory result limit".to_string());
            }
            let mut url = sidecar_url(handshake.port, &["memory"])?;
            {
                let mut query_pairs = url.query_pairs_mut();
                query_pairs.append_pair("cwd", &root);
                if let Some(query) = query.filter(|value| !value.trim().is_empty()) {
                    query_pairs.append_pair("q", query.trim());
                    query_pairs.append_pair("top_k", &top_k.to_string());
                }
            }
            client.get(url)
        }
        SidecarOperation::GetSwarm { swarm_id } => {
            client.get(sidecar_url(handshake.port, &["swarm", &swarm_id])?)
        }
        SidecarOperation::CreateSwarm {
            goal,
            builders,
            roster,
        } => client
            .post(sidecar_url(handshake.port, &["swarm"])?)
            .json(&serde_json::json!({
                "goal": goal,
                "builders": builders,
                "cwd": root,
                "roster": roster,
            })),
        SidecarOperation::RunSwarm { swarm_id } => {
            client.post(sidecar_url(handshake.port, &["swarm", &swarm_id, "run"])?)
        }
        SidecarOperation::ObserveEvent { event, evidence } => client
            .post(sidecar_url(handshake.port, &["observe", "events"])?)
            .json(&serde_json::json!({ "event": event, "evidence": evidence })),
        SidecarOperation::ObserveSettingsGet => {
            client.get(sidecar_url(handshake.port, &["observe", "settings"])?)
        }
        SidecarOperation::ObserveSettingsPatch {
            repository_id,
            enrollment,
        } => client
            .patch(sidecar_url(handshake.port, &["observe", "settings"])?)
            .json(&serde_json::json!({
                "repository_id": repository_id,
                "enrollment": enrollment,
            })),
    };

    if is_observe {
        return send_observe_event(&handshake.token, request).await;
    }
    send_sidecar_request(&handshake.token, request).await
}

fn take_sse_frame(buffer: &mut Vec<u8>) -> Option<Vec<u8>> {
    let (index, separator_len) = buffer
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .map(|index| (index, 4))
        .or_else(|| {
            buffer
                .windows(2)
                .position(|window| window == b"\n\n")
                .map(|index| (index, 2))
        })?;
    let frame = buffer[..index].to_vec();
    buffer.drain(..index + separator_len);
    Some(frame)
}

fn decode_sse_frame(frame: &[u8]) -> Option<serde_json::Value> {
    let text = std::str::from_utf8(frame).ok()?;
    let data = text
        .lines()
        .filter_map(|line| line.trim_end_matches('\r').strip_prefix("data:"))
        .map(str::trim_start)
        .collect::<Vec<_>>()
        .join("\n");
    if data.is_empty() {
        return None;
    }
    serde_json::from_str(&data).ok()
}

#[tauri::command]
async fn subscribe_voss_events(
    window: tauri::WebviewWindow,
    sidecar_id: String,
    session_id: String,
    on_event: tauri::ipc::Channel<SidecarStreamEvent>,
    sidecars: VossServeMap<'_>,
    streams: VossStreamMap<'_>,
) -> Result<String, String> {
    require_orchestration_window(&window)?;
    let (handshake, _) = sidecar_connection(&sidecar_id, sidecars.inner())?;
    let response = reqwest::Client::new()
        .get(sidecar_url(
            handshake.port,
            &["session", &session_id, "events"],
        )?)
        .bearer_auth(&handshake.token)
        .send()
        .await
        .map_err(|_| "sidecar event stream failed".to_string())?;
    if !response.status().is_success() {
        return Err(format!(
            "sidecar event stream failed: {}",
            response.status()
        ));
    }

    let stream_id = uuid::Uuid::new_v4().to_string();
    let task = tauri::async_runtime::spawn(async move {
        let mut response = response;
        let mut buffer = Vec::new();
        loop {
            match response.chunk().await {
                Ok(Some(chunk)) => {
                    buffer.extend_from_slice(&chunk);
                    if buffer.len() > 1_048_576 {
                        let _ = on_event.send(SidecarStreamEvent::Error {
                            message: "sidecar event exceeded limit".to_string(),
                        });
                        break;
                    }
                    while let Some(frame) = take_sse_frame(&mut buffer) {
                        if let Some(event) = decode_sse_frame(&frame) {
                            if on_event.send(SidecarStreamEvent::Event { event }).is_err() {
                                return;
                            }
                        }
                    }
                }
                Ok(None) => break,
                Err(_) => {
                    let _ = on_event.send(SidecarStreamEvent::Error {
                        message: "sidecar event stream failed".to_string(),
                    });
                    break;
                }
            }
        }
        let _ = on_event.send(SidecarStreamEvent::End);
    });
    streams
        .lock()
        .map_err(|_| "stream lock poisoned".to_string())?
        .insert(stream_id.clone(), task);
    Ok(stream_id)
}

#[tauri::command]
fn unsubscribe_voss_events(
    window: tauri::WebviewWindow,
    stream_id: String,
    streams: VossStreamMap<'_>,
) -> Result<(), String> {
    require_orchestration_window(&window)?;
    if let Some(task) = streams
        .lock()
        .map_err(|_| "stream lock poisoned".to_string())?
        .remove(&stream_id)
    {
        task.abort();
    }
    Ok(())
}

#[tauri::command]
async fn start_voss_serve(
    window: tauri::WebviewWindow,
    cwd: String,
    state: VossServeMap<'_>,
) -> Result<SidecarHandle, String> {
    require_orchestration_window(&window)?;
    let index = workspaces::load_workspaces_index();
    let canonical = authorize_sidecar_cwd(&cwd, &index)?;
    let key = canonical.to_string_lossy().into_owned();

    {
        let mut map = state.lock().map_err(|_| "lock poisoned".to_string())?;
        match map.get(&cwd) {
            Some(serve) if serve.pid().is_some() => return Ok(serve.handshake.clone()),
            Some(_) => {
                map.remove(&cwd);
            }
            None => {}
        }
    }

    let serve = spawn_voss_serve(&python_path(), &canonical)
        .await
        .map_err(|e| e.to_string())?;
    let handshake = serve.handshake.clone();

    let mut map = state.lock().map_err(|_| "lock poisoned".to_string())?;
    map.insert(
        key,
        VossServeEntry {
            id: sidecar_id.clone(),
            root: canonical,
            serve,
        },
    );
    Ok(SidecarHandle { sidecar_id })
}

#[tauri::command]
fn ui_log(level: String, scope: String, detail: String) {
    let line = format!("[ui] {scope}: {detail}");
    if level == "error" {
        eprintln!("{line}");
    } else {
        println!("{line}");
    }
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
        .manage(Mutex::new(HashMap::<String, VossServe>::new()))
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
            spawn_managed_agent,
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
            load_run,
            enumerate_runs,
            run_decision,
            start_voss_serve,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
