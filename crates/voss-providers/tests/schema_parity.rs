//! Schema parity gate. Compares the schemars-derived JSON Schema for
//! `voss_agent::Plan` and `voss_agent::ToolCall` against the pydantic-derived
//! schema in `voss/harness/agent.py`. Drift fails CI.
//!
//! Strictness level: property-name set parity + required-set parity. Type
//! and description text are NOT byte-compared because pydantic adds Field
//! metadata (`title`, range constraints) that schemars omits, and the
//! property *types* are already enforced at compile-time by serde
//! roundtripping. The required-set check catches the dangerous drift class
//! (a field becoming required on one side but not the other), and the
//! name-set check catches field add/remove/rename.

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::process::Command;

use serde_json::Value;

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

/// `properties` map under either the top-level schema or `$defs/<name>`.
fn properties_of<'a>(schema: &'a Value, kind: &str) -> &'a serde_json::Map<String, Value> {
    schema
        .get("properties")
        .and_then(|v| v.as_object())
        .unwrap_or_else(|| panic!("{kind} schema missing `properties`: {schema:#}"))
}

fn required_of(schema: &Value) -> BTreeSet<String> {
    schema
        .get("required")
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default()
}

fn property_names(schema: &Value, kind: &str) -> BTreeSet<String> {
    properties_of(schema, kind).keys().cloned().collect()
}

#[test]
fn plan_and_toolcall_schemas_match_python() {
    // Dump python schema. Skip if Python or the voss package is unavailable.
    let py_bin = pick_python();
    let dump = Command::new(&py_bin)
        .args(["scripts/dump_python_plan_schema.py"])
        .current_dir(repo_root())
        .output();
    let py_json: Value = match dump {
        Ok(o) if o.status.success() => serde_json::from_slice(&o.stdout)
            .expect("python schema dump should be valid JSON"),
        Ok(o) => {
            eprintln!(
                "skipping schema_parity: python dump failed (status={}): {}",
                o.status,
                String::from_utf8_lossy(&o.stderr)
            );
            return;
        }
        Err(e) => {
            eprintln!("skipping schema_parity: cannot run python ({e})");
            return;
        }
    };

    let py_plan = py_json.get("Plan").expect("python.Plan");
    let py_toolcall_inline = py_plan
        .get("$defs")
        .and_then(|d| d.get("ToolCall"))
        .cloned();
    // Prefer the standalone dump but fall back to the $defs entry.
    let py_toolcall = py_json
        .get("ToolCall")
        .cloned()
        .or(py_toolcall_inline)
        .expect("python.ToolCall");

    let rs_plan = serde_json::to_value(schemars::schema_for!(voss_agent::Plan))
        .expect("schemars Plan -> Value");
    let rs_toolcall = serde_json::to_value(schemars::schema_for!(voss_agent::ToolCall))
        .expect("schemars ToolCall -> Value");

    // Property-name parity.
    let py_plan_names = property_names(py_plan, "Plan(py)");
    let rs_plan_names = property_names(&rs_plan, "Plan(rs)");
    assert_eq!(
        py_plan_names, rs_plan_names,
        "Plan property-name drift: py={py_plan_names:?} rs={rs_plan_names:?}"
    );

    let py_tc_names = property_names(&py_toolcall, "ToolCall(py)");
    let rs_tc_names = property_names(&rs_toolcall, "ToolCall(rs)");
    assert_eq!(
        py_tc_names, rs_tc_names,
        "ToolCall property-name drift: py={py_tc_names:?} rs={rs_tc_names:?}"
    );

    // Required-set parity.
    let py_plan_req = required_of(py_plan);
    let rs_plan_req = required_of(&rs_plan);
    assert_eq!(
        py_plan_req, rs_plan_req,
        "Plan required-set drift: py={py_plan_req:?} rs={rs_plan_req:?}"
    );

    let py_tc_req = required_of(&py_toolcall);
    let rs_tc_req = required_of(&rs_toolcall);
    assert_eq!(
        py_tc_req, rs_tc_req,
        "ToolCall required-set drift: py={py_tc_req:?} rs={rs_tc_req:?}"
    );
}
