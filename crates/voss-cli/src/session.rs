//! Persisted session snapshots. Wire-format-compatible with
//! `voss/harness/session.py`.
//!
//! Storage path: `$XDG_STATE_HOME/voss/sessions/<id>.json` (default
//! `~/.local/state/voss/sessions/`).
//!
//! IMPORTANT: provider creds (access tokens, refresh tokens, API keys) are
//! NEVER serialized into a session record.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

fn state_dir() -> PathBuf {
    let base = std::env::var("XDG_STATE_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            dirs::home_dir()
                .unwrap_or_default()
                .join(".local")
                .join("state")
        });
    base.join("voss").join("sessions")
}

pub fn session_path(id: &str) -> PathBuf {
    state_dir().join(format!("{id}.json"))
}

/// Mirrors `voss/harness/session.py::SessionRecord` field-for-field.
/// JSON key order: id, name, cwd, model, started_at, updated_at, total_cost_usd, turns.
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct SessionRecord {
    pub id: String,
    pub name: String,
    pub cwd: String,
    pub model: String,
    /// ISO-8601 UTC, seconds precision. Matches Python
    /// `datetime.now(timezone.utc).isoformat(timespec="seconds")`,
    /// e.g. `"2026-05-09T15:30:00+00:00"`.
    pub started_at: String,
    pub updated_at: String,
    #[serde(default)]
    pub total_cost_usd: f64,
    #[serde(default)]
    pub turns: Vec<Turn>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Turn {
    pub role: String,
    pub content: String,
    /// Preserves any unknown fields a Python session may carry.
    #[serde(flatten)]
    pub extra: BTreeMap<String, serde_json::Value>,
}

impl SessionRecord {
    pub fn new(cwd: &Path, model: &str, name: Option<&str>) -> Self {
        // 12-hex-char id, matching Python `uuid.uuid4().hex[:12]`.
        let full = uuid::Uuid::new_v4().simple().to_string();
        let id: String = full.chars().take(12).collect();
        let now = iso_now();
        let resolved_cwd = cwd
            .canonicalize()
            .unwrap_or_else(|_| cwd.to_path_buf())
            .to_string_lossy()
            .into_owned();
        let derived_name = format!("session-{}", &id[..id.len().min(8)]);
        Self {
            id,
            name: name
                .map(|n| {
                    if n.is_empty() {
                        derived_name.clone()
                    } else {
                        n.to_string()
                    }
                })
                .unwrap_or(derived_name),
            cwd: resolved_cwd,
            model: model.into(),
            started_at: now.clone(),
            updated_at: now,
            total_cost_usd: 0.0,
            turns: Vec::new(),
        }
    }

    pub fn first_task(&self) -> String {
        for t in &self.turns {
            if t.role == "user" {
                return t.content.chars().take(60).collect();
            }
        }
        "(empty)".into()
    }
}

/// Format current time as Python `isoformat(timespec="seconds")` does:
/// `YYYY-MM-DDTHH:MM:SS+00:00`.
pub fn iso_now() -> String {
    let now: DateTime<Utc> = Utc::now();
    now.format("%Y-%m-%dT%H:%M:%S+00:00").to_string()
}

pub fn save(record: &mut SessionRecord) -> std::io::Result<PathBuf> {
    record.updated_at = iso_now();
    let path = session_path(&record.id);
    if let Some(p) = path.parent() {
        std::fs::create_dir_all(p)?;
    }
    let bytes = serde_json::to_vec_pretty(record)?;
    std::fs::write(&path, bytes)?;
    set_owner_only(&path)?;
    Ok(path)
}

#[cfg(unix)]
fn set_owner_only(path: &Path) -> std::io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600))
}

#[cfg(not(unix))]
fn set_owner_only(_path: &Path) -> std::io::Result<()> {
    Ok(())
}

/// Resolve by id-prefix OR exact name. Errors on ambiguity / not-found.
pub fn load(id_or_name: &str) -> std::io::Result<SessionRecord> {
    let dir = state_dir();
    if !dir.exists() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("no session: {id_or_name}"),
        ));
    }
    let mut matches: Vec<SessionRecord> = Vec::new();
    for entry in std::fs::read_dir(&dir)? {
        let entry = entry?;
        if !entry.path().extension().map_or(false, |e| e == "json") {
            continue;
        }
        let bytes = std::fs::read(entry.path())?;
        let rec: SessionRecord = match serde_json::from_slice(&bytes) {
            Ok(r) => r,
            Err(_) => continue,
        };
        if rec.id.starts_with(id_or_name) || rec.name == id_or_name {
            matches.push(rec);
        }
    }
    match matches.len() {
        0 => Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("no session: {id_or_name}"),
        )),
        1 => Ok(matches.into_iter().next().unwrap()),
        _ => {
            let names: Vec<String> = matches
                .iter()
                .map(|r| r.id.chars().take(8).collect())
                .collect();
            Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                format!("ambiguous session id; candidates: {}", names.join(", ")),
            ))
        }
    }
}

pub fn list_sessions() -> std::io::Result<Vec<SessionRecord>> {
    let dir = state_dir();
    if !dir.exists() {
        return Ok(Vec::new());
    }
    let mut entries: Vec<(std::time::SystemTime, SessionRecord)> = Vec::new();
    for entry in std::fs::read_dir(&dir)? {
        let entry = entry?;
        if !entry.path().extension().map_or(false, |e| e == "json") {
            continue;
        }
        let mtime = entry
            .metadata()
            .and_then(|m| m.modified())
            .unwrap_or(std::time::UNIX_EPOCH);
        let bytes = std::fs::read(entry.path())?;
        if let Ok(rec) = serde_json::from_slice::<SessionRecord>(&bytes) {
            entries.push((mtime, rec));
        }
    }
    entries.sort_by(|a, b| b.0.cmp(&a.0));
    Ok(entries.into_iter().map(|(_, r)| r).collect())
}

pub fn delete(id: &str) -> std::io::Result<bool> {
    let path = session_path(id);
    if path.exists() {
        std::fs::remove_file(&path)?;
        Ok(true)
    } else {
        Ok(false)
    }
}
