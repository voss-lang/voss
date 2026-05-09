//! resolve() preference picker; T4 fills it in.

use crate::{AnthropicOAuthCreds, CodexCreds};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AuthPref {
    Auto,
    Claude,
    Codex,
    Api,
    None,
}

#[derive(Clone, Debug)]
pub enum Resolution {
    EnvAnthropic { detail: String },
    EnvOpenAI { api_key: String, detail: String },
    ClaudeOAuth { creds: AnthropicOAuthCreds, detail: String },
    Codex { api_key: String, detail: String },
    CodexOAuth { creds: CodexCreds, detail: String },
    None { detail: String },
}

pub fn resolve(_pref: AuthPref) -> Resolution {
    Resolution::None {
        detail: "stub".into(),
    }
}
