//! voss-agent — agent loop, plan schema, turn execution.

mod dispatch;
pub mod episodic;
pub mod plan;
pub mod run_turn;

pub use episodic::{EpisodicEntry, EpisodicMemory};
pub use plan::{Plan, ToolCall};
pub use run_turn::{
    run_turn, AlwaysAllow, PermissionCheck, TurnConfig, TurnResult, PLAN_SYSTEM,
};

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
