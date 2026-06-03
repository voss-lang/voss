//! H3.2 — thin-client invariant.
//!
//! The Rust client must hold NO credentials and reimplement NO provider/auth
//! logic: all of that stays server-side (Python). This grep-gate fails the
//! build if a credential identifier leaks into the client sources, so the
//! invariant cannot silently regress.

const SOURCES: &[(&str, &str)] = &[
    ("lib.rs", include_str!("../src/lib.rs")),
    ("main.rs", include_str!("../src/main.rs")),
    ("event.rs", include_str!("../src/event.rs")),
    ("net.rs", include_str!("../src/net.rs")),
    ("server.rs", include_str!("../src/server.rs")),
    ("app.rs", include_str!("../src/app.rs")),
    ("doctor.rs", include_str!("../src/doctor.rs")),
];

#[test]
fn client_references_no_credential_identifiers() {
    // Concrete credential/provider identifiers — NOT the generic word
    // "credential" (which may appear in a comment explaining the invariant).
    let forbidden = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "anthropic_oauth",
        "codex_oauth",
        "client_secret",
        "refresh_token",
        "keyring",
        "keychain",
        "get_generic_password",
    ];
    for (name, src) in SOURCES {
        for needle in forbidden {
            assert!(
                !src.contains(needle),
                "thin-client invariant violated: {name} references `{needle}` — \
                 auth/providers must stay server-side"
            );
        }
    }
}
