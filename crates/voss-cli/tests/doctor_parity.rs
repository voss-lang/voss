//! `voss-cli doctor` output structure must match `voss/harness/cli.py::doctor_cmd`.
//!
//! Test runs in a hermetic `$HOME = <tempdir>` so neither cred source
//! resolves and the output reduces to its skeleton: 7 fixed lines, in order,
//! each with a known label prefix.

use std::path::PathBuf;
use std::process::Command;

const EXPECTED_PREFIXES: &[&str] = &[
    "default model       :",
    "ANTHROPIC_API_KEY   :",
    "OPENAI_API_KEY      :",
    "Claude Code OAuth   :",
    "Codex creds         :",
    "--auth=auto picks   :",
    "voss_runtime        :",
];

fn repo_root() -> PathBuf {
    let mf = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    mf.parent().unwrap().parent().unwrap().to_path_buf()
}

#[test]
fn doctor_emits_seven_labelled_lines_in_order() {
    let root = repo_root();
    let bin = assert_cmd::cargo::cargo_bin("voss-cli");
    let tmp = tempfile::tempdir().expect("tempdir");

    let out = Command::new(&bin)
        .arg("doctor")
        .env("HOME", tmp.path())
        .env_remove("ANTHROPIC_API_KEY")
        .env_remove("OPENAI_API_KEY")
        .env("VOSS_DISABLE_KEYCHAIN", "1")
        .env_remove("VOSS_KEYCHAIN_SERVICE")
        .env_remove("VOSS_MODEL")
        .current_dir(&root)
        .output()
        .expect("voss-cli should spawn");
    assert!(
        out.status.success(),
        "doctor exit {}: stderr={}",
        out.status,
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    let lines: Vec<&str> = stdout.lines().collect();

    assert_eq!(
        lines.len(),
        EXPECTED_PREFIXES.len(),
        "doctor output should be {} lines, got {}: {}",
        EXPECTED_PREFIXES.len(),
        lines.len(),
        stdout
    );
    for (i, (line, want)) in lines.iter().zip(EXPECTED_PREFIXES.iter()).enumerate() {
        assert!(
            line.starts_with(want),
            "line {i}: expected prefix `{want}`, got `{line}`"
        );
    }

    // With HOME=tempdir + service override + no env keys, all sources should
    // miss and report unset/not-found.
    assert!(
        stdout.contains("ANTHROPIC_API_KEY   : unset"),
        "expected ANTHROPIC_API_KEY unset, got: {stdout}"
    );
    assert!(
        stdout.contains("OPENAI_API_KEY      : unset"),
        "expected OPENAI_API_KEY unset, got: {stdout}"
    );
    // Note: macOS Keychain may still satisfy load_anthropic_oauth via the
    // service-override env var. We only assert the unset env-var lines.
}
