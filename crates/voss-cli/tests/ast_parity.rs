use std::path::PathBuf;
use std::process::Command;

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

fn pick_fixture() -> PathBuf {
    let p = repo_root().join("samples/classify.voss");
    assert!(p.exists(), "fixture not found: {}", p.display());
    p
}

#[test]
fn rust_and_python_ast_agree() {
    let root = repo_root();
    let python = pick_python();
    let fixture = pick_fixture();

    // Python: `python -m voss.cli ast <fixture> --compact` (Click emits JSON).
    let py_out = Command::new(&python)
        .args([
            "-m",
            "voss.cli",
            "ast",
            fixture.to_str().unwrap(),
            "--compact",
        ])
        .current_dir(&root)
        .output()
        .expect("python invocation should spawn");
    assert!(
        py_out.status.success(),
        "python ast exit {}: stderr={}",
        py_out.status,
        String::from_utf8_lossy(&py_out.stderr)
    );
    let py_json: serde_json::Value = serde_json::from_slice(&py_out.stdout).unwrap_or_else(|e| {
        panic!(
            "python stdout was not JSON: {e}\n{}",
            String::from_utf8_lossy(&py_out.stdout)
        )
    });

    // Rust: cargo-built voss-cli binary.
    let bin = assert_cmd::cargo::cargo_bin("voss-cli");
    let rs_out = Command::new(&bin)
        .args(["ast", fixture.to_str().unwrap(), "--json", "--compact"])
        .current_dir(&root)
        .output()
        .expect("rust binary should spawn");
    assert!(
        rs_out.status.success(),
        "rust ast exit {}: stderr={}",
        rs_out.status,
        String::from_utf8_lossy(&rs_out.stderr)
    );
    let rs_json: serde_json::Value = serde_json::from_slice(&rs_out.stdout).unwrap_or_else(|e| {
        panic!(
            "rust stdout was not JSON: {e}\n{}",
            String::from_utf8_lossy(&rs_out.stdout)
        )
    });

    // The Rust path wraps Python's program in a versioned envelope:
    //   { "v": 1, "program": <to_dict(program)> }
    // Python `voss ast` emits the bare program dict.
    assert_eq!(rs_json.get("v").and_then(|v| v.as_i64()), Some(1));
    let rs_program = rs_json
        .get("program")
        .expect("rust output must have program key");

    // Both sides come from the same serializer, so the AST node names match.
    assert_eq!(
        rs_program.get("_node").and_then(|v| v.as_str()),
        Some("Program"),
        "rust program._node mismatch"
    );
    assert_eq!(
        py_json.get("_node").and_then(|v| v.as_str()),
        Some("Program"),
        "python program._node mismatch"
    );

    // Top-level structure (body) shape matches: same number of top-level decls.
    let rs_body = rs_program
        .get("body")
        .and_then(|v| v.as_array())
        .unwrap_or(&Vec::new())
        .len();
    let py_body = py_json
        .get("body")
        .and_then(|v| v.as_array())
        .unwrap_or(&Vec::new())
        .len();
    assert_eq!(
        rs_body, py_body,
        "body length mismatch: rust={rs_body}, python={py_body}"
    );

    // First-node parity (kind only — spans differ trivially across runs in theory).
    if rs_body > 0 {
        let rs_first_kind = rs_program.get("body").unwrap()[0]
            .get("_node")
            .and_then(|v| v.as_str());
        let py_first_kind = py_json.get("body").unwrap()[0]
            .get("_node")
            .and_then(|v| v.as_str());
        assert_eq!(
            rs_first_kind, py_first_kind,
            "first body node kind mismatch"
        );
    }
}
