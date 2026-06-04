//! A5 project-open persistence — canonical project metadata, recents JSON,
//! best-effort git branch detection, and project-less default cwd resolution.
//!
//! The on-disk recents shape is versioned so the same camelCase payload the
//! TypeScript model uses (`"gitBranch"`) round-trips unchanged while the
//! persisted file remains a small `{ version, recents }` schema. Bump
//! `CURRENT_RECENTS_VERSION` whenever the recents file shape changes.
//!
//! All errors are typed (`ProjectError`) so app-level `#[tauri::command]`
//! wrappers can pass the UI copy through verbatim. Corrupt, missing, or
//! unsupported `recents.json` files fail closed to an empty list so app
//! startup is never blocked by a convenience file (D-10).
//!
//! `open_project` never touches `<workspace>/.voss/`; that directory remains
//! lazily created by later write paths such as layout save (CONCEPT §10 Q7).

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// On-disk recents schema version. Bump when the schema shape changes.
pub const CURRENT_RECENTS_VERSION: u32 = 1;

/// Maximum number of recent project paths persisted.
pub const RECENTS_CAP: usize = 5;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectInfo {
    pub path: String,
    pub name: String,
    pub git_branch: Option<String>,
}

/// Typed errors for project open. Display strings match the UI-SPEC
/// user-facing copy so app-level command wrappers can pass them through
/// verbatim.
#[derive(Debug, thiserror::Error)]
pub enum ProjectError {
    #[error("project not found")]
    NotFound,
    #[error("project path is not a directory")]
    NotADirectory,
    #[error("could not resolve project path")]
    InvalidPath,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct RecentsFile {
    pub version: u32,
    pub recents: Vec<String>,
}

pub fn open_project(path: &Path) -> Result<ProjectInfo, ProjectError> {
    let canonical = std::fs::canonicalize(path).map_err(|e| {
        eprintln!("[voss-app] open_project canonicalize: {e}");
        ProjectError::NotFound
    })?;

    if !canonical.is_dir() {
        return Err(ProjectError::NotADirectory);
    }

    let name = canonical
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or(ProjectError::InvalidPath)?
        .to_string();

    let git_branch = read_git_branch(&canonical);
    update_recents(&canonical);

    Ok(ProjectInfo {
        path: canonical.to_string_lossy().into_owned(),
        name,
        git_branch,
    })
}

pub fn list_recents() -> Vec<String> {
    load_recents().recents
}

pub fn default_cwd(project_path: Option<&Path>) -> String {
    if let Some(path) = project_path {
        return path.to_string_lossy().into_owned();
    }

    home_dir_string(dirs::home_dir())
}

/// Read the current git branch, if any. `Repository::discover` intentionally
/// walks up from `path`, matching `git status` behavior for nested folders.
fn read_git_branch(path: &Path) -> Option<String> {
    let repo = git2::Repository::discover(path).ok()?;
    let head = repo.head().ok()?;
    head.shorthand().map(|s| s.to_string())
}

fn load_recents() -> RecentsFile {
    let path = recents_path();
    let empty = || RecentsFile {
        version: CURRENT_RECENTS_VERSION,
        recents: Vec::new(),
    };

    let raw = match std::fs::read_to_string(&path) {
        Ok(raw) => raw,
        Err(e) => {
            eprintln!("[voss-app] recents.json missing or corrupt; using empty list: {e}");
            return empty();
        }
    };

    let file: RecentsFile = match serde_json::from_str(&raw) {
        Ok(file) => file,
        Err(e) => {
            eprintln!("[voss-app] recents.json missing or corrupt; using empty list: {e}");
            return empty();
        }
    };

    if file.version != CURRENT_RECENTS_VERSION {
        eprintln!("[voss-app] recents.json missing or corrupt; using empty list");
        return empty();
    }

    file
}

fn update_recents(canonical: &Path) {
    let mut file = load_recents();
    let entry = canonical.to_string_lossy().into_owned();
    file.recents.retain(|path| path != &entry);
    file.recents.insert(0, entry);
    file.recents.truncate(RECENTS_CAP);

    if let Err(e) = save_recents(&file) {
        eprintln!("[voss-app] recents save failed (non-fatal): {e}");
    }
}

fn save_recents(file: &RecentsFile) -> std::io::Result<()> {
    let path = recents_path();
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }

    // Write recents.json.tmp before renaming over recents.json.
    let tmp = path.with_extension("json.tmp");
    let json = serde_json::to_string_pretty(file).map_err(std::io::Error::other)?;
    std::fs::write(&tmp, json)?;
    std::fs::rename(&tmp, &path)?;
    Ok(())
}

#[cfg(not(test))]
fn recents_path() -> PathBuf {
    // NOTE: build the path manually from home_dir() so it resolves to
    // ~/.config/voss-app/recents.json on every platform (CONTEXT D-08/D-09).
    // The `dirs` crate's platform-native config helper is intentionally NOT
    // used: on macOS it resolves to ~/Library/Application Support, which
    // diverges from the user-facing ~/.config path locked by D-08.
    // See A1-RESEARCH.md Pitfall 8 and A1-UI-SPEC.md Theme Override System Contract.
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("recents.json")
}

#[cfg(test)]
fn recents_path() -> PathBuf {
    TEST_RECENTS_PATH.with(|path| {
        path.borrow()
            .clone()
            .expect("tests must set TEST_RECENTS_PATH before touching recents")
    })
}

fn home_dir_string(home: Option<PathBuf>) -> String {
    home.map(|h| h.to_string_lossy().into_owned())
        .unwrap_or_else(|| "/".to_string())
}

#[cfg(test)]
thread_local! {
    /// Thread-local override keeps recents tests hermetic and parallel-safe:
    /// unit tests never touch the developer's real ~/.config/voss-app/recents.json.
    static TEST_RECENTS_PATH: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::{tempdir, TempDir};

    fn isolate_recents() -> TempDir {
        let dir = tempdir().unwrap();
        let path = dir.path().join("recents.json");
        TEST_RECENTS_PATH.with(|override_path| {
            *override_path.borrow_mut() = Some(path);
        });
        dir
    }

    fn canonical_string(path: &Path) -> String {
        std::fs::canonicalize(path)
            .unwrap()
            .to_string_lossy()
            .into_owned()
    }

    fn commit_initial_head(repo: &git2::Repository) {
        let workdir = repo.workdir().unwrap();
        std::fs::write(workdir.join("README.md"), "test\n").unwrap();

        let mut index = repo.index().unwrap();
        index.add_path(Path::new("README.md")).unwrap();
        index.write().unwrap();
        let tree_id = index.write_tree().unwrap();
        let tree = repo.find_tree(tree_id).unwrap();
        let sig = git2::Signature::now("Voss Test", "test@example.com").unwrap();
        repo.commit(Some("HEAD"), &sig, &sig, "initial", &tree, &[])
            .unwrap();
    }

    #[test]
    fn project_info_serializes_git_branch_as_camel_case() {
        let info = ProjectInfo {
            path: "/repo".into(),
            name: "repo".into(),
            git_branch: None,
        };
        let json = serde_json::to_string(&info).unwrap();
        assert!(json.contains("\"gitBranch\":null"));
        let loaded: ProjectInfo = serde_json::from_str(&json).unwrap();
        assert_eq!(loaded, info);
    }

    #[test]
    fn recents_file_round_trips_version_and_order() {
        let file = RecentsFile {
            version: CURRENT_RECENTS_VERSION,
            recents: vec!["/a".into(), "/b".into()],
        };
        let json = serde_json::to_string(&file).unwrap();
        let loaded: RecentsFile = serde_json::from_str(&json).unwrap();
        assert_eq!(loaded, file);
    }

    #[test]
    fn project_error_display_strings_match_contract() {
        assert_eq!(ProjectError::NotFound.to_string(), "project not found");
        assert_eq!(
            ProjectError::NotADirectory.to_string(),
            "project path is not a directory"
        );
        assert_eq!(
            ProjectError::InvalidPath.to_string(),
            "could not resolve project path"
        );
    }

    #[test]
    fn recents_constants_match_contract() {
        assert_eq!(CURRENT_RECENTS_VERSION, 1);
        assert_eq!(RECENTS_CAP, 5);
    }

    #[test]
    fn open_project_returns_basename_as_name() {
        let _recents = isolate_recents();
        let dir = tempdir().unwrap();
        let info = open_project(dir.path()).unwrap();
        assert_eq!(info.name, dir.path().file_name().unwrap().to_string_lossy());
    }

    #[test]
    fn open_project_returns_none_branch_for_non_git_dir() {
        let _recents = isolate_recents();
        let dir = tempdir().unwrap();
        let info = open_project(dir.path()).unwrap();
        assert_eq!(info.git_branch, None);
    }

    #[test]
    fn open_project_returns_current_branch_for_git_dir() {
        let _recents = isolate_recents();
        let dir = tempdir().unwrap();
        let repo = git2::Repository::init(dir.path()).unwrap();
        commit_initial_head(&repo);

        let info = open_project(dir.path()).unwrap();
        assert_eq!(
            info.git_branch,
            repo.head().unwrap().shorthand().map(str::to_string)
        );
    }

    #[test]
    fn open_project_nonexistent_path_returns_not_found() {
        let dir = tempdir().unwrap();
        let missing = dir.path().join("missing");
        let err = open_project(&missing).unwrap_err();
        assert!(matches!(err, ProjectError::NotFound));
    }

    #[test]
    fn open_project_regular_file_returns_not_a_directory() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("file.txt");
        std::fs::write(&file, "not a dir").unwrap();
        let err = open_project(&file).unwrap_err();
        assert!(matches!(err, ProjectError::NotADirectory));
    }

    #[test]
    fn open_project_root_path_returns_invalid_path() {
        let err = open_project(Path::new("/")).unwrap_err();
        assert!(matches!(err, ProjectError::InvalidPath));
    }

    #[test]
    fn open_project_does_not_create_voss_directory() {
        let _recents = isolate_recents();
        let dir = tempdir().unwrap();
        let voss = dir.path().join(".voss");
        assert!(!voss.exists(), "precondition: .voss must not pre-exist");

        let _info = open_project(dir.path()).unwrap();

        assert!(!voss.exists(), "open_project must not create .voss");
    }

    #[test]
    fn open_project_returns_canonical_path() {
        let _recents = isolate_recents();
        let dir = tempdir().unwrap();
        let info = open_project(dir.path()).unwrap();
        assert_eq!(info.path, canonical_string(dir.path()));
    }

    #[test]
    fn default_cwd_returns_project_path_when_present() {
        let path = Path::new("/workspace/project");
        assert_eq!(default_cwd(Some(path)), "/workspace/project");
    }

    #[test]
    fn default_cwd_falls_back_to_home_for_no_project() {
        let cwd = default_cwd(None);
        assert_eq!(cwd, dirs::home_dir().unwrap().to_string_lossy());
    }

    #[test]
    fn home_dir_string_falls_back_to_root_when_home_is_none() {
        assert_eq!(home_dir_string(None), "/");
    }

    #[test]
    fn load_recents_returns_empty_when_file_is_missing() {
        let _recents = isolate_recents();
        assert_eq!(
            load_recents(),
            RecentsFile {
                version: CURRENT_RECENTS_VERSION,
                recents: Vec::new()
            }
        );
    }

    #[test]
    fn load_recents_returns_empty_for_corrupt_json() {
        let _recents = isolate_recents();
        std::fs::write(recents_path(), "not json").unwrap();
        assert_eq!(load_recents().recents, Vec::<String>::new());
    }

    #[test]
    fn load_recents_returns_empty_for_unsupported_version() {
        let _recents = isolate_recents();
        let file = RecentsFile {
            version: CURRENT_RECENTS_VERSION + 1,
            recents: vec!["/old".into()],
        };
        save_recents(&file).unwrap();
        assert_eq!(load_recents().recents, Vec::<String>::new());
    }

    #[test]
    fn update_recents_then_list_recents_round_trips_single_path() {
        let _recents = isolate_recents();
        let dir = tempdir().unwrap();
        let canonical = std::fs::canonicalize(dir.path()).unwrap();

        update_recents(&canonical);

        assert_eq!(list_recents(), vec![canonical.to_string_lossy()]);
    }

    #[test]
    fn update_recents_caps_at_five_newest_first() {
        let _recents = isolate_recents();
        let dirs: Vec<TempDir> = (0..6).map(|_| tempdir().unwrap()).collect();
        let canonical: Vec<PathBuf> = dirs
            .iter()
            .map(|dir| std::fs::canonicalize(dir.path()).unwrap())
            .collect();

        for path in &canonical {
            update_recents(path);
        }

        let expected: Vec<String> = canonical
            .iter()
            .rev()
            .take(RECENTS_CAP)
            .map(|p| p.to_string_lossy().into_owned())
            .collect();
        assert_eq!(list_recents(), expected);
    }

    #[test]
    fn update_recents_moves_existing_path_to_front_without_duplicate() {
        let _recents = isolate_recents();
        let first = tempdir().unwrap();
        let second = tempdir().unwrap();
        let first = std::fs::canonicalize(first.path()).unwrap();
        let second = std::fs::canonicalize(second.path()).unwrap();

        update_recents(&first);
        update_recents(&second);
        update_recents(&first);

        assert_eq!(
            list_recents(),
            vec![
                first.to_string_lossy().into_owned(),
                second.to_string_lossy().into_owned()
            ]
        );
    }

    #[test]
    fn save_recents_writes_json_tmp_then_renames() {
        let _recents = isolate_recents();
        let file = RecentsFile {
            version: CURRENT_RECENTS_VERSION,
            recents: vec!["/repo".into()],
        };

        save_recents(&file).unwrap();

        assert!(recents_path().exists());
        assert!(!recents_path().with_extension("json.tmp").exists());
        assert_eq!(load_recents(), file);
    }

    #[test]
    fn open_project_updates_recents_newest_first() {
        let _recents = isolate_recents();
        let first = tempdir().unwrap();
        let second = tempdir().unwrap();

        let first_info = open_project(first.path()).unwrap();
        let second_info = open_project(second.path()).unwrap();

        assert_eq!(list_recents(), vec![second_info.path, first_info.path]);
    }

    #[test]
    fn recents_writes_do_not_touch_workspace_voss_directory() {
        let _recents = isolate_recents();
        let dir = tempdir().unwrap();
        let canonical = std::fs::canonicalize(dir.path()).unwrap();

        update_recents(&canonical);

        assert!(!dir.path().join(".voss").exists());
    }
}
