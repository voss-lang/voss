use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Source {
    pub kind: String,
    pub text: String,
    pub reference: Option<String>,
    pub revision: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Context { pub id: String, pub text: String }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scope { pub allow: Vec<String>, pub deny: Vec<String> }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Briefing {
    pub source: Source,
    pub cwd: String,
    pub harness: String,
    pub model: String,
    pub tier: String,
    pub scope: Scope,
    #[serde(default)]
    pub context: Vec<Context>,
    pub swarm: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: String,
    pub goal: String,
    pub depends_on: Vec<String>,
    pub files: Vec<String>,
    pub criteria: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Preview {
    pub v: u32,
    pub id: String,
    pub revision: String,
    pub briefing: Briefing,
    pub input_revision: String,
    pub base_revision: String,
    pub base_branch: Option<String>,
    pub provider: Option<String>,
    pub workspace_revision: String,
    pub tasks: Vec<Node>,
    pub accepted_context: Vec<String>,
    pub execution: String,
    pub policy: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Result {
    pub v: u32,
    pub status: String,
    pub message: Option<String>,
    pub availability: Option<crate::oauth::Availability>,
    pub preview: Option<Preview>,
    pub session_id: Option<String>,
    pub run_id: Option<String>,
    pub attempt_id: Option<String>,
}
