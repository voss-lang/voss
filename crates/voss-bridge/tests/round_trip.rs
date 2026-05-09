use std::path::{Path, PathBuf};
use voss_bridge::PyBridge;

fn repo_root() -> PathBuf {
    // CARGO_MANIFEST_DIR for this crate is <repo>/crates/voss-bridge.
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

fn pick_fixture() -> PathBuf {
    let p = repo_root().join("samples/classify.voss");
    assert!(p.exists(), "fixture not found: {}", p.display());
    p
}

#[tokio::test]
async fn ast_round_trip() {
    let python = pick_python();
    let fixture = pick_fixture();
    // Run from repo root so `python -m voss.bridge_server` resolves the package.
    std::env::set_current_dir(repo_root()).unwrap();
    let bridge = PyBridge::with_python(python);
    let v = bridge
        .ast(Path::new(&fixture))
        .await
        .expect("ast call should succeed");
    assert_eq!(v.get("v").and_then(|x| x.as_i64()), Some(1), "envelope version mismatch: {v}");
    let prog = v.get("program").expect("program key");
    assert_eq!(
        prog.get("_node").and_then(|x| x.as_str()),
        Some("Program"),
        "expected program._node == \"Program\", got: {prog}"
    );
}
