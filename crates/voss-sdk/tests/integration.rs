use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

use futures_util::StreamExt;
use voss_sdk::error::VossError;
use voss_sdk::types::events::AgentEvent;
use voss_sdk::types::rest::RoleSpec;
use voss_sdk::{event_stream, LaunchOptions, Supervisor, VossClient};

static SERVER_TEST_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

fn venv_voss() -> Option<PathBuf> {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.venv/bin/voss");
    p.exists().then_some(p)
}

async fn spawn_with(voss: &Path, env: &[(&str, &str)]) -> Result<Supervisor, VossError> {
    Supervisor::spawn(LaunchOptions {
        executable: Some(voss.to_path_buf()),
        env: env
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
        ..Default::default()
    })
    .await
}

async fn with_timeout<F, T>(future: F) -> T
where
    F: std::future::Future<Output = T>,
{
    // Must exceed the supervisor's 60s handshake budget (a cold litellm import
    // can take ~45s) so the supervisor's richer error surfaces instead of this
    tokio::time::timeout(Duration::from_secs(75), future)
        .await
        .expect("integration test timed out")
}

#[tokio::test]
async fn rest_roundtrip() {
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[("VOSS_SERVE_FAKE_TURN", "1")])
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
async fn swarm_roster_splits_native_from_cli_roles() {
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let client = supervisor.client.clone();

        let roster = [
            RoleSpec::native("coordinator"),
            RoleSpec::cli("builder1", "claude"),
        ];
        let swarm = client
            .create_swarm("tidy the docs", ".", 1, &roster)
            .await
            .expect("create swarm");

        assert!(!swarm.id.is_empty());
        let native = swarm
            .sessions
            .iter()
            .find(|r| r.role == "coordinator")
            .expect("coordinator in the roster");
        assert!(!native.pending, "a native role runs in the harness");
        assert!(
            native.session_id.is_some(),
            "a native role carries its session"
        );

        let cli = swarm
            .sessions
            .iter()
            .find(|r| r.role == "builder1")
            .expect("builder1 in the roster");
        assert!(cli.pending, "a CLI role is left for the host to spawn");
        assert_eq!(cli.session_id, None);
        assert_eq!(cli.agent, "claude");

        supervisor.shutdown().await;
    })
    .await;
}

#[tokio::test]
async fn swarm_is_readable_and_runnable_by_id() {
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[("VOSS_SERVE_FAKE_TURN", "1")])
            .await
            .expect("server should start");
        let client = supervisor.client.clone();

        let roster = [RoleSpec::cli("builder1", "claude")];
        let created = client
            .create_swarm("tidy the docs", ".", 1, &roster)
            .await
            .expect("create swarm");

        let swarm = client.swarm(&created.id).await.expect("read swarm");
        assert_eq!(swarm.id, created.id);
        assert_eq!(swarm.goal, "tidy the docs");
        assert_eq!(
            swarm
                .roster
                .iter()
                .map(|r| r.name.as_str())
                .collect::<Vec<_>>(),
            ["builder1"]
        );
        assert!(swarm.tasks.is_empty(), "a fresh swarm has no plan yet");

        client.run_swarm(&created.id).await.expect("run swarm");
        assert_eq!(
            client
                .swarm(&created.id)
                .await
                .expect("read swarm again")
                .id,
            created.id
        );

        let missing = client.swarm("not-a-swarm").await.unwrap_err();
        assert!(matches!(missing, VossError::HttpStatus { status: 404, .. }));

        supervisor.shutdown().await;
    })
    .await;
}

#[tokio::test]
async fn auth_bad_token() {
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[("VOSS_SERVE_FAKE_TURN", "1")])
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
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[]).await.expect("server should start");
        let client = supervisor.client.clone();

        let sid = match client.create_session(".").await {
            Ok(sid) => sid,
            Err(error) => {
                eprintln!("skipping busy-session check: no provider credentials ({error})");
                supervisor.shutdown().await;
                return;
            }
        };
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
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[("VOSS_SERVE_FAKE_TURN", "1")])
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
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[("VOSS_SERVE_FAKE_TURN", "1")])
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
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[("VOSS_SERVE_FAKE_TURN", "1")])
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

// FAKE_TURN emits no permission.updated event (app.py 166. A hermetic
// permission test needs a future VOSS_SERVE_FAKE_TURN_PERMISSION server seam.
#[tokio::test]
async fn permission_roundtrip() {
    let Some(voss) = venv_voss() else {
        eprintln!("skipping: .venv/bin/voss not found");
        return;
    };

    let _guard = SERVER_TEST_LOCK.lock().await;
    with_timeout(async {
        let supervisor = spawn_with(&voss, &[]).await.expect("server should start");
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
