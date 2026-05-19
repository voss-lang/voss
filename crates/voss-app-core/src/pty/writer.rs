//! PTY master-side write helpers.
//!
//! `PtySession::write` (mod.rs) performs the locked `write_all` + `flush`.
//! The validated command path is `commands::pty_write`. The size/empty guard
//! is factored here as a pure fn so it is unit-testable without a Tauri
//! `State` (A2-02 Task 1 acceptance: assert empty / >1MiB rejection).

/// Max single `pty_write` payload (1 MiB) — DoS bound (T-A2-04).
pub const MAX_WRITE: usize = 1_048_576;

/// Validate a write payload before it reaches the PTY. Pure — no I/O, no state.
pub fn validate_write(data: &[u8]) -> Result<(), String> {
    if data.is_empty() {
        return Err("empty payload".into());
    }
    if data.len() > MAX_WRITE {
        return Err("payload exceeds 1MB limit".into());
    }
    Ok(())
}
