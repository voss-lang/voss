use thiserror::Error;

/// All errors returned by the voss-sdk public API.
#[derive(Debug, Error)]
pub enum VossError {
    #[error("http request failed: {0}")]
    Http(#[from] reqwest::Error),

    #[error("http status {status}: {detail}")]
    HttpStatus { status: u16, detail: String },

    #[error("sse stream error: {0}")]
    Sse(String),

    #[error("failed to decode protocol payload: {0}")]
    Decode(String),

    #[error("server handshake failed: {0}")]
    Handshake(String),

    #[error("failed to spawn voss server: {0}")]
    Spawn(#[from] std::io::Error),
}

#[cfg(test)]
mod tests {
    use super::VossError;

    #[test]
    fn http_status_formatting_does_not_include_unstored_token() {
        let token = "voss_test_token_should_not_appear";
        let error = VossError::HttpStatus {
            status: 401,
            detail: "unauthorized".into(),
        };

        let display = format!("{error}");
        let debug = format!("{error:?}");

        assert!(!display.contains(token));
        assert!(!debug.contains(token));
    }
}
