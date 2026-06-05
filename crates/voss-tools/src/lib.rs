//! voss-tools — sandbox + tools + registry.

pub mod anchor;
pub mod fs_edit;
pub mod fs_glob;
pub mod fs_grep;
pub mod fs_read;
pub mod fs_write;
pub mod git_diff;
pub mod git_status;
pub mod registry;
pub mod sandbox;
pub mod shell_capture;
pub mod shell_run;
pub mod tool_trait;
pub mod voss_check;

pub use registry::default_toolset;
pub use tool_trait::Tool;

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
