use std::path::PathBuf;

use async_trait::async_trait;
use globset::{Glob, GlobMatcher};
use regex::Regex;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;
use walkdir::WalkDir;

use crate::tool_trait::Tool;

const MAX_HITS: usize = 200;

fn default_glob() -> String {
    "**/*".to_string()
}

#[derive(Deserialize, JsonSchema)]
pub struct FsGrepArgs {
    /// Regex pattern.
    pub pattern: String,
    /// Glob filter (default: `**/*`).
    #[serde(default = "default_glob")]
    pub glob: String,
}

pub struct FsGrep {
    pub cwd: PathBuf,
}

fn matcher_for(pattern: &str) -> Option<GlobMatcher> {
    Glob::new(pattern).ok().map(|g| g.compile_matcher())
}

#[async_trait]
impl Tool for FsGrep {
    fn name(&self) -> &str {
        "fs_grep"
    }
    fn description(&self) -> &str {
        "Recursively search for a regex pattern. Returns matching lines with file:line."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(FsGrepArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        false
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: FsGrepArgs = serde_json::from_value(args)?;
        let rx = match Regex::new(&args.pattern) {
            Ok(r) => r,
            Err(e) => return Ok(format!("<error: bad regex: {e}>")),
        };
        let glob_m = match matcher_for(&args.glob) {
            Some(m) => m,
            None => return Ok(format!("<error: bad glob: {}>", args.glob)),
        };
        let cwd = self.cwd.canonicalize().unwrap_or_else(|_| self.cwd.clone());
        let mut hits: Vec<String> = Vec::new();
        'outer: for entry in WalkDir::new(&cwd).into_iter().filter_map(|e| e.ok()) {
            if !entry.file_type().is_file() {
                continue;
            }
            let path = entry.path();
            let rel = match path.strip_prefix(&cwd) {
                Ok(r) => r,
                Err(_) => continue,
            };
            if !glob_m.is_match(rel) {
                continue;
            }
            let text = match std::fs::read_to_string(path) {
                Ok(t) => t,
                Err(_) => continue,
            };
            for (i, line) in text.lines().enumerate() {
                if rx.is_match(line) {
                    hits.push(format!("{}:{}: {}", rel.display(), i + 1, line));
                    if hits.len() >= MAX_HITS {
                        break 'outer;
                    }
                }
            }
        }
        Ok(if hits.is_empty() {
            "<no matches>".to_string()
        } else {
            hits.join("\n")
        })
    }
}
