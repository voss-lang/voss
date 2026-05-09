use voss_auth::AnthropicOAuthCreds;
use voss_providers::{AnthropicOAuthProvider, CompleteRequest, Message, ModelProvider};
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

fn fake_creds() -> AnthropicOAuthCreds {
    AnthropicOAuthCreds {
        access_token: "test-access".into(),
        refresh_token: "test-refresh".into(),
        expires_at_ms: i64::MAX,
        subscription_type: "max".into(),
    }
}

#[tokio::test]
async fn anthropic_request_body_with_response_schema() {
    let server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/v1/messages"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "id": "msg_1",
            "model": "claude-sonnet-4-5",
            "content": [{
                "type": "tool_use",
                "input": {
                    "rationale": "r",
                    "steps": [],
                    "confidence": 0.9,
                    "final_when_done": "done",
                }
            }],
            "usage": {"input_tokens": 10, "output_tokens": 5}
        })))
        .mount(&server)
        .await;

    let mut provider = AnthropicOAuthProvider::new(fake_creds()).with_base_url(server.uri());
    let req = CompleteRequest {
        messages: vec![
            Message {
                role: "system".into(),
                content: "Be terse.".into(),
            },
            Message {
                role: "user".into(),
                content: "what is 2+2?".into(),
            },
        ],
        model: "claude-sonnet-4-5".into(),
        temperature: 0.2,
        max_tokens: Some(1024),
        response_schema: Some(serde_json::json!({
            "type": "object",
            "properties": {"x": {"type": "number"}}
        })),
        response_schema_name: Some("Plan".into()),
        tools: None,
    };
    let _resp = provider.complete(req).await.expect("complete ok");

    let received = server.received_requests().await.expect("requests recorded");
    assert_eq!(received.len(), 1, "expected 1 request, got {}", received.len());
    let body: serde_json::Value =
        serde_json::from_slice(&received[0].body).expect("body is JSON");

    insta::assert_json_snapshot!(body);
}
