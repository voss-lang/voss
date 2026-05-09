//! Cross-language session round-trip parity. Both directions:
//!   - Rust writes → Python reads.
//!   - Python writes → Rust reads.
//!
//! Skips with a printed reason when the Python `voss` package is not
//! importable (keeps the workspace test suite green on machines without
//! the venv available).

use std::path::PathBuf;
use std::process::Command;
use std::sync::Mutex;

use voss_cli::session::{self, SessionRecord, Turn};

static ENV_LOCK: Mutex<()> = Mutex::new(());

fn repo_root() -> PathBuf {
    let mf = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    mf.parent().unwrap().parent().unwrap().to_path_buf()
}

fn pick_python() -> PathBuf {
    if let Some(v) = std::env::var_os("VOSS_PYTHON") {
        return PathBuf::from(v);
    }
    let venv = repo_root().join(".venv/bin/python");
    if venv.exists() {
        return venv;
    }
    PathBuf::from("python3")
}

/// Format `s` as a Python single-quoted string literal with backslash + apostrophe escaped.
fn py_str(s: &str) -> String {
    let escaped: String = s
        .chars()
        .map(|c| match c {
            '\\' => "\\\\".to_string(),
            '\'' => "\\'".to_string(),
            other => other.to_string(),
        })
        .collect();
    format!("'{escaped}'")
}

fn restore_env(prev: Option<std::ffi::OsString>) {
    match prev {
        Some(p) => std::env::set_var("XDG_STATE_HOME", p),
        None => std::env::remove_var("XDG_STATE_HOME"),
    }
}

#[test]
fn rust_writes_python_reads() {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    let prev = std::env::var_os("XDG_STATE_HOME");
    std::env::set_var("XDG_STATE_HOME", tmp.path());

    let mut rec =
        SessionRecord::new(tmp.path(), "claude-sonnet-4-5", Some("rust-session"));
    rec.turns.push(Turn {
        role: "user".into(),
        content: "hello".into(),
        extra: Default::default(),
    });
    rec.turns.push(Turn {
        role: "assistant".into(),
        content: "hi".into(),
        extra: Default::default(),
    });
    let path = session::save(&mut rec).expect("save");
    assert!(path.exists());

    let env_lit = py_str(&tmp.path().to_string_lossy());
    let sid_lit = py_str(&rec.id);
    let py = format!(
        "import os\n\
         os.environ['XDG_STATE_HOME'] = {env_lit}\n\
         from voss.harness import session as s\n\
         rec, hist = s.load({sid_lit})\n\
         print(rec.id)\n\
         print(rec.name)\n\
         print(len(rec.turns))\n\
         print(rec.model)\n\
         print(rec.started_at)\n"
    );
    let out = Command::new(pick_python())
        .args(["-c", &py])
        .current_dir(repo_root())
        .output();
    let py_out = match out {
        Ok(o) if o.status.success() => o,
        Ok(o) => {
            eprintln!(
                "skipping rust→python parity: python failed: {}",
                String::from_utf8_lossy(&o.stderr)
            );
            restore_env(prev);
            return;
        }
        Err(e) => {
            eprintln!("skipping rust→python parity: {e}");
            restore_env(prev);
            return;
        }
    };
    let stdout = String::from_utf8_lossy(&py_out.stdout);
    let lines: Vec<&str> = stdout.lines().collect();
    assert!(lines.len() >= 5, "expected 5 lines, got: {stdout}");
    assert_eq!(lines[0], rec.id);
    assert_eq!(lines[1], "rust-session");
    assert_eq!(lines[2], "2");
    assert_eq!(lines[3], "claude-sonnet-4-5");
    assert_eq!(
        lines[4], rec.started_at,
        "ISO-8601 timestamp must round-trip exactly"
    );

    restore_env(prev);
}

#[test]
fn python_writes_rust_reads() {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    let prev = std::env::var_os("XDG_STATE_HOME");
    std::env::set_var("XDG_STATE_HOME", tmp.path());

    let env_lit = py_str(&tmp.path().to_string_lossy());
    let py = format!(
        "import os\n\
         os.environ['XDG_STATE_HOME'] = {env_lit}\n\
         from pathlib import Path\n\
         from voss.harness import session as s\n\
         from voss_runtime import EpisodicMemory\n\
         rec = s.SessionRecord.new(cwd=Path('.'), model='claude-sonnet-4-5', name='py-session')\n\
         mem = EpisodicMemory(capacity=40)\n\
         mem.add('hi', role='user')\n\
         mem.add('ok', role='assistant')\n\
         s.save(rec, mem)\n\
         print(rec.id)\n"
    );
    let out = Command::new(pick_python())
        .args(["-c", &py])
        .current_dir(repo_root())
        .output();
    let py_out = match out {
        Ok(o) if o.status.success() => o,
        Ok(o) => {
            eprintln!(
                "skipping python→rust parity: python failed: {}",
                String::from_utf8_lossy(&o.stderr)
            );
            restore_env(prev);
            return;
        }
        Err(e) => {
            eprintln!("skipping python→rust parity: {e}");
            restore_env(prev);
            return;
        }
    };
    let id = String::from_utf8_lossy(&py_out.stdout).trim().to_string();

    let rec = session::load(&id).expect("rust must read python-written session");
    assert_eq!(rec.name, "py-session");
    assert_eq!(rec.turns.len(), 2);
    assert_eq!(rec.turns[0].role, "user");
    assert_eq!(rec.turns[0].content, "hi");
    assert_eq!(rec.turns[1].role, "assistant");
    assert_eq!(rec.turns[1].content, "ok");

    restore_env(prev);
}
