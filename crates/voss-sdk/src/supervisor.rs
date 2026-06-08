use std::process::Stdio;

use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};

use crate::auth::Handshake;
use crate::client::VossClient;
use crate::error::VossError;

pub struct Supervisor {
    child: Child,
    pub client: VossClient,
}

impl Drop for Supervisor {
    fn drop(&mut self) {
        let _ = self.child.start_kill();
    }
}

impl Supervisor {
    pub fn pid(&self) -> Option<u32> {
        self.child.id()
    }

    /// Kill the server child and reap it, preventing a zombie process.
    pub async fn shutdown(mut self) {
        let _ = self.child.start_kill();
        let _ = self.child.wait().await;
    }
}

/// Interpreter used to launch the server:
/// `VOSS_PYTHON` > repo `.venv/bin/python` > `python3`.
pub fn python_path() -> String {
    if let Ok(p) = std::env::var("VOSS_PYTHON") {
        return p;
    }
    // CARGO_MANIFEST_DIR = <repo>/crates/voss-sdk, so ../.. reaches repo root.
    let venv = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python");
    if venv.exists() {
        return venv.to_string_lossy().into_owned();
    }
    "python3".to_string()
}

/// Spawn `voss serve` and complete the startup handshake.
pub async fn spawn() -> Result<Supervisor, VossError> {
    spawn_with(&python_path(), &[]).await
}

/// Spawn with an explicit interpreter and extra environment.
pub async fn spawn_with(python: &str, extra_env: &[(&str, &str)]) -> Result<Supervisor, VossError> {
    let mut cmd = Command::new(python);
    cmd.args(["-m", "voss.cli", "serve", "--port", "0"])
        .stdin(Stdio::piped()) // held open = heartbeat; EOF terminates server
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .kill_on_drop(true);
    for (key, value) in extra_env {
        cmd.env(key, value);
    }

    let mut child = cmd.spawn().map_err(VossError::Spawn)?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| VossError::Handshake("server: no stdout pipe".into()))?;
    let mut lines = BufReader::new(stdout).lines();

    let handshake = tokio::time::timeout(std::time::Duration::from_secs(20), async {
        while let Some(line) = lines
            .next_line()
            .await
            .map_err(|err| VossError::Handshake(err.to_string()))?
        {
            if let Ok(handshake) = Handshake::from_line(&line) {
                return Ok(handshake);
            }
        }

        Err(VossError::Handshake(
            "server exited before handshake".into(),
        ))
    })
    .await
    .map_err(|_| VossError::Handshake("server handshake timed out".into()))??;

    // Drain remaining stdout so a full pipe buffer never blocks the server.
    tokio::spawn(async move { while let Ok(Some(_)) = lines.next_line().await {} });

    Ok(Supervisor {
        child,
        client: handshake.into_client(),
    })
}

#[cfg(test)]
mod tests {
    use super::spawn_with;
    use crate::error::VossError;

    #[tokio::test]
    async fn bad_interpreter_yields_typed_error() {
        let result = tokio::time::timeout(
            std::time::Duration::from_secs(2),
            spawn_with("/no/such/python-xyz", &[]),
        )
        .await;

        match result.expect("bad interpreter should not hang") {
            Err(VossError::Spawn(_) | VossError::Handshake(_)) => {}
            Err(other) => panic!("expected spawn or handshake error, got {other:?}"),
            Ok(_) => panic!("bad interpreter unexpectedly spawned a supervisor"),
        }
    }
}
