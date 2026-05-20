//! A6 session persistence — versioned `session.json` / `global-session.json`,
//! locked writes, and fail-safe loads.
//!
//! Follows the `layouts.rs` pattern: a versioned wrapper around `GridState`
//! with typed errors whose Display strings surface through Tauri verbatim.
//! Corrupt, missing, or unsupported session files fail closed to `Ok(None)`
//! so app startup is never blocked (D-11).
//!
//! Two save tiers share the same file and schema (D-04/D-06):
//! - **Structural auto-save** writes tree + cwds + shells + focus + preset
//!   with `scrollback: null` per pane.
//! - **Quit full-save** writes the same shape with scrollback arrays populated.
//!
//! Every write is locked exclusively via `fs2::FileExt` (PER-06) and uses
//! a tmp-file rename so readers never see a partial write.

use std::path::{Path, PathBuf};

use fs2::FileExt;
use serde::{Deserialize, Serialize};

use crate::grid::GridState;

/// On-disk session schema version. Bump when the schema shape changes.
pub const CURRENT_SESSION_VERSION: u32 = 1;

/// Persisted session file. Wraps `GridState` with per-pane scrollback,
/// the active preset, and the project-less flag (D-12).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionFile {
    pub version: u32,
    pub active_preset: Option<String>,
    pub grid: GridState,
    pub panes: Vec<SessionPane>,
    pub project_less_accepted: bool,
}

/// Per-pane scrollback payload. `scrollback: None` means tree-only auto-save
/// (D-04); `Some(lines)` means full quit save (D-01).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionPane {
    pub id: String,
    pub scrollback: Option<Vec<String>>,
}

impl SessionFile {
    /// Build a v1 SessionFile.
    pub fn new(
        grid: GridState,
        active_preset: Option<String>,
        panes: Vec<SessionPane>,
        project_less_accepted: bool,
    ) -> Self {
        Self {
            version: CURRENT_SESSION_VERSION,
            active_preset,
            grid,
            panes,
            project_less_accepted,
        }
    }
}

/// Typed errors for session save/load. Display strings are safe for UI
/// passthrough — no Rust internals leak.
#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    #[error("could not save session")]
    SaveFailed,
    #[error("could not load session")]
    LoadFailed,
}

// --- Path resolution ---------------------------------------------------------

/// `<workspace>/.voss/session.json`
pub fn session_path(workspace: &Path) -> PathBuf {
    workspace.join(".voss").join("session.json")
}

/// `~/.config/voss-app/global-session.json`
#[cfg(not(test))]
pub fn global_session_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("global-session.json")
}

#[cfg(test)]
pub fn global_session_path() -> PathBuf {
    TEST_GLOBAL_SESSION_PATH.with(|p| {
        p.borrow()
            .clone()
            .expect("tests must set TEST_GLOBAL_SESSION_PATH before touching global session")
    })
}

// --- Save / Load -------------------------------------------------------------

/// Save a project session to `<workspace>/.voss/session.json`.
pub fn save_session(workspace: &Path, session: &SessionFile) -> Result<(), SessionError> {
    let path = session_path(workspace);
    let json = serde_json::to_string_pretty(session).map_err(|e| {
        eprintln!("[voss-app] session serialize failed: {e}");
        SessionError::SaveFailed
    })?;
    locked_write(&path, &json)
}

/// Load a project session. Returns `Ok(None)` for missing, corrupt, or
/// unsupported files — never crashes startup (D-11).
pub fn load_session(workspace: &Path) -> Result<Option<SessionFile>, SessionError> {
    fail_safe_load(&session_path(workspace))
}

/// Save the global (project-less) session to
/// `~/.config/voss-app/global-session.json`.
pub fn save_global_session(session: &SessionFile) -> Result<(), SessionError> {
    let path = global_session_path();
    let json = serde_json::to_string_pretty(session).map_err(|e| {
        eprintln!("[voss-app] global session serialize failed: {e}");
        SessionError::SaveFailed
    })?;
    locked_write(&path, &json)
}

/// Load the global session. Returns `Ok(None)` for missing, corrupt, or
/// unsupported files.
pub fn load_global_session() -> Result<Option<SessionFile>, SessionError> {
    fail_safe_load(&global_session_path())
}

// --- Internal helpers --------------------------------------------------------

/// Locked write: create parent dir → open lock file → lock exclusively →
/// write tmp → rename over destination. Lock released on drop.
fn locked_write(path: &Path, json: &str) -> Result<(), SessionError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| {
            eprintln!("[voss-app] session save mkdir failed: {e}");
            SessionError::SaveFailed
        })?;
    }

    let lock_path = path.with_extension("json.lock");
    let lock_file = std::fs::OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true)
        .open(&lock_path)
        .map_err(|e| {
            eprintln!("[voss-app] session lock open failed: {e}");
            SessionError::SaveFailed
        })?;
    lock_file.lock_exclusive().map_err(|e| {
        eprintln!("[voss-app] session lock failed: {e}");
        SessionError::SaveFailed
    })?;

    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, json).map_err(|e| {
        eprintln!("[voss-app] session write tmp failed: {e}");
        SessionError::SaveFailed
    })?;
    std::fs::rename(&tmp, path).map_err(|e| {
        eprintln!("[voss-app] session rename failed: {e}");
        SessionError::SaveFailed
    })?;

    // lock_file dropped here → exclusive lock released
    Ok(())
}

/// Fail-safe load: missing → `Ok(None)`, corrupt → `Ok(None)` + stderr,
/// unsupported version → `Ok(None)` + stderr. Never panics.
fn fail_safe_load(path: &Path) -> Result<Option<SessionFile>, SessionError> {
    if !path.exists() {
        return Ok(None);
    }
    let raw = match std::fs::read_to_string(path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] could not read session: {e}");
            return Ok(None);
        }
    };
    match parse_session(&raw) {
        Ok(s) => Ok(Some(s)),
        Err(reason) => {
            eprintln!("[voss-app] session ignored: {reason}");
            Ok(None)
        }
    }
}

/// Version-gated parse — same pattern as `layouts::parse_layout`.
fn parse_session(raw: &str) -> Result<SessionFile, &'static str> {
    let value: serde_json::Value =
        serde_json::from_str(raw).map_err(|_| "invalid JSON")?;
    let version = value.get("version").and_then(|v| v.as_u64());
    match version {
        Some(v) if v == CURRENT_SESSION_VERSION as u64 => {
            serde_json::from_value(value).map_err(|_| "invalid session file")
        }
        Some(_) => Err("unsupported version"),
        None => Err("missing version"),
    }
}

// ---------------------------------------------------------------------------

#[cfg(test)]
thread_local! {
    static TEST_GLOBAL_SESSION_PATH: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::grid::{GridState, Orientation, PaneLeaf, SplitNode, TreeNode};
    use tempfile::{tempdir, TempDir};

    fn sample_grid() -> GridState {
        GridState {
            root: TreeNode::Split(SplitNode {
                orientation: Orientation::H,
                ratio: 0.5,
                left: Box::new(TreeNode::Pane(PaneLeaf {
                    id: "a".into(),
                    cwd: "/repo".into(),
                    shell: "zsh".into(),
                    index: 1,
                })),
                right: Box::new(TreeNode::Pane(PaneLeaf {
                    id: "b".into(),
                    cwd: "/repo".into(),
                    shell: "zsh".into(),
                    index: 2,
                })),
            }),
            focused_id: "a".into(),
        }
    }

    fn sample_panes() -> Vec<SessionPane> {
        vec![
            SessionPane {
                id: "a".into(),
                scrollback: Some(vec!["$ ls".into(), "file.txt".into()]),
            },
            SessionPane {
                id: "b".into(),
                scrollback: None,
            },
        ]
    }

    fn sample_session() -> SessionFile {
        SessionFile::new(
            sample_grid(),
            Some("fanout".into()),
            sample_panes(),
            false,
        )
    }

    fn isolate_global() -> TempDir {
        let dir = tempdir().unwrap();
        let path = dir.path().join("global-session.json");
        TEST_GLOBAL_SESSION_PATH.with(|p| {
            *p.borrow_mut() = Some(path);
        });
        dir
    }

    // --- Task 1: schema + serde -------------------------------------------

    #[test]
    fn session_file_new_sets_version_1() {
        let s = sample_session();
        assert_eq!(s.version, 1);
        assert_eq!(CURRENT_SESSION_VERSION, 1);
    }

    #[test]
    fn session_file_round_trips_through_json() {
        let original = sample_session();
        let json = serde_json::to_string(&original).expect("serialize");
        let back: SessionFile = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(original, back);
    }

    #[test]
    fn json_contains_expected_camel_case_keys() {
        let s = sample_session();
        let json = serde_json::to_string(&s).unwrap();
        assert!(json.contains("\"version\":1"), "version: {json}");
        assert!(json.contains("\"focusedId\""), "focusedId: {json}");
        assert!(json.contains("\"activePreset\""), "activePreset: {json}");
        assert!(
            json.contains("\"projectLessAccepted\""),
            "projectLessAccepted: {json}"
        );
    }

    #[test]
    fn scrollback_none_serializes_as_null() {
        let pane = SessionPane {
            id: "x".into(),
            scrollback: None,
        };
        let json = serde_json::to_string(&pane).unwrap();
        assert!(json.contains("\"scrollback\":null"), "null: {json}");
    }

    #[test]
    fn scrollback_some_serializes_as_array() {
        let pane = SessionPane {
            id: "x".into(),
            scrollback: Some(vec!["line1".into(), "line2".into()]),
        };
        let json = serde_json::to_string(&pane).unwrap();
        assert!(
            json.contains("[\"line1\",\"line2\"]"),
            "array: {json}"
        );
    }

    #[test]
    fn session_error_display_strings() {
        assert_eq!(SessionError::SaveFailed.to_string(), "could not save session");
        assert_eq!(SessionError::LoadFailed.to_string(), "could not load session");
    }

    // --- Task 2: file I/O ------------------------------------------------

    #[test]
    fn session_path_resolves_to_workspace_voss_session_json() {
        let p = session_path(Path::new("/ws"));
        assert_eq!(p, PathBuf::from("/ws/.voss/session.json"));
    }

    #[test]
    fn global_session_path_resolves_to_config_voss_app() {
        let _g = isolate_global();
        let p = global_session_path();
        assert!(
            p.to_string_lossy().ends_with("global-session.json"),
            "path: {p:?}"
        );
    }

    #[test]
    fn save_then_load_round_trips_project_session() {
        let dir = tempdir().unwrap();
        let session = sample_session();
        save_session(dir.path(), &session).unwrap();
        let loaded = load_session(dir.path()).unwrap();
        assert_eq!(loaded, Some(session));
    }

    #[test]
    fn save_lazily_creates_voss_only_on_write() {
        let dir = tempdir().unwrap();
        let voss = dir.path().join(".voss");
        assert!(!voss.exists(), "precondition: .voss must not pre-exist");

        // Load must not create .voss
        assert!(load_session(dir.path()).unwrap().is_none());
        assert!(!voss.exists(), ".voss must remain absent before save");

        save_session(dir.path(), &sample_session()).unwrap();
        assert!(voss.join("session.json").exists());
    }

    #[test]
    fn load_session_does_not_create_directories() {
        let dir = tempdir().unwrap();
        let voss = dir.path().join(".voss");
        let _ = load_session(dir.path());
        assert!(!voss.exists());
    }

    #[test]
    fn load_session_returns_none_for_missing_file() {
        let dir = tempdir().unwrap();
        assert!(load_session(dir.path()).unwrap().is_none());
    }

    #[test]
    fn load_session_returns_none_for_corrupt_json() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(path.join("session.json"), "not json").unwrap();
        assert!(load_session(dir.path()).unwrap().is_none());
    }

    #[test]
    fn load_session_returns_none_for_unsupported_version() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(
            path.join("session.json"),
            r#"{"version":999,"activePreset":null,"grid":{},"panes":[],"projectLessAccepted":false}"#,
        )
        .unwrap();
        assert!(load_session(dir.path()).unwrap().is_none());
    }

    #[test]
    fn save_then_load_round_trips_global_session() {
        let _g = isolate_global();
        let session = SessionFile::new(
            sample_grid(),
            None,
            sample_panes(),
            true,
        );
        save_global_session(&session).unwrap();
        let loaded = load_global_session().unwrap();
        assert_eq!(loaded, Some(session));
    }

    #[test]
    fn load_global_session_returns_none_when_missing() {
        let _g = isolate_global();
        assert!(load_global_session().unwrap().is_none());
    }

    #[test]
    fn save_writes_tmp_then_renames() {
        let dir = tempdir().unwrap();
        save_session(dir.path(), &sample_session()).unwrap();
        let session_path = dir.path().join(".voss").join("session.json");
        let tmp_path = dir.path().join(".voss").join("session.json.tmp");
        assert!(session_path.exists());
        assert!(!tmp_path.exists(), "tmp must be cleaned up by rename");
    }

    #[test]
    fn save_overwrites_existing_session() {
        let dir = tempdir().unwrap();
        let first = SessionFile::new(sample_grid(), Some("fanout".into()), vec![], false);
        save_session(dir.path(), &first).unwrap();

        let second = SessionFile::new(sample_grid(), Some("pipeline".into()), vec![], true);
        save_session(dir.path(), &second).unwrap();

        let loaded = load_session(dir.path()).unwrap().unwrap();
        assert_eq!(loaded.active_preset, Some("pipeline".into()));
        assert!(loaded.project_less_accepted);
    }
}
