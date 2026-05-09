//! Anthropic OAuth provider — Claude Code subscription via Messages API.
//!
//! Verbatim port of `voss/harness/providers.py::AnthropicOAuthProvider` (lines
//! 22-210). Critical parity rules:
//!   - System block list MUST begin with the Claude Code preamble verbatim,
//!     else the OAuth token is rejected.
//!   - `response_format` translates to a forced `submit_response` tool call.
//!   - 401 responses trigger a single refresh + retry.

use std::sync::Arc;
use std::time::Duration;

use async_trait::async_trait;
use serde_json::{json, Value};
use tokio::sync::Mutex;

use crate::traits::{CompleteRequest, ModelProvider, ProviderResponse};
use voss_auth::{AnthropicOAuthCreds, ANTHROPIC_API_BASE, ANTHROPIC_OAUTH_BETA};

/// Verbatim per `voss/harness/providers.py:38`. Anthropic OAuth tokens REJECT
/// requests whose system block does not begin with this exact string.
/// Do not paraphrase.
pub const CLAUDE_CODE_PREAMBLE: &str =
    "You are Claude Code, Anthropic's official CLI for Claude.";

/// Conservative model alias map matching providers.py:27-32.
fn resolve_model(model: &str) -> &str {
    match model {
        "claude-sonnet-4-7" => "claude-sonnet-4-5",
        "claude-opus-4-7" => "claude-opus-4-5",
        other => other,
    }
}

pub struct AnthropicOAuthProvider {
    creds: Arc<Mutex<AnthropicOAuthCreds>>,
    client: reqwest::Client,
    base_url: String,
    token_url_override: Option<String>,
    max_output_tokens: u32,
}

impl AnthropicOAuthProvider {
    pub fn new(creds: AnthropicOAuthCreds) -> Self {
        Self {
            creds: Arc::new(Mutex::new(creds)),
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(120))
                .build()
                .expect("reqwest client"),
            base_url: ANTHROPIC_API_BASE.to_string(),
            token_url_override: None,
            max_output_tokens: 4096,
        }
    }

    pub fn with_base_url(mut self, base: impl Into<String>) -> Self {
        self.base_url = base.into();
        self
    }

    /// Override the token endpoint used by `refresh_anthropic` (test seam).
    pub fn with_token_url_override(mut self, url: impl Into<String>) -> Self {
        self.token_url_override = Some(url.into());
        self
    }

    pub fn with_max_output_tokens(mut self, n: u32) -> Self {
        self.max_output_tokens = n;
        self
    }

    fn build_payload(&self, req: &CompleteRequest) -> Value {
        // Split system messages from chat per providers.py:101-110.
        let mut system_chunks: Vec<String> = Vec::new();
        let mut chat: Vec<Value> = Vec::new();
        for m in &req.messages {
            match m.role.as_str() {
                "system" => system_chunks.push(m.content.clone()),
                role => chat.push(json!({"role": role, "content": m.content})),
            }
        }

        // Preamble first, then any harness system messages (providers.py:116-119).
        let mut system_blocks: Vec<Value> =
            vec![json!({"type": "text", "text": CLAUDE_CODE_PREAMBLE})];
        for chunk in system_chunks.into_iter().filter(|c| !c.is_empty()) {
            system_blocks.push(json!({"type": "text", "text": chunk}));
        }

        let mut body = json!({
            "model": resolve_model(&req.model),
            "max_tokens": req.max_tokens.unwrap_or(self.max_output_tokens),
            "temperature": req.temperature,
            "messages": chat,
            "system": system_blocks,
        });

        if let Some(schema) = &req.response_schema {
            let mut tools: Vec<Value> = req.tools.clone().unwrap_or_default();
            tools.push(json!({
                "name": "submit_response",
                "description": "Return the final structured response.",
                "input_schema": schema,
            }));
            body["tools"] = Value::Array(tools);
            body["tool_choice"] = json!({"type": "tool", "name": "submit_response"});
        } else if let Some(tools) = &req.tools {
            body["tools"] = Value::Array(tools.clone());
        }
        body
    }

    async fn build_headers(&self) -> reqwest::header::HeaderMap {
        let creds = self.creds.lock().await;
        let mut h = reqwest::header::HeaderMap::new();
        h.insert(
            "authorization",
            format!("Bearer {}", creds.access_token).parse().unwrap(),
        );
        h.insert("anthropic-beta", ANTHROPIC_OAUTH_BETA.parse().unwrap());
        h.insert("anthropic-version", "2023-06-01".parse().unwrap());
        h.insert("content-type", "application/json".parse().unwrap());
        h.insert("user-agent", "voss-harness/0.1".parse().unwrap());
        h
    }

    async fn maybe_refresh(&self) -> anyhow::Result<()> {
        let mut creds = self.creds.lock().await;
        if creds.expired() {
            voss_auth::refresh::refresh_anthropic(
                &mut *creds,
                &self.client,
                self.token_url_override.as_deref(),
            )
            .await?;
        }
        Ok(())
    }

    async fn force_refresh(&self) -> anyhow::Result<()> {
        let mut creds = self.creds.lock().await;
        voss_auth::refresh::refresh_anthropic(
            &mut *creds,
            &self.client,
            self.token_url_override.as_deref(),
        )
        .await?;
        Ok(())
    }

    async fn post_once(&self, url: &str, body: &Value) -> reqwest::Result<reqwest::Response> {
        let h = self.build_headers().await;
        self.client.post(url).headers(h).json(body).send().await
    }
}

#[async_trait]
impl ModelProvider for AnthropicOAuthProvider {
    async fn complete(&mut self, req: CompleteRequest) -> anyhow::Result<ProviderResponse> {
        self.maybe_refresh().await?;
        let body = self.build_payload(&req);
        let url = format!("{}/v1/messages", self.base_url);

        let mut resp = self.post_once(&url, &body).await?;
        if resp.status().as_u16() == 401 {
            self.force_refresh().await?;
            resp = self.post_once(&url, &body).await?;
        }
        let status = resp.status();
        if !status.is_success() {
            let text = resp.text().await.unwrap_or_default();
            let truncated = &text[..text.len().min(500)];
            anyhow::bail!("Anthropic OAuth call failed [{}]: {}", status, truncated);
        }
        let data: Value = resp.json().await?;

        let usage = data.get("usage").cloned().unwrap_or(Value::Null);
        let prompt_tokens = usage
            .get("input_tokens")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;
        let completion_tokens = usage
            .get("output_tokens")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;

        let mut text = String::new();
        let mut parsed: Option<Value> = None;
        if let Some(content) = data.get("content").and_then(|v| v.as_array()) {
            for block in content {
                match block.get("type").and_then(|v| v.as_str()) {
                    Some("text") => {
                        if let Some(t) = block.get("text").and_then(|v| v.as_str()) {
                            text.push_str(t);
                        }
                    }
                    Some("tool_use") if req.response_schema.is_some() => {
                        if let Some(input) = block.get("input") {
                            parsed = Some(input.clone());
                            if text.is_empty() {
                                text = serde_json::to_string(input).unwrap_or_default();
                            }
                        }
                    }
                    _ => {}
                }
            }
        }

        let model = data
            .get("model")
            .and_then(|v| v.as_str())
            .unwrap_or(&req.model)
            .to_string();

        Ok(ProviderResponse {
            text,
            model,
            prompt_tokens,
            completion_tokens,
            cost_usd: 0.0, // subscription billing
            raw: data,
            parsed,
        })
    }
}
