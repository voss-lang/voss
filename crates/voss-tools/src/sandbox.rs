//! Sandbox: path jailing + shell allowlist. Verbatim port of
//! `voss/harness/sandbox.py`. Allowlist persists to
//! `~/.config/voss/sandbox.toml` (overridable via `$XDG_CONFIG_HOME`).

use std::collections::HashSet;
use std::path::{Path, PathBuf};

pub const DEFAULT_SHELL_ALLOWLIST: &[&str] = &[
    "ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "git", "pytest", "python", "python3",
    "voss", "npm", "node", "echo", "pwd", "which",
];

pub const DENY_TOKENS: &[&str] = &[
    "rm -rf",
    "sudo",
    "curl http",
    "nc ",
    " > /",
    "shutdown",
    "reboot",
    "mkfs",
];

/// Shell metacharacters that change command-flow semantics. Mirrors
/// `voss/harness/sandbox.py::SHELL_METACHARS`. Even though callers MAY use
/// exec-style invocation (no shell), we reject these at allowlist time so a
/// misuse of the API by a future caller can't re-enable shell parsing.
pub const SHELL_METACHARS: &[&str] = &[
    ";", "|", "&&", "||", "&", "$(", "`", ">", "<", ">>", "<<", "<(", ">(",
];

#[derive(thiserror::Error, Debug)]
pub enum SandboxError {
    #[error("path escapes cwd: {0}")]
    Escape(PathBuf),
    #[error("denied token: {0:?}")]
    DenyToken(String),
    #[error("binary not in allowlist: {0}")]
    NotAllowed(String),
    #[error("unparseable: {0}")]
    Unparseable(String),
    #[error("empty command")]
    Empty,
}

/// Resolve `target` against `cwd`; reject any path that escapes `cwd`.
///
/// Mirrors `voss/harness/sandbox.py::jail_path`. For non-existent paths,
/// canonicalization may fail — fall back to lexical join + parent-canonical
/// containment check so the jail still rejects `../etc/passwd` style escapes.
pub fn jail_path(cwd: &Path, target: &str) -> Result<PathBuf, SandboxError> {
    let cwd_real = cwd.canonicalize().unwrap_or_else(|_| cwd.to_path_buf());
    let p = Path::new(target);
    let abs = if p.is_absolute() {
        p.to_path_buf()
    } else {
        cwd_real.join(p)
    };
    let resolved = match abs.canonicalize() {
        Ok(c) => c,
        Err(_) => {
            // Path may not exist yet (e.g. fs_write target). Anchor to the
            // nearest existing ancestor; collect remaining components in
            // reverse and re-append in order so we don't introduce trailing
            // slashes (which would make `std::fs::write` think the target
            // is a directory).
            let mut base = abs.clone();
            let mut tail_rev: Vec<std::ffi::OsString> = Vec::new();
            loop {
                if base.exists() {
                    break;
                }
                match (base.parent(), base.file_name()) {
                    (Some(p), Some(name)) => {
                        tail_rev.push(name.to_os_string());
                        base = p.to_path_buf();
                    }
                    _ => break,
                }
            }
            let mut joined = base.canonicalize().unwrap_or(base);
            for comp in tail_rev.into_iter().rev() {
                joined.push(comp);
            }
            joined
        }
    };
    if !resolved.starts_with(&cwd_real) {
        return Err(SandboxError::Escape(resolved));
    }
    Ok(resolved)
}

/// Check whether `cmd` is allowed under `allowlist`. Returns Ok(()) on allow.
pub fn shell_allowed(cmd: &str, allowlist: &HashSet<String>) -> Result<(), SandboxError> {
    let lowered = cmd.to_lowercase();
    for bad in DENY_TOKENS {
        if lowered.contains(bad) {
            return Err(SandboxError::DenyToken((*bad).to_string()));
        }
    }
    for meta in SHELL_METACHARS {
        if cmd.contains(meta) {
            return Err(SandboxError::DenyToken((*meta).to_string()));
        }
    }
    let parts = shlex::split(cmd).ok_or_else(|| SandboxError::Unparseable(cmd.into()))?;
    if parts.is_empty() {
        return Err(SandboxError::Empty);
    }
    let binary = Path::new(&parts[0])
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("")
        .to_string();
    if !allowlist.contains(&binary) {
        return Err(SandboxError::NotAllowed(binary));
    }
    Ok(())
}

pub fn default_allowlist() -> HashSet<String> {
    DEFAULT_SHELL_ALLOWLIST
        .iter()
        .map(|s| (*s).to_string())
        .collect()
}

fn allowlist_path() -> PathBuf {
    let base = std::env::var("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| dirs::home_dir().unwrap_or_default().join(".config"));
    base.join("voss").join("sandbox.toml")
}

#[derive(serde::Serialize, serde::Deserialize, Default)]
struct AllowlistFile {
    #[serde(default)]
    extra: Vec<String>,
}

pub fn load_allowlist() -> HashSet<String> {
    let mut set = default_allowlist();
    if let Ok(text) = std::fs::read_to_string(allowlist_path()) {
        if let Ok(file) = toml::from_str::<AllowlistFile>(&text) {
            for x in file.extra {
                set.insert(x);
            }
        }
    }
    set
}

pub fn save_allowlist_extra(extra: &[String]) -> std::io::Result<()> {
    let path = allowlist_path();
    if let Some(p) = path.parent() {
        std::fs::create_dir_all(p)?;
    }
    let file = AllowlistFile {
        extra: extra.to_vec(),
    };
    let text = toml::to_string(&file).map_err(|e| std::io::Error::other(e.to_string()))?;
    std::fs::write(&path, text)?;
    Ok(())
}
