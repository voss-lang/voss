use serde::Deserialize;

use crate::client::VossClient;
use crate::error::VossError;

/// Parsed from the one-line `{"v":1,"port":...,"token":...}` emitted by
/// `voss serve` on startup.
///
/// This helper only models the local server bearer token handshake. Provider
/// credentials and JSON-RPC transport authentication are separate concerns.
#[derive(Debug, Deserialize)]
pub struct Handshake {
    pub port: u16,
    pub token: String,
}

impl Handshake {
    pub fn from_line(line: &str) -> Result<Self, VossError> {
        serde_json::from_str(line).map_err(|e| VossError::Handshake(e.to_string()))
    }

    pub fn into_client(self) -> VossClient {
        VossClient::new(format!("http://127.0.0.1:{}", self.port), self.token)
    }
}

#[cfg(test)]
mod tests {
    use super::Handshake;
    use crate::error::VossError;

    #[test]
    fn parses_handshake_line() {
        let handshake = Handshake::from_line(r#"{"v":1,"port":54321,"token":"abc"}"#).unwrap();

        assert_eq!(handshake.port, 54321);
        assert_eq!(handshake.token, "abc");
    }

    #[test]
    fn invalid_json_maps_to_handshake_error() {
        let error = Handshake::from_line("not json").unwrap_err();

        assert!(matches!(error, VossError::Handshake(_)));
    }

    #[test]
    fn handshake_into_client_binds_loopback_base() {
        let client = Handshake {
            port: 54321,
            token: "abc".into(),
        }
        .into_client();

        assert_eq!(client.base, "http://127.0.0.1:54321");
    }

    #[test]
    fn handshake_ignores_protocol_version_field() {
        let handshake = Handshake::from_line(r#"{"v":1,"port":54321,"token":"abc"}"#).unwrap();

        assert_eq!(handshake.port, 54321);
        assert_eq!(handshake.token, "abc");
    }
}
