//! PTY master-side streaming reader loop.
//!
//! The PTY reader is BLOCKING (`Box<dyn Read + Send>`), so it MUST run on
//! `spawn_blocking`, never the async executor (A2-RESEARCH Pitfall 3).
//! Watermark backpressure: a `pause_rx` signal blocks the loop until resumed
//! (D-02 server-side half).

use std::io::Read;
use std::sync::Arc;

use crate::pty::commands::PtyEvent;
use crate::pty::PtyRegistry;

/// Start the blocking read loop for `session_id`. On EOF/err it emits
/// `PtyEvent::Exit` with the real exit code, reaps the child, and removes the
/// session from the registry (no zombie — Pitfall 4).
pub fn start_reader(
    session_id: String,
    mut reader: Box<dyn Read + Send>,
    mut pause_rx: tokio::sync::mpsc::Receiver<bool>,
    on_data: tauri::ipc::Channel<PtyEvent>,
    registry: Arc<PtyRegistry>,
) {
    tokio::task::spawn_blocking(move || {
        let mut buf = [0u8; 8192];
        loop {
            // Non-blocking backpressure check; if paused, block until resumed.
            if let Ok(true) = pause_rx.try_recv() {
                while pause_rx.blocking_recv() != Some(false) {}
            }
            match reader.read(&mut buf) {
                Ok(0) => break, // EOF — child exited
                Ok(n) => {
                    if on_data
                        .send(PtyEvent::Data {
                            bytes: buf[..n].to_vec(),
                        })
                        .is_err()
                    {
                        break; // channel closed (pane gone)
                    }
                }
                Err(_) => break,
            }
        }

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
    });
}
