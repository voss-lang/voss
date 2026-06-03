//! `voss-tui sessions` (H4.1) — list resumable saved sessions.
//!
//! The server reads them from the on-disk session store; the client only
//! renders. Resume happens via `voss-tui resume <id>` (see main.rs).

use anyhow::Result;
use serde::Deserialize;

use crate::net::HttpClient;

#[derive(Debug, Deserialize)]
pub struct SavedSession {
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub cwd: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub updated_at: String,
    #[serde(default)]
    pub total_cost_usd: f64,
    #[serde(default)]
    pub turns: u64,
}

pub async fn list(http: &HttpClient, cwd: &str) -> Result<()> {
    let sessions = http.list_saved_sessions(cwd).await?;
    if sessions.is_empty() {
        println!("no saved sessions for {cwd}");
        return Ok(());
    }
    println!("{:<14} {:<24} {:>5} {:>9}  UPDATED", "ID", "NAME", "TURNS", "COST$");
    for s in &sessions {
        println!(
            "{:<14} {:<24} {:>5} {:>9.4}  {}",
            s.id, s.name, s.turns, s.total_cost_usd, s.updated_at
        );
    }
    println!("\nresume with: voss-tui resume <id>");
    Ok(())
}
