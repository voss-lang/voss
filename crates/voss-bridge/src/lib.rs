//! voss-bridge — LSP-framed JSON-RPC over stdio to the Python bridge server.

pub mod framing;
pub mod jsonrpc;

pub use framing::{read_frame, write_frame};
pub use jsonrpc::PyBridge;

pub fn version() -> &'static str { env!("CARGO_PKG_VERSION") }
