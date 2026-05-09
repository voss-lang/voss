use serde_json::json;

use voss_tools::{shell_run::ShellRun, Tool};

#[tokio::test]
async fn shell_run_allowed_cmd() {
    let tmp = tempfile::tempdir().unwrap();
    let runner = ShellRun::new(tmp.path().to_path_buf());
    let res = runner.invoke(json!({"cmd": "echo hello"})).await.unwrap();
    assert!(res.contains("hello"), "got: {res}");
    assert!(res.starts_with("[exit 0]"), "got: {res}");
}

#[tokio::test]
async fn shell_run_denied_token() {
    let tmp = tempfile::tempdir().unwrap();
    let runner = ShellRun::new(tmp.path().to_path_buf());
    let res = runner
        .invoke(json!({"cmd": "rm -rf /tmp/voss-nonexistent"}))
        .await
        .unwrap();
    assert!(res.contains("<denied:"), "got: {res}");
}

#[tokio::test]
async fn shell_run_unknown_binary() {
    let tmp = tempfile::tempdir().unwrap();
    let runner = ShellRun::new(tmp.path().to_path_buf());
    let res = runner
        .invoke(json!({"cmd": "badbin --x"}))
        .await
        .unwrap();
    assert!(res.contains("<denied:"), "got: {res}");
}

#[tokio::test]
async fn shell_run_timeout() {
    // Use a 1s timeout + python3 sleep 5 to verify the timeout path.
    let tmp = tempfile::tempdir().unwrap();
    let runner = ShellRun::new(tmp.path().to_path_buf()).with_timeout_secs(1);
    let res = runner
        .invoke(json!({"cmd": "python3 -c \"import time; time.sleep(5)\""}))
        .await
        .unwrap();
    assert!(res.contains("<timeout: 1s>"), "got: {res}");
}
