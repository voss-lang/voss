//! HTTP + SSE client (H2.3, H2.5).
//!
//! Thin REST commands (create session, post message, abort, permission reply)
//! plus an SSE consumer that parses the event stream into [`AppEvent`]s and
//! forwards them over an mpsc channel to the UI task. Uses reqwest's
//! `bytes_stream()` + `eventsource-stream` (avoids the stale
//! `reqwest-eventsource` crate, which pins an incompatible reqwest).

use anyhow::{anyhow, Result};
use eventsource_stream::Eventsource;
use futures_util::StreamExt;
use tokio::sync::mpsc;

use crate::event::AppEvent;

#[derive(Clone)]
pub struct HttpClient {
    inner: reqwest::Client,
    base: String,
    token: String,
}

impl HttpClient {
    pub fn new(base: String, token: String) -> Self {
        Self {
            inner: reqwest::Client::new(),
            base,
            token,
        }
    }

    fn auth(&self, rb: reqwest::RequestBuilder) -> reqwest::RequestBuilder {
        rb.bearer_auth(&self.token)
    }

    /// POST /session — returns the new session id.
    pub async fn create_session(&self, cwd: &str) -> Result<String> {
        let resp = self
            .auth(self.inner.post(format!("{}/session", self.base)))
            .json(&serde_json::json!({ "cwd": cwd }))
            .send()
            .await?
            .error_for_status()?;
        let v: serde_json::Value = resp.json().await?;
        v.get("id")
            .and_then(serde_json::Value::as_str)
            .map(str::to_string)
            .ok_or_else(|| anyhow!("create_session: no id in response"))
    }

    /// POST /session/:id/message — enqueue a turn (server returns 202).
    pub async fn post_message(&self, sid: &str, text: &str, mode: &str) -> Result<()> {
        self.auth(self.inner.post(format!("{}/session/{}/message", self.base, sid)))
            .json(&serde_json::json!({
                "parts": [{ "type": "text", "text": text }],
                "mode": mode,
            }))
            .send()
            .await?
            .error_for_status()?;
        Ok(())
    }

    /// POST /session/:id/abort.
    pub async fn abort(&self, sid: &str) -> Result<()> {
        self.auth(self.inner.post(format!("{}/session/{}/abort", self.base, sid)))
            .send()
            .await?
            .error_for_status()?;
        Ok(())
    }

    /// POST /session/:id/permission — reply to a pending request.
    pub async fn permission_reply(&self, sid: &str, id: &str, choice: &str) -> Result<()> {
        self.auth(self.inner.post(format!("{}/session/{}/permission", self.base, sid)))
            .json(&serde_json::json!({ "id": id, "choice": choice }))
            .send()
            .await?
            .error_for_status()?;
        Ok(())
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
            .await?
            .error_for_status()?;

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
