use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use futures_util::StreamExt;
use voss_sdk::{tasks::TaskPhase, VossClient};

struct Server(Child);
impl Drop for Server {
    fn drop(&mut self) { let _ = self.0.kill(); let _ = self.0.wait(); }
}

fn server(root: &std::path::Path) -> (Server, VossClient) {
    let python = std::env::var("VOSS_TEST_PYTHON").expect("explicit engine test Python required");
    let source = std::env::var("VOSS_TEST_ROOT").expect("explicit engine source required");
    let mut child = Command::new(python).arg(concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/task_server.py"))
        .env("PYTHONPATH", source).current_dir(root).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().unwrap();
    let mut line = String::new();
    BufReader::new(child.stdout.take().unwrap()).read_line(&mut line).unwrap();
    let handshake: serde_json::Value = serde_json::from_str(&line).expect("synthetic server handshake");
    let client = VossClient::new(format!("http://127.0.0.1:{}", handshake["port"]), "synthetic-sdk-replay".into());
    (Server(child), client)
}

async fn next(stream: &mut futures_util::stream::BoxStream<'static, Result<voss_sdk::tasks::TaskEvent, voss_sdk::error::VossError>>) -> voss_sdk::tasks::TaskEvent {
    tokio::time::timeout(std::time::Duration::from_secs(5), stream.next()).await.unwrap().unwrap().unwrap()
}

#[tokio::test]
#[ignore = "requires VOSS_TEST_PYTHON and VOSS_TEST_ROOT; uses only synthetic turns"]
async fn real_engine_replay_cancel_crash_and_reopen() {
    let root = tempfile::tempdir().unwrap();
    let (mut process, client) = server(root.path());
    assert!(client.capabilities().await.unwrap().supports("tasks.replay.v1"));
    let sid = client.create_session(root.path().to_str().unwrap()).await.unwrap();
    let snapshot = client.task_snapshot(&sid).await.unwrap();
    let mut a = voss_sdk::stream::task_stream(client.clone(), sid.clone(), snapshot.watermark).await.unwrap();
    let mut b = voss_sdk::stream::task_stream(client.clone(), sid.clone(), snapshot.watermark).await.unwrap();
    let ack = client.submit_message(&sid, "hello", "plan", "one").await.unwrap();
    assert_eq!(ack.attempt_id, client.submit_message(&sid, "hello", "plan", "one").await.unwrap().attempt_id);
    assert!(client.submit_message(&sid, "different", "plan", "one").await.is_err());
    let first = next(&mut a).await;
    assert_eq!(first.cursor, next(&mut b).await.cursor);
    drop(a);
    let mut last = first.cursor;
    loop { let event = next(&mut b).await; last = last.max(event.cursor); if event.snapshot.phase == TaskPhase::Completed { break; } }
    let mut replay = voss_sdk::stream::task_stream(client.clone(), sid.clone(), first.cursor).await.unwrap();
    assert_eq!(next(&mut replay).await.cursor, first.cursor + 1);
    drop(replay);
    client.submit_message(&sid, "wait", "plan", "two").await.unwrap();
    let second = next(&mut b).await;
    assert!(second.cursor > last);
    assert_ne!(second.snapshot.attempt_id, ack.attempt_id);
    assert_eq!(second.snapshot.phase, TaskPhase::Active);
    assert_eq!(client.reply_permission(&sid, "old", "a").await.unwrap().status, "stale");
    assert_eq!(client.reply_diff(&sid, "old", &[]).await.unwrap().status, "stale");
    assert_eq!(client.abort_task(&sid).await.unwrap().status, "cancelled");
    assert_eq!(client.task_snapshot(&sid).await.unwrap().phase, TaskPhase::Cancelled);
    let third = client.submit_message(&sid, "wait", "plan", "three").await.unwrap();
    loop {
        let event = next(&mut b).await;
        if event.snapshot.attempt_id == third.attempt_id && event.event["type"] == "warning" { break; }
    }
    drop(b);
    process.0.kill().unwrap(); process.0.wait().unwrap();
    let (_restarted, client) = server(root.path());
    let recovered = client.task_snapshot(&sid).await.unwrap();
    assert_eq!(recovered.phase, TaskPhase::Interrupted);
    assert_eq!(recovered.attempt_id, third.attempt_id);
    assert_eq!(client.submit_message(&sid, "wait", "plan", "three").await.unwrap().attempt_id, third.attempt_id);
    assert_eq!(std::fs::read_to_string(root.path().join("starts")).unwrap().lines().count(), 3);
}

#[tokio::test]
async fn task_stream_checks_wire_cursor_and_keeps_unknown_events() {
    use std::io::{Read, Write};
    for (wire_id, valid) in [("1", true), ("9", false)] {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        let body = format!("id: {wire_id}\nevent: task.event\ndata: {}\n\n", serde_json::json!({
            "v":1,"cursor":1,"snapshot":{"v":1,"task_id":"fixture","session_id":"fixture",
            "phase":"future_phase","pending_actions":[],"watermark":1},"event":{"type":"future.event"}
        }));
        let worker = std::thread::spawn(move || {
            let (mut socket, _) = listener.accept().unwrap();
            socket.set_read_timeout(Some(std::time::Duration::from_secs(5))).unwrap();
            let mut request = Vec::new();
            let mut chunk = [0; 1024];
            while !request.windows(4).any(|w| w == b"\r\n\r\n") {
                let count = socket.read(&mut chunk).unwrap();
                assert!(count > 0);
                request.extend_from_slice(&chunk[..count]);
            }
            assert!(String::from_utf8(request).unwrap().starts_with("GET /session/fixture/task-events?after=0 "));
            write!(socket, "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len()).unwrap();
        });
        let client = VossClient::new(format!("http://{address}"), "synthetic".into());
        let mut stream = voss_sdk::stream::task_stream(client, "fixture".into(), 0).await.unwrap();
        let result = stream.next().await.unwrap();
        if valid {
            let event = result.unwrap();
            assert_eq!(event.snapshot.phase, TaskPhase::Unknown);
            assert_eq!(event.event["type"], "future.event");
        } else { assert!(result.is_err()); }
        worker.join().unwrap();
    }
}

#[tokio::test]
#[ignore = "requires VOSS_TEST_PYTHON and VOSS_TEST_ROOT; uses only synthetic planning and turns"]
async fn real_engine_preview_start_and_retry_use_the_same_graph() {
    let root = tempfile::tempdir().unwrap();
    let repo = root.path().join("repo");
    std::fs::create_dir(&repo).unwrap();
    for args in [vec!["init"], vec!["-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.test", "commit", "--allow-empty", "-m", "fixture"]] {
        assert!(Command::new("git").args(args).current_dir(&repo).output().unwrap().status.success());
    }
    let (mut process, client) = server(root.path());
    let briefing: voss_sdk::plans::Briefing = serde_json::from_value(serde_json::json!({
        "source":{"kind":"objective","text":"Inspect synthetic repository"}, "cwd":repo,
        "harness":"codex","model":"gpt-6-astra","tier":"plan","scope":{"allow":["**/*"],"deny":[]},
        "context":[{"id":"brief","text":"Synthetic context"}]
    })).unwrap();
    assert!(client.capabilities().await.unwrap().supports("plans.preview.v1"));
    assert!(client.capabilities().await.unwrap().supports("tasks.graph.v1"));
    let plan = client.preview_plan(&briefing).await.unwrap().preview.unwrap();
    assert_eq!(plan.tasks[1].depends_on, vec![plan.tasks[0].id.clone()]);
    assert_eq!(plan.accepted_context, vec!["brief"]);
    assert!(!root.path().join("starts").exists());
    let (a, b) = tokio::join!(client.start_plan(&plan.id, &plan.revision, &briefing), client.start_plan(&plan.id, &plan.revision, &briefing));
    let a = a.unwrap(); let b = b.unwrap();
    assert_eq!(a.status, "accepted"); assert_eq!(a.run_id, b.run_id); assert_eq!(a.session_id, b.session_id);
    let sid = a.session_id.unwrap();
    let mut stream = voss_sdk::stream::task_stream(client.clone(), sid.clone(), 0).await.unwrap();
    loop {
        let event = next(&mut stream).await;
        assert_eq!(event.snapshot.execution_plan.as_ref().unwrap().revision, plan.revision);
        if event.snapshot.phase == TaskPhase::Completed {
            assert!(event.snapshot.node_states.values().all(|state| state == "completed"));
            break;
        }
    }
    drop(stream);
    let snapshot = client.task_snapshot(&sid).await.unwrap();
    let graph = snapshot.graph.unwrap();
    assert_eq!(graph.revision, plan.revision);
    assert_eq!(graph.nodes.iter().map(|node| &node.id).collect::<Vec<_>>(), plan.tasks.iter().map(|node| &node.id).collect::<Vec<_>>());
    for node in &graph.nodes {
        assert_eq!(node.attempts.len(), 1);
        let attempt = &node.attempts[0];
        assert_eq!(attempt.run_id, snapshot.run_id);
        let output = client.graph_output(&sid, &node.id, &attempt.id, 0).await.unwrap();
        assert_eq!(output.status, "available");
        assert!(output.events.iter().all(|row| row["cursor"].as_u64().unwrap() <= attempt.output_through.unwrap()));
    }
    process.0.kill().unwrap(); process.0.wait().unwrap();
    let (_restarted, client) = server(root.path());
    assert_eq!(client.plan_status(&plan.id).await.unwrap().run_id, a.run_id);
    assert_eq!(client.task_snapshot(&sid).await.unwrap().graph.unwrap().revision, graph.revision);
    assert_eq!(client.start_plan(&plan.id, &plan.revision, &briefing).await.unwrap().run_id, a.run_id);
    assert_eq!(std::fs::read_to_string(root.path().join("starts")).unwrap().lines().count(), 2);
    let mut changed = briefing; changed.source.text = "Different request".into();
    assert_eq!(client.start_plan(&plan.id, &plan.revision, &changed).await.unwrap().status, "stale");
}
