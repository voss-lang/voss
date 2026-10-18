use std::io::{Read, Write};
use std::net::TcpListener;
use voss_sdk::{VossClient, oauth::Preflight};

fn serve(body: serde_json::Value) -> (VossClient, std::thread::JoinHandle<String>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap();
    let worker = std::thread::spawn(move || {
        let (mut socket, _) = listener.accept().unwrap();
        socket.set_read_timeout(Some(std::time::Duration::from_secs(5))).unwrap();
        let mut bytes = Vec::new();
        let mut buffer = [0; 1024];
        loop {
            let count = socket.read(&mut buffer).unwrap();
            assert!(count > 0);
            bytes.extend_from_slice(&buffer[..count]);
            if let Some(end) = bytes.windows(4).position(|w| w == b"\r\n\r\n") {
                let headers = String::from_utf8_lossy(&bytes[..end]).to_lowercase();
                let size = headers.lines().find_map(|line| line.strip_prefix("content-length: "))
                    .map(|value| value.parse::<usize>().unwrap()).unwrap_or(0);
                if bytes.len() >= end + 4 + size { break; }
            }
        }
        let request = String::from_utf8(bytes).unwrap();
        assert!(request.to_lowercase().contains("authorization: bearer synthetic-transport"));
        let body = body.to_string();
        write!(socket, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len()).unwrap();
        request
    });
    (VossClient::new(format!("http://{address}"), "synthetic-transport".into()), worker)
}

fn unavailable() -> serde_json::Value {
    serde_json::json!({"v":1,"harness":"codex","provider":"openai","model":"gpt-6-astra",
        "cli_installed":true,"available":false,"code":"oauth_missing","message":"Sign in again",
        "login_command":"codex login","checked_at":"2026-10-17T00:00:00Z","check_scope":"local_metadata",
        "account_alias":null,"account_selection":false})
}

#[tokio::test]
async fn unavailable_launch_is_data_and_preserves_explicit_selection() {
    let (client, worker) = serve(serde_json::json!({"v":1,"status":"unavailable","availability":unavailable()}));
    let result = client.create_oauth_session("/synthetic", "codex", "gpt-6-astra").await.unwrap();
    assert!(result.id.is_none());
    assert_eq!(result.availability.unwrap().code, "oauth_missing");
    let request = worker.join().unwrap();
    assert!(request.starts_with("POST /session "));
    let body: serde_json::Value = serde_json::from_str(request.split("\r\n\r\n").nth(1).unwrap()).unwrap();
    assert_eq!(body, serde_json::json!({"cwd":"/synthetic","auth":"codex","model":"gpt-6-astra"}));
}

#[tokio::test]
async fn preflight_cannot_accept_another_harness_or_protocol() {
    for change in [serde_json::json!({"harness":"claude"}), serde_json::json!({"v":2})] {
        let mut report = unavailable();
        for (key, value) in change.as_object().unwrap() { report[key] = value.clone(); }
        let (client, worker) = serve(report);
        assert!(client.harness_preflight(&Preflight { harness:"codex".into(), model:"gpt-6-astra".into(), account_alias:None }).await.is_err());
        worker.join().unwrap();
    }
}

#[tokio::test]
async fn login_recheck_does_not_submit_work() {
    let (client, worker) = serve(serde_json::json!({"v":1,"harnesses":[unavailable()],"selected_harness":"codex"}));
    let catalog = client.harness_catalog().await.unwrap();
    assert!(!catalog.harnesses[0].available);
    assert!(worker.join().unwrap().starts_with("GET /harnesses "));
}

#[tokio::test]
async fn swarm_start_preserves_unavailable_acknowledgement() {
    let (client, worker) = serve(serde_json::json!({"v":1,"status":"unavailable","availability":unavailable()}));
    let ack = client.start_swarm("synthetic-swarm").await.unwrap();
    assert_eq!(ack.status, "unavailable");
    assert!(ack.run_id.is_none());
    assert_eq!(ack.availability.unwrap().harness, "codex");
    assert!(worker.join().unwrap().starts_with("POST /swarm/synthetic-swarm/run "));
}
