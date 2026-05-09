//! Auth-path resolution. Mirrors `voss/harness/auth.py::resolve` (lines 286-329).

use crate::anthropic::AnthropicOAuthCreds;
use crate::codex::CodexCreds;
use crate::{load_anthropic_oauth, load_codex};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AuthPref {
    Auto,
    Claude,
    Codex,
    Api,
    None,
}

impl AuthPref {
    pub fn parse(s: &str) -> Self {
        match s {
            "auto" => Self::Auto,
            "claude" => Self::Claude,
            "codex" => Self::Codex,
            "api" => Self::Api,
            _ => Self::None,
        }
    }
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

impl Resolution {
    pub fn source(&self) -> &'static str {
        match self {
            Self::EnvAnthropic { .. } => "env-anthropic",
            Self::EnvOpenAI { .. } => "env-openai",
            Self::ClaudeOAuth { .. } => "claude-oauth",
            Self::Codex { .. } => "codex",
            Self::CodexOAuth { .. } => "codex-oauth",
            Self::None { .. } => "none",
        }
    }

    pub fn detail(&self) -> &str {
        match self {
            Self::EnvAnthropic { detail }
            | Self::EnvOpenAI { detail, .. }
            | Self::ClaudeOAuth { detail, .. }
            | Self::Codex { detail, .. }
            | Self::CodexOAuth { detail, .. }
            | Self::None { detail } => detail,
        }
    }
}

pub fn resolve(pref: AuthPref) -> Resolution {
    if pref == AuthPref::None {
        return Resolution::None {
            detail: "forced none".into(),
        };
    }

    if matches!(pref, AuthPref::Auto | AuthPref::Api) {
        if std::env::var("ANTHROPIC_API_KEY").is_ok() {
            return Resolution::EnvAnthropic {
                detail: "ANTHROPIC_API_KEY".into(),
            };
        }
        if let Ok(k) = std::env::var("OPENAI_API_KEY") {
            return Resolution::EnvOpenAI {
                api_key: k,
                detail: "OPENAI_API_KEY".into(),
            };
        }
    }

    if matches!(pref, AuthPref::Auto | AuthPref::Claude) {
        if let Some(creds) = load_anthropic_oauth() {
            let detail = format!(
                "keychain ({}, expires {}s)",
                creds.subscription_type,
                creds.expires_in_seconds()
            );
            return Resolution::ClaudeOAuth { creds, detail };
        }
    }

    if matches!(pref, AuthPref::Auto | AuthPref::Codex) {
        if let Some(codex) = load_codex() {
            if let Some(k) = codex.api_key.clone() {
                return Resolution::Codex {
                    api_key: k,
                    detail: format!("~/.codex/auth.json ({}, api key)", codex.auth_mode),
                };
            }
            if codex.has_oauth() {
                let detail = format!("~/.codex/auth.json ({}, OAuth)", codex.auth_mode);
                return Resolution::CodexOAuth {
                    creds: codex,
                    detail,
                };
            }
        }
    }

    let detail = match pref {
        AuthPref::Claude => "no Claude OAuth creds found",
        AuthPref::Codex => "no Codex creds found",
        AuthPref::Api => "no API key in env",
        _ => "no creds found via any path",
    };
    Resolution::None {
        detail: detail.into(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_strings_match_python() {
        // Verify the exact string identifiers Python uses.
        let cases: &[(Resolution, &str)] = &[
            (
                Resolution::EnvAnthropic {
                    detail: "x".into(),
                },
                "env-anthropic",
            ),
            (
                Resolution::EnvOpenAI {
                    api_key: "k".into(),
                    detail: "x".into(),
                },
                "env-openai",
            ),
            (Resolution::None { detail: "x".into() }, "none"),
        ];
        for (r, want) in cases {
            assert_eq!(r.source(), *want);
        }
    }

    #[test]
    fn forced_none_short_circuits() {
        let r = resolve(AuthPref::None);
        assert_eq!(r.source(), "none");
        assert_eq!(r.detail(), "forced none");
    }
}
