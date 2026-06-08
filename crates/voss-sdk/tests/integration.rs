use std::path::Path;
use std::process::Command;
use std::time::Duration;

use futures_util::StreamExt;
use voss_sdk::error::VossError;
use voss_sdk::types::events::AgentEvent;
use voss_sdk::{event_stream, spawn_with, VossClient};

fn venv_python() -> Option<String> {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/python");
    p.exists().then(|| p.to_string_lossy().into_owned())
}

async fn with_timeout<F, T>(future: F) -> T
where
    F: std::future::Future<Output = T>,
{
    tokio::time::timeout(Duration::from_secs(20), future)
        .await
        .expect("integration test timed out")
}

#[tokio::test]
async fn rest_roundtrip() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    with_timeout(async {
        let supervisor = spawn_with(&python, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let client = supervisor.client.clone();

        let sid = client.create_session(".").await.expect("create session");
        client
            .post_message(&sid, "ping", "plan")
            .await
            .expect("post message");
        let cost = client.cost(&sid).await.expect("read cost");
        assert_eq!(cost.turns, 0);
        client.delete_session(&sid).await.expect("delete session");

        supervisor.shutdown().await;
    })
    .await;
}

#[tokio::test]
async fn auth_bad_token() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    with_timeout(async {
        let supervisor = spawn_with(&python, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let bad_client =
            VossClient::new(supervisor.client.base_url().to_string(), "bad-token".into());

        let error = bad_client.create_session(".").await.unwrap_err();
        assert!(matches!(error, VossError::HttpStatus { status: 401, .. }));

        supervisor.shutdown().await;
    })
    .await;
}

#[tokio::test]
async fn post_while_busy() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    with_timeout(async {
        let supervisor = spawn_with(&python, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let client = supervisor.client.clone();

        let sid = client.create_session(".").await.expect("create session");
        client
            .post_message(&sid, "first", "plan")
            .await
            .expect("post first message");

        let error = client
            .post_message(&sid, "second", "plan")
            .await
            .unwrap_err();
        assert!(matches!(error, VossError::HttpStatus { status: 409, .. }));

        supervisor.shutdown().await;
    })
    .await;
}

#[tokio::test]
async fn sse_event_sequence() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    with_timeout(async {
        let supervisor = spawn_with(&python, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let client = supervisor.client.clone();

        let sid = client.create_session(".").await.expect("create session");
        client
            .post_message(&sid, "ping", "plan")
            .await
            .expect("post message");

        let events: Vec<AgentEvent> = event_stream(client, sid)
            .collect::<Vec<Result<AgentEvent, VossError>>>()
            .await
            .into_iter()
            .collect::<Result<Vec<_>, _>>()
            .expect("collect events");

        assert!(matches!(
            events.first(),
            Some(AgentEvent::ServerConnected(_))
        ));
        assert!(events
            .iter()
            .any(|event| matches!(event, AgentEvent::StreamDelta(_))));
        assert!(matches!(events.last(), Some(AgentEvent::SessionIdle(_))));

        supervisor.shutdown().await;
    })
    .await;
}

#[tokio::test]
async fn sse_drop_midstream() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    with_timeout(async {
        let supervisor = spawn_with(&python, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let client = supervisor.client.clone();

        let sid = client.create_session(".").await.expect("create session");
        let mut stream = Box::pin(event_stream(client.clone(), sid.clone()));
        client
            .post_message(&sid, "ping", "plan")
            .await
            .expect("post message");

        assert!(matches!(
            stream.next().await,
            Some(Ok(AgentEvent::ServerConnected(_)))
        ));
        drop(stream);

        let _ = client.cost(&sid).await.expect("server remains responsive");
        supervisor.shutdown().await;
    })
    .await;
}

#[tokio::test]
async fn supervisor_no_orphan() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    with_timeout(async {
        let supervisor = spawn_with(&python, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let pid = supervisor.pid();
        supervisor.shutdown().await;

        #[cfg(unix)]
        if let Some(pid) = pid {
            for _ in 0..10 {
                if !pid_is_alive(pid) {
                    return;
                }
                tokio::time::sleep(Duration::from_millis(100)).await;
            }
            panic!("orphan voss serve process still alive: pid {pid}");
        }

        #[cfg(not(unix))]
        {
            eprintln!("skipping orphan pid assertion on non-unix platform");
        }
    })
    .await;
}

// FAKE_TURN emits no permission.updated event (app.py 166-178). A hermetic
// permission test needs a future VOSS_SERVE_FAKE_TURN_PERMISSION server seam.
#[tokio::test]
async fn permission_roundtrip() {
    let Some(python) = venv_python() else {
        eprintln!("skipping: .venv/bin/python not found");
        return;
    };

    with_timeout(async {
        let supervisor = spawn_with(&python, &[]).await.expect("server should start");
        let client = supervisor.client.clone();

        let sid = match client.create_session(".").await {
            Ok(sid) => sid,
            Err(error) => {
                eprintln!("skipping permission roundtrip: no provider credentials ({error})");
                supervisor.shutdown().await;
                return;
            }
        };

        let mut stream = Box::pin(event_stream(client.clone(), sid.clone()));
        client
            .post_message(
                &sid,
                "Use a shell command to print the current working directory.",
                "plan",
            )
            .await
            .expect("post permission-triggering message");

        let mut permission_id = None;
        for _ in 0..64 {
            match stream.next().await {
                Some(Ok(AgentEvent::PermissionUpdated(event))) => {
                    permission_id = Some(event.id);
                    break;
                }
                Some(Ok(AgentEvent::SessionIdle(_))) | None => break,
                Some(Ok(_)) => {}
                Some(Err(error)) => panic!("stream error before permission event: {error}"),
            }
        }

        let Some(permission_id) = permission_id else {
            eprintln!("skipping permission roundtrip: real turn produced no permission gate");
            supervisor.shutdown().await;
            return;
        };

        client
            .permission_reply(&sid, &permission_id, "a")
            .await
            .expect("allow permission reply");

        let mut saw_tool = false;
        for _ in 0..64 {
            match stream.next().await {
                Some(Ok(AgentEvent::ToolEvent(event))) => {
                    saw_tool = matches!(event.state.as_str(), "ok" | "pending");
                    break;
                }
                Some(Ok(AgentEvent::SessionIdle(_))) | None => break,
                Some(Ok(_)) => {}
                Some(Err(error)) => panic!("stream error after permission reply: {error}"),
            }
        }

        assert!(saw_tool, "allow reply should let the tool proceed");
        supervisor.shutdown().await;
    })
    .await;
}

#[cfg(unix)]
fn pid_is_alive(pid: u32) -> bool {
    Command::new("kill")
        .args(["-0", &pid.to_string()])
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}
