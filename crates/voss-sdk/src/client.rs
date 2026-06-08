use std::fmt;
use std::time::Duration;

use reqwest::{RequestBuilder, StatusCode};

use crate::error::VossError;
use crate::types::rest::{CostInfo, DoctorReport, SavedSession};

/// Per-request timeout for short REST calls. Do not apply this to SSE streams.
const REST_TIMEOUT: Duration = Duration::from_secs(30);

#[derive(Clone)]
pub struct VossClient {
    pub(crate) inner: reqwest::Client,
    pub(crate) base: String,
    pub(crate) token: String,
}

impl fmt::Debug for VossClient {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("VossClient")
            .field("base", &self.base)
            .field("token", &"[REDACTED]")
            .finish()
    }
}

impl VossClient {
    pub fn new(base: String, token: String) -> Self {
        // connect_timeout bounds establishment for all requests, including the
        // future SSE GET, without capping long-lived response bodies.
        let inner = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(10))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        Self { inner, base, token }
    }

    pub(crate) fn auth(&self, rb: RequestBuilder) -> RequestBuilder {
        rb.bearer_auth(&self.token)
    }

    /// POST /session - returns the new session id.
    pub async fn create_session(&self, cwd: &str) -> Result<String, VossError> {
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
            .ok_or_else(|| VossError::Decode("create_session: no id in response".into()))
    }

    /// POST /session {resume} - adopt a saved session and return its id.
    pub async fn create_session_resume(
        &self,
        resume_id: &str,
        cwd: &str,
    ) -> Result<String, VossError> {
        let resp = self
            .auth(self.inner.post(format!("{}/session", self.base)))
            .timeout(REST_TIMEOUT)
            .json(&serde_json::json!({ "resume": resume_id, "cwd": cwd }))
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;
        let v: serde_json::Value = resp.json().await?;
        v.get("id")
            .and_then(serde_json::Value::as_str)
            .map(str::to_string)
            .ok_or_else(|| VossError::Decode("resume: no id in response".into()))
    }

    // The SDK intentionally omits GET /session and GET /session/:id here: they
    // are not in the proven voss-tui surface, and deep readers are V4/V9 gated.

    /// DELETE /session/:id.
    pub async fn delete_session(&self, sid: &str) -> Result<(), VossError> {
        let resp = self
            .auth(self.inner.delete(format!("{}/session/{}", self.base, sid)))
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    /// POST /session/:id/message - enqueue a turn.
    pub async fn post_message(&self, sid: &str, text: &str, mode: &str) -> Result<(), VossError> {
        let resp = self
            .auth(
                self.inner
                    .post(format!("{}/session/{}/message", self.base, sid)),
            )
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
    pub async fn abort(&self, sid: &str) -> Result<(), VossError> {
        let resp = self
            .auth(
                self.inner
                    .post(format!("{}/session/{}/abort", self.base, sid)),
            )
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    /// POST /session/:id/permission.
    pub async fn permission_reply(
        &self,
        sid: &str,
        id: &str,
        choice: &str,
    ) -> Result<(), VossError> {
        let resp = self
            .auth(
                self.inner
                    .post(format!("{}/session/{}/permission", self.base, sid)),
            )
            .timeout(REST_TIMEOUT)
            .json(&serde_json::json!({ "id": id, "choice": choice }))
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    /// GET /sessions/saved - on-disk sessions resumable for this cwd.
    pub async fn list_saved_sessions(&self, cwd: &str) -> Result<Vec<SavedSession>, VossError> {
        let resp = self
            .auth(
                self.inner
                    .get(format!("{}/sessions/saved", self.base))
                    .query(&[("cwd", cwd)]),
            )
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;
        let v: serde_json::Value = resp.json().await?;
        let list = v
            .get("sessions")
            .cloned()
            .unwrap_or_else(|| serde_json::json!([]));
        serde_json::from_value(list).map_err(|e| VossError::Decode(e.to_string()))
    }

    /// GET /session/:id/cost - session cost total.
    pub async fn cost(&self, sid: &str) -> Result<CostInfo, VossError> {
        let resp = self
            .auth(
                self.inner
                    .get(format!("{}/session/{}/cost", self.base, sid)),
            )
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;
        let v: serde_json::Value = resp.json().await?;
        Ok(CostInfo {
            total_usd: v
                .get("total_usd")
                .and_then(serde_json::Value::as_f64)
                .unwrap_or(0.0),
            turns: v
                .get("turns")
                .and_then(serde_json::Value::as_u64)
                .unwrap_or(0),
        })
    }

    /// GET /doctor - server-side diagnostics.
    pub async fn doctor(&self, cwd: &str) -> Result<DoctorReport, VossError> {
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
        resp.json().await.map_err(VossError::Http)
    }
}

async fn ok_or_detail(resp: reqwest::Response) -> Result<reqwest::Response, VossError> {
    let status = resp.status();
    if status.is_success() {
        return Ok(resp);
    }

    let body = resp.text().await.unwrap_or_default();
    Err(http_status_error(status, &body))
}

fn http_status_error(status: StatusCode, body: &str) -> VossError {
    let detail = serde_json::from_str::<serde_json::Value>(body)
        .ok()
        .and_then(|v| {
            v.get("detail")
                .and_then(serde_json::Value::as_str)
                .map(String::from)
        })
        .unwrap_or_else(|| format!("HTTP {status}"));

    VossError::HttpStatus {
        status: status.as_u16(),
        detail,
    }
}

#[cfg(test)]
mod tests {
    use super::{http_status_error, VossClient};
    use crate::error::VossError;

    #[test]
    fn debug_redacts_token() {
        let client = VossClient::new("http://127.0.0.1:9".into(), "secret-tok".into());
        let formatted = format!("{client:?}");

        assert!(formatted.contains("[REDACTED]"));
        assert!(!formatted.contains("secret-tok"));
    }

    #[test]
    fn maps_json_detail_to_http_status_error() {
        let error = http_status_error(
            reqwest::StatusCode::UNAUTHORIZED,
            r#"{"v":1,"detail":"nope"}"#,
        );

        match error {
            VossError::HttpStatus { status, detail } => {
                assert_eq!(status, 401);
                assert_eq!(detail, "nope");
            }
            other => panic!("expected HttpStatus, got {other:?}"),
        }
    }
}
