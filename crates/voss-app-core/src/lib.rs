//! voss-app-core — Tauri plugin: PTY lifecycle, IPC commands.

pub mod pty;

pub use pty::commands::{
    get_fg_process, pty_kill, pty_pause, pty_resize, pty_resume, pty_write, spawn_pty,
    PtyEvent,
};
pub use pty::{PtyRegistry, PtySession};

use std::sync::Arc;

use tauri::Manager;

/// Tauri plugin init. Manages an `Arc<PtyRegistry>` so the blocking reader
/// threads can own cheap clones (commands borrow it via `State`).
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
