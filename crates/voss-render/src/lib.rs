//! voss-render — terminal renderer (Tty/Plain/NDJSON).

pub mod ndjson;
pub mod plain;
pub mod render_trait;
pub mod status_line;
pub mod tty;

pub use ndjson::{NdjsonRender, PROTOCOL_VERSION};
pub use plain::PlainRender;
pub use render_trait::{PlanStepView, Render, ToolState};
pub use tty::TtyRender;

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
