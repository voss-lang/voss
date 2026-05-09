//! Plain renderer. Mirrors `voss/harness/render.py::PlainRenderer`.

use std::io::Write;
use std::path::Path;

use crate::render_trait::{PlanStepView, Render, ToolState};

pub struct PlainRender<W: Write + Send = std::io::Stderr, S: Write + Send = std::io::Stdout> {
    pub stderr: W,
    pub stdout: S,
}

impl Default for PlainRender {
    fn default() -> Self {
        Self {
            stderr: std::io::stderr(),
            stdout: std::io::stdout(),
        }
    }
}

impl<W: Write + Send, S: Write + Send> Render for PlainRender<W, S> {
    fn banner(&mut self, _: &str, _: &Path, _: &str) {}

    fn show_user(&mut self, task: &str) {
        let _ = writeln!(self.stderr, "> {task}");
    }

    fn show_thinking(&mut self, label: &str) {
        let _ = writeln!(self.stderr, "... {label}");
    }

    fn show_plan(
        &mut self,
        _rationale: &str,
        steps: &[PlanStepView<'_>],
        confidence: f32,
        _cost: f64,
    ) {
        let _ = writeln!(
            self.stderr,
            "plan: {} steps, conf={confidence:.2}",
            steps.len()
        );
    }

    fn show_tool_call(
        &mut self,
        name: &str,
        args: &serde_json::Value,
        summary: &str,
        state: ToolState,
    ) {
        let _ = writeln!(
            self.stderr,
            "[{}] {name}({args}) -> {summary}",
            state.as_str()
        );
    }

    fn show_clarify(&mut self, question: &str, _: f32) {
        let _ = writeln!(self.stdout, "{question}");
    }

    fn show_final(&mut self, text: &str, _: f32, _: f64) {
        let _ = writeln!(self.stdout, "{text}");
    }

    fn status(&mut self, _: &str, _: usize, _: f64, _: f32) {}
}
