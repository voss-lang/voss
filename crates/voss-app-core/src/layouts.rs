//! A4 layout persistence — versioned JSON schema for `.voss/layouts/<name>.json`
//! plus path/name validation.
//!
//! The on-disk shape wraps `GridState` so the same camelCase keys the
//! TypeScript model uses (`focusedId`, `kind`, `orientation`, `ratio`, …)
//! round-trip unchanged. Adding fields here without bumping `version`
//! breaks the at-rest contract — bump `CURRENT_LAYOUT_VERSION` whenever
//! the schema shape changes.
//!
//! All errors are typed (`LayoutError`) so the app-level `#[tauri::command]`
//! wrappers can map them to the UI-SPEC error copy without leaking
//! Rust-formatted strings into the UI. Corrupt or unsupported `default.json`
//! files fail closed (load_default_layout returns `Ok(None)` + stderr log)
//! so app startup is never blocked by a bad layout (D-09).
//!
//! `.voss/layouts/` is created lazily on the first SAVE — load/list/default
//! never create directories (CONCEPT §10 Q7).

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::grid::GridState;

/// On-disk integer version. Bump when the schema shape changes.
pub const CURRENT_LAYOUT_VERSION: u32 = 1;

/// Persisted layout file. Wraps `GridState` with a version tag and the
/// active preset name (None = custom geometry).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LayoutFile {
    pub version: u32,
    /// One of "fanout" / "pipeline" / "swarm" / "watchers" / null.
    /// Stored as a free string here — the TS layer validates against
    /// `LayoutPreset` after load (LAY-01..05 own the closed cycle).
    pub active_preset: Option<String>,
    pub grid: GridState,
}

impl LayoutFile {
    /// Build a v1 LayoutFile from the in-memory grid mirror.
    pub fn new(grid: GridState, active_preset: Option<String>) -> Self {
        Self {
            version: CURRENT_LAYOUT_VERSION,
            active_preset,
            grid,
        }
    }
}

/// Typed errors for layout save/load. Display strings match the UI-SPEC
/// user-facing copy so the app-level command wrappers can pass them
/// through verbatim.
#[derive(Debug, thiserror::Error)]
pub enum LayoutError {
    #[error("layout name cannot contain /, \\ or ..")]
    InvalidName,
    #[error("layout not found")]
    NotFound,
    #[error("layout ignored: invalid file")]
    InvalidFile,
    #[error("layout ignored: unsupported version")]
    UnsupportedVersion,
    #[error("could not save layout")]
    SaveFailed,
    #[error("could not load layout")]
    LoadFailed,
}

/// Validate a layout `name` for use as a `.voss/layouts/<name>.json`
/// filename. Accepts `default`, `build-watch`, `my_layout`. Rejects
/// empty, `/`, `\`, `..` (substring), leading `.`, embedded `:` (Windows
/// drive letter), control characters, and `.json` suffix (to keep
/// `<name>.json` unambiguous).
pub fn validate_layout_name(name: &str) -> Result<(), LayoutError> {
    if name.is_empty() {
        return Err(LayoutError::InvalidName);
    }
    if name.contains('/') || name.contains('\\') || name.contains("..") || name.contains(':') {
        return Err(LayoutError::InvalidName);
    }
    if name.starts_with('.') {
        return Err(LayoutError::InvalidName);
    }
    if name.ends_with(".json") {
        return Err(LayoutError::InvalidName);
    }
    if name.chars().any(|c| c.is_control()) {
        return Err(LayoutError::InvalidName);
    }
    Ok(())
}

/// Resolve `<workspace>/.voss/layouts/<name>.json`. Errors if the name
/// fails validation. Does NOT touch the filesystem.
pub fn layout_path(workspace: &Path, name: &str) -> Result<PathBuf, LayoutError> {
    validate_layout_name(name)?;
    Ok(workspace
        .join(".voss")
        .join("layouts")
        .join(format!("{name}.json")))
}

// --- File I/O (Task 2) ------------------------------------------------------

/// Save `layout` to `<workspace>/.voss/layouts/<name>.json`, lazily
/// creating the parent directory on first write (CONCEPT §10 Q7).
pub fn save_layout(workspace: &Path, name: &str, layout: &LayoutFile) -> Result<(), LayoutError> {
    let path = layout_path(workspace, name)?;
    let dir = path.parent().ok_or(LayoutError::SaveFailed)?;
    std::fs::create_dir_all(dir).map_err(|e| {
        eprintln!("[voss-app] layout save mkdir failed: {e}");
        LayoutError::SaveFailed
    })?;
    let json = serde_json::to_string_pretty(layout).map_err(|e| {
        eprintln!("[voss-app] layout serialize failed: {e}");
        LayoutError::SaveFailed
    })?;
    std::fs::write(&path, json).map_err(|e| {
        eprintln!("[voss-app] layout write failed: {e}");
        LayoutError::SaveFailed
    })?;
    Ok(())
}

/// Load `<workspace>/.voss/layouts/<name>.json`. Returns `NotFound` if
/// the file is missing, `InvalidFile` on JSON parse failure, and
/// `UnsupportedVersion` for any version field other than
/// `CURRENT_LAYOUT_VERSION`. Does NOT create directories.
pub fn load_layout(workspace: &Path, name: &str) -> Result<LayoutFile, LayoutError> {
    let path = layout_path(workspace, name)?;
    if !path.exists() {
        return Err(LayoutError::NotFound);
    }
    let raw = std::fs::read_to_string(&path).map_err(|e| {
        eprintln!("[voss-app] layout read failed: {e}");
        LayoutError::LoadFailed
    })?;
    parse_layout(&raw)
}

/// List layout names (without `.json`) sorted alphabetically. Returns an
/// empty list if `.voss/layouts/` does not exist — never creates it.
pub fn list_layouts(workspace: &Path) -> Result<Vec<String>, LayoutError> {
    let dir = workspace.join(".voss").join("layouts");
    if !dir.exists() {
        return Ok(Vec::new());
    }
    let mut names = Vec::new();
    let read = std::fs::read_dir(&dir).map_err(|e| {
        eprintln!("[voss-app] layout list failed: {e}");
        LayoutError::LoadFailed
    })?;
    for entry in read {
        let entry = entry.map_err(|_| LayoutError::LoadFailed)?;
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
            names.push(stem.to_string());
        }
    }
    names.sort();
    Ok(names)
}

/// Auto-load `<workspace>/.voss/layouts/default.json` on project open.
/// Missing file → `Ok(None)` (silent). Corrupt JSON or unsupported
/// version → `Ok(None)` after a stderr log — never crashes startup
/// (D-09 fail-safe).
pub fn load_default_layout(workspace: &Path) -> Result<Option<LayoutFile>, LayoutError> {
    let path = workspace.join(".voss").join("layouts").join("default.json");
    if !path.exists() {
        return Ok(None);
    }
    let raw = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] could not read default layout: {e}");
            return Ok(None);
        }
    };
    match parse_layout(&raw) {
        Ok(l) => Ok(Some(l)),
        Err(LayoutError::InvalidFile) => {
            eprintln!("[voss-app] layout ignored: invalid file (default.json)");
            Ok(None)
        }
        Err(LayoutError::UnsupportedVersion) => {
            eprintln!("[voss-app] layout ignored: unsupported version (default.json)");
            Ok(None)
        }
        Err(e) => Err(e),
    }
}

/// Inspect the `version` field before binding the rest of the JSON so
/// that an unsupported version is reported as `UnsupportedVersion`
/// rather than `InvalidFile` (which would lose the diagnostic).
fn parse_layout(raw: &str) -> Result<LayoutFile, LayoutError> {
    let value: serde_json::Value =
        serde_json::from_str(raw).map_err(|_| LayoutError::InvalidFile)?;
    let version = value.get("version").and_then(|v| v.as_u64());
    match version {
        Some(v) if v == CURRENT_LAYOUT_VERSION as u64 => {
            serde_json::from_value(value).map_err(|_| LayoutError::InvalidFile)
        }
        Some(_) => Err(LayoutError::UnsupportedVersion),
        None => Err(LayoutError::InvalidFile),
    }
}

// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    use crate::grid::{Orientation, PaneLeaf, SplitNode, TreeNode};
    use tempfile::tempdir;

    fn sample_grid() -> GridState {
        let a = TreeNode::Pane(PaneLeaf {
            id: "a".into(),
            cwd: "/repo".into(),
            shell: "zsh".into(),
            index: 1,
        });
        let b = TreeNode::Pane(PaneLeaf {
            id: "b".into(),
            cwd: "/repo".into(),
            shell: "zsh".into(),
            index: 2,
        });
        GridState {
            root: TreeNode::Split(SplitNode {
                orientation: Orientation::H,
                ratio: 0.5,
                left: Box::new(a),
                right: Box::new(b),
            }),
            focused_id: "a".into(),
        }
    }

    // --- Task 1: schema + validation --------------------------------------

    #[test]
    fn layout_file_round_trips_through_json_with_version_1() {
        let original = LayoutFile::new(sample_grid(), Some("fanout".into()));
        assert_eq!(original.version, CURRENT_LAYOUT_VERSION);
        assert_eq!(CURRENT_LAYOUT_VERSION, 1);
        let json = serde_json::to_string(&original).expect("serialize");
        assert!(json.contains("\"version\":1"));
        assert!(json.contains("\"activePreset\":\"fanout\""));
        assert!(json.contains("\"focusedId\""));
        let back: LayoutFile = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(original, back);
    }

    #[test]
    fn validate_layout_name_accepts_simple_names() {
        for name in ["default", "build-watch", "my_layout", "watch1"] {
            assert!(
                validate_layout_name(name).is_ok(),
                "expected {name} to be accepted"
            );
        }
    }

    #[test]
    fn validate_layout_name_rejects_traversal_and_separators() {
        for bad in [
            "",
            "/abs",
            "foo/bar",
            "foo\\bar",
            "..",
            "../foo",
            "foo/..",
            "foo..bar",
            ".hidden",
            "C:layout",
            "trailing.json",
            "with\nnewline",
        ] {
            assert!(
                validate_layout_name(bad).is_err(),
                "expected {bad:?} to be rejected"
            );
        }
    }

    #[test]
    fn layout_path_resolves_to_workspace_voss_layouts_name_json() {
        let p = layout_path(Path::new("/ws"), "default").unwrap();
        assert_eq!(p, PathBuf::from("/ws/.voss/layouts/default.json"));
    }

    #[test]
    fn layout_path_rejects_bad_name() {
        let err = layout_path(Path::new("/ws"), "../escape").unwrap_err();
        assert!(matches!(err, LayoutError::InvalidName));
    }

    // --- Task 2: file I/O -------------------------------------------------

    #[test]
    fn save_then_load_round_trips_the_layout() {
        let dir = tempdir().unwrap();
        let layout = LayoutFile::new(sample_grid(), Some("pipeline".into()));
        save_layout(dir.path(), "build-watch", &layout).unwrap();
        let loaded = load_layout(dir.path(), "build-watch").unwrap();
        assert_eq!(layout, loaded);
    }

    #[test]
    fn save_lazily_creates_voss_layouts_only_on_first_write() {
        let dir = tempdir().unwrap();
        let voss = dir.path().join(".voss");
        assert!(!voss.exists(), "precondition: .voss must not pre-exist");
        // list/load_default must not create the directory.
        assert!(list_layouts(dir.path()).unwrap().is_empty());
        assert!(load_default_layout(dir.path()).unwrap().is_none());
        let missing = load_layout(dir.path(), "default").unwrap_err();
        assert!(matches!(missing, LayoutError::NotFound));
        assert!(!voss.exists(), ".voss must remain absent before any save");

        let layout = LayoutFile::new(sample_grid(), None);
        save_layout(dir.path(), "default", &layout).unwrap();
        assert!(voss.join("layouts").join("default.json").exists());
    }

    #[test]
    fn list_layouts_returns_sorted_names_without_json_suffix() {
        let dir = tempdir().unwrap();
        let layout = LayoutFile::new(sample_grid(), None);
        for name in ["zebra", "apple", "build-watch"] {
            save_layout(dir.path(), name, &layout).unwrap();
        }
        // A non-json sibling must be ignored.
        let stray = dir.path().join(".voss").join("layouts").join("README.md");
        std::fs::write(stray, "ignore me").unwrap();
        let names = list_layouts(dir.path()).unwrap();
        assert_eq!(names, vec!["apple", "build-watch", "zebra"]);
    }

    #[test]
    fn load_default_layout_returns_none_when_missing() {
        let dir = tempdir().unwrap();
        assert!(load_default_layout(dir.path()).unwrap().is_none());
    }

    #[test]
    fn load_default_layout_is_fail_safe_for_corrupt_json() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss").join("layouts");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(path.join("default.json"), "{not-json").unwrap();
        // Must not panic, must return Ok(None) so startup proceeds.
        assert!(load_default_layout(dir.path()).unwrap().is_none());
    }

    #[test]
    fn load_default_layout_is_fail_safe_for_unsupported_version() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss").join("layouts");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(
            path.join("default.json"),
            r#"{"version":999,"activePreset":null,"grid":null}"#,
        )
        .unwrap();
        assert!(load_default_layout(dir.path()).unwrap().is_none());
    }

    #[test]
    fn load_layout_returns_invalid_file_for_corrupt_json() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss").join("layouts");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(path.join("bad.json"), "garbage").unwrap();
        let err = load_layout(dir.path(), "bad").unwrap_err();
        assert!(matches!(err, LayoutError::InvalidFile));
    }

    #[test]
    fn load_layout_returns_unsupported_version_for_v999() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss").join("layouts");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(
            path.join("future.json"),
            r#"{"version":999,"activePreset":null,"grid":{}}"#,
        )
        .unwrap();
        let err = load_layout(dir.path(), "future").unwrap_err();
        assert!(matches!(err, LayoutError::UnsupportedVersion));
    }

    #[test]
    fn load_layout_missing_returns_not_found() {
        let dir = tempdir().unwrap();
        let err = load_layout(dir.path(), "ghost").unwrap_err();
        assert!(matches!(err, LayoutError::NotFound));
    }

    #[test]
    fn save_and_load_reject_traversal_names() {
        let dir = tempdir().unwrap();
        let layout = LayoutFile::new(sample_grid(), None);
        let save_err = save_layout(dir.path(), "../escape", &layout).unwrap_err();
        assert!(matches!(save_err, LayoutError::InvalidName));
        let load_err = load_layout(dir.path(), "../escape").unwrap_err();
        assert!(matches!(load_err, LayoutError::InvalidName));
    }

    #[test]
    fn error_display_strings_match_ui_spec_copy() {
        // Matches A4-UI-SPEC Save/Load Feedback table exactly so the
        // app-level wrappers can forward these to the UI verbatim.
        assert_eq!(
            LayoutError::InvalidName.to_string(),
            "layout name cannot contain /, \\ or .."
        );
        assert_eq!(
            LayoutError::InvalidFile.to_string(),
            "layout ignored: invalid file"
        );
        assert_eq!(
            LayoutError::UnsupportedVersion.to_string(),
            "layout ignored: unsupported version"
        );
        assert_eq!(LayoutError::SaveFailed.to_string(), "could not save layout");
        assert_eq!(LayoutError::LoadFailed.to_string(), "could not load layout");
        assert_eq!(LayoutError::NotFound.to_string(), "layout not found");
    }
}
