use std::path::PathBuf;

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;

use crate::shell_capture::shell_capture_default;
use crate::tool_trait::Tool;

#[derive(Deserialize, JsonSchema, Default)]
pub struct GitStatusArgs {}

pub struct GitStatus {
    pub cwd: PathBuf,
}

#[async_trait]
impl Tool for GitStatus {
    fn name(&self) -> &str {
        "git_status"
    }
    fn description(&self) -> &str {
        "Run `git status --porcelain`."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(GitStatusArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        false
    }
    async fn invoke(&self, _args: Value) -> anyhow::Result<String> {
        Ok(shell_capture_default(&self.cwd, &["git", "status", "--porcelain"]).await)
    }
}
