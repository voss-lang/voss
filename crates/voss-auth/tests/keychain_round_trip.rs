//! macOS Keychain round-trip. Uses a unique `$VOSS_KEYCHAIN_SERVICE` so the
//! real `Claude Code-credentials` item is never touched.

#[cfg(target_os = "macos")]
mod mac {
    use voss_auth::{
        keychain::{delete_anthropic, read_anthropic, write_anthropic},
        AnthropicOAuthCreds,
    };

    use std::sync::Mutex;
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    fn unique_service() -> String {
        let pid = std::process::id();
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        format!("voss-test-{pid}-{nanos}")
    }

    #[test]
    fn keychain_round_trip() {
        let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let svc = unique_service();
        std::env::set_var("VOSS_KEYCHAIN_SERVICE", &svc);
        let creds = AnthropicOAuthCreds {
            access_token: "AT".into(),
            refresh_token: "RT".into(),
            expires_at_ms: 1_800_000_000_000,
            subscription_type: "max".into(),
        };
        write_anthropic(&creds).expect("write");
        let got = read_anthropic().expect("read");
        // Cleanup before assertions so a panic still removes the item.
        let _ = delete_anthropic();
        std::env::remove_var("VOSS_KEYCHAIN_SERVICE");
        assert_eq!(got, creds);
    }
}

#[cfg(not(target_os = "macos"))]
#[test]
fn keychain_noop_off_macos() {
    use voss_auth::keychain::read_anthropic;
    assert!(read_anthropic().is_none());
}
