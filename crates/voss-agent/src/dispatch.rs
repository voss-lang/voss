//! Stub — T2 implements parallel-by-default dispatch.

use std::sync::Arc;

use voss_render::Render;
use voss_tools::Tool;

use crate::run_turn::PermissionCheck;
use crate::ToolCall;

pub(crate) async fn dispatch_steps(
    _steps: &[ToolCall],
    _tools: &[Arc<dyn Tool>],
    _renderer: &mut dyn Render,
    _perms: &mut dyn PermissionCheck,
    _parallel_cap: usize,
) -> Vec<String> {
    Vec::new()
}
