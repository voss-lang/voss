use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use voss_auth::CodexCreds;
use voss_providers::{CompleteRequest, Message, ModelProvider, OpenAIOAuthProvider};
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, Request, Respond, ResponseTemplate};

struct FlakyResponses {
    counter: Arc<AtomicUsize>,
}

impl Respond for FlakyResponses {
    fn respond(&self, _req: &Request) -> ResponseTemplate {
        let n = self.counter.fetch_add(1, Ordering::SeqCst);
        if n == 0 {
            ResponseTemplate::new(401).set_body_string("auth expired")
        } else {
            ResponseTemplate::new(200).set_body_json(serde_json::json!({
                "id": "resp_1",
                "model": "gpt-5",
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": "ok"}]
                }],
                "usage": {"input_tokens": 1, "output_tokens": 1}
            }))
        }
    }
}

#[tokio::test]
async fn refresh_on_401_retries_once() {
    let server = MockServer::start().await;
    let counter = Arc::new(AtomicUsize::new(0));

    Mock::given(method("POST"))
        .and(path("/oauth/token"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "access_token": "fresh",
            "refresh_token": "fresh-rt",
            "expires_in": 3600,
        })))
        .mount(&server)
        .await;

    Mock::given(method("POST"))
        .and(path("/backend-api/codex/responses"))
        .respond_with(FlakyResponses {
            counter: counter.clone(),
        })
        .mount(&server)
        .await;

    std::env::set_var("VOSS_DISABLE_KEYCHAIN", "1");
    let tmp = tempfile::tempdir().expect("tmpdir");
    std::env::set_var("HOME", tmp.path());

    let creds = CodexCreds {
        api_key: None,
        access_token: Some("stale-access".into()),
        refresh_token: Some("stale-refresh".into()),
        account_id: Some("acct_test".into()),
        auth_mode: "chatgpt".into(),
    };
    let mut provider = OpenAIOAuthProvider::new(creds)
        .with_base_url(format!("{}/backend-api/codex", server.uri()))
        .with_token_url(format!("{}/oauth/token", server.uri()));
    let req = CompleteRequest {
        messages: vec![Message {
            role: "user".into(),
            content: "ping".into(),
        }],
        model: "gpt-5".into(),
        temperature: 0.0,
        max_tokens: Some(8),
        response_schema: None,
        response_schema_name: None,
        tools: None,
    };
    let resp = provider.complete(req).await.expect("success after refresh");
    assert_eq!(resp.text, "ok");
    assert_eq!(
        counter.load(Ordering::SeqCst),
        2,
        "expected 2 calls to /responses (401 then 200)"
    );

    std::env::remove_var("VOSS_DISABLE_KEYCHAIN");
}
