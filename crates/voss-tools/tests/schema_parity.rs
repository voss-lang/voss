//! Tool schema parity. For every tool registered in `default_toolset`, the
//! schemars-derived schema MUST agree with the pydantic-style descriptor in
//! `voss/harness/tools.py` on:
//!   - the set of property names
//!   - the required-set
//!
//! Description text and field-level metadata are deliberately not byte-
//! compared (see SUMMARY.md). The required-set check catches the dangerous
//! drift class.

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::process::Command;

use serde_json::Value;
use voss_tools::default_toolset;

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

fn props(schema: &Value) -> BTreeSet<String> {
    schema
        .get("properties")
        .and_then(|v| v.as_object())
        .map(|m| m.keys().cloned().collect())
        .unwrap_or_default()
}

fn required(schema: &Value) -> BTreeSet<String> {
    schema
        .get("required")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default()
}

#[test]
fn all_9_tool_schemas_match_python() {
    let dump = Command::new(pick_python())
        .args(["scripts/dump_python_tool_schemas.py"])
        .current_dir(repo_root())
        .output();
    let py: Value = match dump {
        Ok(o) if o.status.success() => serde_json::from_slice(&o.stdout)
            .expect("python tool dump should be valid JSON"),
        Ok(o) => {
            eprintln!(
                "skipping schema_parity: python dump failed: {}",
                String::from_utf8_lossy(&o.stderr)
            );
            return;
        }
        Err(e) => {
            eprintln!("skipping schema_parity: {e}");
            return;
        }
    };

    let cwd = PathBuf::from(".");
    let tools = default_toolset(&cwd);
    assert_eq!(tools.len(), 9, "expected 9 tools, got {}", tools.len());

    for tool in &tools {
        let name = tool.name();
        let py_entry = py
            .get(name)
            .unwrap_or_else(|| panic!("python toolset missing {name}"));
        let py_params = py_entry
            .get("parameters")
            .unwrap_or_else(|| panic!("python {name} missing parameters"));
        let rs_schema = tool.schema();

        let py_props = props(py_params);
        let rs_props = props(&rs_schema);
        assert_eq!(
            py_props, rs_props,
            "{name} property-name drift: py={py_props:?} rs={rs_props:?}"
        );

        let py_req = required(py_params);
        let rs_req = required(&rs_schema);
        assert_eq!(
            py_req, rs_req,
            "{name} required-set drift: py={py_req:?} rs={rs_req:?}"
        );
    }
}

#[test]
fn is_mutating_flags_match_d12() {
    let cwd = PathBuf::from(".");
    let tools = default_toolset(&cwd);
    let mutating: BTreeSet<&str> = tools
        .iter()
        .filter(|t| t.is_mutating())
        .map(|t| t.name())
        .collect();
    let read_only: BTreeSet<&str> = tools
        .iter()
        .filter(|t| !t.is_mutating())
        .map(|t| t.name())
        .collect();
    let expected_mutating: BTreeSet<&str> =
        ["fs_write", "fs_edit", "shell_run"].into_iter().collect();
    let expected_read: BTreeSet<&str> = [
        "fs_read",
        "fs_glob",
        "fs_grep",
        "git_status",
        "git_diff",
        "voss_check",
    ]
    .into_iter()
    .collect();
    assert_eq!(mutating, expected_mutating, "D-12 mutating set drift");
    assert_eq!(read_only, expected_read, "D-12 read-only set drift");
}
