//! TTY renderer.

use std::io::{Stdout, Write};
use std::path::Path;

use crossterm::terminal::size;

use crate::render_trait::{PlanStepView, Render, ToolState};
use crate::status_line;

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

fn term_width() -> usize {
    size().map(|(w, _)| w as usize).unwrap_or(80)
}

fn short(v: &serde_json::Value, limit: usize) -> String {
    let s = match v {
        serde_json::Value::String(s) => s.clone(),
        other => other.to_string(),
    };
    if s.len() > limit {
        format!("{}…", &s[..limit.saturating_sub(1)])
    } else {
        s
    }
}

fn args_inline(args: &serde_json::Value) -> String {
    if let Some(obj) = args.as_object() {
        obj.iter()
            .map(|(k, v)| format!("{k}={}", short(v, 40)))
            .collect::<Vec<_>>()
            .join(", ")
    } else {
        args.to_string()
    }
}

impl Render for TtyRender {
    fn banner(&mut self, model: &str, cwd: &Path, git: &str) {
        let _ = writeln!(self.out, "voss · agent");
        let _ = writeln!(self.out, "{model} · {} · {git}", cwd.display());
        let _ = writeln!(self.out, "Type a task, or /help.");
    }

    fn show_user(&mut self, task: &str) {
        let _ = writeln!(self.out, "\n▌ {task}\n");
    }

    fn show_thinking(&mut self, label: &str) {
        let _ = writeln!(self.out, "  … {label}");
    }

    fn show_plan(
        &mut self,
        rationale: &str,
        steps: &[PlanStepView<'_>],
        confidence: f32,
        _cost: f64,
    ) {
        let _ = writeln!(self.out, "\n  Plan (confidence {confidence:.2})");
        if !rationale.is_empty() {
            let _ = writeln!(self.out, "  {rationale}");
        }
        for s in steps {
            if s.why.is_empty() {
                let _ = writeln!(self.out, "  • {}", s.name);
            } else {
                let _ = writeln!(self.out, "  • {} — {}", s.name, s.why);
            }
        }
        let _ = writeln!(self.out);
    }

    fn show_tool_call(
        &mut self,
        name: &str,
        args: &serde_json::Value,
        summary: &str,
        state: ToolState,
    ) {
        let mark = match state {
            ToolState::Ok => "✓",
            ToolState::Error => "✗",
            ToolState::Pending => "…",
        };
        let _ = writeln!(
            self.out,
            "  ⏵ {name}({})  {mark} {summary}",
            args_inline(args)
        );
    }

    fn show_clarify(&mut self, q: &str, conf: f32) {
        let _ = writeln!(self.out, "\n  ⚠ confidence {conf:.2} — clarifying:");
        let _ = writeln!(self.out, "  {q}\n");
    }

    fn show_final(&mut self, text: &str, conf: f32, cost: f64) {
        let _ = writeln!(self.out, "\n{text}\n");
        let _ = writeln!(self.out, "  confidence {conf:.2} · ${cost:.4}\n");
    }

    fn status(&mut self, model: &str, tokens: usize, cost: f64, ctx_pct: f32) {
        // D-08: end-of-turn only.
        let line = status_line::format(model, tokens, cost, ctx_pct, term_width());
        let _ = writeln!(self.out, "{line}");
    }
}
