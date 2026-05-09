//! Renderer trait shared by all 3 impls.

use std::path::Path;

use voss_agent::Plan;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ToolState {
    Pending,
    Ok,
    Error,
}

impl ToolState {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Ok => "ok",
            Self::Error => "error",
        }
    }
}

pub trait Render: Send {
    fn banner(&mut self, model: &str, cwd: &Path, git_status: &str);
    fn show_user(&mut self, task: &str);
    fn show_thinking(&mut self, label: &str);
    fn show_plan(&mut self, plan: &Plan, cost_usd: f64);
    fn show_tool_call(
        &mut self,
        name: &str,
        args: &serde_json::Value,
        summary: &str,
        state: ToolState,
    );
    fn show_clarify(&mut self, question: &str, confidence: f32);
    fn show_final(&mut self, text: &str, confidence: f32, cost_usd: f64);
    fn status(&mut self, model: &str, tokens: usize, cost_usd: f64, ctx_pct: f32);
}
