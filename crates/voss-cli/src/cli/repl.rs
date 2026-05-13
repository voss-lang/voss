//! Chat REPL with reedline line editing, slash commands, and Ctrl-C
//! turn-cancel.
//!
//! Input layer: `reedline` (multi-line, history, menu completion, custom
//! prompt with right-side status). Replaces the legacy `rustyline` impl.

use std::borrow::Cow;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use crossterm::style::Stylize;
use nu_ansi_term::{Color, Style};
use reedline::{
    default_emacs_keybindings, ColumnarMenu, Completer, DefaultHinter, EditCommand, Emacs,
    FileBackedHistory, KeyCode, KeyModifiers, MenuBuilder, Prompt, PromptEditMode,
    PromptHistorySearch, PromptHistorySearchStatus, Reedline, ReedlineEvent, ReedlineMenu, Signal,
    Span, Suggestion,
};

use voss_agent::{run_turn, EpisodicMemory, TurnConfig};
use voss_providers::ModelProvider;
use voss_render::{NdjsonRender, PlainRender, Render, TtyRender};

use crate::extensions::{
    agent_ids, run_subagent, skill_ids, tools_with_subagent, SharedProviderAdapter, AGENTS, SKILLS,
};
use crate::permissions::{Mode, PermissionGate, PermissionStore};
use crate::plugins::{load_plugins, set_plugin_enabled};
use crate::session::{self, SessionRecord, Turn};

const SLASH_COMMANDS: &[&str] = &[
    "/help",
    "/exit",
    "/quit",
    "/clear",
    "/cost",
    "/tools",
    "/sessions",
    "/save",
    "/plugins",
    "/plugin",
    "/skills",
    "/skill",
    "/agents",
    "/agent",
];

/// History file location. `~/.local/state/voss/history` (single global; per-cwd
/// scoping deferred — reedline filters duplicates on read).
fn history_path() -> PathBuf {
    let base = dirs::state_dir()
        .or_else(dirs::data_local_dir)
        .unwrap_or_else(|| PathBuf::from("."));
    base.join("voss").join("history")
}

pub async fn run_repl(
    cwd: &Path,
    json_mode: bool,
    mode: Mode,
    provider: Box<dyn ModelProvider>,
    starting_record: Option<SessionRecord>,
) -> std::process::ExitCode {
    let mut history = EpisodicMemory::new(40);
    let mut record =
        starting_record.unwrap_or_else(|| SessionRecord::new(cwd, "claude-sonnet-4-5", None));
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
    let shared_provider = Arc::new(tokio::sync::Mutex::new(provider));
    let mut provider_adapter = SharedProviderAdapter::new(shared_provider.clone());
    let tools = tools_with_subagent(cwd, shared_provider.clone(), mode, &record.model);
    let mut total_cost = record.total_cost_usd;

    renderer.banner(&record.model, cwd, &git_status(cwd));
    if !record.turns.is_empty() {
        println!(
            "resumed: {} ({} prior turns)",
            record.name,
            record.turns.len()
        );
    }

    // SIGINT → cancel current turn (not exit). reedline traps Ctrl-C in raw
    // mode during read_line; this handler only fires while run_turn owns the
    // terminal.
    let cancel = Arc::new(AtomicBool::new(false));
    {
        let c = cancel.clone();
        tokio::spawn(async move {
            loop {
                if tokio::signal::ctrl_c().await.is_ok() {
                    c.store(true, Ordering::Relaxed);
                }
            }
        });
    }

    let mut rl = match build_reedline() {
        Ok(r) => r,
        Err(e) => {
            eprintln!("reedline init failed: {e}");
            return std::process::ExitCode::from(1);
        }
    };

    loop {
        let prompt = VossPrompt {
            model: record.model.clone(),
            mode: mode_label(mode),
            cost: total_cost,
            git: git_status(cwd),
        };
        let sig = rl.read_line(&prompt);
        let line = match sig {
            Ok(Signal::Success(l)) => l,
            Ok(Signal::CtrlC) => {
                // Empty buffer Ctrl-C → noop. Reedline already cleared the
                // current edit. Continue to next prompt.
                continue;
            }
            Ok(Signal::CtrlD) => {
                println!();
                return std::process::ExitCode::SUCCESS;
            }
            Err(e) => {
                eprintln!("read error: {e}");
                return std::process::ExitCode::from(1);
            }
        };
        let line = line.trim().to_string();
        if line.is_empty() {
            continue;
        }

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
            "/plugins" => {
                print_plugins(cwd);
                continue;
            }
            "/skills" => {
                print_skills();
                continue;
            }
            "/agents" => {
                print_agents();
                continue;
            }
            _ => {}
        }

        if let Some(rest) = line.strip_prefix("/plugin ") {
            let parts: Vec<&str> = rest.split_whitespace().collect();
            if parts.len() == 2 && (parts[0] == "enable" || parts[0] == "disable") {
                match set_plugin_enabled(parts[1], parts[0] == "enable") {
                    Ok(path) => println!(
                        "plugin {} {}: {}",
                        parts[1],
                        if parts[0] == "enable" {
                            "enabled"
                        } else {
                            "disabled"
                        },
                        path.display()
                    ),
                    Err(e) => eprintln!("plugin update failed: {e}"),
                }
            } else {
                eprintln!("usage: /plugin enable|disable <id>");
            }
            continue;
        }
        if let Some(rest) = line.strip_prefix("/skill ") {
            let parts: Vec<&str> = rest.split_whitespace().collect();
            if parts.first().copied() == Some("analyze") {
                eprintln!("skill 'analyze' is not implemented in the Rust CLI yet");
            } else {
                eprintln!("unknown skill: {}", parts.first().copied().unwrap_or(""));
            }
            continue;
        }
        if let Some(rest) = line.strip_prefix("/agent ") {
            let parts: Vec<&str> = rest.split_whitespace().collect();
            if parts.len() >= 3 && parts[0] == "spawn" {
                match run_subagent(
                    parts[1],
                    &parts[2..].join(" "),
                    cwd,
                    shared_provider.clone(),
                    mode,
                    &record.model,
                )
                .await
                {
                    Ok(text) => println!("{text}"),
                    Err(e) => eprintln!("agent spawn failed: {e}"),
                }
            } else {
                eprintln!("usage: /agent spawn <id> <task>");
            }
            continue;
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

        // Reset cancel for this turn. SIGINT handler above will flip it.
        cancel.store(false, Ordering::Relaxed);

        let mut adapter = GateAdapter { gate: &mut gate };
        let mut cfg = TurnConfig::default();
        cfg.cancel = Some(cancel.clone());

        let result = match run_turn(
            &line,
            &tools,
            cwd,
            renderer.as_mut(),
            &mut provider_adapter,
            Some(&mut history),
            &mut adapter,
            cfg,
            json_mode,
        )
        .await
        {
            Ok(r) => r,
            Err(e) => {
                if cancel.load(Ordering::Relaxed) {
                    eprintln!("{}", "cancelled (Ctrl-C)".yellow());
                } else {
                    eprintln!("error: {e}");
                }
                continue;
            }
        };
        total_cost += result.cost_usd;
        if !json_mode {
            renderer.show_final(&result.final_text, result.confidence, result.cost_usd);
        }
    }
}

fn build_reedline() -> std::io::Result<Reedline> {
    let path = history_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let history = Box::new(
        FileBackedHistory::with_file(2_000, path)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?,
    );

    // Emacs keybindings + Tab opens the completion menu.
    let mut kb = default_emacs_keybindings();
    kb.add_binding(
        KeyModifiers::NONE,
        KeyCode::Tab,
        ReedlineEvent::UntilFound(vec![
            ReedlineEvent::Menu("completion_menu".into()),
            ReedlineEvent::MenuNext,
        ]),
    );
    // Shift-Enter inserts newline (multi-line input).
    kb.add_binding(
        KeyModifiers::SHIFT,
        KeyCode::Enter,
        ReedlineEvent::Edit(vec![EditCommand::InsertNewline]),
    );

    let menu = ReedlineMenu::EngineCompleter(Box::new(
        ColumnarMenu::default().with_name("completion_menu"),
    ));

    let completer = Box::new(SlashCompleter);
    let hinter =
        Box::new(DefaultHinter::default().with_style(Style::new().fg(Color::DarkGray).italic()));

    let rl = Reedline::create()
        .with_history(history)
        .with_completer(completer)
        .with_menu(menu)
        .with_edit_mode(Box::new(Emacs::new(kb)))
        .with_hinter(hinter)
        .with_quick_completions(false)
        .with_partial_completions(true);

    Ok(rl)
}

/// Slash-command completer. Suggests `/help`, `/cost`, etc. when the buffer
/// starts with `/`. Falls back to empty (no noise on regular prompts).
struct SlashCompleter;

impl Completer for SlashCompleter {
    fn complete(&mut self, line: &str, pos: usize) -> Vec<Suggestion> {
        let head = &line[..pos.min(line.len())];
        if !head.starts_with('/') {
            return Vec::new();
        }
        let start = 0;
        SLASH_COMMANDS
            .iter()
            .filter(|c| c.starts_with(head))
            .map(|c| Suggestion {
                value: (*c).to_string(),
                description: None,
                style: None,
                extra: None,
                span: Span::new(start, pos),
                append_whitespace: false,
            })
            .collect()
    }
}

struct VossPrompt {
    model: String,
    mode: &'static str,
    cost: f64,
    git: String,
}

impl Prompt for VossPrompt {
    fn render_prompt_left(&self) -> Cow<'_, str> {
        Cow::Borrowed("▌ ")
    }

    fn render_prompt_right(&self) -> Cow<'_, str> {
        Cow::Owned(format!(
            "{} · {} · ${:.3} · {}",
            self.model, self.mode, self.cost, self.git
        ))
    }

    fn render_prompt_indicator(&self, _mode: PromptEditMode) -> Cow<'_, str> {
        Cow::Borrowed("")
    }

    fn render_prompt_multiline_indicator(&self) -> Cow<'_, str> {
        Cow::Borrowed("· ")
    }

    fn render_prompt_history_search_indicator(
        &self,
        history_search: PromptHistorySearch,
    ) -> Cow<'_, str> {
        let prefix = match history_search.status {
            PromptHistorySearchStatus::Passing => "",
            PromptHistorySearchStatus::Failing => "failing ",
        };
        Cow::Owned(format!(
            "({}reverse-search: {}) ",
            prefix, history_search.term
        ))
    }
}

fn mode_label(mode: Mode) -> &'static str {
    match mode {
        Mode::Plan => "plan",
        Mode::Edit => "edit",
        Mode::Auto => "auto",
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
         /save [name]   persist session snapshot\n\
         /plugins       list plugin manifests\n\
         /plugin        enable|disable a plugin manifest\n\
         /skills        list registered skills\n\
         /skill         run a registered skill\n\
         /agents        list registered subagents\n\
         /agent         spawn a registered subagent\n\
         \n\
         Tab            complete slash command\n\
         Shift-Enter    insert newline\n\
         Ctrl-C         cancel current turn (or clear buffer)\n\
         Ctrl-R         reverse-search history\n\
         Ctrl-D         exit"
    );
}

fn print_plugins(cwd: &Path) {
    let skills = skill_ids();
    let agents = agent_ids();
    let plugins = load_plugins(cwd, SLASH_COMMANDS, &skills, &agents);
    if plugins.is_empty() {
        println!("(no plugins)");
        return;
    }
    for plugin in plugins {
        let status = if plugin.enabled {
            "enabled"
        } else {
            "disabled"
        };
        println!("  {:<20} {:<8} {}", plugin.id, status, plugin.name);
        for warning in plugin.warnings {
            eprintln!("    warning: {warning}");
        }
    }
}

fn print_skills() {
    for (id, desc) in SKILLS {
        println!("  {id:<16} {desc}");
    }
}

fn print_agents() {
    for (id, desc, _) in AGENTS {
        println!("  {id:<16} {desc}");
    }
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
        _ => "no git".into(),
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
        let (allowed, reason) = self
            .gate
            .check(name, args, crate::permissions::interactive_prompt);
        (allowed, reason.to_string())
    }
}
