use std::sync::Mutex;

use voss_cli::permissions::{Mode, PermissionGate, PermissionStore};

static ENV_LOCK: Mutex<()> = Mutex::new(());

fn with_xdg<F: FnOnce()>(f: F) {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    let prev = std::env::var_os("XDG_CONFIG_HOME");
    std::env::set_var("XDG_CONFIG_HOME", tmp.path());
    let res = std::panic::catch_unwind(std::panic::AssertUnwindSafe(f));
    match prev {
        Some(p) => std::env::set_var("XDG_CONFIG_HOME", p),
        None => std::env::remove_var("XDG_CONFIG_HOME"),
    }
    if let Err(e) = res {
        std::panic::resume_unwind(e);
    }
}

#[test]
fn store_round_trip() {
    with_xdg(|| {
        let cwd = std::env::current_dir().unwrap();
        let mut store = PermissionStore::load(&cwd);
        store.remember("shell_run:git".into()).unwrap();
        store.remember("fs_write".into()).unwrap();
        let reloaded = PermissionStore::load(&cwd);
        assert!(
            reloaded.always.contains("shell_run:git"),
            "missing shell_run:git in {:?}",
            reloaded.always
        );
        assert!(
            reloaded.always.contains("fs_write"),
            "missing fs_write in {:?}",
            reloaded.always
        );
    });
}

#[test]
fn signature_shell_run_uses_first_word() {
    let sig =
        PermissionGate::signature("shell_run", &serde_json::json!({"cmd": "git status --porcelain"}));
    assert_eq!(sig, "shell_run:git");
}

#[test]
fn signature_non_shell_is_tool_name() {
    let sig = PermissionGate::signature("fs_write", &serde_json::json!({"path": "x.txt"}));
    assert_eq!(sig, "fs_write");
}

#[test]
fn needs_prompt_edit_mode() {
    let g = PermissionGate {
        mode: Mode::Edit,
        store: None,
        auto_yes: false,
    };
    assert!(!g.needs_prompt("fs_read"));
    assert!(g.needs_prompt("fs_write"));
    assert!(g.needs_prompt("shell_run"));
}

#[test]
fn needs_prompt_plan_mode_blocks_writes() {
    let g = PermissionGate {
        mode: Mode::Plan,
        store: None,
        auto_yes: false,
    };
    assert!(!g.needs_prompt("fs_read"));
    assert!(g.needs_prompt("fs_write"));
    assert!(g.needs_prompt("shell_run"));
}

#[test]
fn auto_mode_skips_all() {
    let g = PermissionGate {
        mode: Mode::Auto,
        store: None,
        auto_yes: false,
    };
    assert!(!g.needs_prompt("fs_write"));
    assert!(!g.needs_prompt("shell_run"));
}

#[test]
fn auto_yes_overrides_mode() {
    let g = PermissionGate {
        mode: Mode::Edit,
        store: None,
        auto_yes: true,
    };
    assert!(!g.needs_prompt("shell_run"));
}

#[test]
fn check_remembers_when_capital_a() {
    with_xdg(|| {
        let cwd = std::env::current_dir().unwrap();
        let store = PermissionStore::load(&cwd);
        let mut gate = PermissionGate {
            mode: Mode::Edit,
            store: Some(store),
            auto_yes: false,
        };
        let (ok, reason) = gate.check(
            "shell_run",
            &serde_json::json!({"cmd": "git diff"}),
            |_, _| 'A',
        );
        assert!(ok);
        assert_eq!(reason, "allowed always");

        // Reload — should now find the signature in `always`.
        let reloaded = PermissionStore::load(&cwd);
        assert!(reloaded.always.contains("shell_run:git"));
    });
}
