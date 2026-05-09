//! Build a model provider from a resolved auth path. R7 only supports
//! Anthropic OAuth; other paths surface clear errors pointing at the wave
//! that lands them.

use voss_auth::Resolution;
use voss_providers::{AnthropicOAuthProvider, ModelProvider};

pub fn build(res: Resolution) -> anyhow::Result<Box<dyn ModelProvider>> {
    match res {
        Resolution::ClaudeOAuth { creds, .. } => Ok(Box::new(AnthropicOAuthProvider::new(creds))),
        Resolution::Codex { .. } | Resolution::CodexOAuth { .. } => anyhow::bail!(
            "Codex auth path not yet wired into voss-cli — see wave 07-08. \
             Use --auth=claude (Claude OAuth) for the v1.2 chat REPL."
        ),
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
