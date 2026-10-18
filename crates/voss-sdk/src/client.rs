use std::fmt;
use std::time::Duration;

use reqwest::{RequestBuilder, StatusCode};

use crate::error::VossError;
use crate::types::rest::{CostInfo, DoctorReport, RoleSpec, SavedSession, Swarm, SwarmCreated};

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
        // future SSE GET, without capping long-lived response bodies
        let inner = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(10))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        Self { inner, base, token }
    }

    pub fn base_url(&self) -> &str {
        &self.base
    }

    pub fn token(&self) -> &str {
        &self.token
    }

    pub async fn preview_plan(&self, briefing: &crate::plans::Briefing) -> Result<crate::plans::Result, VossError> {
        self.plan_command("plans/preview", serde_json::to_value(briefing).map_err(|e| VossError::Decode(e.to_string()))?).await
    }

    pub async fn plan_status(&self, id: &str) -> Result<crate::plans::Result, VossError> {
        let response = self.auth(self.inner.get(format!("{}/plans/{id}", self.base))).timeout(REST_TIMEOUT).send().await?;
        let result: crate::plans::Result = ok_or_detail(response).await?.json().await?;
        if result.v != 1 || result.preview.as_ref().is_some_and(|p| p.v != 1 || p.id != id) {
            return Err(VossError::Decode("incompatible plan status".into()));
        }
        Ok(result)
    }

    pub async fn start_plan(&self, id: &str, revision: &str, briefing: &crate::plans::Briefing) -> Result<crate::plans::Result, VossError> {
        self.plan_command(&format!("plans/{id}/start"), serde_json::json!({"revision":revision,"briefing":briefing})).await
    }

    async fn plan_command(&self, route: &str, body: serde_json::Value) -> Result<crate::plans::Result, VossError> {
        let response = self.auth(self.inner.post(format!("{}/{route}", self.base)))
            .timeout(Duration::from_secs(180)).json(&body).send().await?;
        let result: crate::plans::Result = ok_or_detail(response).await?.json().await?;
        if result.v != 1 || result.preview.as_ref().is_some_and(|p| p.v != 1)
            || result.availability.as_ref().is_some_and(|a| a.v != 1)
            || (result.status == "prepared" && result.preview.is_none())
            || (result.status == "accepted" && (result.session_id.is_none() || result.run_id.is_none() || result.preview.is_none())) {
            return Err(VossError::Decode("incompatible plan response".into()));
        }
        Ok(result)
    }

    pub async fn graph_output(&self, sid: &str, node_id: &str, attempt_id: &str, after: u64) -> Result<crate::graph::Output, VossError> {
        let response = self.auth(self.inner.get(format!("{}/session/{sid}/graph-output", self.base)))
            .query(&[("node_id", node_id), ("attempt_id", attempt_id), ("after", &after.to_string())])
            .timeout(REST_TIMEOUT).send().await?;
        let output: crate::graph::Output = ok_or_detail(response).await?.json().await?;
        if output.v != 1 { return Err(VossError::Decode("incompatible graph output".into())); }
        Ok(output)
    }

    pub async fn task_review(&self, sid: &str, node_id: &str, attempt_id: &str) -> Result<crate::review::Bundle, VossError> {
        let response = self.auth(self.inner.get(format!("{}/session/{sid}/review", self.base)))
            .query(&[("node_id", node_id), ("attempt_id", attempt_id)])
            .timeout(REST_TIMEOUT).send().await?;
        let bundle: crate::review::Bundle = ok_or_detail(response).await?.json().await?;
        if bundle.v != 1 || bundle.session_id != sid || bundle.task_id != node_id || bundle.attempt_id != attempt_id {
            return Err(VossError::Decode("incompatible task review".into()));
        }
        Ok(bundle)
    }

    /// GET /capabilities - protocol support, without checking provider credentials.
    pub async fn capabilities(&self) -> Result<crate::capabilities::Capabilities, VossError> {
        let resp = self
            .auth(self.inner.get(format!("{}/capabilities", self.base)))
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        ok_or_detail(resp).await?.json().await.map_err(VossError::Http)
    }

    pub async fn task_snapshot(&self, sid: &str) -> Result<crate::tasks::TaskSnapshot, VossError> {
        let resp = self.auth(self.inner.get(format!("{}/session/{sid}/task", self.base)))
            .timeout(REST_TIMEOUT).send().await?;
        let snapshot: crate::tasks::TaskSnapshot = ok_or_detail(resp).await?.json().await?;
        if snapshot.v != 1 || snapshot.session_id != sid || snapshot.graph.as_ref().is_some_and(|graph| graph.v != 1) {
            return Err(VossError::Decode("incompatible task snapshot".into()));
        }
        Ok(snapshot)
    }

    pub async fn submit_message(&self, sid: &str, text: &str, mode: &str, command_id: &str) -> Result<crate::tasks::CommandAck, VossError> {
        self.task_command(sid, "message", serde_json::json!({
            "parts": [{"type": "text", "text": text}], "mode": mode, "command_id": command_id,
        })).await
    }

    pub async fn abort_task(&self, sid: &str) -> Result<crate::tasks::CommandAck, VossError> {
        self.task_command(sid, "abort", serde_json::json!({})).await
    }

    pub async fn reply_permission(&self, sid: &str, id: &str, choice: &str) -> Result<crate::tasks::CommandAck, VossError> {
        self.task_command(sid, "permission", serde_json::json!({"id": id, "choice": choice})).await
    }

    pub async fn reply_diff(&self, sid: &str, id: &str, decisions: &[String]) -> Result<crate::tasks::CommandAck, VossError> {
        self.task_command(sid, "diff", serde_json::json!({"id": id, "decisions": decisions})).await
    }

    async fn task_command(&self, sid: &str, command: &str, body: serde_json::Value) -> Result<crate::tasks::CommandAck, VossError> {
        let resp = self.auth(self.inner.post(format!("{}/session/{sid}/{command}", self.base)))
            .timeout(REST_TIMEOUT).json(&body).send().await?;
        let ack: crate::tasks::CommandAck = ok_or_detail(resp).await?.json().await?;
        if ack.v != 1 || ack.availability.as_ref().is_some_and(|row| row.v != 1) {
            return Err(VossError::Decode("incompatible command acknowledgement".into()));
        }
        Ok(ack)
    }

    pub async fn harness_catalog(&self) -> Result<crate::oauth::Catalog, VossError> {
        let resp = self.auth(self.inner.get(format!("{}/harnesses", self.base)))
            .timeout(REST_TIMEOUT).send().await?;
        let catalog: crate::oauth::Catalog = ok_or_detail(resp).await?.json().await?;
        if catalog.v != 1 || catalog.harnesses.iter().any(|row| row.v != 1) {
            return Err(VossError::Decode("incompatible OAuth availability report".into()));
        }
        Ok(catalog)
    }

    pub async fn harness_preflight(&self, request: &crate::oauth::Preflight) -> Result<crate::oauth::Availability, VossError> {
        let resp = self.auth(self.inner.post(format!("{}/harness/preflight", self.base)))
            .timeout(REST_TIMEOUT).json(request).send().await?;
        let report: crate::oauth::Availability = ok_or_detail(resp).await?.json().await?;
        if report.v != 1 || report.harness != request.harness {
            return Err(VossError::Decode("incompatible OAuth preflight".into()));
        }
        Ok(report)
    }

    pub async fn create_oauth_session(&self, cwd: &str, harness: &str, model: &str) -> Result<crate::oauth::Launch, VossError> {
        self.oauth_launch("session", serde_json::json!({"cwd": cwd, "auth": harness, "model": model})).await
    }

    pub async fn create_oauth_swarm(&self, goal: &str, cwd: &str, builders: u32, roster: &[RoleSpec]) -> Result<crate::oauth::Launch, VossError> {
        self.oauth_launch("swarm", serde_json::json!({"goal": goal, "cwd": cwd, "builders": builders, "roster": roster})).await
    }

    async fn oauth_launch(&self, route: &str, body: serde_json::Value) -> Result<crate::oauth::Launch, VossError> {
        let resp = self.auth(self.inner.post(format!("{}/{route}", self.base)))
            .timeout(REST_TIMEOUT).json(&body).send().await?;
        let launch: crate::oauth::Launch = ok_or_detail(resp).await?.json().await?;
        if launch.v != 1 || (launch.id.is_some() == launch.availability.is_some())
            || launch.availability.as_ref().is_some_and(|row| row.v != 1 || row.available) {
            return Err(VossError::Decode("invalid OAuth launch response".into()));
        }
        Ok(launch)
    }

    pub(crate) fn auth(&self, rb: RequestBuilder) -> RequestBuilder {
        rb.bearer_auth(&self.token)
    }

    /// POST /session - returns the new session id
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

    /// POST /session {resume} - adopt a saved session and return its id
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
    // are not in the proven voss-tui surface, and deep readers are / gated

    /// DELETE /session/:id
    pub async fn delete_session(&self, sid: &str) -> Result<(), VossError> {
        let resp = self
            .auth(self.inner.delete(format!("{}/session/{}", self.base, sid)))
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    /// POST /session/:id/message - enqueue a turn
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

    /// POST /session/:id/abort
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

    /// POST /session/:id/permission
    pub async fn permission_reply(
        &self,
        sid: &str,
        id: &str,
        choice: &str,
    ) -> Result<(), VossError> {
        let ack = self.reply_permission(sid, id, choice).await?;
        if ack.status != "ok" {
            return Err(VossError::Decode(format!("permission reply: {}", ack.status)));
        }
        Ok(())
    }

    /// GET /sessions/saved - on-disk sessions resumable for this cwd
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

    /// GET /session/:id/cost - session cost total
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

    /// POST /swarm - start a swarm and return its id with the spawned roster
    ///
    /// An empty `roster` asks the server for its default (coordinator,
    /// `builders` builders, reviewer). Roles whose `agent` is not `"voss"`
    /// come back `pending`: the server records them, the host spawns them.
    pub async fn create_swarm(
        &self,
        goal: &str,
        cwd: &str,
        builders: u32,
        roster: &[RoleSpec],
    ) -> Result<SwarmCreated, VossError> {
        let mut body = serde_json::json!({ "goal": goal, "cwd": cwd, "builders": builders });
        if !roster.is_empty() {
            body["roster"] =
                serde_json::to_value(roster).map_err(|e| VossError::Decode(e.to_string()))?;
        }
        let resp = self
            .auth(self.inner.post(format!("{}/swarm", self.base)))
            .timeout(REST_TIMEOUT)
            .json(&body)
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;
        resp.json().await.map_err(VossError::Http)
    }

    /// GET /swarm/:id - the swarm with its roster and the state of every task
    pub async fn swarm(&self, swarm_id: &str) -> Result<Swarm, VossError> {
        let resp = self
            .auth(self.inner.get(format!("{}/swarm/{}", self.base, swarm_id)))
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        let resp = ok_or_detail(resp).await?;
        let v: serde_json::Value = resp.json().await?;
        let swarm = v
            .get("swarm")
            .cloned()
            .ok_or_else(|| VossError::Decode("swarm: no swarm in response".into()))?;
        serde_json::from_value(swarm).map_err(|e| VossError::Decode(e.to_string()))
    }

    /// POST /swarm/:id/run - drive the swarm's CLI members
    ///
    /// Fire and forget: the server returns once the run is scheduled and reports
    /// progress over the session event stream. A swarm with no tasks is seeded
    /// from its goal first, so this is what starts work after `create_swarm`.
    pub async fn run_swarm(&self, swarm_id: &str) -> Result<(), VossError> {
        let resp = self
            .auth(
                self.inner
                    .post(format!("{}/swarm/{}/run", self.base, swarm_id)),
            )
            .timeout(REST_TIMEOUT)
            .send()
            .await?;
        ok_or_detail(resp).await?;
        Ok(())
    }

    pub async fn start_swarm(&self, swarm_id: &str) -> Result<crate::tasks::CommandAck, VossError> {
        let resp = self.auth(self.inner.post(format!("{}/swarm/{swarm_id}/run", self.base)))
            .timeout(REST_TIMEOUT).send().await?;
        let ack: crate::tasks::CommandAck = ok_or_detail(resp).await?.json().await?;
        if ack.v != 1 || ack.availability.as_ref().is_some_and(|row| row.v != 1) {
            return Err(VossError::Decode("incompatible swarm acknowledgement".into()));
        }
        Ok(ack)
    }

    /// GET /doctor - server-side diagnostics
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

pub(crate) async fn ok_or_detail(resp: reqwest::Response) -> Result<reqwest::Response, VossError> {
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
