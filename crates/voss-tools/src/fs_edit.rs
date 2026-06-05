use std::path::PathBuf;

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;

use crate::sandbox::jail_path;
use crate::tool_trait::Tool;

#[derive(Deserialize, JsonSchema)]
pub struct FsEditArgs {
    pub path: String,
    /// Replacement text.
    pub new: String,
    /// Verbatim text to replace; must match exactly once. Use this OR `anchor`.
    pub old: Option<String>,
    /// Content hash (from `fs_read` annotate=true) of the first line to replace.
    pub anchor: Option<String>,
    /// Content hash of the last line of a multi-line span. Requires `anchor`.
    pub end_anchor: Option<String>,
}

pub struct FsEdit {
    pub cwd: PathBuf,
}

#[async_trait]
impl Tool for FsEdit {
    fn name(&self) -> &str {
        "fs_edit"
    }
    fn description(&self) -> &str {
        "Replace exact `old` text with `new` in a file. `old` must appear exactly once. Returns line count delta."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(FsEditArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        true
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: FsEditArgs = serde_json::from_value(args)?;
        let p = match jail_path(&self.cwd, &args.path) {
            Ok(p) => p,
            Err(e) => return Ok(format!("<error: {e}>")),
        };
        if !p.exists() {
            return Ok(format!("<error: not found: {}>", args.path));
        }
        let text = match std::fs::read_to_string(&p) {
            Ok(t) => t,
            Err(e) => return Ok(format!("<error: {e}>")),
        };
        let count = text.matches(&args.old).count();
        if count == 0 {
            return Ok(format!("<error: `old` not found in {}>", args.path));
        }
        if count > 1 {
            return Ok(format!(
                "<error: `old` matches {count} times, must be unique>"
            ));
        }
        let new_text = text.replacen(&args.old, &args.new, 1);
        if let Err(e) = std::fs::write(&p, &new_text) {
            return Ok(format!("<error: {e}>"));
        }
        let delta = (new_text.matches('\n').count() as i64) - (text.matches('\n').count() as i64);
        let sign = if delta >= 0 { "+" } else { "" };
        Ok(format!("edited {} ({sign}{delta} lines)", args.path))
    }
}
