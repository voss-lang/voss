//! Anthropic OAuth (Claude Code) types and constants.
//!
//! Verbatim port of the constants and shape from `voss/harness/auth.py`.

use serde::{Deserialize, Serialize};

pub const CLAUDE_CODE_CLIENT_ID: &str = "9d1c250a-e61b-44d9-88ed-5944d1962f5e";
pub const ANTHROPIC_TOKEN_URL: &str = "https://console.anthropic.com/v1/oauth/token";
pub const ANTHROPIC_API_BASE: &str = "https://api.anthropic.com";
pub const ANTHROPIC_OAUTH_BETA: &str = "oauth-2025-04-20";
pub const KEYCHAIN_SERVICE: &str = "Claude Code-credentials";

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AnthropicOAuthCreds {
    pub access_token: String,
    pub refresh_token: String,
    pub expires_at_ms: i64,
    #[serde(default)]
    pub subscription_type: String,
}

impl AnthropicOAuthCreds {
    /// Refresh proactively 60s before stated expiry (matches Python).
    pub fn expired(&self) -> bool {
        let now_ms = now_unix_ms();
        now_ms >= self.expires_at_ms - 60_000
    }

    pub fn expires_in_seconds(&self) -> i64 {
        let now_ms = now_unix_ms();
        ((self.expires_at_ms - now_ms) / 1000).max(0)
    }
}

fn now_unix_ms() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}
