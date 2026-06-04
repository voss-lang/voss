//! Server child supervision (H2.2).
//!
//! Spawns `voss serve`, reads the one-line `{port, token}` handshake, and keeps
//! the child's stdin open as the heartbeat the server watches (closing it makes
//! the server self-terminate — see `server/serve.py`). The child is killed on
//! drop and explicitly on shutdown to avoid zombies.

use std::process::Stdio;

use anyhow::{anyhow, Result};
use serde::Deserialize;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};

pub struct ServerHandle {
    pub child: Child,
    pub base: String,
    pub token: String,
}

impl ServerHandle {
    /// Kill the server child and reap it (prevents a zombie).
    pub async fn shutdown(mut self) {
        let _ = self.child.start_kill();
        let _ = self.child.wait().await;
    }
}

#[derive(Deserialize)]
struct Handshake {
    port: u16,
    token: String,
}

/// Interpreter used to launch the server. `VOSS_PYTHON` overrides; else the
/// repo's `.venv/bin/python` relative to this crate, else `python3` on PATH.
pub fn python_path() -> String {
    if let Ok(p) = std::env::var("VOSS_PYTHON") {
        return p;
    }
    // crate dir = <repo>/crates/voss-tui -> repo root is two levels up.
    let venv = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python");
    if venv.exists() {
        return venv.to_string_lossy().into_owned();
    }
    "python3".to_string()
}

/// Spawn `voss serve` and complete the handshake.
pub async fn spawn_server() -> Result<ServerHandle> {
    spawn_server_with(&python_path(), &[]).await
}

/// Spawn with an explicit interpreter and extra environment (used by tests to
/// set `VOSS_SERVE_FAKE_TURN`).
pub async fn spawn_server_with(python: &str, extra_env: &[(&str, &str)]) -> Result<ServerHandle> {
    let mut cmd = Command::new(python);
    cmd.args(["-m", "voss.cli", "serve", "--port", "0"])
        .stdin(Stdio::piped()) // held open = heartbeat; never written/closed until drop
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .kill_on_drop(true);
    for (k, v) in extra_env {
        cmd.env(k, v);
    }
    let mut child = cmd.spawn()?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| anyhow!("server: no stdout pipe"))?;
    let mut lines = BufReader::new(stdout).lines();

    let hs: Handshake = tokio::time::timeout(std::time::Duration::from_secs(20), async {
        while let Some(line) = lines.next_line().await? {
            if let Ok(h) = serde_json::from_str::<Handshake>(&line) {
                return Ok::<_, anyhow::Error>(h);
            }
        }
        Err(anyhow!("server exited before handshake"))
    })
    .await
    .map_err(|_| anyhow!("server handshake timed out"))??;

    // Drain remaining stdout so a full pipe buffer never blocks the server.
    tokio::spawn(async move { while let Ok(Some(_)) = lines.next_line().await {} });

    let base = format!("http://127.0.0.1:{}", hs.port);
    Ok(ServerHandle {
        child,
        base,
        token: hs.token,
    })
}
