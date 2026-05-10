//! OpenAI/Codex provider — ChatGPT subscription and API-key Responses API.
//!
//! ChatGPT-mode credentials use Codex's Responses endpoint under
//! `chatgpt.com/backend-api/codex`. The captured Codex CLI fixture in
//! `.planning/codex-fixtures/` shows the current protocol uses SSE, reasoning
//! inclusion, a prompt cache key, and Codex session headers.

use std::sync::Arc;
use std::time::Duration;

use async_trait::async_trait;
use serde_json::{json, Value};
use tokio::sync::Mutex;
use uuid::Uuid;

use crate::traits::{CompleteRequest, Message, ModelProvider, ProviderResponse};
use voss_auth::{CodexCreds, CHATGPT_BACKEND_BASE, OPENAI_API_BASE};

const OPENAI_MODEL_DEFAULT: &str = "gpt-5";
const CODEX_ORIGINATOR: &str = "codex_cli_rs";

pub struct OpenAIOAuthProvider {
    creds: Arc<Mutex<CodexCreds>>,
    client: reqwest::Client,
    base_url: String,
    token_url_override: Option<String>,
    session_id: Uuid,
}

impl OpenAIOAuthProvider {
    pub fn new(creds: CodexCreds) -> Self {
        let base_url = if creds.auth_mode.eq_ignore_ascii_case("chatgpt") {
            CHATGPT_BACKEND_BASE
        } else {
            OPENAI_API_BASE
        };
        Self {
            creds: Arc::new(Mutex::new(creds)),
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(120))
                .build()
                .expect("reqwest client"),
            base_url: base_url.to_string(),
            token_url_override: None,
            session_id: Uuid::new_v4(),
        }
    }

    pub fn with_base_url(mut self, base: impl Into<String>) -> Self {
        self.base_url = base.into();
        self
    }

    pub fn with_token_url(mut self, url: impl Into<String>) -> Self {
        self.token_url_override = Some(url.into());
        self
    }

    async fn build_headers(&self) -> reqwest::header::HeaderMap {
        let creds = self.creds.lock().await;
        let mut h = reqwest::header::HeaderMap::new();
        if let Some(token) = creds.access_token.as_ref().or(creds.api_key.as_ref()) {
            h.insert(
                "authorization",
                format!("Bearer {token}")
                    .parse()
                    .expect("authorization header"),
            );
        }
        h.insert("accept", "text/event-stream".parse().unwrap());
        h.insert("content-type", "application/json".parse().unwrap());
        h.insert("user-agent", "voss-harness/0.1".parse().unwrap());
        h.insert("originator", CODEX_ORIGINATOR.parse().unwrap());
        h.insert("OpenAI-Beta", "responses=v1".parse().unwrap());
        h.insert("session_id", self.session_id.to_string().parse().unwrap());
        h.insert("thread_id", self.session_id.to_string().parse().unwrap());
        h.insert(
            "x-client-request-id",
            self.session_id.to_string().parse().unwrap(),
        );
        if let Some(account_id) = &creds.account_id {
            h.insert("chatgpt-account-id", account_id.parse().unwrap());
        }
        h
    }

    fn endpoint(&self) -> String {
        if self.base_url.ends_with("/codex") {
            format!("{}/responses", self.base_url)
        } else {
            format!("{}/v1/responses", self.base_url)
        }
    }

    fn build_payload(&self, req: &CompleteRequest) -> Value {
        let mut instructions = Vec::new();
        let mut input = Vec::new();
        for Message { role, content } in &req.messages {
            match role.as_str() {
                "system" | "developer" => instructions.push(content.clone()),
                "assistant" => input.push(json!({
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": content}],
                })),
                _ => input.push(json!({
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": content}],
                })),
            }
        }

        let mut body = json!({
            "model": if req.model.is_empty() { OPENAI_MODEL_DEFAULT } else { &req.model },
            "input": input,
            "store": false,
            "stream": true,
            "parallel_tool_calls": true,
            "tool_choice": "auto",
            "include": ["reasoning.encrypted_content"],
            "prompt_cache_key": self.session_id.to_string(),
            "reasoning": {"effort": "high"},
            "text": {"verbosity": "low"},
            "client_metadata": {},
        });
        if !instructions.is_empty() {
            body["instructions"] = Value::String(instructions.join("\n\n"));
        }
        if let Some(max_tokens) = req.max_tokens {
            body["max_output_tokens"] = json!(max_tokens);
        }
        if req.temperature.is_finite() {
            body["temperature"] = json!(req.temperature);
        }
        if let Some(schema) = &req.response_schema {
            let mut schema = schema.clone();
            if let Some(obj) = schema.as_object_mut() {
                obj.insert("additionalProperties".into(), json!(false));
            }
            let name = req.response_schema_name.as_deref().unwrap_or("Plan");
            body["text"] = json!({
                "format": {
                    "type": "json_schema",
                    "name": name,
                    "strict": true,
                    "schema": schema,
                }
            });
        }
        let mut tools = req.tools.clone().unwrap_or_default();
        tools.push(json!({
            "type": "function",
            "name": "local_shell",
            "description": "Codex CLI compatibility placeholder; Voss does not execute this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string"}
                },
                "required": ["cmd"],
                "additionalProperties": false
            }
        }));
        body["tools"] = Value::Array(tools);
        body
    }

    async fn force_refresh(&self) -> anyhow::Result<()> {
        let mut creds = self.creds.lock().await;
        voss_auth::refresh::refresh_codex(
            &mut creds,
            &self.client,
            self.token_url_override.as_deref(),
        )
        .await?;
        Ok(())
    }

    async fn post_once(&self, url: &str, body: &Value) -> reqwest::Result<reqwest::Response> {
        let headers = self.build_headers().await;
        self.client
            .post(url)
            .headers(headers)
            .json(body)
            .send()
            .await
    }
}

fn parse_sse_text(raw: &str) -> (String, Option<Value>, Value) {
    let mut text = String::new();
    let mut final_response = Value::Null;
    for line in raw.lines() {
        let Some(data) = line.strip_prefix("data: ") else {
            continue;
        };
        let Ok(event) = serde_json::from_str::<Value>(data) else {
            continue;
        };
        match event.get("type").and_then(|v| v.as_str()) {
            Some("response.output_text.delta") => {
                if let Some(delta) = event.get("delta").and_then(|v| v.as_str()) {
                    text.push_str(delta);
                }
            }
            Some("response.completed") => {
                if let Some(resp) = event.get("response") {
                    final_response = resp.clone();
                }
            }
            _ => {}
        }
    }
    let parsed = serde_json::from_str::<Value>(&text).ok();
    (text, parsed, final_response)
}

fn extract_json_text(data: &Value) -> String {
    let mut text = String::new();
    if let Some(output) = data.get("output").and_then(|v| v.as_array()) {
        for block in output {
            if block.get("type").and_then(|v| v.as_str()) == Some("message") {
                if let Some(content) = block.get("content").and_then(|v| v.as_array()) {
                    for c in content {
                        if matches!(
                            c.get("type").and_then(|v| v.as_str()),
                            Some("output_text" | "text")
                        ) {
                            if let Some(t) = c.get("text").and_then(|v| v.as_str()) {
                                text.push_str(t);
                            }
                        }
                    }
                }
            }
        }
    }
    if text.is_empty() {
        if let Some(t) = data.get("output_text").and_then(|v| v.as_str()) {
            text = t.to_string();
        }
    }
    text
}

#[async_trait]
impl ModelProvider for OpenAIOAuthProvider {
    async fn complete(&mut self, req: CompleteRequest) -> anyhow::Result<ProviderResponse> {
        let body = self.build_payload(&req);
        let url = self.endpoint();
        let mut resp = self.post_once(&url, &body).await?;
        if resp.status().as_u16() == 401 {
            let has_refresh = self.creds.lock().await.refresh_token.is_some();
            if has_refresh {
                self.force_refresh().await?;
                resp = self.post_once(&url, &body).await?;
            }
        }
        let status = resp.status();
        let content_type = resp
            .headers()
            .get(reqwest::header::CONTENT_TYPE)
            .and_then(|v| v.to_str().ok())
            .unwrap_or("")
            .to_string();
        if !status.is_success() {
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!(
                "OpenAI OAuth call failed [{}]: {}",
                status,
                &text[..text.len().min(500)]
            );
        }

        let response_text = resp.text().await?;
        if content_type.starts_with("text/event-stream") || response_text.starts_with("event: ") {
            let (text, parsed, raw_value) = parse_sse_text(&response_text);
            return Ok(ProviderResponse {
                text,
                model: req.model,
                prompt_tokens: 0,
                completion_tokens: 0,
                cost_usd: 0.0,
                raw: raw_value,
                parsed,
            });
        }

        let data: Value = serde_json::from_str(&response_text)?;
        let usage = data.get("usage").cloned().unwrap_or(Value::Null);
        let prompt_tokens = usage
            .get("input_tokens")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;
        let completion_tokens = usage
            .get("output_tokens")
            .and_then(|v| v.as_u64())
            .unwrap_or(0) as u32;
        let text = extract_json_text(&data);
        let parsed = if req.response_schema.is_some() && !text.is_empty() {
            serde_json::from_str::<Value>(&text).ok()
        } else {
            None
        };
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
            cost_usd: 0.0,
            raw: data,
            parsed,
        })
    }
}
