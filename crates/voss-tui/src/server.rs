//! Server child supervision
//! Spawns `voss serve` through voss-sdk, reads the handshake, and keeps the
//! child alive until `shutdown`

use std::path::{Path, PathBuf};

use anyhow::Result;
pub use voss_sdk::LaunchOptions;
use voss_sdk::Supervisor;

pub struct ServerHandle {
    supervisor: Supervisor,
    pub base: String,
    pub token: String,
}

impl ServerHandle {
    /// Kill the server child and reap it (prevents a zombie)
    pub async fn shutdown(self) {
        self.supervisor.shutdown().await;
    }
}

/// Repo-checkout convenience only: with no `VOSS_BIN` set, prefer the sibling
/// `.venv/bin/voss` so `cargo run -p voss-tui` works without activating the
/// venv. A shipped binary never finds this path and falls through to `voss`
/// on PATH via voss-sdk's resolution.
pub fn dev_executable() -> Option<PathBuf> {
    if std::env::var_os("VOSS_BIN").is_some() {
        return None;
    }
    let venv = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/voss");
    venv.exists().then_some(venv)
}

/// Spawn `voss serve` and complete the handshake
pub async fn spawn_server() -> Result<ServerHandle> {
    spawn_server_with(LaunchOptions {
        executable: dev_executable(),
        ..Default::default()
    })
    .await
}

pub async fn spawn_server_with(options: LaunchOptions) -> Result<ServerHandle> {
    let supervisor = Supervisor::spawn(options).await?;
    let base = supervisor.client.base_url().to_string();
    let token = supervisor.client.token().to_string();
    Ok(ServerHandle {
        supervisor,
        base,
        token,
    })
}
