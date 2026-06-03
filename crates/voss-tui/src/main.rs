//! voss-tui entry point (H2.1).
//!
//! Spawns (or attaches to) the harness server, creates a session, then runs the
//! ratatui UI. The terminal is always restored, and a spawned server is killed,
//! on exit.

use anyhow::Result;
use clap::Parser;

use voss_tui::{app, net::HttpClient, server};

#[derive(Parser)]
#[command(name = "voss-tui", version, about = "Voss thin terminal client")]
struct Cli {
    /// Attach to an already-running server (e.g. http://127.0.0.1:PORT) instead
    /// of spawning one.
    #[arg(long)]
    attach: Option<String>,
    /// Bearer token for --attach (or VOSS_TUI_TOKEN).
    #[arg(long, env = "VOSS_TUI_TOKEN")]
    token: Option<String>,
    /// Project working directory for the session.
    #[arg(long, default_value = ".")]
    cwd: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

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

    // Create the session before entering raw mode so credential/connection
    // errors print normally instead of inside the alternate screen.
    let sid = match http.create_session(&cli.cwd).await {
        Ok(id) => id,
        Err(e) => {
            eprintln!("voss-tui: could not start session: {e}");
            if let Some(h) = handle {
                h.shutdown().await;
            }
            std::process::exit(1);
        }
    };

    let terminal = ratatui::init();
    let res = app::run(terminal, http, sid).await;
    ratatui::restore();

    if let Some(h) = handle {
        h.shutdown().await;
    }
    res
}
