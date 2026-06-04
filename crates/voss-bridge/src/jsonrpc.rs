//! PyBridge — spawns `python -m voss.bridge_server` as a long-lived child
//! and dispatches JSON-RPC over LSP-framed stdio.
//!
//! Cross-cutting constraint (07-CONTEXT.md): Rust must NOT link libpython.
//! All Python interaction goes through this subprocess via std::process.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::Value;
use tokio::io::{AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, ChildStdout, Command};
use tokio::sync::Mutex;

use crate::framing::{read_frame, write_frame};

pub struct PyBridge {
    python: PathBuf,
    child: Mutex<Option<BridgeChild>>,
    next_id: AtomicU64,
}

struct BridgeChild {
    _child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

impl PyBridge {
    /// Discover the Python interpreter to use.
    /// Order: `$VOSS_PYTHON`, `.venv/bin/python` (relative to CWD), then `python3` on PATH.
    pub fn discover() -> std::io::Result<Self> {
        let python = if let Some(v) = std::env::var_os("VOSS_PYTHON") {
            PathBuf::from(v)
        } else {
            let venv = PathBuf::from(".venv/bin/python");
            if venv.exists() {
                venv
            } else {
                PathBuf::from("python3")
            }
        };
        Ok(Self {
            python,
            child: Mutex::new(None),
            next_id: AtomicU64::new(1),
        })
    }

    /// Override the python interpreter path (used by tests).
    pub fn with_python(python: PathBuf) -> Self {
        Self {
            python,
            child: Mutex::new(None),
            next_id: AtomicU64::new(1),
        }
    }

    pub fn python_path(&self) -> &Path {
        &self.python
    }

    async fn ensure_started(
        &self,
    ) -> std::io::Result<tokio::sync::MutexGuard<'_, Option<BridgeChild>>> {
        let mut guard = self.child.lock().await;
        if guard.is_none() {
            let mut child = Command::new(&self.python)
                .args(["-m", "voss.bridge_server"])
                .stdin(std::process::Stdio::piped())
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::inherit())
                .spawn()?;
            let stdin = child.stdin.take().expect("stdin piped");
            let stdout = BufReader::new(child.stdout.take().expect("stdout piped"));
            *guard = Some(BridgeChild {
                _child: child,
                stdin,
                stdout,
            });
        }
        Ok(guard)
    }

    pub async fn call(&self, method: &str, params: Value) -> std::io::Result<Value> {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);
        let req = serde_json::json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        });
        let mut guard = self.ensure_started().await?;
        let bc = guard.as_mut().expect("child started");
        let body = serde_json::to_vec(&req)?;
        write_frame(&mut bc.stdin, &body).await?;
        bc.stdin.flush().await?;
        let resp_bytes = read_frame(&mut bc.stdout).await?;
        let resp: Value = serde_json::from_slice(&resp_bytes)?;
        if let Some(err) = resp.get("error") {
            return Err(std::io::Error::other(format!("bridge error: {err}")));
        }
        Ok(resp.get("result").cloned().unwrap_or(Value::Null))
    }

    pub async fn ast(&self, path: &Path) -> std::io::Result<Value> {
        self.call(
            "ast",
            serde_json::json!({ "path": path.to_str().unwrap_or("") }),
        )
        .await
    }

    pub async fn check(&self, path: &Path) -> std::io::Result<Value> {
        self.call(
            "check",
            serde_json::json!({ "path": path.to_str().unwrap_or("") }),
        )
        .await
    }

    pub async fn compile(&self, path: &Path, output: Option<&Path>) -> std::io::Result<Value> {
        let params = match output {
            Some(out) => serde_json::json!({
                "path": path.to_str().unwrap_or(""),
                "output": out.to_str().unwrap_or(""),
            }),
            None => serde_json::json!({ "path": path.to_str().unwrap_or("") }),
        };
        self.call("compile", params).await
    }
}
