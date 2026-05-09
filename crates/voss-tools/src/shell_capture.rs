//! `_shell_capture` mirror — run a process, capture combined stdout+stderr,
//! enforce a timeout, format with `[exit N]` + 4KB truncation.

use std::path::Path;
use std::process::Stdio;
use std::time::Duration;

use tokio::process::Command;

const TRUNCATE_AT: usize = 4096;
const DEFAULT_TIMEOUT_SECS: u64 = 30;

pub async fn shell_capture(cwd: &Path, argv: &[&str], timeout_secs: u64) -> String {
    let mut cmd = Command::new(argv[0]);
    cmd.args(&argv[1..])
        .current_dir(cwd)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => return format!("<error: {e}>"),
    };
    let timeout = Duration::from_secs(timeout_secs);
    let out = match tokio::time::timeout(timeout, child.wait_with_output()).await {
        Ok(Ok(o)) => o,
        Ok(Err(e)) => return format!("<error: {e}>"),
        Err(_) => return format!("<timeout: {timeout_secs}s>"),
    };
    // Mirror Python: stderr piped to stdout. Concatenate.
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
    format!("[exit {code}]\n{body}")
}

pub async fn shell_capture_default(cwd: &Path, argv: &[&str]) -> String {
    shell_capture(cwd, argv, DEFAULT_TIMEOUT_SECS).await
}
