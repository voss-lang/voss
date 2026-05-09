//! ~/.claude/.credentials.json + ~/.codex/auth.json (stub; T2 fills it in).

use crate::anthropic::AnthropicOAuthCreds;
use crate::codex::CodexCreds;

pub fn read_anthropic() -> Option<AnthropicOAuthCreds> {
    None
}

pub fn write_anthropic(_creds: &AnthropicOAuthCreds) -> std::io::Result<()> {
    Ok(())
}

pub fn read_codex() -> Option<CodexCreds> {
    None
}

pub fn write_codex(_creds: &CodexCreds) -> std::io::Result<()> {
    Ok(())
}
