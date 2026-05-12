//! `run_turn` — one agent turn. Mirrors `voss/harness/agent.py::run_turn`
//! but partitions tool execution per D-11..D-14 (parallel-by-default).

use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use voss_providers::{CompleteRequest, Message, ModelProvider};
use voss_render::{PlanStepView, Render};
use voss_tools::Tool;

use crate::episodic::EpisodicMemory;
use crate::Plan;

pub const PLAN_SYSTEM: &str = "You are Voss, a coding agent running in a terminal.\n\
\n\
You receive a task and a list of tools. Produce a Plan: rationale, sequential\n\
tool calls, self-rated confidence (0.0-1.0), and the final answer to surface\n\
to the user once tools have run.\n\
\n\
Confidence rubric:\n\
- 0.95+: trivial, deterministic, single-step\n\
- 0.80-0.94: clear path, normal risk\n\
- 0.60-0.79: ambiguity present; consider asking\n\
- below 0.60: unclear; populate open_question and leave steps empty\n\
\n\
Only call tools from the provided list. Reference tool result placeholders\n\
({{step_0}}, {{step_1}}, ...) inside `final_when_done` if the answer depends\n\
on them. Keep `final_when_done` short — under 200 words.\n";

/// Permission-check abstraction. **Defined in voss-agent** (not voss-cli) so
/// voss-cli can supply an adapter without forcing voss-agent to depend on
/// voss-cli (build-graph cycle prevention). voss-cli's `cli/repl.rs`
/// provides `GateAdapter` implementing this trait.
pub trait PermissionCheck: Send + Sync {
    fn check(&mut self, tool_name: &str, args: &serde_json::Value) -> (bool, String);
}

/// Always-allow stub used by tests + non-interactive runs.
pub struct AlwaysAllow;

impl PermissionCheck for AlwaysAllow {
    fn check(&mut self, _: &str, _: &serde_json::Value) -> (bool, String) {
        (true, "auto".into())
    }
}

#[derive(Clone, Debug)]
pub struct TurnConfig {
    pub confidence_threshold: f32,
    pub token_budget: usize,
    pub max_output_tokens: u32,
    pub model: String,
    pub parallel_cap: usize,
    /// Ctrl-C cancel signal. When set to `true`, `run_turn` aborts at the
    /// next checkpoint (before LLM call, before dispatch, between steps).
    /// `None` = uncancellable (test/headless default).
    pub cancel: Option<Arc<AtomicBool>>,
}

impl Default for TurnConfig {
    fn default() -> Self {
        Self {
            confidence_threshold: 0.60,
            token_budget: 60_000,
            max_output_tokens: 4096,
            model: "claude-sonnet-4-5".into(),
            parallel_cap: 8,
            cancel: None,
        }
    }
}

/// True if a cancel token is set and tripped.
pub(crate) fn cancelled(tok: &Option<Arc<AtomicBool>>) -> bool {
    tok.as_ref()
        .map(|t| t.load(Ordering::Relaxed))
        .unwrap_or(false)
}

#[derive(Debug)]
pub struct TurnResult {
    pub plan: Plan,
    pub confidence: f32,
    pub final_text: String,
    pub tool_results: Vec<String>,
    pub cost_usd: f64,
}

fn format_tools(tools: &[Arc<dyn Tool>]) -> String {
    tools
        .iter()
        .map(|t| {
            let schema = t.schema();
            let props = schema.get("properties").and_then(|v| v.as_object());
            let sig: String = props
                .map(|m| {
                    m.iter()
                        .map(|(k, v)| {
                            let typ = v.get("type").and_then(|x| x.as_str()).unwrap_or("any");
                            format!("{k}: {typ}")
                        })
                        .collect::<Vec<_>>()
                        .join(", ")
                })
                .unwrap_or_default();
            format!("- {}({sig}) — {}", t.name(), t.description())
        })
        .collect::<Vec<_>>()
        .join("\n")
}

#[allow(clippy::too_many_arguments)]
pub async fn run_turn(
    task: &str,
    tools: &[Arc<dyn Tool>],
    cwd: &Path,
    renderer: &mut dyn Render,
    provider: &mut dyn ModelProvider,
    mut history: Option<&mut EpisodicMemory>,
    permissions: &mut dyn PermissionCheck,
    cfg: TurnConfig,
    suppress_status: bool,
) -> anyhow::Result<TurnResult> {
    let history_block = match history.as_deref() {
        Some(h) => {
            let recent = h.last(6);
            if recent.is_empty() {
                String::new()
            } else {
                let mut s = String::from("\n\nRecent conversation:\n");
                for m in &recent {
                    s.push_str(&format!("{}: {}\n", m.role, m.content));
                }
                s
            }
        }
        None => String::new(),
    };

    let user_prompt = format!(
        "Task:\n{task}\n\nWorking directory: {}\n\nAvailable tools:\n{}{}\n",
        cwd.display(),
        format_tools(tools),
        history_block,
    );
    if let Some(h) = history.as_deref_mut() {
        h.add(task, "user");
    }

    if cancelled(&cfg.cancel) {
        anyhow::bail!("cancelled");
    }
    renderer.show_thinking("planning");

    let plan_schema = serde_json::to_value(schemars::schema_for!(Plan))?;
    let req = CompleteRequest {
        messages: vec![
            Message {
                role: "system".into(),
                content: PLAN_SYSTEM.into(),
            },
            Message {
                role: "user".into(),
                content: user_prompt,
            },
        ],
        model: cfg.model.clone(),
        temperature: 0.2,
        max_tokens: Some(cfg.max_output_tokens),
        response_schema: Some(plan_schema),
        response_schema_name: Some("Plan".into()),
        tools: None,
    };
    let resp = provider.complete(req).await?;
    let plan: Plan = match resp.parsed.clone() {
        Some(v) => serde_json::from_value(v)?,
        None => anyhow::bail!(
            "provider returned no parsed Plan; raw text: {}",
            &resp.text[..resp.text.len().min(300)]
        ),
    };
    let step_args: Vec<serde_json::Value> = plan
        .steps
        .iter()
        .map(|s| serde_json::Value::Object(s.args.clone()))
        .collect();
    let step_views: Vec<PlanStepView> = plan
        .steps
        .iter()
        .zip(step_args.iter())
        .map(|(s, a)| PlanStepView {
            name: &s.name,
            args: a,
            why: &s.why,
        })
        .collect();
    renderer.show_plan(&plan.rationale, &step_views, plan.confidence, resp.cost_usd);

    let confidence = plan.confidence;
    if confidence < cfg.confidence_threshold {
        let q = plan
            .open_question
            .clone()
            .unwrap_or_else(|| "I'm not confident enough — can you clarify the task?".into());
        renderer.show_clarify(&q, confidence);
        return Ok(TurnResult {
            plan,
            confidence,
            final_text: q,
            tool_results: Vec::new(),
            cost_usd: resp.cost_usd,
        });
    }

    if cancelled(&cfg.cancel) {
        anyhow::bail!("cancelled");
    }
    let results = crate::dispatch::dispatch_steps(
        &plan.steps,
        tools,
        renderer,
        permissions,
        cfg.parallel_cap,
        cfg.cancel.clone(),
    )
    .await;

    let mut final_text = if plan.final_when_done.is_empty() {
        "(no final answer)".into()
    } else {
        plan.final_when_done.clone()
    };
    for (i, r) in results.iter().enumerate() {
        final_text = final_text.replace(&format!("{{{{step_{i}}}}}"), r);
    }

    if let Some(h) = history.as_deref_mut() {
        h.add(&final_text, "assistant");
    }

    let total_tokens = (resp.prompt_tokens + resp.completion_tokens) as usize;
    let ctx_pct = if cfg.token_budget == 0 {
        0.0
    } else {
        total_tokens as f32 / cfg.token_budget as f32
    };

    // D-08: status line at end of turn ONLY in TTY mode (suppressed in --json).
    // Exactly once per turn in TTY mode.
    if !suppress_status {
        renderer.status(&cfg.model, total_tokens, resp.cost_usd, ctx_pct);
    }

    Ok(TurnResult {
        plan,
        confidence,
        final_text,
        tool_results: results,
        cost_usd: resp.cost_usd,
    })
}
