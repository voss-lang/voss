//! voss-providers — model provider implementations.

pub mod anthropic;
pub mod traits;

pub use anthropic::AnthropicOAuthProvider;
pub use traits::{CompleteRequest, Message, ModelProvider, ProviderResponse};

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
