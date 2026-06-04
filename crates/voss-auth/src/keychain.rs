//! macOS Keychain access for Anthropic OAuth.
//!
//! Stores a single generic-password item under service `Claude Code-credentials`,
//! account = `$USER`. Payload is a JSON blob in the same shape Claude Code
//! itself writes.
//!
//! For tests, the service name can be overridden via `$VOSS_KEYCHAIN_SERVICE`
//! to avoid touching the user's real credentials.

#[cfg_attr(not(target_os = "macos"), allow(unused_imports))]
use crate::anthropic::{AnthropicOAuthCreds, KEYCHAIN_SERVICE};

#[cfg(target_os = "macos")]
fn service() -> String {
    std::env::var("VOSS_KEYCHAIN_SERVICE").unwrap_or_else(|_| KEYCHAIN_SERVICE.to_string())
}

#[cfg(target_os = "macos")]
fn account() -> String {
    std::env::var("USER").unwrap_or_else(|_| "voss".to_string())
}

/// When set to "1", all Keychain calls short-circuit. Tests use this to keep
/// macOS from popping authentication dialogs during automated runs.
#[cfg(target_os = "macos")]
fn disabled() -> bool {
    std::env::var("VOSS_DISABLE_KEYCHAIN")
        .map(|v| v == "1")
        .unwrap_or(false)
}

#[cfg(target_os = "macos")]
pub fn read_anthropic() -> Option<AnthropicOAuthCreds> {
    use security_framework::passwords::get_generic_password;

    if disabled() {
        return None;
    }
    let bytes = get_generic_password(&service(), &account()).ok()?;
    parse_blob(&bytes)
}

#[cfg(target_os = "macos")]
pub fn write_anthropic(creds: &AnthropicOAuthCreds) -> std::io::Result<()> {
    use security_framework::passwords::set_generic_password;

    if disabled() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::Unsupported,
            "keychain disabled by VOSS_DISABLE_KEYCHAIN",
        ));
    }
    let bytes = serde_json::to_vec(&serialize_blob(creds))?;
    set_generic_password(&service(), &account(), &bytes)
        .map_err(|e| std::io::Error::other(e.to_string()))
}

#[cfg(target_os = "macos")]
pub fn delete_anthropic() -> std::io::Result<()> {
    use security_framework::passwords::delete_generic_password;
    if disabled() {
        return Ok(());
    }
    delete_generic_password(&service(), &account())
        .map_err(|e| std::io::Error::other(e.to_string()))
}

#[cfg(not(target_os = "macos"))]
pub fn read_anthropic() -> Option<AnthropicOAuthCreds> {
    None
}

#[cfg(not(target_os = "macos"))]
pub fn write_anthropic(_creds: &AnthropicOAuthCreds) -> std::io::Result<()> {
    Err(std::io::Error::new(
        std::io::ErrorKind::Unsupported,
        "keychain only on macOS",
    ))
}

#[cfg(not(target_os = "macos"))]
pub fn delete_anthropic() -> std::io::Result<()> {
    Ok(())
}

#[cfg(target_os = "macos")]
fn parse_blob(bytes: &[u8]) -> Option<AnthropicOAuthCreds> {
    let blob: serde_json::Value = serde_json::from_slice(bytes).ok()?;
    let oauth = blob.get("claudeAiOauth")?.as_object()?;
    let access = oauth.get("accessToken")?.as_str()?.to_string();
    let refresh = oauth.get("refreshToken")?.as_str()?.to_string();
    let expires_at = oauth.get("expiresAt").and_then(|v| v.as_i64()).unwrap_or(0);
    let subscription_type = oauth
        .get("subscriptionType")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    Some(AnthropicOAuthCreds {
        access_token: access,
        refresh_token: refresh,
        expires_at_ms: expires_at,
        subscription_type,
    })
}

#[cfg(target_os = "macos")]
fn serialize_blob(creds: &AnthropicOAuthCreds) -> serde_json::Value {
    serde_json::json!({
        "claudeAiOauth": {
            "accessToken": creds.access_token,
            "refreshToken": creds.refresh_token,
            "expiresAt": creds.expires_at_ms,
            "subscriptionType": creds.subscription_type,
        }
    })
}
