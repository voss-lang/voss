use std::sync::Mutex;

use assert_cmd::Command;
use voss_cli::session::{self, SessionRecord};

static ENV_LOCK: Mutex<()> = Mutex::new(());

#[test]
fn sessions_lists_saved_records() {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    let prev = std::env::var_os("XDG_STATE_HOME");
    std::env::set_var("XDG_STATE_HOME", tmp.path());

    // Empty state dir → "(no sessions)".
    Command::cargo_bin("voss-cli")
        .unwrap()
        .env("XDG_STATE_HOME", tmp.path())
        .arg("sessions")
        .assert()
        .success()
        .stdout(predicates::str::contains("(no sessions)"));

    // Save a record (with one user turn so first_task() is non-empty).
    // Output mirrors Python `sessions_cmd`: id-prefix + updated_at + model + first_task.
    let mut rec = SessionRecord::new(tmp.path(), "claude-sonnet-4-5", Some("alpha"));
    rec.turns.push(voss_cli::session::Turn {
        role: "user".into(),
        content: "hello world".into(),
        extra: Default::default(),
    });
    let _ = session::save(&mut rec).unwrap();
    let out = Command::cargo_bin("voss-cli")
        .unwrap()
        .env("XDG_STATE_HOME", tmp.path())
        .arg("sessions")
        .output()
        .unwrap();
    let s = String::from_utf8_lossy(&out.stdout);
    assert!(
        s.contains(&rec.id[..8]),
        "expected id prefix {}, stdout: {s}",
        &rec.id[..8]
    );
    assert!(
        s.contains("claude-sonnet-4-5"),
        "expected model in output, stdout: {s}"
    );
    assert!(
        s.contains("hello world"),
        "expected first_task in output, stdout: {s}"
    );

    match prev {
        Some(p) => std::env::set_var("XDG_STATE_HOME", p),
        None => std::env::remove_var("XDG_STATE_HOME"),
    }
}

#[test]
fn resume_unknown_session_errors() {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    Command::cargo_bin("voss-cli")
        .unwrap()
        .env("XDG_STATE_HOME", tmp.path())
        .args(["resume", "nope"])
        .assert()
        .failure()
        .stderr(predicates::str::contains("resume failed"));
}

#[test]
fn resume_resolves_by_id_prefix() {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    let prev = std::env::var_os("XDG_STATE_HOME");
    std::env::set_var("XDG_STATE_HOME", tmp.path());

    let mut rec = SessionRecord::new(tmp.path(), "claude-sonnet-4-5", Some("beta"));
    let _ = session::save(&mut rec).unwrap();
    let prefix: String = rec.id.chars().take(6).collect();

    Command::cargo_bin("voss-cli")
        .unwrap()
        .env("XDG_STATE_HOME", tmp.path())
        .args(["resume", &prefix])
        .assert()
        .success()
        .stdout(predicates::str::contains("beta"));

    match prev {
        Some(p) => std::env::set_var("XDG_STATE_HOME", p),
        None => std::env::remove_var("XDG_STATE_HOME"),
    }
}

#[test]
fn resume_resolves_by_name() {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    let prev = std::env::var_os("XDG_STATE_HOME");
    std::env::set_var("XDG_STATE_HOME", tmp.path());

    let mut rec = SessionRecord::new(tmp.path(), "claude-sonnet-4-5", Some("gamma"));
    let _ = session::save(&mut rec).unwrap();

    Command::cargo_bin("voss-cli")
        .unwrap()
        .env("XDG_STATE_HOME", tmp.path())
        .args(["resume", "gamma"])
        .assert()
        .success()
        .stdout(predicates::str::contains("gamma"));

    match prev {
        Some(p) => std::env::set_var("XDG_STATE_HOME", p),
        None => std::env::remove_var("XDG_STATE_HOME"),
    }
}
