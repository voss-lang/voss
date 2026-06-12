//! E4 Rust consumer subprogram: public-API-only (VossClient::new + event_stream
//! + permission_reply). The Python eval runner owns the serve lifecycle and
//! passes coordinates via env — this example never spawns the server itself.

use futures_util::StreamExt;
use voss_sdk::types::events::AgentEvent;
use voss_sdk::{event_stream, VossClient};

fn event_type(ev: &AgentEvent) -> String {
    serde_json::to_value(ev)
        .ok()
        .and_then(|v| v.get("type").and_then(|t| t.as_str()).map(str::to_string))
        .unwrap_or_else(|| "unknown".into())
}

#[tokio::main]
async fn main() {
    let Ok(base) = std::env::var("VOSS_BASE_URL") else {
        eprintln!("VOSS_BASE_URL required");
        std::process::exit(2);
    };
    let token = std::env::var("VOSS_TOKEN").unwrap_or_default();
    let cwd = std::env::var("VOSS_CWD").unwrap_or_else(|_| ".".into());
    let prompt = std::env::var("VOSS_PROMPT").unwrap_or_default();
    let mode = std::env::var("VOSS_MODE").unwrap_or_else(|_| "plan".into());

    let client = VossClient::new(base, token);
    let sid = client.create_session(&cwd).await.expect("create_session");
    client
        .post_message(&sid, &prompt, &mode)
        .await
        .expect("post_message");

    let mut final_text = String::new();
    let mut saw_permission_gate = false;
    let mut event_types_seen: Vec<String> = Vec::new();

    let mut stream = std::pin::pin!(event_stream(client.clone(), sid.clone()));
    while let Some(item) = stream.next().await {
        let ev = match item {
            Ok(ev) => ev,
            Err(error) => {
                eprintln!("stream error: {error}");
                break;
            }
        };
        event_types_seen.push(event_type(&ev));
        match ev {
            AgentEvent::PermissionUpdated(e) => {
                saw_permission_gate = true;
                client
                    .permission_reply(&sid, &e.id, "a")
                    .await
                    .expect("permission_reply");
            }
            AgentEvent::FinalEvent(e) => final_text = e.text,
            AgentEvent::SessionIdle(_) => break,
            _ => {}
        }
    }

    let cost_usd = client.cost(&sid).await.map(|c| c.total_usd).unwrap_or(0.0);
    println!(
        "{}",
        serde_json::json!({
            "surface": "sdk:rust",
            "session_id": sid,
            "final": final_text,
            "saw_permission_gate": saw_permission_gate,
            "cost_usd": cost_usd,
            "event_types_seen": event_types_seen,
        })
    );
}
