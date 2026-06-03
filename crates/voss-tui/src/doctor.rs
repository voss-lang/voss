//! `voss-tui doctor` (H3.1).
//!
//! The thin client reimplements NO diagnostics: it asks the server's `/doctor`
//! (which runs the harness's own `diagnostics.run_all_checks`, the same source
//! `voss doctor` uses) and renders the result. Returns the server's exit code.

use anyhow::Result;
use serde::Deserialize;

use crate::net::HttpClient;

#[derive(Debug, Deserialize)]
pub struct DoctorCheck {
    pub name: String,
    pub status: String, // OK | WARN | FAIL
    #[serde(default)]
    pub detail: String,
    #[serde(default)]
    pub fix: String,
}

#[derive(Debug, Deserialize)]
pub struct DoctorReport {
    pub auth_source: String,
    pub auth_detail: String,
    pub has_provider: bool,
    pub default_model: String,
    #[serde(default)]
    pub exit_code: i32,
    #[serde(default)]
    pub checks: Vec<DoctorCheck>,
}

fn glyph(status: &str) -> &'static str {
    match status {
        "OK" => "✓",
        "WARN" => "⚠",
        "FAIL" => "✗",
        _ => "?",
    }
}

/// Fetch + render the server diagnostics. Returns the server's aggregate exit code.
pub async fn run(http: &HttpClient, cwd: &str) -> Result<i32> {
    let r = http.doctor(cwd).await?;
    println!("  auth      : {} — {}", r.auth_source, r.auth_detail);
    println!(
        "  provider  : {}",
        if r.has_provider { "resolved" } else { "none" }
    );
    println!("  model     : {}", r.default_model);
    for c in &r.checks {
        println!("  {} {:<22} {}", glyph(&c.status), c.name, c.detail);
        if c.status != "OK" && !c.fix.is_empty() {
            println!("       → {}", c.fix);
        }
    }
    Ok(r.exit_code)
}
