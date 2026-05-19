//! voss-app-core — Tauri plugin: PTY lifecycle, IPC commands.
//!
//! A2-01 (Wave 0): plugin-init shell + empty pty submodules only.
//! PTY spawn/read/write/resize/kill + foreground tracking land in A2-02..05.

pub mod pty;

pub use pty::PtyRegistry;

use tauri::Manager;

/// Tauri plugin init. `#[tauri::command]` handlers are wired in A2-02
/// (`invoke_handler` deliberately omitted here — no commands exist yet).
pub fn init<R: tauri::Runtime>() -> tauri::plugin::TauriPlugin<R> {
    tauri::plugin::Builder::new("voss-app-core")
        .setup(|app, _api| {
            app.manage(PtyRegistry::default());
            Ok(())
        })
        .build()
}
