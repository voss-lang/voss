//! `voss-cli resume <id-prefix-or-name>` — resolve and print session identity.
//! Full REPL hookup lands in R7.

use crate::session;

pub fn run_resume(id_or_name: &str) -> std::process::ExitCode {
    match session::load(id_or_name) {
        Ok(rec) => {
            println!(
                "resumed: {} ({}, {} turns)",
                rec.name,
                rec.id,
                rec.turns.len()
            );
            println!("cwd:   {}", rec.cwd);
            println!("model: {}", rec.model);
            std::process::ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("resume failed: {e}");
            std::process::ExitCode::from(1)
        }
    }
}
