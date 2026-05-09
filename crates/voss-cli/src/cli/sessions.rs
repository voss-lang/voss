//! `voss-cli sessions` — list saved session records, mtime-descending.

use crate::session;

pub fn run_sessions() -> std::process::ExitCode {
    match session::list_sessions() {
        Ok(records) => {
            if records.is_empty() {
                println!("(no sessions)");
                return std::process::ExitCode::SUCCESS;
            }
            for r in records {
                let id_short: String = r.id.chars().take(8).collect();
                println!(
                    "  {}  {}  {:<28}  {}",
                    id_short,
                    r.updated_at,
                    r.model,
                    r.first_task()
                );
            }
            std::process::ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("sessions: {e}");
            std::process::ExitCode::from(1)
        }
    }
}
