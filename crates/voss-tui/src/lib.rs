//! voss-tui — thin terminal client for the Voss harness REST+SSE server.
//!
//! Library surface so integration tests can drive the network + event layers
//! (`net`, `event`, `server`) over the wire without a TTY. `main.rs` wires
//! these into the ratatui UI loop in `app`.
//!
//! See `.planning/PROTOCOL.md` for the wire contract and
//! `.planning/HYBRID-REFACTOR-PLAN.md` (H2) for the build plan.

pub mod app;
pub mod doctor;
pub mod event;
pub mod net;
pub mod server;
pub mod sessions;
