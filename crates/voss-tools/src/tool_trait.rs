//! `Tool` trait shared by every concrete tool impl.
//!
//! Per D-12: `is_mutating` is a static, data-driven flag. Read-only tools
//! fan out concurrently; mutating tools execute serially in plan order.

use async_trait::async_trait;
use serde_json::Value;

#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    /// JSON Schema for the tool's arguments. Derived via schemars in concrete impls.
    fn schema(&self) -> Value;
    /// True iff invoking this tool may mutate state outside the agent. (D-12)
    fn is_mutating(&self) -> bool;
    async fn invoke(&self, args: Value) -> anyhow::Result<String>;
}
