//! PTY Tauri IPC commands + the typed Channel event enum.
//!
//! The plugin manages `Arc<PtyRegistry>` (lib.rs setup) so the blocking reader
//! thread can own a cheap clone while commands borrow it via Tauri `State`.

use std::sync::Arc;

use crate::pty::reader::start_reader;
use crate::pty::writer::validate_write;
use crate::pty::{spawn_session, PtyRegistry};

/// Events streamed to the webview over a `Channel<PtyEvent>`.
/// serde-tagged like the ndjson `"type"` discriminant (A2-PATTERNS commands.rs).
#[derive(serde::Serialize, Clone)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PtyEvent {
    Data { bytes: Vec<u8> },
    Exit { code: i32 },
    FgProcess { name: String },
    TitleChange { title: String },
}

type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;

#[tauri::command]
pub async fn spawn_pty(
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
pub async fn pty_write(session_id: String, data: Vec<u8>, state: Reg<'_>) -> Result<(), String> {
    validate_write(&data)?;
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.write(&data).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn pty_resize(
    session_id: String,
    rows: u16,
    cols: u16,
    state: Reg<'_>,
) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.resize(rows, cols).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn pty_pause(session_id: String, state: Reg<'_>) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.set_paused(true).await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn pty_resume(session_id: String, state: Reg<'_>) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.set_paused(false).await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn pty_kill(session_id: String, state: Reg<'_>) -> Result<(), String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    session.kill().map_err(|e| e.to_string())?;
    state.remove(&session_id);
    Ok(())
}

#[tauri::command]
pub async fn get_fg_process(session_id: String, state: Reg<'_>) -> Result<Option<String>, String> {
    let session = state.get(&session_id).ok_or("unknown session")?;
    let fd = match session.master_raw_fd() {
        Some(fd) => fd,
        None => return Ok(None),
    };
    Ok(crate::pty::foreground::get_foreground_name(fd))
}
