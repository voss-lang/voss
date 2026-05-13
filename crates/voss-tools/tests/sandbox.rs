use std::sync::Mutex;

use voss_tools::sandbox::{
    default_allowlist, jail_path, load_allowlist, save_allowlist_extra, shell_allowed, SandboxError,
};

static ENV_LOCK: Mutex<()> = Mutex::new(());

#[test]
fn jail_rejects_escape() {
    let tmp = tempfile::tempdir().unwrap();
    let err = jail_path(tmp.path(), "../etc/passwd").unwrap_err();
    matches!(err, SandboxError::Escape(_));
}

#[test]
fn jail_accepts_relative() {
    let tmp = tempfile::tempdir().unwrap();
    let p = jail_path(tmp.path(), "foo.txt").unwrap();
    let real = tmp.path().canonicalize().unwrap();
    assert!(p.starts_with(&real), "expected {p:?} under {real:?}");
}

#[test]
fn shell_denies_rm_rf() {
    let err = shell_allowed("rm -rf /", &default_allowlist()).unwrap_err();
    matches!(err, SandboxError::DenyToken(_));
}

#[test]
fn shell_denies_unknown_binary() {
    let err = shell_allowed("foo --bar", &default_allowlist()).unwrap_err();
    matches!(err, SandboxError::NotAllowed(_));
}

#[test]
fn shell_allows_git() {
    shell_allowed("git status", &default_allowlist()).expect("git status should be allowed");
}

#[test]
fn shell_allows_python_with_path() {
    shell_allowed("/usr/bin/python3 -c \"print(1)\"", &default_allowlist())
        .expect("python3 binary basename should match allowlist");
}

#[test]
fn allowlist_round_trip() {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().unwrap();
    let prev = std::env::var_os("XDG_CONFIG_HOME");
    std::env::set_var("XDG_CONFIG_HOME", tmp.path());
    save_allowlist_extra(&["customtool".into()]).expect("save");
    let loaded = load_allowlist();
    assert!(
        loaded.contains("customtool"),
        "loaded set should include extra; got {:?}",
        loaded
    );
    // Default entries still present.
    assert!(loaded.contains("git"));
    match prev {
        Some(p) => std::env::set_var("XDG_CONFIG_HOME", p),
        None => std::env::remove_var("XDG_CONFIG_HOME"),
    }
}
