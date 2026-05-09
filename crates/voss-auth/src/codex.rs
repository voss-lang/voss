//! Codex (OpenAI) credential type + endpoint constants.

use serde::{Deserialize, Serialize};

pub const CODEX_CLIENT_ID: &str = "app_EMoamEEZ73f0CkXaXp7hrann";
pub const OPENAI_TOKEN_URL: &str = "https://auth.openai.com/oauth/token";
pub const OPENAI_API_BASE: &str = "https://api.openai.com";
pub const CHATGPT_BACKEND_BASE: &str = "https://chatgpt.com/backend-api/codex";

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct CodexCreds {
    pub api_key: Option<String>,
    pub access_token: Option<String>,
    pub refresh_token: Option<String>,
    pub account_id: Option<String>,
    #[serde(default)]
    pub auth_mode: String, // "ApiKey" | "ChatGPT" | "chatgpt" | ""
}

impl CodexCreds {
    pub fn has_oauth(&self) -> bool {
        self.access_token.is_some() && self.refresh_token.is_some()
    }
}
