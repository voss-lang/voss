//! OAuth refresh stubs; T3 implements.

use crate::{AnthropicOAuthCreds, CodexCreds};

pub async fn refresh_anthropic(
    _creds: &mut AnthropicOAuthCreds,
    _client: &reqwest::Client,
    _token_url_override: Option<&str>,
) -> anyhow::Result<()> {
    anyhow::bail!("refresh_anthropic stub")
}

pub async fn refresh_codex(
    _creds: &mut CodexCreds,
    _client: &reqwest::Client,
    _token_url_override: Option<&str>,
) -> anyhow::Result<()> {
    anyhow::bail!("refresh_codex stub")
}
