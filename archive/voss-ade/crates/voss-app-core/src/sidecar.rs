use std::process::Stdio;

use serde::{Deserialize, Serialize};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};

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

pub struct VossServe {
    child: Child,
    pub handshake: ServeHandshake,
}

impl VossServe {
    pub fn pid(&self) -> Option<u32> {
        self.child.id()
    }

    pub async fn shutdown(mut self) {
        let _ = self.child.start_kill();
        let _ = self.child.wait().await;
    }
}

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

    tokio::spawn(async move { while let Ok(Some(_)) = lines.next_line().await {} });

    Ok(VossServe { child, handshake })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};

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
        assert!(ServeHandshake::from_line("INFO: started").is_none());
    }

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

            let (status_ok, body) = http_get(port, "/session", Some(&token));
            assert_eq!(status_ok, 200, "authed GET /session: {body}");

            let (status_unauth, _) = http_get(port, "/session", None);
            assert!(
                status_unauth == 401 || status_unauth == 403,
                "unauthenticated GET must be rejected, got {status_unauth}"
            );

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

    #[test]
    fn cwd_validation() {
        assert!(validate_workspace_cwd("/definitely/not/a/real/path/xyz", &[]).is_err());

        let dir_a = std::env::temp_dir().join(format!("voss-cwd-valid-a-{}", uuid::Uuid::new_v4()));
        let dir_b = std::env::temp_dir().join(format!("voss-cwd-valid-b-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir_a).unwrap();
        std::fs::create_dir_all(&dir_b).unwrap();

        let ok = validate_workspace_cwd(dir_a.to_str().unwrap(), &[]).expect("existing dir ok");
        assert!(ok.is_dir());

        let canon_b = std::fs::canonicalize(&dir_b).unwrap();
        assert!(
            validate_workspace_cwd(dir_a.to_str().unwrap(), std::slice::from_ref(&canon_b))
                .is_err()
        );
        assert!(validate_workspace_cwd(dir_b.to_str().unwrap(), &[canon_b]).is_ok());

        let _ = std::fs::remove_dir_all(&dir_a);
        let _ = std::fs::remove_dir_all(&dir_b);
    }

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
