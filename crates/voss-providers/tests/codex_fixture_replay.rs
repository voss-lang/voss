use std::path::PathBuf;

use serde_json::Value;
use voss_auth::CodexCreds;
use voss_providers::{CompleteRequest, Message, ModelProvider, OpenAIOAuthProvider};
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join(".planning/codex-fixtures/codex-cli-chatgpt-success.json")
}

fn last_user_message(body: &Value) -> String {
    body.get("input")
        .and_then(|v| v.as_array())
        .and_then(|items| {
            items
                .iter()
                .rev()
                .find(|item| item.get("role") == Some(&Value::String("user".into())))
        })
        .and_then(|item| item.get("content"))
        .and_then(|v| v.as_array())
        .and_then(|content| content.first())
        .and_then(|c| c.get("text"))
        .and_then(|v| v.as_str())
        .unwrap_or("ping")
        .to_string()
}

#[tokio::test]
async fn replay_codex_fixture_projection() {
    let fixture_file = fixture_path();
    assert!(
        fixture_file.exists(),
        "no fixture at {}; run .planning/CODEX-OAUTH-PLAN.md Phase A first",
        fixture_file.display()
    );
    let fixture: Value =
        serde_json::from_slice(&std::fs::read(&fixture_file).expect("read fixture"))
            .expect("fixture json");
    let captured = fixture
        .get("request")
        .and_then(|v| v.get("body"))
        .expect("fixture request.body");
    assert_eq!(captured.get("stream"), Some(&Value::Bool(true)));
    assert_eq!(captured.get("store"), Some(&Value::Bool(false)));
    assert_eq!(
        captured.get("parallel_tool_calls"),
        Some(&Value::Bool(true))
    );
    assert!(captured.get("prompt_cache_key").is_some());
    assert!(captured.get("reasoning").is_some());
    assert!(
        captured
            .get("tools")
            .and_then(|v| v.as_array())
            .unwrap()
            .len()
            > 1
    );

    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/backend-api/codex/responses"))
        .respond_with(
            ResponseTemplate::new(200)
                .append_header("content-type", "text/event-stream")
                .set_body_string(fixture["response"]["body"].as_str().unwrap()),
        )
        .mount(&server)
        .await;

    let creds = CodexCreds {
        api_key: None,
        access_token: Some("test-token".into()),
        refresh_token: Some("test-refresh".into()),
        account_id: Some("acct_test".into()),
        auth_mode: "chatgpt".into(),
    };
    let mut provider = OpenAIOAuthProvider::new(creds)
        .with_base_url(format!("{}/backend-api/codex", server.uri()));
    let req = CompleteRequest {
        messages: vec![Message {
            role: "user".into(),
            content: last_user_message(captured),
        }],
        model: captured["model"].as_str().unwrap().to_string(),
        temperature: 1.0,
        max_tokens: None,
        response_schema: None,
        response_schema_name: None,
        tools: None,
    };

    let resp = provider
        .complete(req)
        .await
        .expect("fixture response parses");
    assert!(resp.text.contains("fixture-ping"));

    let received = server.received_requests().await.expect("requests");
    assert_eq!(received.len(), 1);
    let sent = &received[0];
    assert_eq!(
        sent.headers.get("originator").unwrap().to_str().unwrap(),
        "codex_cli_rs"
    );
    assert_eq!(
        sent.headers.get("OpenAI-Beta").unwrap().to_str().unwrap(),
        "responses=v1"
    );
    assert_eq!(
        sent.headers
            .get("chatgpt-account-id")
            .unwrap()
            .to_str()
            .unwrap(),
        "acct_test"
    );
    let actual: Value = serde_json::from_slice(&sent.body).expect("actual body json");
    assert_eq!(actual["model"], captured["model"]);
    assert_eq!(actual["store"], captured["store"]);
    assert_eq!(actual["stream"], captured["stream"]);
    assert_eq!(
        actual["parallel_tool_calls"],
        captured["parallel_tool_calls"]
    );
    assert!(actual.get("prompt_cache_key").is_some());
    assert!(actual.get("reasoning").is_some());
    assert!(actual["tools"]
        .as_array()
        .unwrap()
        .iter()
        .any(|tool| tool.get("name").and_then(|v| v.as_str()) == Some("local_shell")));
}
