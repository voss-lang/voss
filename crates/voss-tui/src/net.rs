//! HTTP + SSE client (H2.3, H2.5).
//!
//! Thin REST commands (create session, post message, abort, permission reply)
//! plus an SSE consumer that parses the event stream into [`AppEvent`]s and
//! forwards them over an mpsc channel to the UI task. Uses reqwest's
//! `bytes_stream()` + `eventsource-stream` (avoids the stale
//! `reqwest-eventsource` crate, which pins an incompatible reqwest).

use std::time::Duration;

use anyhow::{anyhow, Result};
use eventsource_stream::Eventsource;
use futures_util::StreamExt;
use tokio::sync::mpsc;

use crate::event::AppEvent;

/// Per-request timeout for the short REST calls. NOT applied to the SSE stream
/// (long-lived); the client's connect_timeout covers establishing that.
const REST_TIMEOUT: Duration = Duration::from_secs(30);

/// Turn a non-2xx response into an error that carries the server's `{detail}`
/// (PROTOCOL.md §9) instead of reqwest's status-only message.
async fn ok_or_detail(resp: reqwest::Response) -> Result<reqwest::Response> {
    let status = resp.status();
    if status.is_success() {
        return Ok(resp);
    }
    let body = resp.text().await.unwrap_or_default();
    let detail = serde_json::from_str::<serde_json::Value>(&body)
        .ok()
        .and_then(|v| v.get("detail").and_then(|d| d.as_str()).map(String::from));
    match detail {
        Some(d) => Err(anyhow!("{d} ({status})")),
        None => Err(anyhow!("HTTP {status}")),
    }
}

#[derive(Clone)]
pub struct HttpClient {
    inner: reqwest::Client,
    base: String,
    token: String,
}

impl HttpClient {
    pub fn new(base: String, token: String) -> Self {
        // connect_timeout bounds connection establishment for ALL requests
        // (incl. the SSE GET) without capping the long-lived stream body.
        let inner = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(10))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        Self { inner, base, token }
    }

    fn auth(&self, rb: reqwest::RequestBuilder) -> reqwest::RequestBuilder {
        rb.bearer_auth(&self.token)
    }

    /// POST /session — returns the new session id.
    pub async fn create_session(&self, cwd: &str) -> Result<String> {
        let resp = self
            .auth(self.inner.post(format!("{}/session", self.base)))
            .timeout(REST_TIMEOUT)
            .json(&serde_json::json!({ "cwd": cwd }))
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;
        let v: serde_json::Value = resp.json().await?;
        v.get("id")
            .and_then(serde_json::Value::as_str)
            .map(str::to_string)
            .ok_or_else(|| anyhow!("create_session: no id in response"))
    }

    /// POST /session/:id/message — enqueue a turn (server returns 202).
    pub async fn post_message(&self, sid: &str, text: &str, mode: &str) -> Result<()> {
        let resp = self
            .auth(self.inner.post(format!("{}/session/{}/message", self.base, sid)))
            .timeout(REST_TIMEOUT)
            .json(&serde_json::json!({
                "parts": [{ "type": "text", "text": text }],
                "mode": mode,
            }))
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    /// POST /session/:id/abort.
    pub async fn abort(&self, sid: &str) -> Result<()> {
        let resp = self
            .auth(self.inner.post(format!("{}/session/{}/abort", self.base, sid)))
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    /// POST /session/:id/permission — reply to a pending request.
    pub async fn permission_reply(&self, sid: &str, id: &str, choice: &str) -> Result<()> {
        let resp = self
            .auth(self.inner.post(format!("{}/session/{}/permission", self.base, sid)))
            .timeout(REST_TIMEOUT)
            .json(&serde_json::json!({ "id": id, "choice": choice }))
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    /// GET /doctor — server-side diagnostics (the client renders, never computes).
    pub async fn doctor(&self, cwd: &str) -> Result<crate::doctor::DoctorReport> {
        let resp = self
            .auth(
                self.inner
                    .get(format!("{}/doctor", self.base))
                    .query(&[("cwd", cwd)]),
            )
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;
        Ok(resp.json().await?)
    }

    /// GET /session/:id/events — stream SSE, forwarding parsed events to `tx`.
    ///
    /// Returns when the turn ends (`session.idle`), the stream errors, or the
    /// receiver is dropped. One call streams one turn; the caller reopens per
    /// turn.
    pub async fn stream_events(&self, sid: &str, tx: mpsc::Sender<AppEvent>) -> Result<()> {
        let resp = self
            .auth(
                self.inner
                    .get(format!("{}/session/{}/events", self.base, sid))
                    .header("Accept", "text/event-stream"),
            )
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;

        let mut es = resp.bytes_stream().eventsource();
        while let Some(item) = es.next().await {
            match item {
                Ok(frame) => {
                    let ev = AppEvent::from_wire(&frame.event, &frame.data);
                    let stop = matches!(ev, AppEvent::SessionIdle);
                    if tx.send(ev).await.is_err() {
                        break; // UI gone
                    }
                    if stop {
                        break; // turn complete
                    }
                }
                Err(e) => {
                    let _ = tx.send(AppEvent::Error(e.to_string())).await;
                    break;
                }
            }
        }
        Ok(())
    }
}
