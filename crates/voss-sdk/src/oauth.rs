use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Availability {
    pub v: u32,
    pub harness: String,
    pub provider: String,
    pub model: String,
    pub cli_installed: bool,
    pub available: bool,
    pub code: String,
    pub message: String,
    pub login_command: Option<String>,
    pub checked_at: String,
    pub check_scope: String,
    pub account_alias: Option<String>,
    pub account_selection: bool,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Catalog {
    pub v: u32,
    pub harnesses: Vec<Availability>,
    pub selected_harness: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Preflight {
    pub harness: String,
    pub model: String,
    pub account_alias: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Launch {
    pub v: u32,
    pub id: Option<String>,
    pub availability: Option<Availability>,
    #[serde(default)]
    pub sessions: Vec<crate::types::rest::SwarmRole>,
}
