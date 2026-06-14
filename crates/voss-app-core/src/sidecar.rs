//! V15 SPIKE — `voss serve` sidecar: spawn/own the server from the Tauri
//! (Rust) side and hand the `{v,port,token}` stdout handshake to the webview.
//!
//! Ported from the proven `crates/voss-sdk` supervisor (60s cold-start budget,
//! `LITELLM_LOCAL_MODEL_COST_MAP=true`, stdin-pipe heartbeat, stderr drain).
//! This module is the intended production home; the Tauri command wrapper
//! (`start_voss_serve` in src-tauri) lands in the V15 phase proper.
//!
//! Spike scope proven by the gated test below:
//!   spawn → handshake parse → authed `GET /session` (200) → missing Bearer
//!   (401) → kill + reap (no orphan).

use std::process::Stdio;

use serde::{Deserialize, Serialize};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};

/// The one-line startup handshake `voss serve` prints on stdout. Serialized
/// camelCase-free (all lowercase single words) — safe to return through Tauri
/// IPC as-is.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServeHandshake {
    pub port: u16,
    pub token: String,
}

impl ServeHandshake {
    pub fn from_line(line: &str) -> Option<Self> {
        serde_json::from_str(line).ok()
    }
}

/// A running `voss serve` owned by the app. Dropping kills the child
/// (kill_on_drop) — hold it in Tauri state for the app's lifetime.
pub struct VossServe {
    child: Child,
    pub handshake: ServeHandshake,
}

impl VossServe {
    pub fn pid(&self) -> Option<u32> {
        self.child.id()
    }

    /// Kill and reap (no zombie).
    pub async fn shutdown(mut self) {
        let _ = self.child.start_kill();
        let _ = self.child.wait().await;
    }
}

/// Interpreter resolution: `VOSS_PYTHON` > repo `.venv/bin/python` > `python3`.
/// CARGO_MANIFEST_DIR = `<repo>/crates/voss-app-core`, so `../..` is the root.
pub fn python_path() -> String {
    if let Ok(p) = std::env::var("VOSS_PYTHON") {
        return p;
    }
    let venv = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python");
    if venv.exists() {
        return venv.to_string_lossy().into_owned();
    }
    "python3".to_string()
}

/// T-V15-01: canonicalize and validate a webview-supplied workspace `cwd`
/// before it becomes a process-spawn argument. With empty `allowed_roots`,
/// any existing directory is accepted (single-user local default); otherwise
/// the canonical path must equal or descend from one of the roots.
pub fn validate_workspace_cwd(
    cwd: &str,
    allowed_roots: &[std::path::PathBuf],
) -> Result<std::path::PathBuf, String> {
    let canonical =
        std::fs::canonicalize(cwd).map_err(|_| "workspace path does not exist".to_string())?;
    if !canonical.is_dir() {
        return Err("workspace path is not a directory".to_string());
    }
    if !allowed_roots.is_empty() && !allowed_roots.iter().any(|root| canonical.starts_with(root)) {
        return Err("workspace path is outside allowed roots".to_string());
    }
    Ok(canonical)
}

/// Spawn `voss serve --port 0` in `cwd` and complete the startup handshake.
///
/// litellm's import tree cold-compiles in ~45s on first run (warm ~15s), so
/// the handshake budget is 60s; `LITELLM_LOCAL_MODEL_COST_MAP=true` removes
/// the boot-time network fetch entirely (voss-sdk findings, V13.2-06).
pub async fn spawn_voss_serve(python: &str, cwd: &std::path::Path) -> anyhow::Result<VossServe> {
    let mut cmd = Command::new(python);
    cmd.args(["-m", "voss.cli", "serve", "--port", "0"])
        .current_dir(cwd)
        .stdin(Stdio::piped()) // held open = heartbeat; EOF terminates server
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .env("PYDANTIC_DISABLE_PLUGINS", "1")
        .env("LITELLM_LOCAL_MODEL_COST_MAP", "true")
        .kill_on_drop(true);

    let mut child = cmd.spawn()?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| anyhow::anyhow!("voss serve: no stdout pipe"))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| anyhow::anyhow!("voss serve: no stderr pipe"))?;

    // Drain stderr continuously (a full pipe blocks the server); keep the tail
    // for timeout diagnostics.
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
    let handshake = tokio::time::timeout(std::time::Duration::from_secs(60), async {
        while let Some(line) = lines.next_line().await? {
            if let Some(h) = ServeHandshake::from_line(&line) {
                return Ok::<_, anyhow::Error>(h);
            }
        }
        anyhow::bail!("voss serve exited before handshake")
    })
    .await
    .map_err(|_| {
        let captured = stderr_buf.lock().map(|b| b.clone()).unwrap_or_default();
        anyhow::anyhow!("voss serve handshake timed out; stderr:\n{captured}")
    })??;

    // Drain remaining stdout so a full pipe never blocks the server.
    tokio::spawn(async move { while let Ok(Some(_)) = lines.next_line().await {} });

    Ok(VossServe { child, handshake })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};

    /// Minimal HTTP/1.1 GET over a raw TcpStream — keeps the spike dependency-
    /// free. Returns the status line + body.
    fn http_get(port: u16, path: &str, bearer: Option<&str>) -> (u16, String) {
        let mut stream =
            std::net::TcpStream::connect(("127.0.0.1", port)).expect("connect voss serve");
        stream
            .set_read_timeout(Some(std::time::Duration::from_secs(10)))
            .unwrap();
        let auth = bearer
            .map(|t| format!("Authorization: Bearer {t}\r\n"))
            .unwrap_or_default();
        let req = format!(
            "GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{auth}Connection: close\r\n\r\n"
        );
        stream.write_all(req.as_bytes()).unwrap();
        let mut response = String::new();
        let _ = stream.read_to_string(&mut response);
        let status: u16 = response
            .split_whitespace()
            .nth(1)
            .and_then(|s| s.parse().ok())
            .unwrap_or(0);
        (status, response)
    }

    #[test]
    fn handshake_parses_and_ignores_version() {
        let h = ServeHandshake::from_line(r#"{"v":1,"port":54321,"token":"abc"}"#).unwrap();
        assert_eq!(h.port, 54321);
        assert_eq!(h.token, "abc");
        assert!(ServeHandshake::from_line("not json").is_none());
        // Server log lines must not parse as handshakes.
        assert!(ServeHandshake::from_line("INFO: started").is_none());
    }

    /// V15 SPIKE proof — the full sidecar loop against the real server:
    /// spawn → handshake → authed GET /session 200 → no-Bearer 401 → reap.
    ///
    /// Needs the repo Python env (heavy, ~15-60s): runs only when
    /// `VOSS_SIDECAR_SPIKE=1` (set VOSS_PYTHON to override the interpreter).
    #[test]
    fn spike_spawn_handshake_authed_request_and_reap() {
        if std::env::var("VOSS_SIDECAR_SPIKE").as_deref() != Ok("1") {
            eprintln!("skipping sidecar spike (set VOSS_SIDECAR_SPIKE=1)");
            return;
        }
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();
        rt.block_on(async {
            let cwd =
                std::env::temp_dir().join(format!("voss-sidecar-spike-{}", uuid::Uuid::new_v4()));
            std::fs::create_dir_all(&cwd).unwrap();

            let serve = spawn_voss_serve(&python_path(), &cwd)
                .await
                .expect("spawn voss serve");
            let port = serve.handshake.port;
            let token = serve.handshake.token.clone();
            assert!(port > 0);
            assert!(!token.is_empty());
            let pid = serve.pid().expect("child pid");

            // Authed request succeeds.
            let (status_ok, body) = http_get(port, "/session", Some(&token));
            assert_eq!(status_ok, 200, "authed GET /session: {body}");

            // Missing Bearer is rejected.
            let (status_unauth, _) = http_get(port, "/session", None);
            assert!(
                status_unauth == 401 || status_unauth == 403,
                "unauthenticated GET must be rejected, got {status_unauth}"
            );

            // Reap: no orphan after shutdown.
            serve.shutdown().await;
            let alive = std::process::Command::new("kill")
                .args(["-0", &pid.to_string()])
                .status()
                .map(|s| s.success())
                .unwrap_or(false);
            assert!(!alive, "voss serve pid {pid} still alive after shutdown");

            let _ = std::fs::remove_dir_all(&cwd);
        });
    }

    /// V15-01: cwd validation (T-V15-01) — pure path checks, no spawn, ungated.
    #[test]
    fn cwd_validation() {
        assert!(validate_workspace_cwd("/definitely/not/a/real/path/xyz", &[]).is_err());

        let dir_a = std::env::temp_dir().join(format!("voss-cwd-valid-a-{}", uuid::Uuid::new_v4()));
        let dir_b = std::env::temp_dir().join(format!("voss-cwd-valid-b-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir_a).unwrap();
        std::fs::create_dir_all(&dir_b).unwrap();

        // Empty roots: any existing directory is accepted (canonicalized).
        let ok = validate_workspace_cwd(dir_a.to_str().unwrap(), &[]).expect("existing dir ok");
        assert!(ok.is_dir());

        // A path outside every allowed root is rejected; inside its root passes.
        let canon_b = std::fs::canonicalize(&dir_b).unwrap();
        assert!(validate_workspace_cwd(dir_a.to_str().unwrap(), &[canon_b.clone()]).is_err());
        assert!(validate_workspace_cwd(dir_b.to_str().unwrap(), &[canon_b]).is_ok());

        let _ = std::fs::remove_dir_all(&dir_a);
        let _ = std::fs::remove_dir_all(&dir_b);
    }

    /// V15-01 reuse-if-alive sentinel proof: different cwds spawn different
    /// server processes, and after kill+reap `pid()` returns `None` — the
    /// stale-map signal `start_voss_serve` keys respawn on (Pitfall 5).
    ///
    /// Heavy (real server spawns): gated exactly like the spike test.
    #[test]
    fn reuse_if_alive() {
        if std::env::var("VOSS_SIDECAR_SPIKE").as_deref() != Ok("1") {
            eprintln!("skipping reuse_if_alive (set VOSS_SIDECAR_SPIKE=1)");
            return;
        }
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .unwrap();
        rt.block_on(async {
            let cwd_a = std::env::temp_dir().join(format!("voss-reuse-a-{}", uuid::Uuid::new_v4()));
            let cwd_b = std::env::temp_dir().join(format!("voss-reuse-b-{}", uuid::Uuid::new_v4()));
            std::fs::create_dir_all(&cwd_a).unwrap();
            std::fs::create_dir_all(&cwd_b).unwrap();

            let serve_a = spawn_voss_serve(&python_path(), &cwd_a)
                .await
                .expect("spawn voss serve (cwd A)");
            let pid_a = serve_a.pid().expect("pid A");

            let mut serve_b = spawn_voss_serve(&python_path(), &cwd_b)
                .await
                .expect("spawn voss serve (cwd B)");
            let pid_b = serve_b.pid().expect("pid B");
            assert_ne!(pid_a, pid_b, "different cwds must spawn different servers");

            // Kill + reap B in place (same-module access to the private child),
            // then assert the stale-entry sentinel: pid() is None after reap.
            let _ = serve_b.child.start_kill();
            let _ = serve_b.child.wait().await;
            assert!(
                serve_b.pid().is_none(),
                "pid() must return None after the child is reaped"
            );

            serve_a.shutdown().await;
            let _ = std::fs::remove_dir_all(&cwd_a);
            let _ = std::fs::remove_dir_all(&cwd_b);
        });
    }
}
