//! H3.3 — cross-language protocol parity (drift guard).
//!
//! Enumerates every event `type` the server's `events.py` AgentEvent union
//! declares (via the real Python), and asserts the Rust client's known set
//! matches exactly. If the server adds/renames/removes an event type, this
//! fails and forces a human to decide whether the client should render it.
//! Also asserts the rendered subset maps to specific AppEvent variants.
//!
//! Skips (does not fail) when the repo venv interpreter is absent.

use std::collections::BTreeSet;
use std::path::Path;
use std::process::Command;

use voss_tui::event::AppEvent;

/// Every event type the client is aware of (must equal the server union).
const KNOWN: &[&str] = &[
    "server.connected",
    "session.idle",
    "permission.updated",
    "banner",
    "user",
    "thinking",
    "plan",
    "tool",
    "clarify",
    "final",
    "stream.delta",
    "stream.finalize",
    "status",
    "cognition_loaded",
    "cognition_overflow",
    "warning",
    "probable",
    "budget.updated",
    "confidence.updated",
    "gate.updated",
];

/// The subset the MVP client renders to a specific (non-Other) AppEvent.
const RENDERED: &[&str] = &[
    "server.connected",
    "user",
    "thinking",
    "plan",
    "tool",
    "clarify",
    "final",
    "stream.delta",
    "stream.finalize",
    "status",
    "permission.updated",
    "warning",
    "session.idle",
];

const PY_ENUM: &str = r#"
import json, typing
from voss.harness.server import events as E
union = typing.get_args(E.AgentEvent)[0]
models = typing.get_args(union)
print(json.dumps([m.model_fields['type'].default for m in models]))
"#;

fn venv_python() -> Option<String> {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python");
    p.exists().then(|| p.to_string_lossy().into_owned())
}

#[test]
fn rendered_types_map_to_specific_variants() {
    for t in RENDERED {
        assert!(
            !matches!(AppEvent::from_wire(t, "{}"), AppEvent::Other(_)),
            "`{t}` is in RENDERED but from_wire maps it to Other"
        );
    }
}

#[test]
fn event_types_match_server_union() {
    let Some(py) = venv_python() else {
        eprintln!("skipping protocol parity: .venv/bin/python not found");
        return;
    };
    let out = Command::new(&py)
        .args(["-c", PY_ENUM])
        .output()
        .expect("run python enumerator");
    assert!(
        out.status.success(),
        "python enumerator failed: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    let server_types: Vec<String> =
        serde_json::from_slice(&out.stdout).expect("parse python type list");
    let server: BTreeSet<String> = server_types.into_iter().collect();
    let known: BTreeSet<String> = KNOWN.iter().map(|s| s.to_string()).collect();

    assert_eq!(
        server,
        known,
        "event-type drift between server events.py and voss-tui.\n  server-only (add to KNOWN + handle): {:?}\n  client-only (stale in KNOWN): {:?}",
        server.difference(&known).collect::<Vec<_>>(),
        known.difference(&server).collect::<Vec<_>>(),
    );
}
