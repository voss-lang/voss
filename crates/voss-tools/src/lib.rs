//! voss-tools — sandbox + tool registry.

pub mod sandbox;

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
