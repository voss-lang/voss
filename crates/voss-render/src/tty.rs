//! TTY renderer — T2 implements.

use std::io::Stdout;
use std::path::Path;

use voss_agent::Plan;

use crate::render_trait::{Render, ToolState};

pub struct TtyRender {
    pub out: Stdout,
}

impl Default for TtyRender {
    fn default() -> Self {
        Self {
            out: std::io::stdout(),
        }
    }
}

impl Render for TtyRender {
    fn banner(&mut self, _model: &str, _cwd: &Path, _git: &str) {}
    fn show_user(&mut self, _task: &str) {}
    fn show_thinking(&mut self, _label: &str) {}
    fn show_plan(&mut self, _plan: &Plan, _cost: f64) {}
    fn show_tool_call(&mut self, _: &str, _: &serde_json::Value, _: &str, _: ToolState) {}
    fn show_clarify(&mut self, _q: &str, _c: f32) {}
    fn show_final(&mut self, _text: &str, _c: f32, _cost: f64) {}
    fn status(&mut self, _model: &str, _tokens: usize, _cost: f64, _ctx: f32) {}
}
