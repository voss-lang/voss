//! Chat REPL with rustyline line editing + slash commands.

use std::path::Path;

use rustyline::DefaultEditor;
use voss_agent::{run_turn, EpisodicMemory, TurnConfig};
use voss_providers::ModelProvider;
use voss_render::{NdjsonRender, PlainRender, Render, TtyRender};

use crate::permissions::{Mode, PermissionGate, PermissionStore};
use crate::session::{self, SessionRecord, Turn};

pub async fn run_repl(
    cwd: &Path,
    json_mode: bool,
    mode: Mode,
    provider: &mut dyn ModelProvider,
    starting_record: Option<SessionRecord>,
) -> std::process::ExitCode {
    let mut history = EpisodicMemory::new(40);
    let mut record = starting_record
        .unwrap_or_else(|| SessionRecord::new(cwd, "claude-sonnet-4-5", None));
    for t in &record.turns {
        history.add(t.content.clone(), t.role.clone());
    }

    let mut renderer: Box<dyn Render> = if json_mode {
        Box::new(NdjsonRender::default())
    } else if is_terminal::is_terminal(std::io::stdout()) {
        Box::new(TtyRender::default())
    } else {
        Box::new(PlainRender::default())
    };

    let mut gate = PermissionGate {
        mode,
        store: Some(PermissionStore::load(cwd)),
        auto_yes: false,
    };
    let tools = voss_tools::default_toolset(cwd);
    let mut total_cost = record.total_cost_usd;

    renderer.banner(&record.model, cwd, &git_status(cwd));
    if !record.turns.is_empty() {
        println!("resumed: {} ({} prior turns)", record.name, record.turns.len());
    }

    let mut rl = match DefaultEditor::new() {
        Ok(r) => r,
        Err(e) => {
            eprintln!("rustyline init failed: {e}");
            return std::process::ExitCode::from(1);
        }
    };

    loop {
        let line = match rl.readline("▌ ") {
            Ok(l) => l,
            Err(_) => {
                println!();
                return std::process::ExitCode::SUCCESS;
            }
        };
        let line = line.trim().to_string();
        if line.is_empty() {
            continue;
        }
        let _ = rl.add_history_entry(&line);

        match line.as_str() {
            "/exit" | "/quit" => return std::process::ExitCode::SUCCESS,
            "/help" => {
                print_slash_help();
                continue;
            }
            "/clear" => {
                history = EpisodicMemory::new(40);
                println!("episodic memory cleared.");
                continue;
            }
            "/cost" => {
                println!("session cost: ${total_cost:.4}");
                continue;
            }
            "/tools" => {
                for t in &tools {
                    println!("  {} — {}", t.name(), t.description());
                }
                continue;
            }
            "/sessions" => {
                if let Ok(records) = session::list_sessions() {
                    for r in records {
                        let id_short: String = r.id.chars().take(8).collect();
                        println!("  {}  {}  {}", id_short, r.updated_at, r.name);
                    }
                }
                continue;
            }
            _ => {}
        }

        if let Some(rest) = line.strip_prefix("/save") {
            let name = rest.trim();
            if !name.is_empty() {
                record.name = name.into();
            }
            record.total_cost_usd = total_cost;
            record.turns = history
                .last(10_000)
                .into_iter()
                .map(|e| Turn {
                    role: e.role,
                    content: e.content,
                    extra: Default::default(),
                })
                .collect();
            match session::save(&mut record) {
                Ok(p) => println!("saved: {}", p.display()),
                Err(e) => eprintln!("save failed: {e}"),
            }
            continue;
        }
        if line.starts_with('/') {
            eprintln!("unknown command: {line}. /help for list.");
            continue;
        }

        renderer.show_user(&line);
        let mut adapter = GateAdapter { gate: &mut gate };
        let result = match run_turn(
            &line,
            &tools,
            cwd,
            renderer.as_mut(),
            provider,
            Some(&mut history),
            &mut adapter,
            TurnConfig::default(),
            json_mode,
        )
        .await
        {
            Ok(r) => r,
            Err(e) => {
                eprintln!("error: {e}");
                continue;
            }
        };
        total_cost += result.cost_usd;
        if !json_mode {
            renderer.show_final(&result.final_text, result.confidence, result.cost_usd);
        }
    }
}

fn print_slash_help() {
    println!(
        "/help          show this list\n\
         /exit /quit    leave the REPL (also Ctrl-D)\n\
         /clear         drop episodic memory\n\
         /cost          session cost so far\n\
         /tools         list registered tools\n\
         /sessions      list saved sessions\n\
         /save [name]   persist session snapshot"
    );
}

fn git_status(cwd: &Path) -> String {
    let out = std::process::Command::new("git")
        .args(["status", "--porcelain"])
        .current_dir(cwd)
        .output();
    match out {
        Ok(o) if o.status.success() => {
            let lines: Vec<&str> = std::str::from_utf8(&o.stdout)
                .unwrap_or("")
                .lines()
                .filter(|l| !l.trim().is_empty())
                .collect();
            if lines.is_empty() {
                "clean".into()
            } else {
                let plus = lines
                    .iter()
                    .filter(|l| l.starts_with('A') || l.starts_with('?'))
                    .count();
                let minus = lines.iter().filter(|l| l.starts_with('D')).count();
                let m = lines
                    .iter()
                    .filter(|l| l.starts_with(" M") || l.starts_with('M'))
                    .count();
                format!("+{plus} ~{m} -{minus}")
            }
        }
        _ => "not a git repo".into(),
    }
}

/// Adapter: implements `voss_agent::PermissionCheck` (defined in voss-agent)
/// by delegating to voss-cli's `PermissionGate`. Trait lives in voss-agent so
/// voss-agent has zero dep on voss-cli; voss-cli hosts the impl here.
pub struct GateAdapter<'a> {
    pub gate: &'a mut PermissionGate,
}

impl<'a> voss_agent::PermissionCheck for GateAdapter<'a> {
    fn check(&mut self, name: &str, args: &serde_json::Value) -> (bool, String) {
        let (allowed, reason) =
            self.gate
                .check(name, args, crate::permissions::interactive_prompt);
        (allowed, reason.to_string())
    }
}
