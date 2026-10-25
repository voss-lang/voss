use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct Capabilities {
    pub v: u32,
    pub engine_version: String,
    pub capabilities: Vec<String>,
}

impl Capabilities {
    pub fn compatible(&self) -> bool {
        self.v == 1
    }

    pub fn supports(&self, capability: &str) -> bool {
        self.compatible() && self.capabilities.iter().any(|c| c == capability)
    }
}
