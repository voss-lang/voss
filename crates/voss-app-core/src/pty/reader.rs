//! PTY master-side streaming reader loop.
//!
//! The PTY reader is BLOCKING (`Box<dyn Read + Send>`), so it MUST run on
//! `spawn_blocking`, never the async executor (A2-RESEARCH Pitfall 3).
//! Watermark backpressure: a `pause_rx` signal blocks the loop until resumed
//! (D-02 server-side half).

use std::io::Read;
use std::sync::Arc;

use crate::pty::commands::{BudgetData, ContextData, PtyEvent};
use crate::pty::PtyRegistry;

const BUDGET_PREFIX: &[u8] = b"\x1b]1337;voss-budget=";
const CONTEXT_PREFIX: &[u8] = b"\x1b]1337;voss-context=";

/// Scans `data` for one complete `{prefix}{json}BEL` OSC 1337 sequence.
/// Returns `Some((json_bytes, display_bytes))` if the full sequence is present;
/// `None` passes through the buffer unchanged as display bytes.
/// Buffer fragmentation: returns `None` silently — next emission has cumulative
/// state (F3 D-03 / F4 D-26).
pub(crate) fn extract_voss_osc(data: &[u8], prefix: &[u8]) -> Option<(Vec<u8>, Vec<u8>)> {
    let start = data.windows(prefix.len()).position(|w| w == prefix)?;
    let json_start = start + prefix.len();
    let rel_end = data[json_start..].iter().position(|&b| b == 0x07)?;
    let end = json_start + rel_end;
    let json_bytes = data[json_start..end].to_vec();
    let mut display = data[..start].to_vec();
    display.extend_from_slice(&data[end + 1..]);
    Some((json_bytes, display))
}

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
                    let slice = &buf[..n];
                    // Budget OSC check (F3)
                    if let Some((json_bytes, display_bytes)) =
                        extract_voss_osc(slice, BUDGET_PREFIX)
                    {
                        if let Ok(data) =
                            serde_json::from_slice::<BudgetData>(&json_bytes)
                        {
                            let _ = on_data.send(PtyEvent::BudgetUpdate(data));
                        }
                        if !display_bytes.is_empty()
                            && on_data
                                .send(PtyEvent::Data {
                                    bytes: display_bytes,
                                })
                                .is_err()
                        {
                            break;
                        }
                        continue;
                    }
                    // Context OSC check (F4)
                    if let Some((json_bytes, display_bytes)) =
                        extract_voss_osc(slice, CONTEXT_PREFIX)
                    {
                        if let Ok(data) =
                            serde_json::from_slice::<ContextData>(&json_bytes)
                        {
                            let _ = on_data.send(PtyEvent::ContextUpdate(data));
                        }
                        if !display_bytes.is_empty()
                            && on_data
                                .send(PtyEvent::Data {
                                    bytes: display_bytes,
                                })
                                .is_err()
                        {
                            break;
                        }
                        continue;
                    }
                    // No OSC — plain display bytes
                    if on_data
                        .send(PtyEvent::Data {
                            bytes: slice.to_vec(),
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
