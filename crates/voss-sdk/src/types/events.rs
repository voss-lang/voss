// PLACEHOLDER: replace with `cargo typify contracts/events.schema.json` output in Wave 5 (V13.2-06).

use serde::{Deserialize, Serialize};

fn default_protocol_version() -> u32 {
    1
}

fn default_json_object() -> serde_json::Value {
    serde_json::Value::Object(serde_json::Map::new())
}

fn default_dimension() -> String {
    "tool".to_string()
}

fn default_cognition_budget() -> i64 {
    6000
}

fn default_principles_budget() -> i64 {
    1000
}

fn default_budget_unit() -> String {
    "tokens".to_string()
}

#[derive(Deserialize, Serialize, Clone, Debug)]
#[serde(tag = "type")]
pub enum AgentEvent {
    #[serde(rename = "server.connected")]
    ServerConnected(ServerConnected),
    #[serde(rename = "session.idle")]
    SessionIdle(SessionIdle),
    #[serde(rename = "permission.updated")]
    PermissionUpdated(PermissionUpdated),
    #[serde(rename = "banner")]
    BannerEvent(BannerEvent),
    #[serde(rename = "user")]
    UserEvent(UserEvent),
    #[serde(rename = "thinking")]
    ThinkingEvent(ThinkingEvent),
    #[serde(rename = "plan")]
    PlanEvent(PlanEvent),
    #[serde(rename = "tool")]
    ToolEvent(ToolEvent),
    #[serde(rename = "clarify")]
    ClarifyEvent(ClarifyEvent),
    #[serde(rename = "final")]
    FinalEvent(FinalEvent),
    #[serde(rename = "stream.delta")]
    StreamDelta(StreamDelta),
    #[serde(rename = "stream.finalize")]
    StreamFinalize(StreamFinalize),
    #[serde(rename = "status")]
    StatusEvent(StatusEvent),
    #[serde(rename = "cognition_loaded")]
    CognitionLoaded(CognitionLoaded),
    #[serde(rename = "cognition_overflow")]
    CognitionOverflow(CognitionOverflow),
    #[serde(rename = "principles_overflow")]
    PrinciplesOverflow(PrinciplesOverflow),
    #[serde(rename = "warning")]
    WarningEvent(WarningEvent),
    #[serde(rename = "probable")]
    ProbableEvent(ProbableEvent),
    #[serde(rename = "budget.updated")]
    BudgetUpdated(BudgetUpdated),
    #[serde(rename = "confidence.updated")]
    ConfidenceUpdated(ConfidenceUpdated),
    #[serde(rename = "gate.updated")]
    GateUpdated(GateUpdated),
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ServerConnected {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct SessionIdle {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub session_id: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct PermissionUpdated {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub id: String,
    pub tool_name: String,
    #[serde(default = "default_json_object")]
    pub args: serde_json::Value,
    #[serde(default = "default_dimension")]
    pub dimension: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct BannerEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub model: String,
    pub cwd: String,
    pub git: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct UserEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub task: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ThinkingEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub label: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct PlanStep {
    pub name: String,
    #[serde(default = "default_json_object")]
    pub args: serde_json::Value,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct PlanEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub confidence: f64,
    #[serde(default)]
    pub steps: Vec<PlanStep>,
    pub cost_usd: f64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ToolEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub name: String,
    #[serde(default = "default_json_object")]
    pub args: serde_json::Value,
    #[serde(default)]
    pub summary: String,
    pub state: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ClarifyEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub question: String,
    pub confidence: f64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct FinalEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub text: String,
    pub confidence: f64,
    pub cost_usd: f64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct StreamDelta {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub text: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct StreamFinalize {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub role: String,
    #[serde(default)]
    pub confidence: Option<f64>,
    #[serde(default)]
    pub cost_usd: Option<f64>,
    #[serde(default)]
    pub timestamp: Option<String>,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct StatusEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub model: String,
    pub tokens: u64,
    pub cost_usd: f64,
    pub ctx_pct: f64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct CognitionLoaded {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub architecture_tokens: i64,
    pub constraints_count: i64,
    #[serde(default)]
    pub plans_loaded: i64,
    #[serde(default)]
    pub decisions_loaded: i64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct CognitionOverflow {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub architecture_tokens: i64,
    #[serde(default = "default_cognition_budget")]
    pub budget: i64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct PrinciplesOverflow {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub principles_tokens: i64,
    #[serde(default = "default_principles_budget")]
    pub budget: i64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct WarningEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub message: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct Alternative {
    pub text: String,
    pub probability: f64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ProbableEvent {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub text: String,
    pub probability: f64,
    #[serde(default)]
    pub alternatives: Vec<Alternative>,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct BudgetUpdated {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub session_id: String,
    pub spent: f64,
    pub limit: f64,
    pub remaining: f64,
    #[serde(default = "default_budget_unit")]
    pub unit: String,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ConfidenceUpdated {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub session_id: String,
    #[serde(default)]
    pub message_id: Option<String>,
    pub score: f64,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct GateUpdated {
    #[serde(default = "default_protocol_version")]
    pub v: u32,
    pub session_id: String,
    pub gate: String,
    pub decision: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn deserializes_stream_delta() {
        let event: AgentEvent =
            serde_json::from_str(r#"{"v":1,"type":"stream.delta","text":"hi"}"#).unwrap();

        match event {
            AgentEvent::StreamDelta(payload) => assert_eq!(payload.text, "hi"),
            _ => panic!("expected StreamDelta"),
        }
    }

    #[test]
    fn deserializes_session_idle() {
        let event: AgentEvent =
            serde_json::from_str(r#"{"v":1,"type":"session.idle","session_id":"s"}"#).unwrap();

        match event {
            AgentEvent::SessionIdle(payload) => assert_eq!(payload.session_id, "s"),
            _ => panic!("expected SessionIdle"),
        }
    }

    #[test]
    fn deserializes_server_connected() {
        let event: AgentEvent =
            serde_json::from_str(r#"{"v":1,"type":"server.connected"}"#).unwrap();

        match event {
            AgentEvent::ServerConnected(payload) => assert_eq!(payload.v, 1),
            _ => panic!("expected ServerConnected"),
        }
    }

    #[test]
    fn agent_event_match_is_exhaustive() {
        fn assert_exhaustive(event: AgentEvent) -> &'static str {
            match event {
                AgentEvent::ServerConnected(_) => "server.connected",
                AgentEvent::SessionIdle(_) => "session.idle",
                AgentEvent::PermissionUpdated(_) => "permission.updated",
                AgentEvent::BannerEvent(_) => "banner",
                AgentEvent::UserEvent(_) => "user",
                AgentEvent::ThinkingEvent(_) => "thinking",
                AgentEvent::PlanEvent(_) => "plan",
                AgentEvent::ToolEvent(_) => "tool",
                AgentEvent::ClarifyEvent(_) => "clarify",
                AgentEvent::FinalEvent(_) => "final",
                AgentEvent::StreamDelta(_) => "stream.delta",
                AgentEvent::StreamFinalize(_) => "stream.finalize",
                AgentEvent::StatusEvent(_) => "status",
                AgentEvent::CognitionLoaded(_) => "cognition_loaded",
                AgentEvent::CognitionOverflow(_) => "cognition_overflow",
                AgentEvent::PrinciplesOverflow(_) => "principles_overflow",
                AgentEvent::WarningEvent(_) => "warning",
                AgentEvent::ProbableEvent(_) => "probable",
                AgentEvent::BudgetUpdated(_) => "budget.updated",
                AgentEvent::ConfidenceUpdated(_) => "confidence.updated",
                AgentEvent::GateUpdated(_) => "gate.updated",
            }
        }

        let event = AgentEvent::ServerConnected(ServerConnected { v: 1 });
        assert_eq!(assert_exhaustive(event), "server.connected");
    }
}
