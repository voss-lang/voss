use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Check {
    pub name: String,
    pub status: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evidence {
    pub id: String,
    pub label: String,
    pub reference: String,
    pub summary: String,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Row {
    pub id: String,
    pub text: String,
    pub test_outcome: String,
    pub test_scope: String,
    pub reviewer_outcome: String,
    pub reviewer_mode: Option<String>,
    pub evidence: Vec<Evidence>,
    pub unresolved: Vec<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bundle {
    pub v: u32,
    pub status: String,
    pub message: Option<String>,
    pub session_id: String,
    pub run_id: Option<String>,
    pub task_id: String,
    pub attempt_id: String,
    pub plan_id: Option<String>,
    pub plan_revision: Option<String>,
    pub candidate_revision: Option<String>,
    pub base_revision: Option<String>,
    pub worktree: Option<String>,
    pub branch: Option<String>,
    pub current_head: Option<String>,
    pub clean: bool,
    pub evidence_revision: String,
    pub checked_at: String,
    pub criteria_source: String,
    pub rows: Vec<Row>,
    pub checks: Vec<Check>,
    pub unresolved: Vec<String>,
}
