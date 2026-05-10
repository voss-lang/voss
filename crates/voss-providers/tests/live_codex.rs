use voss_providers::{CompleteRequest, Message, ModelProvider, OpenAIOAuthProvider};

fn live_enabled() -> bool {
    std::env::var("VOSS_LIVE_SMOKES")
        .map(|v| v == "1")
        .unwrap_or(false)
}

#[tokio::test]
async fn live_codex_returns_text() {
    if !live_enabled() {
        eprintln!("skipping: set VOSS_LIVE_SMOKES=1 to run");
        return;
    }
    let creds = voss_auth::load_codex().expect("Codex creds required (run codex login)");
    if !creds.has_oauth() && creds.api_key.is_none() {
        eprintln!("skipping: Codex creds present but no OAuth or api_key");
        return;
    }
    let mut provider = OpenAIOAuthProvider::new(creds);
    let req = CompleteRequest {
        messages: vec![Message {
            role: "user".into(),
            content: "what is 2+2? answer with the digit only.".into(),
        }],
        model: "gpt-5".into(),
        temperature: 0.0,
        max_tokens: Some(64),
        response_schema: None,
        response_schema_name: None,
        tools: None,
    };
    let resp = provider
        .complete(req)
        .await
        .expect("live codex call failed");
    assert!(!resp.text.trim().is_empty(), "expected non-empty response");
}
