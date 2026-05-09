use std::path::PathBuf;

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;

use crate::sandbox::jail_path;
use crate::tool_trait::Tool;

#[derive(Deserialize, JsonSchema)]
pub struct FsReadArgs {
    /// Path relative to cwd.
    pub path: String,
}

pub struct FsRead {
    pub cwd: PathBuf,
}

#[async_trait]
impl Tool for FsRead {
    fn name(&self) -> &str {
        "fs_read"
    }
    fn description(&self) -> &str {
        "Read a UTF-8 text file from the project. Path must be inside cwd."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(FsReadArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        false
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: FsReadArgs = serde_json::from_value(args)?;
        let p = match jail_path(&self.cwd, &args.path) {
            Ok(p) => p,
            Err(e) => return Ok(format!("<error: {e}>")),
        };
        if !p.exists() {
            return Ok(format!("<error: not found: {}>", args.path));
        }
        if p.is_dir() {
            return Ok(format!("<error: is a directory: {}>", args.path));
        }
        match std::fs::read_to_string(&p) {
            Ok(s) => Ok(s),
            Err(e) if e.kind() == std::io::ErrorKind::InvalidData => {
                Ok(format!("<error: binary file: {}>", args.path))
            }
            Err(e) => Ok(format!("<error: {e}>")),
        }
    }
}
