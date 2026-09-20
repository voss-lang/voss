//! Hand-written REST request/response types for the local Voss harness

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SavedSession {
    pub id: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub cwd: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub updated_at: String,
    #[serde(default)]
    pub total_cost_usd: f64,
    #[serde(default)]
    pub turns: u64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DoctorCheck {
    pub name: String,
    pub status: String,
    #[serde(default)]
    pub detail: String,
    #[serde(default)]
    pub fix: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct DoctorReport {
    pub auth_source: String,
    pub auth_detail: String,
    pub has_provider: bool,
    pub default_model: String,
    #[serde(default)]
    pub exit_code: i32,
    #[serde(default)]
    pub checks: Vec<DoctorCheck>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CostInfo {
    pub total_usd: f64,
    pub turns: u64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SessionInfo {
    pub id: String,
    #[serde(default)]
    pub cwd: String,
    #[serde(default)]
    pub model: String,
}

/// One role in a requested swarm roster (`POST /swarm`).
///
/// `agent` names the executor: `"voss"` is the harness's own in-process loop,
/// any other value names a CLI the host spawns in the role's own worktree.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RoleSpec {
    pub name: String,
    #[serde(default = "native_agent")]
    pub agent: String,
    #[serde(default)]
    pub command: String,
    #[serde(default)]
    pub args: Vec<String>,
    #[serde(default = "default_model")]
    pub model: String,
    #[serde(default = "auto_auth")]
    pub auth_pref: String,
}

fn native_agent() -> String {
    "voss".into()
}

fn default_model() -> String {
    "default".into()
}

fn auto_auth() -> String {
    "auto".into()
}

impl RoleSpec {
    /// A role run by the harness itself.
    pub fn native(name: &str) -> Self {
        Self {
            name: name.into(),
            agent: native_agent(),
            command: String::new(),
            args: Vec::new(),
            model: default_model(),
            auth_pref: auto_auth(),
        }
    }

    /// A role the host spawns as a CLI. The server returns it as pending.
    pub fn cli(name: &str, agent: &str) -> Self {
        Self {
            agent: agent.into(),
            ..Self::native(name)
        }
    }
}

/// One roster entry as the server answered it.
///
/// Native roles carry the `session_id` of the harness session already running
/// them. CLI roles carry no session and are marked `pending`: the server
/// records the axis but leaves the spawning to the host.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SwarmRole {
    #[serde(default)]
    pub session_id: Option<String>,
    pub role: String,
    #[serde(default)]
    pub agent: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub pending: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SwarmCreated {
    pub id: String,
    #[serde(default)]
    pub sessions: Vec<SwarmRole>,
}

/// One task in a swarm's plan, as `GET /swarm/{id}` reports it.
///
/// `state` is the store's own vocabulary: `open`, `assigned`, `candidate_ready`
/// or `done`.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct SwarmTask {
    pub id: String,
    #[serde(default)]
    pub goal: String,
    #[serde(default)]
    pub owned_files: Vec<String>,
    #[serde(default)]
    pub depends_on: Vec<String>,
    #[serde(default)]
    pub state: String,
    #[serde(default)]
    pub candidate_branch: Option<String>,
    #[serde(default)]
    pub candidate_worktree: Option<String>,
    #[serde(default)]
    pub candidate_head: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Swarm {
    pub id: String,
    #[serde(default)]
    pub goal: String,
    #[serde(default)]
    pub cwd: String,
    #[serde(default)]
    pub roster: Vec<RoleSpec>,
    #[serde(default)]
    pub tasks: Vec<SwarmTask>,
}
