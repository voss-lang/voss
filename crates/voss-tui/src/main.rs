//! voss-tui entry point (H2.1).
//!
//! Spawns (or attaches to) the harness server, creates a session, then runs the
//! ratatui UI. The terminal is always restored, and a spawned server is killed,
//! on exit.

use anyhow::Result;
use clap::{Parser, Subcommand};

use voss_tui::{app, doctor, net::HttpClient, server, sessions};

#[derive(Parser)]
#[command(name = "voss-tui", version, about = "Voss thin terminal client")]
struct Cli {
    #[command(subcommand)]
    cmd: Option<Cmd>,
    /// Attach to an already-running server (e.g. http://127.0.0.1:PORT) instead
    /// of spawning one.
    #[arg(long, global = true)]
    attach: Option<String>,
    /// Bearer token for --attach (or VOSS_TUI_TOKEN).
    #[arg(long, global = true, env = "VOSS_TUI_TOKEN")]
    token: Option<String>,
    /// Project working directory for the session.
    #[arg(long, global = true, default_value = ".")]
    cwd: String,
}

#[derive(Subcommand)]
enum Cmd {
    /// Run server-side diagnostics and exit (no TUI).
    Doctor,
    /// List resumable saved sessions and exit (no TUI).
    Sessions {
        /// Read via the Python server instead of natively (H7).
        #[arg(long)]
        via_server: bool,
    },
    /// Resume a saved session by id/name into the TUI.
    Resume {
        /// Saved session id or name.
        id: String,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // H7: native session listing needs no Python server — short-circuit before
    // spawning one. Rust reads the same on-disk format Python writes.
    if matches!(cli.cmd, Some(Cmd::Sessions { via_server: false })) {
        return sessions::list_native(&cli.cwd);
    }

    // Resolve the server: attach to an existing one, or spawn + supervise.
    let (handle, http) = match cli.attach.clone() {
        Some(url) => {
            let token = cli.token.clone().unwrap_or_default();
            (None, HttpClient::new(url, token))
        }
        None => {
            let h = server::spawn_server().await?;
            let http = HttpClient::new(h.base.clone(), h.token.clone());
            (Some(h), http)
        }
    };

    // Run the chosen command, ALWAYS shutting the server down before exiting
    // (std::process::exit skips Drop, so shutdown must precede it explicitly).
    let outcome: Result<Option<i32>> = match cli.cmd {
        Some(Cmd::Doctor) => doctor::run(&http, &cli.cwd).await.map(Some),
        Some(Cmd::Sessions { .. }) => sessions::list(&http, &cli.cwd).await.map(|()| Some(0)),
        Some(Cmd::Resume { ref id }) => run_resume(&http, id, &cli.cwd).await.map(|()| None),
        None => run_tui(&http, &cli.cwd).await.map(|()| None),
    };

    if let Some(h) = handle {
        h.shutdown().await;
    }

    match outcome {
        Ok(Some(code)) => std::process::exit(code),
        Ok(None) => Ok(()),
        Err(e) => Err(e),
    }
}

async fn run_tui(http: &HttpClient, cwd: &str) -> Result<()> {
    // Create the session before entering raw mode so credential/connection
    // errors print normally instead of inside the alternate screen.
    let sid = http
        .create_session(cwd)
        .await
        .map_err(|e| anyhow::anyhow!("could not start session: {e}"))?;
    enter_tui(http, sid).await
}

async fn run_resume(http: &HttpClient, id: &str, cwd: &str) -> Result<()> {
    let sid = http
        .create_session_resume(id, cwd)
        .await
        .map_err(|e| anyhow::anyhow!("could not resume {id}: {e}"))?;
    enter_tui(http, sid).await
}

async fn enter_tui(http: &HttpClient, sid: String) -> Result<()> {
    let terminal = ratatui::init();
    let res = app::run(terminal, http.clone(), sid).await;
    ratatui::restore();
    res
}
