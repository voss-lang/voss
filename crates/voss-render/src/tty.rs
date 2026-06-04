//! TTY renderer. Boxed cards for plan / tool calls, ANSI-styled assistant
//! replies via the markdown sub-module, and a budget-bar at end-of-turn.

use std::io::{Stdout, Write};
use std::path::Path;

use crossterm::terminal::size;

use crate::markdown;
use crate::render_trait::{PlanStepView, Render, ToolState};
use crate::status_line;

const RESET: &str = "\x1b[0m";
const BOLD: &str = "\x1b[1m";
const DIM: &str = "\x1b[2m";
const GREEN: &str = "\x1b[32m";
const RED: &str = "\x1b[31m";
const YELLOW: &str = "\x1b[33m";
const CYAN: &str = "\x1b[36m";

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
    size().map(|(w, _)| w as usize).unwrap_or(80).clamp(40, 200)
}

fn short(v: &serde_json::Value, limit: usize) -> String {
    let s = match v {
        serde_json::Value::String(s) => s.clone(),
        other => other.to_string(),
    };
    if s.chars().count() > limit {
        let trimmed: String = s.chars().take(limit.saturating_sub(1)).collect();
        format!("{trimmed}…")
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

/// 8-cell confidence meter. Red <0.6, yellow <0.8, green ≥0.8.
fn confidence_bar(confidence: f32) -> String {
    let conf = confidence.clamp(0.0, 1.0);
    let filled = (conf * 8.0).round() as usize;
    let bar: String = (0..8).map(|i| if i < filled { '▰' } else { '▱' }).collect();
    let color = if conf >= 0.80 {
        GREEN
    } else if conf >= 0.60 {
        YELLOW
    } else {
        RED
    };
    format!("{color}{bar}{RESET}")
}

/// Render a card with a titled top bar and bottom edge. `title_left` shown
/// bold; `title_right` shown dim and right-aligned. Body is written between.
fn open_card(out: &mut Stdout, title_left: &str, title_right: &str) {
    let w = term_width();
    let left_visible = title_left.chars().count();
    let right_visible = title_right.chars().count();
    let pad = w.saturating_sub(left_visible + right_visible + 4).max(1);
    let dashes = "─".repeat(pad);
    let _ = writeln!(
        out,
        "{DIM}╭─{RESET} {BOLD}{title_left}{RESET} {DIM}{dashes} {title_right} ─╮{RESET}"
    );
}

fn close_card(out: &mut Stdout) {
    let w = term_width();
    let dashes = "─".repeat(w.saturating_sub(2));
    let _ = writeln!(out, "{DIM}╰{dashes}╯{RESET}");
}

fn body_line(out: &mut Stdout, line: &str) {
    let _ = writeln!(out, "{DIM}│{RESET} {line}");
}

impl Render for TtyRender {
    fn banner(&mut self, model: &str, cwd: &Path, git: &str) {
        open_card(&mut self.out, "voss · agent", git);
        body_line(&mut self.out, &format!("model  {CYAN}{model}{RESET}"));
        body_line(&mut self.out, &format!("cwd    {}", cwd.display()));
        body_line(&mut self.out, "type a task, or /help");
        close_card(&mut self.out);
    }

    fn show_user(&mut self, task: &str) {
        let _ = writeln!(self.out, "\n{BOLD}▌ {task}{RESET}\n");
    }

    fn show_thinking(&mut self, label: &str) {
        let _ = writeln!(self.out, "{DIM}  … {label}{RESET}");
    }

    fn show_plan(
        &mut self,
        rationale: &str,
        steps: &[PlanStepView<'_>],
        confidence: f32,
        cost: f64,
    ) {
        let title = format!(
            "plan · {} {confidence:.2} · ${cost:.4}",
            confidence_bar(confidence)
        );
        open_card(&mut self.out, "plan", &title);
        if !rationale.is_empty() {
            for line in rationale.lines() {
                body_line(&mut self.out, line);
            }
        }
        for (i, s) in steps.iter().enumerate() {
            let why = if s.why.is_empty() {
                String::new()
            } else {
                format!(" {DIM}— {}{RESET}", s.why)
            };
            body_line(
                &mut self.out,
                &format!("{DIM}{:>2}.{RESET} {CYAN}{}{RESET}{why}", i + 1, s.name),
            );
        }
        close_card(&mut self.out);
    }

    fn show_tool_call(
        &mut self,
        name: &str,
        args: &serde_json::Value,
        summary: &str,
        state: ToolState,
    ) {
        let (mark, color) = match state {
            ToolState::Ok => ("✓", GREEN),
            ToolState::Error => ("✗", RED),
            ToolState::Pending => ("…", YELLOW),
        };
        let args_str = args_inline(args);
        // Single line — compact like Claude Code.
        let _ = writeln!(
            self.out,
            "  {color}{mark}{RESET} {CYAN}{name}{RESET}({DIM}{args_str}{RESET})  {DIM}{summary}{RESET}"
        );
    }

    fn show_clarify(&mut self, q: &str, conf: f32) {
        open_card(
            &mut self.out,
            "clarify",
            &format!("{} {conf:.2}", confidence_bar(conf)),
        );
        for line in q.lines() {
            body_line(&mut self.out, line);
        }
        close_card(&mut self.out);
    }

    fn show_final(&mut self, text: &str, conf: f32, cost: f64) {
        let body = markdown::to_ansi(text);
        let _ = writeln!(self.out, "\n{body}\n");
        let _ = writeln!(
            self.out,
            "{DIM}  confidence {} {:.2} · ${:.4}{RESET}\n",
            confidence_bar(conf),
            conf,
            cost
        );
    }

    fn status(&mut self, model: &str, tokens: usize, cost: f64, ctx_pct: f32) {
        // D-08: end-of-turn only.
        let line = status_line::format(model, tokens, cost, ctx_pct, term_width());
        let _ = writeln!(self.out, "{line}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bar_clamps_and_colors() {
        let red = confidence_bar(0.1);
        assert!(red.contains(RED));
        let yellow = confidence_bar(0.65);
        assert!(yellow.contains(YELLOW));
        let green = confidence_bar(0.95);
        assert!(green.contains(GREEN));
    }

    #[test]
    fn bar_extremes() {
        let zero = confidence_bar(0.0);
        assert!(zero.contains("▱"));
        let one = confidence_bar(1.0);
        assert_eq!(one.matches('▰').count(), 8);
    }
}
