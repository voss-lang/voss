//! Provider trait + request/response shapes shared by every model backend.

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ProviderResponse {
    pub text: String,
    pub model: String,
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub cost_usd: f64,
    pub raw: Value,
    pub parsed: Option<Value>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Message {
    pub role: String, // "system" | "user" | "assistant"
    pub content: String,
}

#[derive(Clone, Debug, Serialize)]
pub struct CompleteRequest {
    pub messages: Vec<Message>,
    pub model: String,
    pub temperature: f32,
    pub max_tokens: Option<u32>,
    /// JSON Schema for forced structured output. None = free-form.
    pub response_schema: Option<Value>,
    /// Optional name for the response schema (used as tool name).
    pub response_schema_name: Option<String>,
    pub tools: Option<Vec<Value>>,
}

#[async_trait]
pub trait ModelProvider: Send + Sync {
    async fn complete(&mut self, req: CompleteRequest) -> anyhow::Result<ProviderResponse>;

    fn count_tokens(&self, text: &str, _model: &str) -> usize {
        (text.len() / 4).max(1)
    }
}
