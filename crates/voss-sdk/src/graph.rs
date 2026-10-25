use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Attempt {
    pub id: String,
    pub run_id: Option<String>,
    pub plan_revision: String,
    pub role: Option<String>,
    pub harness: Option<String>,
    pub provider: Option<String>,
    pub model: Option<String>,
    pub session_id: Option<String>,
    pub state: String,
    pub branch: Option<String>,
    pub worktree: Option<String>,
    pub repository: Option<String>,
    pub base_revision: Option<String>,
    pub candidate_revision: Option<String>,
    pub review_state: String,
    pub blockers: Vec<String>,
    pub started_at: Option<String>,
    pub ended_at: Option<String>,
    pub output_after: Option<u64>,
    pub output_through: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: String,
    pub goal: String,
    pub depends_on: Vec<String>,
    pub files: Vec<String>,
    pub criteria: Vec<String>,
    pub state: String,
    pub harness: Option<String>,
    pub provider: Option<String>,
    pub model: Option<String>,
    pub blocked_by: Vec<String>,
    pub blockers: Vec<String>,
    pub attempts: Vec<Attempt>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Graph {
    pub v: u32,
    pub source: String,
    pub plan_id: String,
    pub revision: String,
    pub run_id: Option<String>,
    pub owner_session_id: String,
    pub updated_at: String,
    pub nodes: Vec<Node>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Output {
    pub v: u32,
    pub status: String,
    pub message: Option<String>,
    pub events: Vec<serde_json::Value>,
    pub next_cursor: u64,
    pub has_more: bool,
}
