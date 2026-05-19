//! PTY master-side write helpers.
//!
//! The validated write path lives in `commands::pty_write` (empty / >1MiB /
//! unknown-session guards + Tauri error mapping). `PtySession::write` (mod.rs)
//! performs the locked `write_all` + `flush`. This module is the documented
//! seam for future write-side concerns (bracketed-paste framing, A2-04).
