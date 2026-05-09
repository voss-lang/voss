pub mod cli;
pub mod permissions;

use std::ffi::OsString;
use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "voss-cli", version)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Parse a Voss source file and print its AST as JSON.
    Ast {
        source: PathBuf,
        /// Print JSON (currently always JSON; flag accepted for parity with the Python CLI).
        #[arg(long)]
        json: bool,
        /// Print compact (single-line) JSON.
        #[arg(long)]
        compact: bool,
    },
    /// Stub — implemented in a later wave.
    Doctor,
    /// Stub — implemented in a later wave.
    Do {
        task: Vec<String>,
    },
    /// Stub — implemented in a later wave.
    Chat,
    /// Stub — implemented in a later wave.
    Sessions,
    /// Stub — implemented in a later wave.
    Resume {
        id: String,
    },
}

pub async fn run<I: IntoIterator<Item = OsString>>(argv: I) -> ExitCode {
    let cli = match Cli::try_parse_from(argv) {
        Ok(c) => c,
        Err(e) => {
            let _ = e.print();
            // clap exits 0 for --help/--version which is correct.
            return if e.use_stderr() {
                ExitCode::from(2)
            } else {
                ExitCode::SUCCESS
            };
        }
    };

    match cli.cmd {
        Cmd::Ast {
            source,
            json: _,
            compact,
        } => {
            let bridge = match voss_bridge::PyBridge::discover() {
                Ok(b) => b,
                Err(e) => {
                    eprintln!("bridge discover failed: {e}");
                    return ExitCode::from(1);
                }
            };
            match bridge.ast(&source).await {
                Ok(v) => {
                    let s = if compact {
                        serde_json::to_string(&v).unwrap_or_else(|_| "null".to_string())
                    } else {
                        serde_json::to_string_pretty(&v).unwrap_or_else(|_| "null".to_string())
                    };
                    println!("{s}");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("ast failed: {e}");
                    ExitCode::from(1)
                }
            }
        }
        Cmd::Doctor => cli::doctor::run_doctor(),
        _ => {
            eprintln!("voss-cli: unimplemented (later wave)");
            ExitCode::from(2)
        }
    }
}
