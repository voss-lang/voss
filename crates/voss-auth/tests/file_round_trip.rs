use voss_auth::{
    file_store::{read_anthropic, read_codex, write_anthropic, write_codex},
    AnthropicOAuthCreds, CodexCreds,
};

/// Test helpers must serialize: HOME-override is process-global state.
use std::sync::Mutex;
static ENV_LOCK: Mutex<()> = Mutex::new(());

fn with_home<F: FnOnce()>(f: F) {
    let _g = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let tmp = tempfile::tempdir().expect("tempdir");
    let prev = std::env::var_os("HOME");
    std::env::set_var("HOME", tmp.path());
    let res = std::panic::catch_unwind(std::panic::AssertUnwindSafe(f));
    if let Some(p) = prev {
        std::env::set_var("HOME", p);
    } else {
        std::env::remove_var("HOME");
    }
    if let Err(e) = res {
        std::panic::resume_unwind(e);
    }
}

#[test]
fn anthropic_file_round_trip() {
    with_home(|| {
        let creds = AnthropicOAuthCreds {
            access_token: "AT".into(),
            refresh_token: "RT".into(),
            expires_at_ms: 1_700_000_000_000,
            subscription_type: "max".into(),
        };
        write_anthropic(&creds).expect("write");
        let got = read_anthropic().expect("read");
        assert_eq!(got, creds);

        // Verify the stored file is mode 0600 on Unix.
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let path = dirs::home_dir()
                .unwrap()
                .join(".claude")
                .join(".credentials.json");
            let mode = std::fs::metadata(&path).unwrap().permissions().mode() & 0o777;
            assert_eq!(mode, 0o600, "credentials file should be 0600, got {:o}", mode);
        }
    });
}

#[test]
fn codex_file_round_trip() {
    with_home(|| {
        let creds = CodexCreds {
            api_key: Some("sk-test".into()),
            access_token: Some("AT".into()),
            refresh_token: Some("RT".into()),
            account_id: Some("acct_1".into()),
            auth_mode: "ChatGPT".into(),
        };
        write_codex(&creds).expect("write");
        let got = read_codex().expect("read");
        assert_eq!(got, creds);
    });
}

#[test]
fn anthropic_missing_file_returns_none() {
    with_home(|| {
        assert!(read_anthropic().is_none());
    });
}

#[test]
fn codex_missing_file_returns_none() {
    with_home(|| {
        assert!(read_codex().is_none());
    });
}
