//! NDJSON renderer — one JSON object per line on stdout, every payload
//! prefixed with `"v": 1`. Mirrors `voss/harness/render.py::JsonRenderer`.

use std::io::Write;
use std::path::Path;

use serde_json::json;

use crate::render_trait::{PlanStepView, Render, ToolState};

pub const PROTOCOL_VERSION: u32 = 1;

pub struct NdjsonRender<W: Write + Send = std::io::Stdout> {
    pub out: W,
}

impl Default for NdjsonRender {
    fn default() -> Self {
        Self {
            out: std::io::stdout(),
        }
    }
}

impl<W: Write + Send> NdjsonRender<W> {
    fn emit(&mut self, mut value: serde_json::Value) {
        if let Some(obj) = value.as_object_mut() {
            obj.insert("v".to_string(), json!(PROTOCOL_VERSION));
        }
        let _ = writeln!(self.out, "{}", serde_json::to_string(&value).unwrap());
        let _ = self.out.flush();
    }
}

impl<W: Write + Send> Render for NdjsonRender<W> {
    fn banner(&mut self, model: &str, cwd: &Path, git: &str) {
        self.emit(json!({
            "type": "banner",
            "model": model,
            "cwd": cwd.to_string_lossy(),
            "git": git,
        }));
    }

    fn show_user(&mut self, task: &str) {
        self.emit(json!({"type": "user", "task": task}));
    }

    fn show_thinking(&mut self, label: &str) {
        self.emit(json!({"type": "thinking", "label": label}));
    }

    fn show_plan(
        &mut self,
        _rationale: &str,
        steps: &[PlanStepView<'_>],
        confidence: f32,
        cost_usd: f64,
    ) {
        let steps_json: Vec<_> = steps
            .iter()
            .map(|s| json!({"name": s.name, "args": s.args}))
            .collect();
        self.emit(json!({
            "type": "plan",
            "confidence": confidence,
            "steps": steps_json,
            "cost_usd": cost_usd,
        }));
    }

    fn show_tool_call(
        &mut self,
        name: &str,
        args: &serde_json::Value,
        summary: &str,
        state: ToolState,
    ) {
        self.emit(json!({
            "type": "tool",
            "name": name,
            "args": args,
            "summary": summary,
            "state": state.as_str(),
        }));
    }

    fn show_clarify(&mut self, question: &str, confidence: f32) {
        self.emit(json!({
            "type": "clarify",
            "question": question,
            "confidence": confidence,
        }));
    }

    fn show_final(&mut self, text: &str, confidence: f32, cost_usd: f64) {
        self.emit(json!({
            "type": "final",
            "text": text,
            "confidence": confidence,
            "cost_usd": cost_usd,
        }));
    }

    fn status(&mut self, model: &str, tokens: usize, cost_usd: f64, ctx_pct: f32) {
        self.emit(json!({
            "type": "status",
            "model": model,
            "tokens": tokens,
            "cost_usd": cost_usd,
            "ctx_pct": ctx_pct,
        }));
    }
}
