//! `voss-cli do <task>` — one-shot agent invocation.

use std::path::Path;

use voss_agent::{run_turn, EpisodicMemory, TurnConfig};
use voss_auth::{resolve, AuthPref};
use voss_render::{NdjsonRender, PlainRender, Render, TtyRender};

use crate::cli::auth_to_provider;
use crate::extensions::{tools_with_subagent, SharedProviderAdapter};
use crate::cli::repl::GateAdapter;
use crate::permissions::{Mode, PermissionGate, PermissionStore};

pub async fn run_do(
    task: &str,
    json_mode: bool,
    mode_str: &str,
    yes: bool,
    auth_pref: &str,
) -> std::process::ExitCode {
    let cwd = std::env::current_dir().unwrap_or_else(|_| Path::new(".").to_path_buf());

    let res = resolve(AuthPref::parse(auth_pref));
    let provider = match auth_to_provider::build(res) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("auth failed: {e}");
            return std::process::ExitCode::from(2);
        }
    };
    let shared_provider = std::sync::Arc::new(tokio::sync::Mutex::new(provider));
    let mut provider_adapter = SharedProviderAdapter::new(shared_provider.clone());

    let mode = Mode::parse(mode_str).unwrap_or(Mode::Edit);
    let mut gate = PermissionGate {
        mode,
        store: Some(PermissionStore::load(&cwd)),
        auto_yes: yes,
    };
    let mut adapter = GateAdapter { gate: &mut gate };

    let mut renderer: Box<dyn Render> = if json_mode {
        Box::new(NdjsonRender::default())
    } else if is_terminal::is_terminal(std::io::stdout()) {
        Box::new(TtyRender::default())
    } else {
        Box::new(PlainRender::default())
    };

    let tools = tools_with_subagent(&cwd, shared_provider, mode, "claude-sonnet-4-5");
    let mut history = EpisodicMemory::new(40);

    match run_turn(
        task,
        &tools,
        &cwd,
        renderer.as_mut(),
        &mut provider_adapter,
        Some(&mut history),
        &mut adapter,
        TurnConfig::default(),
        json_mode,
    )
    .await
    {
        Ok(result) => {
            if !json_mode {
                renderer.show_final(&result.final_text, result.confidence, result.cost_usd);
            }
            std::process::ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("error: {e}");
            std::process::ExitCode::from(1)
        }
    }
}
