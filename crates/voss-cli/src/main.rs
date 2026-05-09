#[tokio::main]
async fn main() -> std::process::ExitCode {
    voss_cli::run(std::env::args_os()).await
}
