use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::Arc;

use anyhow::anyhow;
use async_trait::async_trait;
use serde_json::{json, Value};
use tokio::sync::Mutex;

use voss_agent::{run_turn, AlwaysAllow, EpisodicMemory, TurnConfig};
use voss_providers::{CompleteRequest, ModelProvider, ProviderResponse};
use voss_render::PlainRender;
use voss_tools::Tool;

pub const SKILLS: &[(&str, &str)] = &[("analyze", "Refresh project cognition.")];
pub const AGENTS: &[(&str, &str, &str)] = &[
    (
        "explorer",
        "Inspect code and return concise findings.",
        "You are a read-heavy code explorer. Inspect first, avoid edits unless explicitly required.",
    ),
    (
        "worker",
        "Carry out a bounded implementation task.",
        "You are an implementation worker. Keep changes scoped and verify the result.",
    ),
    (
        "reviewer",
        "Review code for bugs, regressions, and missing tests.",
        "You are a code reviewer. Prioritize concrete findings over summaries.",
    ),
];

pub fn agent_ids() -> Vec<&'static str> {
    AGENTS.iter().map(|(id, _, _)| *id).collect()
}

pub fn skill_ids() -> Vec<&'static str> {
    SKILLS.iter().map(|(id, _)| *id).collect()
}

pub fn pick_python() -> PathBuf {
    if let Some(path) = std::env::var_os("VOSS_PYTHON") {
        return PathBuf::from(path);
    }
    let venv = std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join(".venv/bin/python");
    if venv.exists() {
        return venv;
    }
    PathBuf::from("python3")
}

pub fn run_python_skill(skill_id: &str, args: &[String]) -> std::process::ExitCode {
    if !SKILLS.iter().any(|(id, _)| *id == skill_id) {
        eprintln!("unknown skill: {skill_id}");
        return std::process::ExitCode::from(1);
    }
    let mut cmd = Command::new(pick_python());
    cmd.args(["-m", "voss.harness", "skill", "run", skill_id]);
    cmd.args(args);
    match cmd.status() {
        Ok(status) if status.success() => std::process::ExitCode::SUCCESS,
        Ok(status) => std::process::ExitCode::from(status.code().unwrap_or(1) as u8),
        Err(e) => {
            eprintln!("skill {skill_id} failed to start Python harness: {e}");
            std::process::ExitCode::from(1)
        }
    }
}

pub type SharedProvider = Arc<Mutex<Box<dyn ModelProvider>>>;

pub struct SharedProviderAdapter {
    inner: SharedProvider,
}

impl SharedProviderAdapter {
    pub fn new(inner: SharedProvider) -> Self {
        Self { inner }
    }
}

#[async_trait]
impl ModelProvider for SharedProviderAdapter {
    async fn complete(&mut self, req: CompleteRequest) -> anyhow::Result<ProviderResponse> {
        self.inner.lock().await.complete(req).await
    }

    fn count_tokens(&self, text: &str, model: &str) -> usize {
        if let Ok(provider) = self.inner.try_lock() {
            provider.count_tokens(text, model)
        } else {
            (text.len() / 4).max(1)
        }
    }
}

pub struct SubagentRunTool {
    pub cwd: PathBuf,
    pub provider: SharedProvider,
    pub mode: crate::permissions::Mode,
    pub model: String,
}

#[async_trait]
impl Tool for SubagentRunTool {
    fn name(&self) -> &str {
        "subagent_run"
    }

    fn description(&self) -> &str {
        "Run a registered Voss subagent on a bounded task."
    }

    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "task": {"type": "string"}
            },
            "required": ["agent", "task"]
        })
    }

    fn is_mutating(&self) -> bool {
        true
    }

    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let agent = args
            .get("agent")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("missing agent"))?;
        let task = args
            .get("task")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("missing task"))?;
        run_subagent(
            agent,
            task,
            &self.cwd,
            self.provider.clone(),
            self.mode,
            &self.model,
        )
        .await
    }
}

pub fn tools_with_subagent(
    cwd: &Path,
    provider: SharedProvider,
    mode: crate::permissions::Mode,
    model: &str,
) -> Vec<Arc<dyn Tool>> {
    let mut tools = voss_tools::default_toolset(cwd);
    tools.push(Arc::new(SubagentRunTool {
        cwd: cwd.to_path_buf(),
        provider,
        mode,
        model: model.to_string(),
    }));
    tools
}

pub async fn run_subagent(
    agent: &str,
    task: &str,
    cwd: &Path,
    provider: SharedProvider,
    _mode: crate::permissions::Mode,
    model: &str,
) -> anyhow::Result<String> {
    let Some((_, _, role)) = AGENTS.iter().find(|(id, _, _)| *id == agent) else {
        return Ok(format!("<error: unknown subagent {agent:?}>"));
    };
    let child_task = format!("Subagent role:\n{role}\n\nTask:\n{task}");
    let tools = voss_tools::default_toolset(cwd);
    let mut adapter = SharedProviderAdapter::new(provider);
    let mut renderer = PlainRender::default();
    let mut history = EpisodicMemory::new(20);
    let mut perms = AlwaysAllow;
    let cfg = TurnConfig {
        model: model.to_string(),
        ..TurnConfig::default()
    };
    let result = run_turn(
        &child_task,
        &tools,
        cwd,
        &mut renderer,
        &mut adapter,
        Some(&mut history),
        &mut perms,
        cfg,
        false,
    )
    .await?;
    Ok(result.final_text)
}
