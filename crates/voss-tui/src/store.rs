//! Native session-store reader (HYBRID-REFACTOR-PLAN H7, first increment).
//!
//! Reads `<cwd>/.voss/sessions/*.json` — the exact on-disk format the Python
//! `session.save` writes — directly in Rust, no server round-trip. This is the
//! load-bearing proof for *all* incremental server→Rust porting: Rust reads
//! what Python writes, identically. The hot-path ports (agent loop, providers)
//! remain Python; this is the cheap, verifiable first step.

use std::path::Path;

use serde::Deserialize;

use crate::sessions::SavedSession;

#[derive(Deserialize)]
struct OnDiskRecord {
    id: String,
    #[serde(default)]
    name: String,
    #[serde(default)]
    cwd: String,
    #[serde(default)]
    model: String,
    #[serde(default)]
    updated_at: String,
    #[serde(default)]
    total_cost_usd: f64,
    #[serde(default)]
    turns: Vec<serde_json::Value>,
}

/// Read + parse saved sessions for `cwd`, newest first (matches the Python
/// `session.list_sessions` ordering: `updated_at` descending).
pub fn read_saved_sessions(cwd: &str) -> Vec<SavedSession> {
    let dir = Path::new(cwd).join(".voss").join("sessions");
    let mut out: Vec<SavedSession> = Vec::new();
    let Ok(entries) = std::fs::read_dir(&dir) else {
        return out;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let Ok(r) = serde_json::from_str::<OnDiskRecord>(&text) else {
            continue; // skip malformed/foreign files, like the Python store
        };
        out.push(SavedSession {
            id: r.id,
            name: r.name,
            cwd: r.cwd,
            model: r.model,
            updated_at: r.updated_at,
            total_cost_usd: r.total_cost_usd,
            turns: r.turns.len() as u64,
        });
    }
    out.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
    out
}
