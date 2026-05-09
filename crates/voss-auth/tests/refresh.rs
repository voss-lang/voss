use std::sync::Mutex;

use voss_auth::{
    refresh::{refresh_anthropic, refresh_codex},
    AnthropicOAuthCreds, CodexCreds,
};
use wiremock::matchers::{body_json, body_string_contains, header, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

static ENV_LOCK: Mutex<()> = Mutex::new(());

fn with_temp_home<F: FnOnce()>(f: F) {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().expect("tempdir");
    let prev_home = std::env::var_os("HOME");
    let prev_dis = std::env::var_os("VOSS_DISABLE_KEYCHAIN");
    std::env::set_var("HOME", tmp.path());
    // Block macOS Keychain access entirely — refresh paths must fall through
    // to the file_store. Without this, set_generic_password may prompt the
    // user the first time it runs in a test environment.
    std::env::set_var("VOSS_DISABLE_KEYCHAIN", "1");
    let res = std::panic::catch_unwind(std::panic::AssertUnwindSafe(f));
    match prev_home {
        Some(p) => std::env::set_var("HOME", p),
        None => std::env::remove_var("HOME"),
    }
    match prev_dis {
        Some(p) => std::env::set_var("VOSS_DISABLE_KEYCHAIN", p),
        None => std::env::remove_var("VOSS_DISABLE_KEYCHAIN"),
    }
    if let Err(e) = res {
        std::panic::resume_unwind(e);
    }
}

#[test]
fn refresh_anthropic_request_body() {
    with_temp_home(|| {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        rt.block_on(async {
            let server = MockServer::start().await;
            Mock::given(method("POST"))
                .and(path("/v1/oauth/token"))
                .and(header("content-type", "application/json"))
                .and(body_json(serde_json::json!({
                    "grant_type": "refresh_token",
                    "refresh_token": "OLD_RT",
                    "client_id": "9d1c250a-e61b-44d9-88ed-5944d1962f5e",
                })))
                .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
                    "access_token": "NEW_AT",
                    "refresh_token": "NEW_RT",
                    "expires_in": 3600,
                })))
                .expect(1)
                .mount(&server)
                .await;

            let mut creds = AnthropicOAuthCreds {
                access_token: "OLD_AT".into(),
                refresh_token: "OLD_RT".into(),
                expires_at_ms: 0,
                subscription_type: "max".into(),
            };
            let url = format!("{}/v1/oauth/token", server.uri());
            let client = reqwest::Client::new();
            refresh_anthropic(&mut creds, &client, Some(&url))
                .await
                .expect("refresh ok");
            assert_eq!(creds.access_token, "NEW_AT");
            assert_eq!(creds.refresh_token, "NEW_RT");
            assert!(creds.expires_at_ms > 0);
        });
    });
}

#[test]
fn refresh_codex_request_form() {
    with_temp_home(|| {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        rt.block_on(async {
            let server = MockServer::start().await;
            Mock::given(method("POST"))
                .and(path("/oauth/token"))
                .and(body_string_contains(
                    "client_id=app_EMoamEEZ73f0CkXaXp7hrann",
                ))
                .and(body_string_contains("grant_type=refresh_token"))
                .and(body_string_contains("refresh_token=OLD_RT"))
                .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
                    "access_token": "NEW_AT",
                    "refresh_token": "NEW_RT",
                })))
                .expect(1)
                .mount(&server)
                .await;

            let mut creds = CodexCreds {
                api_key: None,
                access_token: Some("OLD_AT".into()),
                refresh_token: Some("OLD_RT".into()),
                account_id: Some("acct".into()),
                auth_mode: "ChatGPT".into(),
            };
            let url = format!("{}/oauth/token", server.uri());
            let client = reqwest::Client::new();
            refresh_codex(&mut creds, &client, Some(&url))
                .await
                .expect("refresh ok");
            assert_eq!(creds.access_token.as_deref(), Some("NEW_AT"));
            assert_eq!(creds.refresh_token.as_deref(), Some("NEW_RT"));
        });
    });
}
