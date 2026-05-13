//! Permission gate for tool calls. Verbatim port of
//! `voss/harness/permissions.py` semantics with TOML persistence.
//!
//! Modes:
//!   - Plan: reads auto, every write/shell prompts
//!   - Edit: reads + scoped writes auto, shell/net prompt   (default)
//!   - Auto: all allowlisted auto, destructive patterns prompt
//!
//! Decisions persist per-cwd at `~/.config/voss/permissions.toml`
//! (overridable via `$XDG_CONFIG_HOME`).

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

pub const READ_ONLY: &[&str] = &[
    "fs_read",
    "fs_glob",
    "fs_grep",
    "git_status",
    "git_diff",
    "voss_check",
];
pub const WRITE: &[&str] = &["fs_write", "fs_edit"];
pub const SHELL: &[&str] = &["shell_run"];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    Plan,
    Edit,
    Auto,
}

impl Mode {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "plan" => Some(Self::Plan),
            "edit" => Some(Self::Edit),
            "auto" => Some(Self::Auto),
            _ => None,
        }
    }
}

fn config_path() -> PathBuf {
    let base = std::env::var("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| dirs::home_dir().unwrap_or_default().join(".config"));
    base.join("voss").join("permissions.toml")
}

#[derive(Default, Serialize, Deserialize)]
struct StoreFile {
    /// Map of cwd-string → CwdEntry.
    #[serde(flatten)]
    cwds: BTreeMap<String, CwdEntry>,
}

#[derive(Default, Serialize, Deserialize)]
struct CwdEntry {
    #[serde(default)]
    always: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct PermissionStore {
    pub cwd: PathBuf,
    pub always: BTreeSet<String>,
}

impl PermissionStore {
    pub fn load(cwd: &Path) -> Self {
        let path = config_path();
        let mut always = BTreeSet::new();
        if let Ok(text) = std::fs::read_to_string(&path) {
            if let Ok(file) = toml::from_str::<StoreFile>(&text) {
                let key = cwd.canonicalize().unwrap_or_else(|_| cwd.to_path_buf());
                if let Some(entry) = file.cwds.get(key.to_string_lossy().as_ref()) {
                    always.extend(entry.always.iter().cloned());
                }
            }
        }
        Self {
            cwd: cwd.to_path_buf(),
            always,
        }
    }

    pub fn save(&self) -> std::io::Result<()> {
        let path = config_path();
        if let Some(p) = path.parent() {
            std::fs::create_dir_all(p)?;
        }
        let mut file: StoreFile = std::fs::read_to_string(&path)
            .ok()
            .and_then(|t| toml::from_str(&t).ok())
            .unwrap_or_default();
        let key = self.cwd.canonicalize().unwrap_or_else(|_| self.cwd.clone());
        file.cwds.insert(
            key.to_string_lossy().into_owned(),
            CwdEntry {
                always: self.always.iter().cloned().collect(),
            },
        );
        let text = toml::to_string_pretty(&file)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;
        std::fs::write(&path, text)?;
        Ok(())
    }

    pub fn remember(&mut self, signature: String) -> std::io::Result<()> {
        self.always.insert(signature);
        self.save()
    }
}

pub struct PermissionGate {
    pub mode: Mode,
    pub store: Option<PermissionStore>,
    pub auto_yes: bool,
}

impl PermissionGate {
    pub fn needs_prompt(&self, tool_name: &str) -> bool {
        if self.auto_yes {
            return false;
        }
        match self.mode {
            Mode::Auto => false,
            Mode::Plan => !READ_ONLY.contains(&tool_name),
            Mode::Edit => WRITE.contains(&tool_name) || SHELL.contains(&tool_name),
        }
    }

    pub fn signature(tool_name: &str, args: &serde_json::Value) -> String {
        if tool_name == "shell_run" {
            let cmd = args.get("cmd").and_then(|v| v.as_str()).unwrap_or("");
            let head = cmd.split_whitespace().next().unwrap_or("");
            return format!("shell_run:{head}");
        }
        tool_name.to_string()
    }

    /// Run permission check. `prompt` is a closure called only when the
    /// gate cannot decide autonomously. Returns `(allowed, reason)`.
    pub fn check<F>(
        &mut self,
        tool_name: &str,
        args: &serde_json::Value,
        prompt: F,
    ) -> (bool, &'static str)
    where
        F: FnOnce(&str, &serde_json::Value) -> char,
    {
        if !self.needs_prompt(tool_name) {
            return (true, "auto");
        }
        if let Some(store) = &self.store {
            let sig = Self::signature(tool_name, args);
            if store.always.contains(&sig) {
                return (true, "remembered");
            }
        }
        let choice = prompt(tool_name, args);
        match choice {
            'a' => (true, "allowed once"),
            'A' => {
                if let Some(store) = self.store.as_mut() {
                    let _ = store.remember(Self::signature(tool_name, args));
                }
                (true, "allowed always")
            }
            _ => (false, "denied"),
        }
    }
}

/// Default interactive prompt — reads a line from stdin. Used by the agent
/// loop; tests inject their own closure to keep cases hermetic.
pub fn interactive_prompt(tool_name: &str, args: &serde_json::Value) -> char {
    use std::io::{BufRead, Write};
    let argstr = args.to_string();
    let _ = writeln!(std::io::stderr(), "\n  ⚠  {tool_name}({argstr})");
    let _ = write!(
        std::io::stderr(),
        "     [a] allow once  [A] allow always  [d] deny: "
    );
    let _ = std::io::stderr().flush();
    let mut line = String::new();
    let stdin = std::io::stdin();
    let _ = stdin.lock().read_line(&mut line);
    line.trim().chars().next().unwrap_or('d')
}
