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

    http.post_message(&sid, "Reply with exactly the word PONG and nothing else.", "plan")
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
        matches!(seen.first(), Some(AppEvent::User(_))) || seen.iter().any(|e| matches!(e, AppEvent::User(_))),
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
