use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use voss_auth::AnthropicOAuthCreds;
use voss_providers::{AnthropicOAuthProvider, CompleteRequest, Message, ModelProvider};
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, Request, Respond, ResponseTemplate};

struct FlakyMessages {
    counter: Arc<AtomicUsize>,
}

impl Respond for FlakyMessages {
    fn respond(&self, _req: &Request) -> ResponseTemplate {
        let n = self.counter.fetch_add(1, Ordering::SeqCst);
        if n == 0 {
            ResponseTemplate::new(401).set_body_string("auth expired")
        } else {
            ResponseTemplate::new(200).set_body_json(serde_json::json!({
                "id": "msg_1",
                "model": "claude-sonnet-4-5",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }))
        }
    }
}

#[tokio::test]
async fn refresh_on_401_retries_once() {
    let server = MockServer::start().await;
    let counter = Arc::new(AtomicUsize::new(0));

    // Token endpoint mock — returns refreshed creds.
    Mock::given(method("POST"))
        .and(path("/v1/oauth/token"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "access_token": "fresh",
            "refresh_token": "fresh-rt",
            "expires_in": 3600,
        })))
        .mount(&server)
        .await;

    // Messages: 401 first call, 200 second.
    Mock::given(method("POST"))
        .and(path("/v1/messages"))
        .respond_with(FlakyMessages {
            counter: counter.clone(),
        })
        .mount(&server)
        .await;

    // Block keychain writes that refresh_anthropic would attempt.
    std::env::set_var("VOSS_DISABLE_KEYCHAIN", "1");
    let tmp = tempfile::tempdir().expect("tmpdir");
    std::env::set_var("HOME", tmp.path());

    let creds = AnthropicOAuthCreds {
        access_token: "stale-access".into(),
        refresh_token: "stale-refresh".into(),
        expires_at_ms: i64::MAX, // do not preempt-refresh; force the 401 path.
        subscription_type: "max".into(),
    };
    let mut provider = AnthropicOAuthProvider::new(creds)
        .with_base_url(server.uri())
        .with_token_url_override(format!("{}/v1/oauth/token", server.uri()));

    let req = CompleteRequest {
        messages: vec![Message {
            role: "user".into(),
            content: "ping".into(),
        }],
        model: "claude-sonnet-4-5".into(),
        temperature: 0.0,
        max_tokens: Some(8),
        response_schema: None,
        response_schema_name: None,
        tools: None,
    };
    let resp = provider
        .complete(req)
        .await
        .expect("expected eventual success after refresh");
    assert_eq!(resp.text, "ok");

    assert_eq!(
        counter.load(Ordering::SeqCst),
        2,
        "expected 2 calls to /v1/messages (401 then 200)"
    );

    std::env::remove_var("VOSS_DISABLE_KEYCHAIN");
}
