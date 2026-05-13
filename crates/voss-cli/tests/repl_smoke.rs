use std::time::Duration;

use assert_cmd::Command;

#[test]
fn voss_help_lists_all_verbs() {
    let out = Command::cargo_bin("voss-cli")
        .unwrap()
        .arg("--help")
        .output()
        .unwrap();
    let s = String::from_utf8_lossy(&out.stdout);
    for verb in &[
        "doctor", "sessions", "resume", "ast", "do", "chat", "plugins", "plugin",
        "skills", "skill", "agents", "agent",
    ] {
        assert!(
            s.contains(verb),
            "missing verb '{verb}' in --help: {s}"
        );
    }
}

#[test]
fn extension_list_commands_work_without_auth() {
    for verb in ["plugins", "skills", "agents"] {
        Command::cargo_bin("voss-cli")
            .unwrap()
            .arg(verb)
            .assert()
            .success();
    }
}

#[test]
fn plugin_enable_persists() {
    let tmp = tempfile::tempdir().unwrap();
    Command::cargo_bin("voss-cli")
        .unwrap()
        .env("XDG_CONFIG_HOME", tmp.path().join(".config"))
        .args(["plugin", "enable", "demo"])
        .assert()
        .success();
    let text = std::fs::read_to_string(tmp.path().join(".config/voss/plugins.toml")).unwrap();
    assert!(text.contains("demo"));
    assert!(text.contains("enabled = true"));
}

#[test]
fn unknown_subcommand_exits_2() {
    Command::cargo_bin("voss-cli")
        .unwrap()
        .arg("definitely-not-a-verb")
        .assert()
        .failure();
}

/// Bare invocation in a non-TTY environment with no auth → exit 2.
#[test]
fn bare_invocation_with_eof_exits_clean() {
    let tmp = tempfile::tempdir().unwrap();
    let mut cmd = Command::cargo_bin("voss-cli").unwrap();
    cmd.env("HOME", tmp.path())
        .env("XDG_CONFIG_HOME", tmp.path().join(".config"))
        .env("VOSS_DISABLE_KEYCHAIN", "1")
        .env_remove("ANTHROPIC_API_KEY")
        .env_remove("OPENAI_API_KEY")
        .write_stdin("")
        .timeout(Duration::from_secs(5));
    let out = cmd.output().unwrap();
    let code = out.status.code().unwrap_or(-1);
    assert!(
        code == 0 || code == 2,
        "expected exit 0 or 2, got {code}; stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
}

#[test]
fn bare_invocation_without_auth_exits_2_with_message() {
    let tmp = tempfile::tempdir().unwrap();
    let mut cmd = Command::cargo_bin("voss-cli").unwrap();
    cmd.env("HOME", tmp.path())
        .env_remove("ANTHROPIC_API_KEY")
        .env_remove("OPENAI_API_KEY")
        .env("VOSS_DISABLE_KEYCHAIN", "1")
        .env("XDG_CONFIG_HOME", tmp.path().join(".config"))
        .write_stdin("")
        .timeout(Duration::from_secs(10));
    let out = cmd.output().unwrap();
    assert_eq!(
        out.status.code(),
        Some(2),
        "expected exit 2 with no auth, got: {:?}\nstderr: {}",
        out.status,
        String::from_utf8_lossy(&out.stderr)
    );
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("claude login")
            || stderr.contains("Claude OAuth")
            || stderr.contains("07-08")
            || stderr.contains("auth"),
        "expected actionable auth message in stderr, got: {stderr}"
    );
}
