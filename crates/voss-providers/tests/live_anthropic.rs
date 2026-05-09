//! Live smoke against real Anthropic via Claude Code OAuth.
//!
//! Opt-in only. Set `VOSS_LIVE_SMOKES=1` to run. Default skip in CI.

use voss_providers::{AnthropicOAuthProvider, CompleteRequest, Message, ModelProvider};

fn live_enabled() -> bool {
    std::env::var("VOSS_LIVE_SMOKES")
        .map(|v| v == "1")
        .unwrap_or(false)
}

#[tokio::test]
async fn live_anthropic_returns_text() {
    if !live_enabled() {
        eprintln!("skipping live_anthropic: set VOSS_LIVE_SMOKES=1 to run");
        return;
    }
    let creds = voss_auth::load_anthropic_oauth()
        .expect("Claude OAuth creds required for live smoke (run `claude login`)");
    let mut provider = AnthropicOAuthProvider::new(creds);
    let req = CompleteRequest {
        messages: vec![Message {
            role: "user".into(),
            content: "what is 2+2? answer with the digit only.".into(),
        }],
        model: "claude-sonnet-4-5".into(),
        temperature: 0.0,
        max_tokens: Some(64),
        response_schema: None,
        response_schema_name: None,
        tools: None,
    };
    let resp = provider
        .complete(req)
        .await
        .expect("live anthropic call failed");
    assert!(
        !resp.text.trim().is_empty(),
        "expected non-empty text, got empty"
    );
    assert!(
        resp.text.contains('4'),
        "expected '4' in answer, got: {}",
        resp.text
    );
}
