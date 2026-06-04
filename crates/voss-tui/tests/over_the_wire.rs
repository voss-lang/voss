//! Over-the-wire SSE test (H2 exit criterion, deferred from H1).
//!
//! Spawns the real Python server with VOSS_SERVE_FAKE_TURN (hermetic, no creds
//! or provider), then drives it through the actual Rust net+SSE client:
//! create session -> post message -> consume the event stream. Verifies the
//! full Rust<->Python protocol path end to end.
//!
//! Skips (does not fail) if the repo venv interpreter is missing, so the suite
//! stays green in environments without the Python harness installed.

use std::path::Path;

use tokio::sync::mpsc;
use voss_tui::event::AppEvent;
use voss_tui::store::read_saved_sessions;
use voss_tui::{net::HttpClient, server};

fn venv_python() -> Option<String> {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python");
    p.exists().then(|| p.to_string_lossy().into_owned())
}

/// Live end-to-end smoke: real server + real provider (no fake seam) driven
/// through the Rust net+SSE client. `#[ignore]` so normal runs cost nothing;
/// opt in with `cargo test -p voss-tui --test over_the_wire -- --ignored
/// --nocapture`. Requires real credentials (e.g. Claude OAuth in keychain).
#[tokio::test]
#[ignore]
async fn real_turn_over_the_wire() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    let handle = server::spawn_server_with(&python, &[]) // NO fake-turn env
        .await
        .expect("server should start");
    let http = HttpClient::new(handle.base.clone(), handle.token.clone());

    let sid = match http.create_session(".").await {
        Ok(id) => id,
        Err(e) => {
            eprintln!("skipping real turn (no usable credentials): {e}");
            handle.shutdown().await;
            return;
        }
    };

    http.post_message(
        &sid,
        "Reply with exactly the word PONG and nothing else.",
        "plan",
    )
    .await
    .expect("post message");

    let (tx, mut rx) = tokio::sync::mpsc::channel::<AppEvent>(256);
    let sid2 = sid.clone();
    let http2 = http.clone();
    let stream = tokio::spawn(async move { http2.stream_events(&sid2, tx).await });

    let mut deltas = String::new();
    let mut got_final = false;
    let collect = async {
        while let Some(ev) = rx.recv().await {
            match &ev {
                AppEvent::StreamDelta(t) => deltas.push_str(t),
                AppEvent::Final { text, .. } => {
                    got_final = true;
                    eprintln!("FINAL: {text}");
                }
                AppEvent::SessionIdle => break,
                other => eprintln!("event: {other:?}"),
            }
        }
    };
    tokio::time::timeout(std::time::Duration::from_secs(120), collect)
        .await
        .expect("real turn did not complete in time");

    let _ = stream.await;
    handle.shutdown().await;

    eprintln!("STREAMED: {deltas}");
    assert!(got_final, "expected a final event from the real turn");
    assert!(
        !deltas.is_empty() || got_final,
        "expected streamed output or a final"
    );
}

/// H7 parity: the native Rust session reader produces the same listing the
/// Python server's /sessions/saved returns for the same directory. Hermetic
/// (crafted sessions in a tmp dir, no creds). Skips if no venv.
#[tokio::test]
async fn native_store_matches_server_listing() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };
    let tmp = tempfile::tempdir().unwrap();
    let cwd = tmp.path().to_string_lossy().to_string();
    let sessions = tmp.path().join(".voss").join("sessions");
    std::fs::create_dir_all(&sessions).unwrap();
    for (id, updated, turns) in [
        ("aaaa00000001", "2026-05-01T00:00:00+00:00", 2usize),
        ("bbbb00000002", "2026-05-09T00:00:00+00:00", 4),
        ("cccc00000003", "2026-05-05T00:00:00+00:00", 1),
    ] {
        let tj: Vec<serde_json::Value> = (0..turns)
            .map(|i| serde_json::json!({"role": "user", "content": format!("t{i}")}))
            .collect();
        let rec = serde_json::json!({
            "id": id, "name": "s", "cwd": cwd, "model": "m",
            "started_at": updated, "updated_at": updated,
            "total_cost_usd": 0.0, "turns": tj, "runs": [],
        });
        std::fs::write(
            sessions.join(format!("{id}.json")),
            serde_json::to_string(&rec).unwrap(),
        )
        .unwrap();
    }

    let handle = server::spawn_server_with(&python, &[]).await.unwrap();
    let http = HttpClient::new(handle.base.clone(), handle.token.clone());
    let server_list = http.list_saved_sessions(&cwd).await.expect("server list");
    handle.shutdown().await;

    let native = read_saved_sessions(&cwd);

    let s: Vec<(String, u64)> = server_list
        .iter()
        .map(|x| (x.id.clone(), x.turns))
        .collect();
    let n: Vec<(String, u64)> = native.iter().map(|x| (x.id.clone(), x.turns)).collect();
    assert_eq!(
        n, s,
        "native reader must match Python server listing (id+order+turns)"
    );
}

#[tokio::test]
async fn fake_turn_streams_over_the_wire() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    let handle = server::spawn_server_with(&python, &[("VOSS_SERVE_FAKE_TURN", "1")])
        .await
        .expect("server should start");
    let http = HttpClient::new(handle.base.clone(), handle.token.clone());

    let sid = http.create_session(".").await.expect("create session");

    http.post_message(&sid, "ping", "plan")
        .await
        .expect("post message");

    let (tx, mut rx) = mpsc::channel::<AppEvent>(256);
    let stream = tokio::spawn(async move { http.stream_events(&sid, tx).await });

    let mut seen: Vec<AppEvent> = Vec::new();
    let collect = async {
        while let Some(ev) = rx.recv().await {
            let idle = matches!(ev, AppEvent::SessionIdle);
            seen.push(ev);
            if idle {
                break;
            }
        }
    };
    tokio::time::timeout(std::time::Duration::from_secs(20), collect)
        .await
        .expect("stream did not complete in time");

    let _ = stream.await;
    handle.shutdown().await;

    assert!(
        matches!(seen.first(), Some(AppEvent::User(_)))
            || seen.iter().any(|e| matches!(e, AppEvent::User(_))),
        "expected a user event, got {seen:?}"
    );
    assert!(
        seen.iter().any(|e| matches!(e, AppEvent::StreamDelta(_))),
        "expected stream deltas"
    );
    assert!(
        seen.iter().any(|e| matches!(e, AppEvent::Final { .. })),
        "expected a final event"
    );
    assert!(
        matches!(seen.last(), Some(AppEvent::SessionIdle)),
        "expected session.idle terminator, got {:?}",
        seen.last()
    );
}
