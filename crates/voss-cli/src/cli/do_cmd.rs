//! `voss-cli do <task>` — one-shot agent invocation.

use std::path::Path;

use voss_agent::{run_turn, EpisodicMemory, TurnConfig};
use voss_auth::{resolve, AuthPref};
use voss_render::{NdjsonRender, PlainRender, Render, TtyRender};

use crate::cli::auth_to_provider;
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
    let mut provider = match auth_to_provider::build(res) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("auth failed: {e}");
            return std::process::ExitCode::from(2);
        }
    };

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

    let tools = voss_tools::default_toolset(&cwd);
    let mut history = EpisodicMemory::new(40);

    match run_turn(
        task,
        &tools,
        &cwd,
        renderer.as_mut(),
        provider.as_mut(),
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
