# A5-01 Summary

## Tests

- Added 24 focused `project::tests` covering schema serde, `ProjectError` display strings, constants, project open canonicalization/error handling/git branch read/lazy `.voss/`, `default_cwd`, and recents I/O.
- Passing target: `cargo test -p voss-app-core project:: -- --nocapture`

## Shipped Signatures

```rust
pub const CURRENT_RECENTS_VERSION: u32 = 1;
pub const RECENTS_CAP: usize = 5;

pub struct ProjectInfo {
    pub path: String,
    pub name: String,
    pub git_branch: Option<String>,
}

pub enum ProjectError {
    NotFound,
    NotADirectory,
    InvalidPath,
}

pub struct RecentsFile {
    pub version: u32,
    pub recents: Vec<String>,
}

pub fn open_project(path: &Path) -> Result<ProjectInfo, ProjectError>;
pub fn list_recents() -> Vec<String>;
pub fn default_cwd(project_path: Option<&Path>) -> String;
fn read_git_branch(path: &Path) -> Option<String>;
fn load_recents() -> RecentsFile;
fn update_recents(canonical: &Path);
fn save_recents(file: &RecentsFile) -> std::io::Result<()>;
fn recents_path() -> PathBuf;
```

## Test Recents Override

`project.rs` uses a `#[cfg(test)]` thread-local `TEST_RECENTS_PATH` override for `recents_path()`. Each recents/open-project test calls `isolate_recents()`, which points recents I/O at a tempdir-backed `recents.json`; tests panic if recents are touched without an override, so the developer's real `~/.config/voss-app/recents.json` is never used under `cfg(test)`.
