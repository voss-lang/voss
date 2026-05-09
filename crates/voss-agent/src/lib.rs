//! voss-agent — agent loop, plan schema, turn execution.

pub mod plan;

pub use plan::{Plan, ToolCall};

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
