//! Plan + ToolCall — Rust mirror of `voss/harness/agent.py::Plan / ToolCall`.
//!
//! Field names and required-ness MUST match the Python pydantic schema.
//! Drift is enforced as a CI failure by
//! `crates/voss-providers/tests/schema_parity.rs`.

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct ToolCall {
    /// Tool name from the available tool list.
    pub name: String,

    /// Keyword arguments.
    #[serde(default)]
    pub args: serde_json::Map<String, serde_json::Value>,

    /// One-line rationale for this call.
    #[serde(default)]
    pub why: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct Plan {
    /// One-paragraph reasoning for the chosen approach.
    pub rationale: String,

    /// Sequential tool calls.
    #[serde(default)]
    pub steps: Vec<ToolCall>,

    /// Self-rated confidence the plan resolves the user's task. 0.0-1.0.
    pub confidence: f32,

    /// If confidence is low, the clarifying question to ask the user.
    #[serde(default)]
    pub open_question: Option<String>,

    /// The answer to surface to the user once tools have run. May reference results.
    #[serde(default)]
    pub final_when_done: String,
}
