//! Hand-written REST request/response types for the local Voss harness.

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
