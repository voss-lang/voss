use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskPhase {
    Idle, Active, Waiting, CandidateReady, Completed, Failed, Cancelled, Interrupted,
    #[serde(other)]
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskSnapshot {
    pub v: u32,
    pub task_id: String,
    pub session_id: String,
    pub swarm_id: Option<String>,
    pub swarm_task_id: Option<String>,
    pub run_id: Option<String>,
    pub attempt_id: Option<String>,
    pub phase: TaskPhase,
    pub outcome: Option<String>,
    pub pending_actions: Vec<Value>,
    pub watermark: u64,
    pub execution_plan: Option<crate::plans::Preview>,
    #[serde(default)]
    pub node_states: std::collections::HashMap<String, String>,
    pub graph: Option<crate::graph::Graph>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskEvent {
    pub v: u32,
    pub cursor: u64,
    pub snapshot: TaskSnapshot,
    pub event: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandAck {
    pub v: u32,
    pub status: String,
    pub availability: Option<crate::oauth::Availability>,
    pub run_id: Option<String>,
    pub attempt_id: Option<String>,
}
