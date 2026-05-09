//! voss-auth — credential discovery, refresh, and resolution for Claude
//! (Anthropic OAuth) and Codex (OpenAI) auth.

pub mod anthropic;
pub mod codex;
pub mod file_store;
pub mod keychain;
pub mod refresh;
pub mod resolve;

pub use anthropic::{
    AnthropicOAuthCreds, ANTHROPIC_API_BASE, ANTHROPIC_OAUTH_BETA, ANTHROPIC_TOKEN_URL,
    CLAUDE_CODE_CLIENT_ID, KEYCHAIN_SERVICE,
};
pub use codex::{
    CodexCreds, CHATGPT_BACKEND_BASE, CODEX_CLIENT_ID, OPENAI_API_BASE, OPENAI_TOKEN_URL,
};
pub use refresh::{refresh_anthropic, refresh_codex};
pub use resolve::{resolve, AuthPref, Resolution};

/// Load Anthropic OAuth credentials from Keychain (macOS) or fall back to
/// `~/.claude/.credentials.json`.
pub fn load_anthropic_oauth() -> Option<AnthropicOAuthCreds> {
    keychain::read_anthropic().or_else(file_store::read_anthropic)
}

/// Load Codex credentials from `~/.codex/auth.json`.
pub fn load_codex() -> Option<CodexCreds> {
    file_store::read_codex()
}

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
