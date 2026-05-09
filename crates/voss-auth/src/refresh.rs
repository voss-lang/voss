//! OAuth refresh paths for Anthropic (JSON body) and Codex (form-encoded body).
//!
//! Wire shape mirrors `voss/harness/auth.py` lines 147-251 so existing
//! recorded fixtures and back-end expectations remain valid.

use crate::anthropic::{AnthropicOAuthCreds, ANTHROPIC_TOKEN_URL, CLAUDE_CODE_CLIENT_ID};
use crate::codex::{CodexCreds, CODEX_CLIENT_ID, OPENAI_TOKEN_URL};
use crate::{file_store, keychain};

pub async fn refresh_anthropic(
    creds: &mut AnthropicOAuthCreds,
    client: &reqwest::Client,
    token_url_override: Option<&str>,
) -> anyhow::Result<()> {
    let url = token_url_override.unwrap_or(ANTHROPIC_TOKEN_URL);
    let body = serde_json::json!({
        "grant_type": "refresh_token",
        "refresh_token": creds.refresh_token,
        "client_id": CLAUDE_CODE_CLIENT_ID,
    });
    let resp = client
        .post(url)
        .header("content-type", "application/json")
        .json(&body)
        .send()
        .await?
        .error_for_status()?;
    let json: serde_json::Value = resp.json().await?;

    let now_ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_millis() as i64;

    creds.access_token = json
        .get("access_token")
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("missing access_token in response"))?
        .to_string();
    if let Some(rt) = json.get("refresh_token").and_then(|v| v.as_str()) {
        creds.refresh_token = rt.to_string();
    }
    let expires_in = json
        .get("expires_in")
        .and_then(|v| v.as_i64())
        .unwrap_or(3600);
    creds.expires_at_ms = now_ms + expires_in * 1000;

    // Persist: try Keychain on macOS, else file.
    if keychain::write_anthropic(creds).is_err() {
        file_store::write_anthropic(creds).ok();
    }
    Ok(())
}

pub async fn refresh_codex(
    creds: &mut CodexCreds,
    client: &reqwest::Client,
    token_url_override: Option<&str>,
) -> anyhow::Result<()> {
    let url = token_url_override.unwrap_or(OPENAI_TOKEN_URL);
    let rt = creds
        .refresh_token
        .clone()
        .ok_or_else(|| anyhow::anyhow!("no codex refresh_token"))?;
    let form = [
        ("grant_type", "refresh_token"),
        ("refresh_token", rt.as_str()),
        ("client_id", CODEX_CLIENT_ID),
    ];
    let resp = client
        .post(url)
        .form(&form)
        .send()
        .await?
        .error_for_status()?;
    let json: serde_json::Value = resp.json().await?;

    if let Some(at) = json.get("access_token").and_then(|v| v.as_str()) {
        creds.access_token = Some(at.to_string());
    }
    if let Some(rtn) = json.get("refresh_token").and_then(|v| v.as_str()) {
        creds.refresh_token = Some(rtn.to_string());
    }
    file_store::write_codex(creds).ok();
    Ok(())
}
