use std::path::PathBuf;
use std::process::Stdio;
use std::time::Duration;

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;
use tokio::process::Command;

use crate::sandbox::{load_allowlist, shell_allowed};
use crate::tool_trait::Tool;

const TRUNCATE_AT: usize = 4096;
const DEFAULT_TIMEOUT_SECS: u64 = 30;

#[derive(Deserialize, JsonSchema)]
pub struct ShellRunArgs {
    /// Shell command. Binary must be on the allowlist.
    pub cmd: String,
}

pub struct ShellRun {
    pub cwd: PathBuf,
    /// Timeout in seconds (test seam).
    pub timeout_secs: u64,
}

impl ShellRun {
    pub fn new(cwd: PathBuf) -> Self {
        Self {
            cwd,
            timeout_secs: DEFAULT_TIMEOUT_SECS,
        }
    }

    pub fn with_timeout_secs(mut self, t: u64) -> Self {
        self.timeout_secs = t;
        self
    }
}

#[async_trait]
impl Tool for ShellRun {
    fn name(&self) -> &str {
        "shell_run"
    }
    fn description(&self) -> &str {
        "Run a shell command from the allowlist. Output truncated to 4KB."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(ShellRunArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        true
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: ShellRunArgs = serde_json::from_value(args)?;
        if let Err(e) = shell_allowed(&args.cmd, &load_allowlist()) {
            return Ok(format!("<denied: {e}>"));
        }
        let mut cmd = Command::new("sh");
        cmd.arg("-c")
            .arg(&args.cmd)
            .current_dir(&self.cwd)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        let child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => return Ok(format!("<error: {e}>")),
        };
        let timeout = Duration::from_secs(self.timeout_secs);
        let out = match tokio::time::timeout(timeout, child.wait_with_output()).await {
            Ok(Ok(o)) => o,
            Ok(Err(e)) => return Ok(format!("<error: {e}>")),
            Err(_) => return Ok(format!("<timeout: {}s>", self.timeout_secs)),
        };
        let mut combined = out.stdout;
        combined.extend(out.stderr);
        let total = combined.len();
        let text = String::from_utf8_lossy(&combined).into_owned();
        let body = if text.len() > TRUNCATE_AT {
            format!(
                "{}\n<truncated, total {total} bytes>",
                &text[..TRUNCATE_AT]
            )
        } else {
            text
        };
        let code = out
            .status
            .code()
            .map(|c| c.to_string())
            .unwrap_or_else(|| "?".into());
        Ok(format!("[exit {code}]\n{body}"))
    }
}
