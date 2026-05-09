//! `voss_check` tool — delegates to `voss_bridge::PyBridge::check`.
//!
//! Bridge caching: a single `PyBridge` instance is constructed lazily on
//! first call and reused for the lifetime of the `VossCheck` tool. This
//! amortizes the Python subprocess startup over repeated checks within a
//! session. (Per-invoke construction would re-spawn Python on every call.)

use std::path::{Path, PathBuf};

use async_trait::async_trait;
use schemars::JsonSchema;
use serde::Deserialize;
use serde_json::Value;
use tokio::sync::OnceCell;

use crate::sandbox::jail_path;
use crate::tool_trait::Tool;
use voss_bridge::PyBridge;

fn default_path() -> String {
    ".".to_string()
}

#[derive(Deserialize, JsonSchema)]
pub struct VossCheckArgs {
    /// Path (file or directory) to check.
    #[serde(default = "default_path")]
    pub path: String,
}

pub struct VossCheck {
    pub cwd: PathBuf,
    bridge: OnceCell<PyBridge>,
}

impl VossCheck {
    pub fn new(cwd: PathBuf) -> Self {
        Self {
            cwd,
            bridge: OnceCell::new(),
        }
    }

    async fn bridge(&self) -> anyhow::Result<&PyBridge> {
        self.bridge
            .get_or_try_init(|| async { PyBridge::discover().map_err(anyhow::Error::from) })
            .await
    }
}

#[async_trait]
impl Tool for VossCheck {
    fn name(&self) -> &str {
        "voss_check"
    }
    fn description(&self) -> &str {
        "Run `voss check` on a .voss file or directory. Returns analyzer diagnostics."
    }
    fn schema(&self) -> Value {
        serde_json::to_value(schemars::schema_for!(VossCheckArgs)).unwrap()
    }
    fn is_mutating(&self) -> bool {
        false
    }
    async fn invoke(&self, args: Value) -> anyhow::Result<String> {
        let args: VossCheckArgs = serde_json::from_value(args)?;
        let p = match jail_path(&self.cwd, &args.path) {
            Ok(p) => p,
            Err(e) => return Ok(format!("<error: {e}>")),
        };
        let bridge = self.bridge().await?;
        match bridge.check(Path::new(&p)).await {
            Ok(v) => {
                // Python tool prints raw diagnostics text; we surface JSON
                // result for now (parity test only checks args schema).
                Ok(serde_json::to_string_pretty(&v)
                    .unwrap_or_else(|_| "<error: bad json>".to_string()))
            }
            Err(e) => Ok(format!("<error: {e}>")),
        }
    }
}
