pub mod cli;
pub mod extensions;
pub mod permissions;
pub mod plugins;
pub mod session;

use std::ffi::OsString;
use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "voss-cli", version)]
struct Cli {
    #[command(subcommand)]
    cmd: Option<Cmd>,
}

#[derive(Subcommand)]
enum Cmd {
    /// Parse a Voss source file and print its AST as JSON.
    Ast {
        source: PathBuf,
        #[arg(long)]
        json: bool,
        #[arg(long)]
        compact: bool,
    },
    /// Diagnose env: credentials, runtime imports, picked auth path.
    Doctor,
    /// One-shot agent invocation: run a single task and exit.
    Do {
        task: Vec<String>,
        #[arg(long)]
        json: bool,
        #[arg(long, default_value = "edit")]
        mode: String,
        #[arg(long)]
        yes: bool,
        #[arg(long, default_value = "auto")]
        auth: String,
    },
    /// Drop into the chat REPL (also the default with no subcommand).
    Chat {
        #[arg(long)]
        json: bool,
        #[arg(long, default_value = "edit")]
        mode: String,
        #[arg(long, default_value = "auto")]
        auth: String,
    },
    /// List saved agent sessions.
    Sessions,
    /// List plugin manifests.
    Plugins,
    /// Manage plugin manifest enablement.
    Plugin {
        #[command(subcommand)]
        cmd: PluginCmd,
    },
    /// List registered skills.
    Skills,
    /// Run registered skills.
    Skill {
        #[command(subcommand)]
        cmd: SkillCmd,
    },
    /// List registered subagents.
    Agents,
    /// Run registered subagents.
    Agent {
        #[command(subcommand)]
        cmd: AgentCmd,
    },
    /// Resume a saved session by id-prefix or name.
    Resume {
        id: String,
    },
}

#[derive(Subcommand)]
enum PluginCmd {
    Enable { id: String },
    Disable { id: String },
}

#[derive(Subcommand)]
enum SkillCmd {
    Run { id: String, args: Vec<String> },
}

#[derive(Subcommand)]
enum AgentCmd {
    Spawn {
        id: String,
        task: Vec<String>,
        #[arg(long, default_value = "auto")]
        auth: String,
        #[arg(long, default_value = "edit")]
        mode: String,
    },
}

pub async fn run<I: IntoIterator<Item = OsString>>(argv: I) -> ExitCode {
    let cli = match Cli::try_parse_from(argv) {
        Ok(c) => c,
        Err(e) => {
            let _ = e.print();
            return if e.use_stderr() {
                ExitCode::from(2)
            } else {
                ExitCode::SUCCESS
            };
        }
    };

    let cmd = cli.cmd.unwrap_or(Cmd::Chat {
        json: false,
        mode: "edit".into(),
        auth: "auto".into(),
    });

    match cmd {
        Cmd::Ast { source, json: _, compact } => {
            let bridge = match voss_bridge::PyBridge::discover() {
                Ok(b) => b,
                Err(e) => {
                    eprintln!("bridge discover failed: {e}");
                    return ExitCode::from(1);
                }
            };
            match bridge.ast(&source).await {
                Ok(v) => {
                    let s = if compact {
                        serde_json::to_string(&v).unwrap_or_else(|_| "null".to_string())
                    } else {
                        serde_json::to_string_pretty(&v).unwrap_or_else(|_| "null".to_string())
                    };
                    println!("{s}");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("ast failed: {e}");
                    ExitCode::from(1)
                }
            }
        }
        Cmd::Doctor => cli::doctor::run_doctor(),
        Cmd::Sessions => cli::sessions::run_sessions(),
        Cmd::Plugins => {
            let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
            let skills = extensions::skill_ids();
            let agents = extensions::agent_ids();
            let plugins = plugins::load_plugins(&cwd, &["/plugins", "/plugin", "/skills", "/skill", "/agents", "/agent"], &skills, &agents);
            if plugins.is_empty() {
                println!("(no plugins)");
            } else {
                for plugin in plugins {
                    println!(
                        "  {:<20} {:<8} {}",
                        plugin.id,
                        if plugin.enabled { "enabled" } else { "disabled" },
                        plugin.name
                    );
                    for warning in plugin.warnings {
                        eprintln!("    warning: {warning}");
                    }
                }
            }
            ExitCode::SUCCESS
        }
        Cmd::Plugin { cmd } => {
            let (id, enabled) = match cmd {
                PluginCmd::Enable { id } => (id, true),
                PluginCmd::Disable { id } => (id, false),
            };
            match plugins::set_plugin_enabled(&id, enabled) {
                Ok(path) => {
                    println!(
                        "plugin {id} {}: {}",
                        if enabled { "enabled" } else { "disabled" },
                        path.display()
                    );
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("plugin update failed: {e}");
                    ExitCode::from(1)
                }
            }
        }
        Cmd::Skills => {
            for (id, desc) in extensions::SKILLS {
                println!("  {id:<16} {desc}");
            }
            ExitCode::SUCCESS
        }
        Cmd::Skill { cmd } => {
            match cmd {
                SkillCmd::Run { id, args: _ } if id == "analyze" => {
                    eprintln!("skill 'analyze' is not implemented in the Rust CLI yet");
                    ExitCode::from(1)
                }
                SkillCmd::Run { id, .. } => {
                    eprintln!("unknown skill: {id}");
                    ExitCode::from(1)
                }
            }
        }
        Cmd::Agents => {
            for (id, desc, _) in extensions::AGENTS {
                println!("  {id:<16} {desc}");
            }
            ExitCode::SUCCESS
        }
        Cmd::Agent { cmd } => {
            match cmd {
                AgentCmd::Spawn { id, task, auth, mode } => {
                    let task_text = task.join(" ");
                    if task_text.is_empty() {
                        eprintln!("no task. usage: voss-cli agent spawn <id> \"<task>\"");
                        return ExitCode::from(2);
                    }
                    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
                    let res = voss_auth::resolve(voss_auth::AuthPref::parse(&auth));
                    let provider = match cli::auth_to_provider::build(res) {
                        Ok(p) => p,
                        Err(e) => {
                            eprintln!("auth failed: {e}");
                            return ExitCode::from(2);
                        }
                    };
                    let shared = std::sync::Arc::new(tokio::sync::Mutex::new(provider));
                    let parsed_mode = permissions::Mode::parse(&mode).unwrap_or(permissions::Mode::Edit);
                    match extensions::run_subagent(&id, &task_text, &cwd, shared, parsed_mode, "claude-sonnet-4-5").await {
                        Ok(text) => {
                            println!("{text}");
                            ExitCode::SUCCESS
                        }
                        Err(e) => {
                            eprintln!("agent spawn failed: {e}");
                            ExitCode::from(1)
                        }
                    }
                }
            }
        }
        Cmd::Resume { id } => cli::resume::run_resume(&id),
        Cmd::Do { task, json, mode, yes, auth } => {
            let task_text = task.join(" ");
            if task_text.is_empty() {
                eprintln!("no task. usage: voss-cli do \"<task>\"");
                return ExitCode::from(2);
            }
            cli::do_cmd::run_do(&task_text, json, &mode, yes, &auth).await
        }
        Cmd::Chat { json, mode, auth } => {
            let cwd = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
            let res = voss_auth::resolve(voss_auth::AuthPref::parse(&auth));
            let mut provider = match cli::auth_to_provider::build(res) {
                Ok(p) => p,
                Err(e) => {
                    eprintln!("auth failed: {e}");
                    return ExitCode::from(2);
                }
            };
            let parsed_mode = permissions::Mode::parse(&mode).unwrap_or(permissions::Mode::Edit);
            cli::repl::run_repl(&cwd, json, parsed_mode, provider, None).await
        }
    }
}
