//! PTY subsystem — lifecycle, IPC commands, reader/writer loops, foreground tracking.
//!
//! A2-01 (Wave 0): submodule declarations + empty `PtyRegistry` skeleton only.
//! The `PtySession` type + spawn/IO logic land in A2-02.

pub mod commands;
pub mod foreground;
pub mod reader;
pub mod writer;

#[cfg(test)]
mod tests;

use std::collections::HashMap;
use std::sync::Mutex;

/// Registry of live PTY sessions, managed by Tauri state.
///
/// A2-01 stub: the value type is `()` and the map is never populated.
/// A2-02 replaces `()` with the real `PtySession` and adds insert/remove APIs.
#[derive(Default)]
pub struct PtyRegistry {
    #[allow(dead_code)]
    sessions: Mutex<HashMap<String, ()>>,
}
