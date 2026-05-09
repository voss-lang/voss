//! Anthropic OAuth provider — T2 implements.

use async_trait::async_trait;

use crate::traits::{CompleteRequest, ModelProvider, ProviderResponse};

pub struct AnthropicOAuthProvider;

#[async_trait]
impl ModelProvider for AnthropicOAuthProvider {
    async fn complete(&mut self, _req: CompleteRequest) -> anyhow::Result<ProviderResponse> {
        anyhow::bail!("AnthropicOAuthProvider stub")
    }
}
