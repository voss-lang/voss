use std::path::PathBuf;

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;

use crate::shell_capture::shell_capture_default;
use crate::tool_trait::Tool;

#[derive(Deserialize, JsonSchema)]
pub struct GitDiffArgs {
    /// Pass `--cached` (staged) when true.
    #[serde(default)]
    pub staged: bool,
    /// Optional path argument for git diff.
    #[serde(default)]
    pub path: String,
}

pub struct GitDiff {
    pub cwd: PathBuf,
}

#[async_trait]
impl Tool for GitDiff {
    fn name(&self) -> &str {
        "git_diff"
    }
    fn description(&self) -> &str {
        "Run `git diff` (unstaged) or `git diff --cached` (staged) on optional path."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(GitDiffArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        false
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: GitDiffArgs = serde_json::from_value(args)?;
        let mut argv: Vec<&str> = vec!["git", "diff"];
        if args.staged {
            argv.push("--cached");
        }
        if !args.path.is_empty() {
            argv.push(args.path.as_str());
        }
        Ok(shell_capture_default(&self.cwd, &argv).await)
    }
}
