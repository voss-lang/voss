use std::path::PathBuf;

use async_trait::async_trait;
use globset::{Glob, GlobMatcher};
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;
use walkdir::WalkDir;

use crate::tool_trait::Tool;

#[derive(Deserialize, JsonSchema)]
pub struct FsGlobArgs {
    /// Glob pattern (e.g. `**/*.rs`).
    pub pattern: String,
}

pub struct FsGlob {
    pub cwd: PathBuf,
}

fn matcher_for(pattern: &str) -> Option<GlobMatcher> {
    Glob::new(pattern).ok().map(|g| g.compile_matcher())
}

#[async_trait]
impl Tool for FsGlob {
    fn name(&self) -> &str {
        "fs_glob"
    }
    fn description(&self) -> &str {
        "List files matching a glob pattern, relative to cwd."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(FsGlobArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        false
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: FsGlobArgs = serde_json::from_value(args)?;
        let m = match matcher_for(&args.pattern) {
            Some(m) => m,
            None => return Ok(format!("<error: bad glob: {}>", args.pattern)),
        };
        let cwd = match self.cwd.canonicalize() {
            Ok(c) => c,
            Err(_) => self.cwd.clone(),
        };
        let mut hits: Vec<String> = Vec::new();
        for entry in WalkDir::new(&cwd).into_iter().filter_map(|e| e.ok()) {
            if !entry.file_type().is_file() {
                continue;
            }
            let path = entry.path();
            let rel = match path.strip_prefix(&cwd) {
                Ok(r) => r,
                Err(_) => continue,
            };
            if m.is_match(rel) {
                hits.push(rel.to_string_lossy().into_owned());
            }
        }
        hits.sort();
        Ok(if hits.is_empty() {
            "<no matches>".to_string()
        } else {
            hits.join("\n")
        })
    }
}
