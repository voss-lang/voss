use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::time::Duration;

use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};

use crate::auth::Handshake;
use crate::client::VossClient;
use crate::error::VossError;

/// How to start `voss serve`. `executable` is resolved with
/// [`resolve_executable`]; everything else is passed through to the child.
#[derive(Debug, Clone)]
pub struct LaunchOptions {
    pub executable: Option<PathBuf>,
    pub cwd: Option<PathBuf>,
    pub env: Vec<(String, String)>,
    pub handshake_timeout: Duration,
}

impl Default for LaunchOptions {
    fn default() -> Self {
        Self {
            executable: None,
            cwd: None,
            env: Vec::new(),
            // litellm's import tree is large; a cold `.pyc` compile can take ~45s
            // on first run (warm startup is ~15s). The stdin-EOF heartbeat reaps
            // the server if the consumer gives up early.
            handshake_timeout: Duration::from_secs(60),
        }
    }
}

/// Explicit path, else `VOSS_BIN`, else `voss` looked up on `PATH` by the OS.
pub fn resolve_executable(explicit: Option<&Path>) -> PathBuf {
    if let Some(path) = explicit {
        return path.to_path_buf();
    }
    if let Some(path) = std::env::var_os("VOSS_BIN") {
        return PathBuf::from(path);
    }
    PathBuf::from("voss")
}

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
    /// Spawn `voss serve --port 0`, complete the startup handshake, and return
    /// a client bound to the ephemeral port.
    pub async fn spawn(options: LaunchOptions) -> Result<Supervisor, VossError> {
        let executable = resolve_executable(options.executable.as_deref());
        let mut cmd = Command::new(&executable);
        cmd.args(["serve", "--port", "0"])
            .stdin(Stdio::piped()) // held open = heartbeat; EOF terminates server
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .env("PYDANTIC_DISABLE_PLUGINS", "1")
            // litellm fetches its model-cost map over the network at import time,
            // adding ~12s (and a hang risk) to server startup. Force the bundled
            // local map so a freshly spawned server never blocks the handshake on
            // a remote request. litellm matches this case-insensitively against
            // "true".
            .env("LITELLM_LOCAL_MODEL_COST_MAP", "true")
            .kill_on_drop(true);
        if let Some(cwd) = &options.cwd {
            cmd.current_dir(cwd);
        }
        for (key, value) in &options.env {
            cmd.env(key, value);
        }

        let mut child = cmd.spawn().map_err(|err| {
            VossError::Spawn(std::io::Error::new(
                err.kind(),
                format!("{}: {err}", executable.display()),
            ))
        })?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| VossError::Handshake("server: no stdout pipe".into()))?;
        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| VossError::Handshake("server: no stderr pipe".into()))?;
        // Continuously drain stderr so the pipe never fills (which would block the
        // server) and so captured lines can be reported on a handshake failure.
        let stderr_buf = std::sync::Arc::new(std::sync::Mutex::new(String::new()));
        {
            let stderr_buf = std::sync::Arc::clone(&stderr_buf);
            tokio::spawn(async move {
                let mut err_lines = BufReader::new(stderr).lines();
                while let Ok(Some(line)) = err_lines.next_line().await {
                    if let Ok(mut buf) = stderr_buf.lock() {
                        buf.push_str(&line);
                        buf.push('\n');
                    }
                }
            });
        }
        let mut lines = BufReader::new(stdout).lines();

        let handshake = tokio::time::timeout(options.handshake_timeout, async {
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
        .map_err(|_| {
            let captured = stderr_buf.lock().map(|b| b.clone()).unwrap_or_default();
            VossError::Handshake(format!("server handshake timed out; stderr:\n{captured}"))
        })??;

        // Drain remaining stdout so a full pipe buffer never blocks the server.
        tokio::spawn(async move { while let Ok(Some(_)) = lines.next_line().await {} });

        Ok(Supervisor {
            child,
            client: handshake.into_client(),
        })
    }

    pub fn pid(&self) -> Option<u32> {
        self.child.id()
    }

    /// Kill the server child and reap it, preventing a zombie process.
    pub async fn shutdown(mut self) {
        let _ = self.child.start_kill();
        let _ = self.child.wait().await;
    }
}

#[cfg(test)]
mod tests {
    use std::path::{Path, PathBuf};

    use super::{resolve_executable, LaunchOptions, Supervisor};
    use crate::error::VossError;

    #[tokio::test]
    async fn bad_executable_yields_typed_error() {
        let options = LaunchOptions {
            executable: Some(PathBuf::from("/no/such/voss-xyz")),
            ..Default::default()
        };
        let result = tokio::time::timeout(
            std::time::Duration::from_secs(2),
            Supervisor::spawn(options),
        )
        .await;

        match result.expect("bad executable should not hang") {
            Err(VossError::Spawn(err)) => {
                assert!(err.to_string().contains("/no/such/voss-xyz"))
            }
            Err(other) => panic!("expected spawn error, got {other:?}"),
            Ok(_) => panic!("bad executable unexpectedly spawned a supervisor"),
        }
    }

    #[test]
    fn executable_resolution_order() {
        std::env::set_var("VOSS_BIN", "/from/env/voss");
        assert_eq!(
            resolve_executable(Some(Path::new("/explicit/voss"))),
            PathBuf::from("/explicit/voss")
        );
        assert_eq!(resolve_executable(None), PathBuf::from("/from/env/voss"));
        std::env::remove_var("VOSS_BIN");
        assert_eq!(resolve_executable(None), PathBuf::from("voss"));
    }
}
