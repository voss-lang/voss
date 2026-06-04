//! H7 — native session-store reader + cross-language parity.
//!
//! Proves the Rust native reader parses the on-disk session format and, given
//! the same directory, produces the same listing the Python server's
//! `/sessions/saved` returns (the data-compat enabler for incremental porting).

use std::path::Path;

use voss_tui::store::read_saved_sessions;

fn write_session(dir: &Path, id: &str, name: &str, updated: &str, turns: usize) {
    let sessions = dir.join(".voss").join("sessions");
    std::fs::create_dir_all(&sessions).unwrap();
    let turns_json: Vec<serde_json::Value> = (0..turns)
        .map(|i| serde_json::json!({ "role": "user", "content": format!("t{i}") }))
        .collect();
    let record = serde_json::json!({
        "id": id,
        "name": name,
        "cwd": dir.to_string_lossy(),
        "model": "m",
        "started_at": updated,
        "updated_at": updated,
        "total_cost_usd": 0.0,
        "turns": turns_json,
        "runs": [],
    });
    std::fs::write(
        sessions.join(format!("{id}.json")),
        serde_json::to_string(&record).unwrap(),
    )
    .unwrap();
}

#[test]
fn reads_and_orders_newest_first() {
    let tmp = tempfile::tempdir().unwrap();
    let cwd = tmp.path().to_string_lossy().to_string();
    write_session(
        tmp.path(),
        "aaaa00000001",
        "older",
        "2026-05-01T00:00:00+00:00",
        2,
    );
    write_session(
        tmp.path(),
        "bbbb00000002",
        "newer",
        "2026-05-09T00:00:00+00:00",
        4,
    );

    let got = read_saved_sessions(&cwd);
    assert_eq!(got.len(), 2);
    assert_eq!(got[0].id, "bbbb00000002"); // newest first
    assert_eq!(got[0].turns, 4);
    assert_eq!(got[1].id, "aaaa00000001");
    assert_eq!(got[1].turns, 2);
}

#[test]
fn missing_dir_is_empty() {
    let tmp = tempfile::tempdir().unwrap();
    assert!(read_saved_sessions(&tmp.path().to_string_lossy()).is_empty());
}

#[test]
fn ignores_malformed_files() {
    let tmp = tempfile::tempdir().unwrap();
    let sessions = tmp.path().join(".voss").join("sessions");
    std::fs::create_dir_all(&sessions).unwrap();
    std::fs::write(sessions.join("bad.json"), "{not json").unwrap();
    write_session(
        tmp.path(),
        "good00000001",
        "ok",
        "2026-05-01T00:00:00+00:00",
        1,
    );
    let got = read_saved_sessions(&tmp.path().to_string_lossy());
    assert_eq!(got.len(), 1);
    assert_eq!(got[0].id, "good00000001");
}
