//! macOS Keychain access for Anthropic OAuth (stub; T2 fills it in).

use crate::anthropic::AnthropicOAuthCreds;

pub fn read_anthropic() -> Option<AnthropicOAuthCreds> {
    None
}

pub fn write_anthropic(_creds: &AnthropicOAuthCreds) -> std::io::Result<()> {
    Err(std::io::Error::new(
        std::io::ErrorKind::Unsupported,
        "keychain stub",
    ))
}
