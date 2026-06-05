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
        "Replace text with `new` in a file. Supply either `old` (verbatim, must match exactly once) or `anchor` (line content-hash from fs_read annotate=true; add `end_anchor` for a multi-line span). Returns line count delta."
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
        if args.old.is_some() && args.anchor.is_some() {
            return Ok("<error: supply `old` OR `anchor`, not both>".to_string());
        }
        if args.anchor.is_none() && args.end_anchor.is_some() {
            return Ok("<error: `end_anchor` requires `anchor`>".to_string());
        }
        let new_text = if let Some(anchor) = &args.anchor {
            let segs: Vec<&str> = text.split('\n').collect();
            let start = match crate::anchor::resolve(&segs, anchor) {
                Ok(i) => i,
                Err(e) => return Ok(format!("<error: {e}>")),
            };
            let end = match &args.end_anchor {
                Some(ea) => match crate::anchor::resolve(&segs, ea) {
                    Ok(i) => i,
                    Err(e) => return Ok(format!("<error: {e}>")),
                },
                None => start,
            };
            if end < start {
                return Ok("<error: `end_anchor` is before `anchor`>".to_string());
            }
            let new_segs: Vec<&str> = args.new.split('\n').collect();
            let mut out: Vec<&str> = Vec::with_capacity(segs.len());
            out.extend_from_slice(&segs[..start]);
            out.extend_from_slice(&new_segs);
            out.extend_from_slice(&segs[end + 1..]);
            out.join("\n")
        } else if let Some(old) = &args.old {
            let count = text.matches(old).count();
            if count == 0 {
                return Ok(format!("<error: `old` not found in {}>", args.path));
            }
            if count > 1 {
                return Ok(format!(
                    "<error: `old` matches {count} times, must be unique>"
                ));
            }
            text.replacen(old, &args.new, 1)
        } else {
            return Ok("<error: supply `old` or `anchor`>".to_string());
        };
        if let Err(e) = std::fs::write(&p, &new_text) {
            return Ok(format!("<error: {e}>"));
        }
        let delta = (new_text.matches('\n').count() as i64) - (text.matches('\n').count() as i64);
        let sign = if delta >= 0 { "+" } else { "" };
        Ok(format!("edited {} ({sign}{delta} lines)", args.path))
    }
}
