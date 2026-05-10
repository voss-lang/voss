//! Build a model provider from a resolved auth path.

use voss_auth::{CodexCreds, Resolution};
use voss_providers::{AnthropicOAuthProvider, ModelProvider, OpenAIOAuthProvider};

pub fn build(res: Resolution) -> anyhow::Result<Box<dyn ModelProvider>> {
    match res {
        Resolution::ClaudeOAuth { creds, .. } => Ok(Box::new(AnthropicOAuthProvider::new(creds))),
        Resolution::CodexOAuth { creds, .. } => Ok(Box::new(OpenAIOAuthProvider::new(creds))),
        Resolution::Codex { api_key, .. } => Ok(Box::new(OpenAIOAuthProvider::new(CodexCreds {
            api_key: Some(api_key),
            access_token: None,
            refresh_token: None,
            account_id: None,
            auth_mode: "ApiKey".into(),
        }))),
        Resolution::EnvAnthropic { .. } | Resolution::EnvOpenAI { .. } => anyhow::bail!(
            "ANTHROPIC_API_KEY / OPENAI_API_KEY env paths are not in v1.2 chat REPL scope. \
             Use --auth=claude (Claude OAuth via `claude login`) instead."
        ),
        Resolution::None { detail } => anyhow::bail!(
            "no auth available: {detail}. Run `claude login` for Claude OAuth, \
             or see wave 07-08 for upcoming Codex/anthropic-oauth support."
        ),
    }
}
