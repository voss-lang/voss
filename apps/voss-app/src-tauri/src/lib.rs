use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use voss_app_core::grid::{self, GridState};
use voss_app_core::layouts::{self, LayoutFile};
use voss_app_core::project::{self, ProjectInfo};
use voss_app_core::pty::reader::start_reader;
use voss_app_core::pty::writer::validate_write;
use voss_app_core::pty::{foreground, spawn_session};
use voss_app_core::{PtyEvent, PtyRegistry};

#[derive(Debug, Deserialize, Serialize, Default)]
struct SettingsFile {
    theme: Option<HashMap<String, String>>,
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

// ---- PTY commands ---------------------------------------------------------
// Thin app-level #[tauri::command] wrappers over the voss-app-core `pty`
// public API. They live in the APP crate (not voss-app-core) because
// `tauri::generate_handler!` can only resolve the hidden command helper
// macros generated in the SAME crate — a `pub use` of cross-crate commands
// does not bring those macros into scope. This keeps the frontend's bare
// `invoke('spawn_pty', …)` contract and app-managed `Arc<PtyRegistry>` state.

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

#[tauri::command]
async fn pty_write(
    session_id: String,
    data: Vec<u8>,
    state: Reg<'_>,
) -> Result<(), String> {
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
async fn get_fg_process(
    session_id: String,
    state: Reg<'_>,
) -> Result<Option<String>, String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    let fd = match session.master_raw_fd() {
        Some(fd) => fd,
        None => return Ok(None),
    };
    Ok(foreground::get_foreground_name(fd))
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
fn save_layout(
    workspace_path: String,
    name: String,
    layout: LayoutFile,
) -> Result<(), String> {
    layouts::save_layout(Path::new(&workspace_path), &name, &layout)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn load_layout(
    workspace_path: String,
    name: String,
) -> Result<LayoutFile, String> {
    layouts::load_layout(Path::new(&workspace_path), &name)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn list_layouts(workspace_path: String) -> Result<Vec<String>, String> {
    layouts::list_layouts(Path::new(&workspace_path))
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn load_default_layout(
    workspace_path: String,
) -> Result<Option<LayoutFile>, String> {
    layouts::load_default_layout(Path::new(&workspace_path))
        .map_err(|e| e.to_string())
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Arc::new(PtyRegistry::default()))
        .manage(Mutex::new(GridState::default()))
        .invoke_handler(tauri::generate_handler![
            get_theme_overrides,
            spawn_pty,
            pty_write,
            pty_resize,
            pty_pause,
            pty_resume,
            pty_kill,
            get_fg_process,
            sync_grid,
            get_grid,
            save_layout,
            load_layout,
            list_layouts,
            load_default_layout,
            open_project,
            load_recents,
            default_cwd,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
