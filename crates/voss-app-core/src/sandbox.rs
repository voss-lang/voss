//! VCKP-13a OS scope-sandbox — per-run profile generation + wrapper argv.
//!
//! The CLI-agnostic enforcement floor for managed launches: the spawned CLI's
//! filesystem writes are denied at the kernel outside the declared scope.
//! macOS uses Seatbelt (`sandbox-exec -f profile.sb`); Linux uses `bwrap`
//! best-effort. When no sandbox tool is available the caller receives
//! `WrapOutcome::Unavailable` and MUST downgrade the displayed capability tier
//! honestly (never claim enforcement that is not active).
//!
//! Security invariants (T-V14-04/05, V5/V12):
//! - Scope paths are canonicalized + validated BEFORE any profile is built;
//!   traversal (`..`), relative paths, and profile-injection characters are
//!   rejected.
//! - The write policy starts from `(deny file-write*)` and allows ONLY the
//!   canonical scope subpath, the temp dirs, and `/dev/` (PTY ttys) — never
//!   `allow default` for writes.

use std::path::PathBuf;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum SandboxError {
    #[error("invalid scope path: {0}")]
    InvalidScope(String),
}

/// Canonicalize + validate a scope path (mirror of the `is_safe_run_id`
/// discipline, applied to filesystem scopes). Rejects empty/relative paths,
/// traversal segments, profile-injection characters, and non-directories.
pub fn validate_scope(scope: &str) -> Result<PathBuf, SandboxError> {
    if scope.trim().is_empty() {
        return Err(SandboxError::InvalidScope("empty".into()));
    }
    if scope.contains("..") {
        return Err(SandboxError::InvalidScope("traversal rejected".into()));
    }
    // Characters that could escape the quoted Seatbelt string literal.
    if scope.contains('"') || scope.contains('\n') || scope.contains('\\') {
        return Err(SandboxError::InvalidScope(
            "profile-unsafe character".into(),
        ));
    }
    let p = std::path::Path::new(scope);
    if !p.is_absolute() {
        return Err(SandboxError::InvalidScope("must be absolute".into()));
    }
    let canon = p
        .canonicalize()
        .map_err(|e| SandboxError::InvalidScope(format!("cannot canonicalize: {e}")))?;
    if !canon.is_dir() {
        return Err(SandboxError::InvalidScope("not a directory".into()));
    }
    let canon_str = canon.to_string_lossy();
    if canon_str.contains('"') || canon_str.contains('\n') || canon_str.contains('\\') {
        return Err(SandboxError::InvalidScope(
            "canonical path profile-unsafe".into(),
        ));
    }
    Ok(canon)
}

/// Generate the per-run Seatbelt profile. Write policy starts from
/// `(deny file-write*)`; only the canonical scope, temp dirs, and `/dev/`
/// (the PTY tty the CLI writes its output to) are writable. Reads stay open
/// (`allow default`) — the floor targets write blast-radius (V12: never widen).
pub fn generate_profile(scope_abs: &str) -> Result<String, SandboxError> {
    let canon = validate_scope(scope_abs)?;
    Ok(format!(
        r#"(version 1)
(allow default)
(deny file-write*)
(allow file-write* (subpath "{scope}"))
(allow file-write* (subpath "/tmp"))
(allow file-write* (subpath "/private/tmp"))
(allow file-write* (subpath "/private/var/folders"))
(allow file-write* (regex #"^/dev/"))
"#,
        scope = canon.display()
    ))
}

/// Result of wrapping a spawn argv with the platform sandbox launcher.
#[derive(Debug, PartialEq, Eq)]
pub enum WrapOutcome {
    /// Spawn this argv instead — the CLI runs under the OS sandbox.
    Sandboxed { binary: String, args: Vec<String> },
    /// No sandbox tool on this platform/host — spawn the ORIGINAL argv and
    /// downgrade the recorded capability tier (no false enforcement claim).
    Unavailable,
}

const MACOS_SANDBOX_EXEC: &str = "/usr/bin/sandbox-exec";

/// Wrap `cmd_binary`/`cmd_args` with the platform sandbox launcher.
///
/// `platform` is passed explicitly (use `std::env::consts::OS`) so the argv
/// shapes are unit-testable on any host. macOS → `sandbox-exec -f <profile>`;
/// Linux → `bwrap` read-only root with the scope (+ /tmp, /dev, /proc) bound
/// writable, best-effort; anything else → `Unavailable`.
pub fn wrap_argv(
    cmd_binary: &str,
    cmd_args: &[String],
    profile_path: &str,
    scope_abs: &str,
    platform: &str,
) -> WrapOutcome {
    match platform {
        "macos" => {
            if !std::path::Path::new(MACOS_SANDBOX_EXEC).exists() {
                return WrapOutcome::Unavailable;
            }
            let mut args = vec![
                "-f".to_string(),
                profile_path.to_string(),
                cmd_binary.to_string(),
            ];
            args.extend(cmd_args.iter().cloned());
            WrapOutcome::Sandboxed {
                binary: MACOS_SANDBOX_EXEC.to_string(),
                args,
            }
        }
        "linux" => {
            let bwrap = ["/usr/bin/bwrap", "/usr/local/bin/bwrap", "/bin/bwrap"]
                .iter()
                .find(|p| std::path::Path::new(p).exists());
            let Some(bwrap) = bwrap else {
                return WrapOutcome::Unavailable;
            };
            let mut args: Vec<String> = [
                "--die-with-parent",
                "--ro-bind",
                "/",
                "/",
                "--bind",
                scope_abs,
                scope_abs,
                "--bind",
                "/tmp",
                "/tmp",
                "--dev",
                "/dev",
                "--proc",
                "/proc",
            ]
            .iter()
            .map(|s| s.to_string())
            .collect();
            args.push(cmd_binary.to_string());
            args.extend(cmd_args.iter().cloned());
            WrapOutcome::Sandboxed {
                binary: bwrap.to_string(),
                args,
            }
        }
        _ => WrapOutcome::Unavailable,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_dirs() -> (PathBuf, PathBuf, PathBuf) {
        let base = std::env::temp_dir().join(format!("voss-sandbox-test-{}", uuid::Uuid::new_v4()));
        let scope = base.join("scope");
        let outside = base.join("outside");
        std::fs::create_dir_all(&scope).expect("create scope");
        std::fs::create_dir_all(&outside).expect("create outside");
        (base, scope, outside)
    }

    #[test]
    fn profile_starts_from_deny_and_allows_only_scope_and_tmp() {
        let (_base, scope, _outside) = fixture_dirs();
        let profile = generate_profile(scope.to_str().unwrap()).unwrap();
        let canon = scope.canonicalize().unwrap();

        // Write policy starts from deny (the deny precedes every write-allow).
        let deny_pos = profile.find("(deny file-write*)").expect("deny present");
        let first_allow_write = profile.find("(allow file-write*").expect("allow present");
        assert!(
            deny_pos < first_allow_write,
            "deny must precede write allows"
        );

        // Only the canonical scope subpath + temp dirs + /dev are writable.
        assert!(profile.contains(&format!("(subpath \"{}\")", canon.display())));
        assert!(profile.contains("(subpath \"/tmp\")"));
        // NEVER a blanket write allow.
        assert!(!profile.contains("(allow file-write* (subpath \"/\"))"));
        assert!(!profile.contains("(allow file-write*)\n"));
    }

    #[test]
    fn scope_validation_rejects_traversal_relative_and_injection() {
        assert!(validate_scope("").is_err());
        assert!(validate_scope("relative/path").is_err());
        assert!(validate_scope("/tmp/../etc").is_err());
        assert!(validate_scope("/tmp/x\"y").is_err());
        assert!(validate_scope("/nonexistent-voss-sandbox-path-xyz").is_err());
    }

    #[test]
    fn wrap_argv_macos_shape_and_unavailable_platform() {
        let args = vec!["--model".to_string(), "sonnet".to_string()];
        // Unknown platform → Unavailable (caller downgrades tier honestly).
        assert_eq!(
            wrap_argv("claude", &args, "/tmp/p.sb", "/tmp", "windows"),
            WrapOutcome::Unavailable
        );
        // macOS shape (only asserted where sandbox-exec exists, i.e. on macOS).
        if std::path::Path::new(MACOS_SANDBOX_EXEC).exists() {
            match wrap_argv("claude", &args, "/tmp/p.sb", "/tmp", "macos") {
                WrapOutcome::Sandboxed { binary, args: a } => {
                    assert_eq!(binary, MACOS_SANDBOX_EXEC);
                    assert_eq!(a[0], "-f");
                    assert_eq!(a[1], "/tmp/p.sb");
                    assert_eq!(a[2], "claude");
                    assert_eq!(&a[3..], &["--model".to_string(), "sonnet".to_string()]);
                }
                WrapOutcome::Unavailable => panic!("sandbox-exec exists but wrap unavailable"),
            }
        }
    }

    /// The kernel-denial floor: an out-of-scope write under `sandbox-exec`
    /// fails at the OS layer; an in-scope write succeeds.
    #[cfg(target_os = "macos")]
    #[test]
    fn sandbox_exec_denies_out_of_scope_write_at_os_layer() {
        use std::process::Command;

        let (base, scope, outside) = fixture_dirs();
        let profile = generate_profile(scope.to_str().unwrap()).unwrap();
        let profile_path = base.join("profile.sb");
        std::fs::write(&profile_path, profile).expect("write profile");

        // The fixture lives under temp_dir, which the profile allows
        // (/private/var/folders|/tmp) — so scope a profile to the SCOPE dir and
        // target a sibling OUTSIDE dir via a profile that does NOT allow temp.
        // Build a stricter profile for the test: only the scope subpath + /dev.
        let canon_scope = scope.canonicalize().unwrap();
        let strict = format!(
            "(version 1)\n(allow default)\n(deny file-write*)\n(allow file-write* (subpath \"{}\"))\n(allow file-write* (regex #\"^/dev/\"))\n",
            canon_scope.display()
        );
        std::fs::write(&profile_path, strict).expect("write strict profile");

        let outside_target = outside.join("denied.txt");
        let status_outside = Command::new(MACOS_SANDBOX_EXEC)
            .args([
                "-f",
                profile_path.to_str().unwrap(),
                "/usr/bin/touch",
                outside_target.to_str().unwrap(),
            ])
            .status()
            .expect("run sandbox-exec");
        assert!(
            !status_outside.success(),
            "out-of-scope write must be DENIED at the OS layer"
        );
        assert!(
            !outside_target.exists(),
            "denied write must not create the file"
        );

        let inside_target = scope.join("allowed.txt");
        let status_inside = Command::new(MACOS_SANDBOX_EXEC)
            .args([
                "-f",
                profile_path.to_str().unwrap(),
                "/usr/bin/touch",
                inside_target.to_str().unwrap(),
            ])
            .status()
            .expect("run sandbox-exec");
        assert!(
            status_inside.success(),
            "in-scope write must be allowed (profile not over-broadly denying)"
        );
        assert!(inside_target.exists());

        let _ = std::fs::remove_dir_all(&base);
    }
}
