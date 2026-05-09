//! File-based credential store: `~/.claude/.credentials.json` (Anthropic) and
//! `~/.codex/auth.json` (Codex).
//!
//! Both readers and writers respect `$HOME` (via `dirs::home_dir`) so tests can
//! point to a `tempfile::TempDir`.

use std::path::PathBuf;

use crate::anthropic::AnthropicOAuthCreds;
use crate::codex::CodexCreds;

fn home() -> PathBuf {
    dirs::home_dir().unwrap_or_default()
}

fn anthropic_path() -> PathBuf {
    home().join(".claude").join(".credentials.json")
}

fn codex_path() -> PathBuf {
    home().join(".codex").join("auth.json")
}

pub fn read_anthropic() -> Option<AnthropicOAuthCreds> {
    let bytes = std::fs::read(anthropic_path()).ok()?;
    let blob: serde_json::Value = serde_json::from_slice(&bytes).ok()?;
    let oauth = blob.get("claudeAiOauth")?.as_object()?;
    let access = oauth.get("accessToken")?.as_str()?.to_string();
    let refresh = oauth.get("refreshToken")?.as_str()?.to_string();
    Some(AnthropicOAuthCreds {
        access_token: access,
        refresh_token: refresh,
        expires_at_ms: oauth
            .get("expiresAt")
            .and_then(|v| v.as_i64())
            .unwrap_or(0),
        subscription_type: oauth
            .get("subscriptionType")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
    })
}

pub fn write_anthropic(creds: &AnthropicOAuthCreds) -> std::io::Result<()> {
    let path = anthropic_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut blob = if path.exists() {
        serde_json::from_slice::<serde_json::Value>(&std::fs::read(&path)?)
            .unwrap_or_else(|_| serde_json::json!({}))
    } else {
        serde_json::json!({})
    };
    blob["claudeAiOauth"] = serde_json::json!({
        "accessToken": creds.access_token,
        "refreshToken": creds.refresh_token,
        "expiresAt": creds.expires_at_ms,
        "subscriptionType": creds.subscription_type,
    });
    let bytes = serde_json::to_vec_pretty(&blob)?;
    std::fs::write(&path, bytes)?;
    set_owner_only(&path)?;
    Ok(())
}

pub fn read_codex() -> Option<CodexCreds> {
    let bytes = std::fs::read(codex_path()).ok()?;
    let data: serde_json::Value = serde_json::from_slice(&bytes).ok()?;
    let tokens = data.get("tokens").and_then(|t| t.as_object());
    Some(CodexCreds {
        api_key: data
            .get("OPENAI_API_KEY")
            .and_then(|v| v.as_str())
            .map(String::from),
        access_token: tokens
            .and_then(|t| t.get("access_token"))
            .and_then(|v| v.as_str())
            .map(String::from),
        refresh_token: tokens
            .and_then(|t| t.get("refresh_token"))
            .and_then(|v| v.as_str())
            .map(String::from),
        account_id: tokens
            .and_then(|t| t.get("account_id"))
            .and_then(|v| v.as_str())
            .map(String::from),
        auth_mode: data
            .get("auth_mode")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
    })
}

pub fn write_codex(creds: &CodexCreds) -> std::io::Result<()> {
    let path = codex_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut data = if path.exists() {
        serde_json::from_slice::<serde_json::Value>(&std::fs::read(&path)?)
            .unwrap_or_else(|_| serde_json::json!({}))
    } else {
        serde_json::json!({})
    };
    if !data.is_object() {
        data = serde_json::json!({});
    }
    let obj = data.as_object_mut().expect("object");
    let tokens = obj
        .entry("tokens".to_string())
        .or_insert_with(|| serde_json::json!({}));
    if !tokens.is_object() {
        *tokens = serde_json::json!({});
    }
    let tobj = tokens.as_object_mut().expect("tokens object");
    if let Some(at) = &creds.access_token {
        tobj.insert("access_token".into(), serde_json::Value::String(at.clone()));
    }
    if let Some(rt) = &creds.refresh_token {
        tobj.insert(
            "refresh_token".into(),
            serde_json::Value::String(rt.clone()),
        );
    }
    if let Some(acct) = &creds.account_id {
        tobj.insert(
            "account_id".into(),
            serde_json::Value::String(acct.clone()),
        );
    }
    if let Some(k) = &creds.api_key {
        obj.insert("OPENAI_API_KEY".into(), serde_json::Value::String(k.clone()));
    }
    if !creds.auth_mode.is_empty() {
        obj.insert(
            "auth_mode".into(),
            serde_json::Value::String(creds.auth_mode.clone()),
        );
    }
    std::fs::write(&path, serde_json::to_vec_pretty(&data)?)?;
    set_owner_only(&path)?;
    Ok(())
}

#[cfg(unix)]
fn set_owner_only(path: &std::path::Path) -> std::io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600))
}

#[cfg(not(unix))]
fn set_owner_only(_path: &std::path::Path) -> std::io::Result<()> {
    Ok(())
}
