//! `voss doctor` — env diagnostics. Output mirrors `voss/harness/cli.py::doctor_cmd`.

use voss_auth::{load_anthropic_oauth, load_codex, resolve, AuthPref};

const DEFAULT_MODEL: &str = "claude-sonnet-4-5";

pub fn run_doctor() -> std::process::ExitCode {
    let model = std::env::var("VOSS_MODEL").unwrap_or_else(|_| DEFAULT_MODEL.to_string());
    println!("default model       : {model}");
    println!(
        "ANTHROPIC_API_KEY   : {}",
        if std::env::var("ANTHROPIC_API_KEY").is_ok() {
            "set"
        } else {
            "unset"
        }
    );
    println!(
        "OPENAI_API_KEY      : {}",
        if std::env::var("OPENAI_API_KEY").is_ok() {
            "set"
        } else {
            "unset"
        }
    );

    match load_anthropic_oauth() {
        Some(c) => println!(
            "Claude Code OAuth   : found ({}, expires in {}s)",
            c.subscription_type,
            c.expires_in_seconds()
        ),
        None => println!("Claude Code OAuth   : not found"),
    }

    match load_codex() {
        Some(c) => {
            let mut bits: Vec<&str> = Vec::new();
            if c.api_key.is_some() {
                bits.push("OPENAI_API_KEY");
            }
            if c.access_token.is_some() {
                bits.push("OAuth tokens");
            }
            let bits_s = if bits.is_empty() {
                "empty".to_string()
            } else {
                bits.join(", ")
            };
            println!("Codex creds         : found ({}; {})", c.auth_mode, bits_s);
        }
        None => println!("Codex creds         : not found"),
    }

    let res = resolve(AuthPref::Auto);
    println!("--auth=auto picks   : {} — {}", res.source(), res.detail());

    // Python tries `import voss_runtime`. Rust mirrors by reporting importable
    // when the package directory is present in the repo root.
    let importable = std::path::Path::new("voss_runtime").is_dir()
        || std::path::Path::new("../voss_runtime").is_dir()
        || std::path::Path::new("../../voss_runtime").is_dir();
    if importable {
        println!("voss_runtime        : importable");
    } else {
        println!("voss_runtime        : FAIL not found");
    }

    std::process::ExitCode::SUCCESS
}
