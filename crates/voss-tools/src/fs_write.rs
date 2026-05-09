use std::path::PathBuf;

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;

use crate::sandbox::jail_path;
use crate::tool_trait::Tool;

#[derive(Deserialize, JsonSchema)]
pub struct FsWriteArgs {
    /// Path relative to cwd.
    pub path: String,
    /// File contents.
    pub content: String,
}

pub struct FsWrite {
    pub cwd: PathBuf,
}

#[async_trait]
impl Tool for FsWrite {
    fn name(&self) -> &str {
        "fs_write"
    }
    fn description(&self) -> &str {
        "Write text to a file inside cwd. Creates parent dirs. Overwrites existing."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(FsWriteArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        true
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: FsWriteArgs = serde_json::from_value(args)?;
        let p = match jail_path(&self.cwd, &args.path) {
            Ok(p) => p,
            Err(e) => return Ok(format!("<error: {e}>")),
        };
        if let Some(parent) = p.parent() {
            if let Err(e) = std::fs::create_dir_all(parent) {
                return Ok(format!("<error: {e}>"));
            }
        }
        if let Err(e) = std::fs::write(&p, &args.content) {
            return Ok(format!("<error: {e}>"));
        }
        Ok(format!(
            "wrote {} bytes to {}",
            args.content.len(),
            args.path
        ))
    }
}
