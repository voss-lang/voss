use std::path::{Path, PathBuf};
use std::process::Command;

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("voss-sdk lives under crates/")
        .to_path_buf()
}

fn python(root: &Path) -> String {
    let venv = root.join(".venv/bin/python");
    if venv.exists() {
        venv.display().to_string()
    } else {
        "python3".to_string()
    }
}

#[test]
fn codegen_is_current() {
    let root = repo_root();
    let schema = root.join("contracts/events.schema.json");
    if !schema.exists() {
        eprintln!("skipping drift: contracts/events.schema.json not present");
        return;
    }

    let typify = Command::new("cargo")
        .args(["typify", "--version"])
        .current_dir(&root)
        .output();
    if !matches!(typify, Ok(output) if output.status.success()) {
        eprintln!("skipping drift: cargo-typify unavailable");
        return;
    }

    // V13.1 owns the Python snapshot drift gate; this is the SDK-side generated
    // Rust gate from contracts/events.schema.json.
    let output = Command::new(python(&root))
        .args(["scripts/generate_sdk_events.py", "--check"])
        .current_dir(&root)
        .output()
        .expect("failed to run SDK event generator");

    assert!(
        output.status.success(),
        "generated events drifted; rerun `.venv/bin/python scripts/generate_sdk_events.py` and commit the result\nstdout:\n{}\nstderr:\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
}
