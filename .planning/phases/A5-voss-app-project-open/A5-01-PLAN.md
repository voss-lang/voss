---
phase: A5-voss-app-project-open
plan: 01
type: execute
wave: 1
depends_on: [A5-00]
files_modified:
  - crates/voss-app-core/src/project.rs
  - crates/voss-app-core/src/lib.rs
  - crates/voss-app-core/Cargo.toml
autonomous: true
requirements: [WS-02, WS-03, WS-04, WS-05, WS-06]
must_haves:
  truths:
    - "Rust owns project canonicalization, basename derivation, git branch read, recents I/O, and home-cwd resolution"
    - "open_project never creates <workspace>/.voss/ — lazy rule preserved across the project-open path"
    - "Recents are capped at 5, newest first, deduplicated by exact string (after canonicalization)"
    - "Git branch read is best-effort: non-git / detached / bare / unborn HEAD all surface as None"
    - "default_cwd(None) falls back to home_dir(), then '/' if HOME is unset (D-11)"
    - "ProjectError Display strings match A4-03 LayoutError pattern and will surface verbatim in any future A11 setup-error UI"
  artifacts:
    - path: "crates/voss-app-core/src/project.rs"
      provides: "ProjectInfo, ProjectError, RecentsFile, open_project, list_recents, default_cwd, read_git_branch + unit tests"
      contains: "pub struct ProjectInfo"
    - path: "crates/voss-app-core/src/lib.rs"
      provides: "Module export and re-export block for the new project module"
      contains: "pub mod project"
    - path: "crates/voss-app-core/Cargo.toml"
      provides: "git2 + dirs dependency lines for the new module"
      contains: "git2"
---

<objective>
Add the Rust core for project open: a new `voss-app-core::project` module owning `ProjectInfo`, `RecentsFile`, `ProjectError`, `open_project`, `list_recents`, `default_cwd`, and `read_git_branch`. Mirror the A4-03 `layouts.rs` structure (versioned schema, fail-safe reads, lazy `.voss/`, typed errors with UI-matching Display strings).

Purpose: Lock the IPC contract Rust-side before any Tauri wrapper or frontend wiring. Every later A5 wave reads off these signatures and casings.
Output: A green `cargo test -p voss-app-core project` suite that covers SPEC requirements 2, 3, 4, 5, 6, and the lazy `.voss/` boundary.
</objective>

<context>
@.planning/phases/A5-voss-app-project-open/A5-SPEC.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A5-voss-app-project-open/A5-RESEARCH.md
@.planning/phases/A5-voss-app-project-open/A5-PATTERNS.md
@crates/voss-app-core/src/layouts.rs
@crates/voss-app-core/src/lib.rs
@crates/voss-app-core/Cargo.toml
@Cargo.toml

<interfaces>
<!-- Contracts later A5 plans will invoke; lock these in this wave. -->
<!-- Mirrors the A4-03 LayoutError pattern (Display strings = UI copy verbatim). -->

From the new crates/voss-app-core/src/project.rs (this plan creates):

pub const CURRENT_RECENTS_VERSION: u32 = 1;
pub const RECENTS_CAP: usize = 5;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectInfo {
    pub path: String,        // canonicalized absolute path
    pub name: String,        // basename
    pub git_branch: Option<String>,  // serde => "gitBranch"
}

#[derive(Debug, thiserror::Error)]
pub enum ProjectError {
    #[error("project not found")]
    NotFound,
    #[error("project path is not a directory")]
    NotADirectory,
    #[error("could not resolve project path")]
    InvalidPath,
}

#[derive(Serialize, Deserialize, Default)]
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

From the new crates/voss-app-core/src/lib.rs additions:

pub mod project;
pub use project::{
    open_project, list_recents, default_cwd,
    ProjectInfo, ProjectError, RecentsFile,
    CURRENT_RECENTS_VERSION, RECENTS_CAP,
};

From A4-03 (analog, do NOT modify) crates/voss-app-core/src/layouts.rs:

#[derive(Debug, thiserror::Error)]
pub enum LayoutError {
    #[error("layout name cannot contain /, \\ or ..")]
    InvalidName,
    // ...  ← mirror this Display-string-as-UI-copy pattern in ProjectError
}
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Untrusted user-supplied path | Folder picker / stale recent / drag-drop entry — must be canonicalized and existence-checked in Rust |
| `<workspace>/.voss/` | Project-open path MUST NOT create this directory; only future write paths (layout save, settings save) may |
| `~/.config/voss-app/recents.json` | Best-effort writes; corruption must not crash the app |
| `git2` filesystem walk | `Repository::discover` walks UP — may surface a parent repo's branch for nested directories (documented, intentional) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A5-01 | Tampering | `open_project` lazy `.voss/` violation | mitigate | Dedicated `open_project_does_not_create_voss_directory` test cloned from `layouts.rs::save_lazily_creates_voss_layouts_only_on_first_write`; no `create_dir_all` call against `<workspace>/.voss/` anywhere in the new module |
| T-A5-03 | Information disclosure / Denial of service | path traversal / non-existent project path | mitigate | `std::fs::canonicalize` first — any error returns `ProjectError::NotFound` so stale recents prune; check `is_dir()` after canonicalize; reject `file_name() == None` (root `/`) with `ProjectError::InvalidPath` |
| T-A5-04 | Denial of service | corrupt recents file crash | mitigate | `load_recents` returns empty `RecentsFile` on any read/parse/version-mismatch error and logs to stderr; never panics; never bubbles to UI |
| T-A5-05 | Information disclosure | git branch leak via `discover` walking past project root | accept | A5-RESEARCH Pitfall 3 — `discover` semantics match `git status` and are what users mean 95% of the time; document in module header; revisit if user feedback |
</threat_model>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Add git2 + dirs deps and define ProjectInfo / ProjectError / RecentsFile schema</name>
  <files>crates/voss-app-core/Cargo.toml, crates/voss-app-core/src/project.rs, crates/voss-app-core/src/lib.rs</files>
  <read_first>
    - crates/voss-app-core/Cargo.toml — current workspace-dep inheritance pattern (lines 12-23)
    - crates/voss-app-core/src/lib.rs — module export + `pub use` block (lines 3-11)
    - crates/voss-app-core/src/layouts.rs lines 1-69 — module header comment style + `CURRENT_LAYOUT_VERSION` constant + `LayoutError` Display pattern
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Standard Stack — git2 0.20 `default-features = false, features = ["vendored-libgit2"]` line (do NOT use `vendored-openssl`; the RESEARCH-locked feature is `vendored-libgit2` — A5-PATTERNS line 132 has a typo, RESEARCH is authoritative)
    - .planning/phases/A5-voss-app-project-open/A5-CONTEXT.md D-09 — recents schema lock
  </read_first>
  <behavior>
    - Test 1: `ProjectInfo` serde round-trip uses camelCase: `git_branch: None` serializes to `"gitBranch": null`
    - Test 2: `RecentsFile` round-trip preserves `version: 1` and `recents: Vec<String>` order
    - Test 3: `ProjectError::NotFound.to_string() == "project not found"` (verbatim Display assertion, A4-03 pattern)
    - Test 4: `ProjectError::NotADirectory.to_string() == "project path is not a directory"`
    - Test 5: `ProjectError::InvalidPath.to_string() == "could not resolve project path"`
    - Test 6: `CURRENT_RECENTS_VERSION == 1` and `RECENTS_CAP == 5`
  </behavior>
  <action>
    Edit `crates/voss-app-core/Cargo.toml`: append to `[dependencies]`:

      git2 = { version = "0.20", default-features = false, features = ["vendored-libgit2"] }
      dirs = { workspace = true }

    The `dirs` dep is workspace-managed (root `Cargo.toml` line 41 area) per A5-PATTERNS Landmine #5; `git2` is NOT in workspace deps so it gets pinned locally. Use `vendored-libgit2` per A5-RESEARCH (not the `vendored-openssl` typo in A5-PATTERNS).

    Create `crates/voss-app-core/src/project.rs` with the module header (clone the `layouts.rs:1-17` doc-comment style, naming the contract and explicitly calling out the **lazy `.voss/` rule** — *open_project never touches `<workspace>/.voss/`*). Define `CURRENT_RECENTS_VERSION: u32 = 1`, `RECENTS_CAP: usize = 5`, `ProjectInfo` (with `#[serde(rename_all = "camelCase")]`), `ProjectError` (`thiserror::Error` enum with `NotFound` / `NotADirectory` / `InvalidPath` variants and Display strings exactly as in the `<interfaces>` block — these strings will surface verbatim in any future A11 setup-error UI per CONTEXT line 99), and `RecentsFile`.

    Edit `crates/voss-app-core/src/lib.rs`: insert `pub mod project;` in module-list alphabetical order and append a `pub use project::{ ... };` block matching the `<interfaces>` block.

    Add `#[cfg(test)] mod tests` at the bottom of `project.rs` with the six Display / serde / constant tests above. Use the existing workspace `tempfile = "3"` (already a dev-dep per `layouts.rs` tests) for any temp-dir setup. No `open_project` impl yet — Tasks 2 and 3 land it.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core project::tests -- --nocapture 2>&1 | tail -30 && grep -q 'pub struct ProjectInfo' crates/voss-app-core/src/project.rs && grep -q 'pub enum ProjectError' crates/voss-app-core/src/project.rs && grep -q 'pub struct RecentsFile' crates/voss-app-core/src/project.rs && grep -q '"gitBranch"' crates/voss-app-core/src/project.rs && grep -q 'pub mod project' crates/voss-app-core/src/lib.rs && grep -q 'git2' crates/voss-app-core/Cargo.toml && grep -q 'vendored-libgit2' crates/voss-app-core/Cargo.toml && echo PROJECT_SCHEMA_OK</automated>
  </verify>
  <acceptance_criteria>
    - `crates/voss-app-core/Cargo.toml` has `git2` (with `vendored-libgit2`) and `dirs` (workspace inherit).
    - `ProjectInfo` serializes `git_branch` as JSON key `"gitBranch"` (verified in a serde round-trip test).
    - `ProjectError` Display strings match the `<interfaces>` block byte-for-byte (verbatim test, A4-03 pattern).
    - `CURRENT_RECENTS_VERSION == 1` and `RECENTS_CAP == 5` constants exist.
    - `pub mod project;` + `pub use project::{...};` in `lib.rs` matches the `<interfaces>` block.
    - `cargo test -p voss-app-core project::tests` exits 0.
    - `PROJECT_SCHEMA_OK` prints.
  </acceptance_criteria>
  <done>The Rust schema, error types, and module exports are locked. Downstream waves can rely on the casings without churn.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Implement open_project, read_git_branch, and default_cwd</name>
  <files>crates/voss-app-core/src/project.rs</files>
  <read_first>
    - crates/voss-app-core/src/project.rs — Task 1 schema
    - crates/voss-app-core/src/layouts.rs lines 181-208 (`load_default_layout`) — fail-safe-by-default pattern for missing/corrupt reads
    - crates/voss-app-core/src/layouts.rs lines 330-344 — the canonical lazy `.voss/` assertion test pattern A5 must clone
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Code Examples — verified `open_project`, `read_git_branch`, `default_cwd` signatures (RESEARCH is authoritative over PATTERNS where they differ)
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md Pitfall 2 (canonicalize on non-existent path) + Pitfall 3 (`discover` walks up) + Pitfall 4 (`home_dir()` None branch) + Pitfall 6 (macOS `/tmp` → `/private/tmp` symlink — always canonicalize first)
  </read_first>
  <behavior>
    - Test 1: `open_project(tempdir().path())` returns `ProjectInfo` with `name == basename` (SPEC Req-3, AC #5)
    - Test 2: `open_project` on a non-git directory returns `git_branch: None` (SPEC Req-3, AC #6)
    - Test 3: `open_project` on a fresh `git2::Repository::init`'d dir returns the current branch shorthand (SPEC Req-3, AC #6)
    - Test 4: `open_project` on a non-existent path returns `ProjectError::NotFound` (Pitfall 2 — stale recents prune contract)
    - Test 5: `open_project` on a regular file (not a dir) returns `ProjectError::NotADirectory`
    - Test 6: `open_project(tempdir().path())` does NOT create `<temp>/.voss/` (SPEC Req-6, AC #9, T-A5-01 mitigation)
    - Test 7: `open_project` canonicalizes — on macOS, the returned `path` is the `/private/var/...` form, not the `/var/...` form (Pitfall 6 — ensures recents dedup works across repeated opens of the same dir)
    - Test 8: `default_cwd(Some(&p))` returns `p.to_string_lossy()`
    - Test 9: `default_cwd(None)` returns `dirs::home_dir()` as a string when HOME is set
    - Test 10: `default_cwd(None)` returns `"/"` when `dirs::home_dir()` is `None` (D-11 fallback — covered via a separate helper that takes an `Option<PathBuf>` so the test can inject `None`, OR documented as untestable on a real machine and gated on the path equality above)
  </behavior>
  <action>
    Implement `open_project(path: &Path) -> Result<ProjectInfo, ProjectError>` exactly per the A5-RESEARCH §Code Examples block (RESEARCH lines ~493-518 are the verified shape):

    1. `std::fs::canonicalize(path)` → on error log to stderr and return `ProjectError::NotFound`.
    2. `is_dir()` check → `ProjectError::NotADirectory` if not.
    3. `file_name().and_then(|n| n.to_str()).ok_or(ProjectError::InvalidPath)?.to_string()` for `name`.
    4. `read_git_branch(&canonical)` for `git_branch`.
    5. `update_recents(&canonical)` (the recents implementation lands in Task 3 — for now stub it as `fn update_recents(_: &Path) {}` and add a TODO referencing A5-01 Task 3).
    6. Return `ProjectInfo`.

    Implement `read_git_branch(path: &Path) -> Option<String>`:
      let repo = git2::Repository::discover(path).ok()?;
      let head = repo.head().ok()?;
      head.shorthand().map(|s| s.to_string())
    Non-git, detached HEAD, bare repos, unborn HEAD all surface as `None`. Document the `discover` walks-up semantic in a `///` comment (A5-RESEARCH Pitfall 3 / T-A5-05).

    Implement `default_cwd(project_path: Option<&Path>) -> String`:
      if let Some(p) = project_path { return p.to_string_lossy().into_owned(); }
      dirs::home_dir().map(|h| h.to_string_lossy().into_owned()).unwrap_or_else(|| "/".to_string())

    Add the test block. Use `tempfile::tempdir()` for filesystem isolation. For Test 3, use `git2::Repository::init(temp_dir)` to create an actual git repo before reading the branch. **Critical**: tests must NOT touch `~/.config/voss-app/recents.json` — the `update_recents` stub keeps tests hermetic for this task (Task 3 will introduce a `recents_path_for_tests` injection seam if needed, or scope recents tests to a separate cfg-test helper that overrides the path).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core project:: -- --nocapture 2>&1 | tail -40 && grep -q 'fn open_project' crates/voss-app-core/src/project.rs && grep -q 'fn read_git_branch' crates/voss-app-core/src/project.rs && grep -q 'fn default_cwd' crates/voss-app-core/src/project.rs && grep -q 'Repository::discover' crates/voss-app-core/src/project.rs && grep -q 'canonicalize' crates/voss-app-core/src/project.rs && ! grep -qE 'create_dir_all\([^)]*\.voss' crates/voss-app-core/src/project.rs && echo PROJECT_OPEN_OK</automated>
  </verify>
  <acceptance_criteria>
    - `open_project` canonicalizes first; non-existent → `NotFound`; non-dir → `NotADirectory`; root `/` → `InvalidPath`.
    - `read_git_branch` uses `Repository::discover` (not `Repository::open`) and returns `None` on any error.
    - `default_cwd(None)` falls back to `home_dir()` then `"/"`.
    - Test for `open_project_does_not_create_voss_directory` passes (T-A5-01 mitigation).
    - macOS canonicalization test passes (Pitfall 6 — recents dedup correctness).
    - `cargo test -p voss-app-core project::` exits 0.
    - Grep proves no `create_dir_all` is called against any `.voss` path in `project.rs`.
    - `PROJECT_OPEN_OK` prints.
  </acceptance_criteria>
  <done>`open_project`, `read_git_branch`, and `default_cwd` are implemented, tested, and respect the lazy `.voss/` boundary.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 3: Implement recents I/O (load_recents, update_recents, save_recents) and wire into open_project</name>
  <files>crates/voss-app-core/src/project.rs</files>
  <read_first>
    - crates/voss-app-core/src/project.rs — Tasks 1 and 2
    - apps/voss-app/src-tauri/src/lib.rs lines 18-30 — the `settings_path()` idiom A5 must clone for `recents_path()` (NOT `dirs::config_dir()` — the A1 D-08 lock is `~/.config/voss-app/` even on macOS; PRESERVE the NOTE comment about why)
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Code Examples lines ~540-604 — verified `RecentsFile`, `load_recents`, `update_recents`, `save_recents`, `recents_path` shapes
    - .planning/phases/A5-voss-app-project-open/A5-CONTEXT.md D-09 (schema), D-10 (atomic-ish best-effort writes)
  </read_first>
  <behavior>
    - Test 1: `load_recents()` returns empty `RecentsFile { version: 1, recents: [] }` when the file does not exist
    - Test 2: `load_recents()` returns empty `RecentsFile` on a corrupt JSON file (no panic)
    - Test 3: `load_recents()` returns empty `RecentsFile` when version != 1 (forward-decline)
    - Test 4: `update_recents` then `list_recents` round-trips a single path to index 0
    - Test 5: Opening 6 distinct dirs leaves recents capped at 5, newest first, oldest dropped (SPEC Req-5, AC #8)
    - Test 6: Re-opening an existing recent moves it to index 0 without duplication (SPEC Req-5)
    - Test 7: `save_recents` writes via tmp + rename (verify by introspection — the function returns `io::Result<()>` and `update_recents` swallows failures)
    - Test 8: `open_project` end-to-end on 2 tempdirs updates the recents file at `recents_path()` to length 2, newest first
    - Test 9: Recents writes do NOT touch `<workspace>/.voss/` (sanity assertion against T-A5-01)
  </behavior>
  <action>
    Implement `recents_path() -> PathBuf` cloning `settings_path()` from `apps/voss-app/src-tauri/src/lib.rs:18-30` verbatim — same `dirs::home_dir().unwrap_or_default().join(".config").join("voss-app")` chain, just `.join("recents.json")` at the end. **Preserve the NOTE comment** explaining why we don't use `dirs::config_dir()` (A1 D-08 lock — the `~/Library/Application Support` macOS divergence is intentional and rejected).

    Implement `load_recents() -> RecentsFile` per RESEARCH §Code Examples: read file, parse, version-check; on any failure log `[voss-app] recents.json missing or corrupt; using empty list` to stderr and return `RecentsFile { version: CURRENT_RECENTS_VERSION, recents: vec![] }`.

    Implement `update_recents(canonical: &Path)`:
      let mut file = load_recents();
      let entry = canonical.to_string_lossy().into_owned();
      file.recents.retain(|p| p != &entry);   // dedup
      file.recents.insert(0, entry);          // newest first
      file.recents.truncate(RECENTS_CAP);     // cap at 5
      if let Err(e) = save_recents(&file) { eprintln!("[voss-app] recents save failed (non-fatal): {e}"); }

    Implement `save_recents(file: &RecentsFile) -> std::io::Result<()>`:
      let path = recents_path();
      if let Some(dir) = path.parent() { std::fs::create_dir_all(dir)?; }  // ~/.config/voss-app is fine — NOT <workspace>/.voss
      let tmp = path.with_extension("json.tmp");
      let json = serde_json::to_string_pretty(file).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
      std::fs::write(&tmp, json)?;
      std::fs::rename(&tmp, &path)?;
      Ok(())

    Replace the Task 2 stub `fn update_recents(_: &Path) {}` with the real implementation.

    Add `pub fn list_recents() -> Vec<String> { load_recents().recents }`.

    **Test isolation**: tests must NOT clobber the developer's real `~/.config/voss-app/recents.json`. The cleanest approach: introduce a `#[cfg(test)]` helper that returns a `tempdir`-backed path via a thread-local or `OnceCell<PathBuf>` test override, OR run recents tests serially with `serial_test` (NOT a workspace dep — avoid adding it; prefer the thread-local override). Implementation suggestion: a `fn recents_path() -> PathBuf` with `#[cfg(not(test))]` and `#[cfg(test)]` siblings, the test variant reading from a `OnceLock<PathBuf>` set in test setup. Document the chosen mechanism in a `///` comment.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core project:: -- --nocapture 2>&1 | tail -40 && grep -q 'fn list_recents' crates/voss-app-core/src/project.rs && grep -q 'fn load_recents' crates/voss-app-core/src/project.rs && grep -q 'fn update_recents' crates/voss-app-core/src/project.rs && grep -q 'fn save_recents' crates/voss-app-core/src/project.rs && grep -q 'fn recents_path' crates/voss-app-core/src/project.rs && grep -q '\.json\.tmp' crates/voss-app-core/src/project.rs && grep -q 'RECENTS_CAP' crates/voss-app-core/src/project.rs && ! grep -qE 'create_dir_all\([^)]*\.voss' crates/voss-app-core/src/project.rs && echo PROJECT_RECENTS_OK</automated>
  </verify>
  <acceptance_criteria>
    - `recents_path()` resolves to `~/.config/voss-app/recents.json` (A1 D-08 lock), and the NOTE comment is preserved.
    - `load_recents()` returns empty on missing / corrupt / version-mismatched files, with stderr log — no panics.
    - `update_recents()` prepends + dedups + caps at `RECENTS_CAP = 5`.
    - `save_recents()` writes via tmp + rename (atomic-ish per D-10).
    - 6-dir test proves the oldest is dropped; re-open test proves move-to-front-no-dup.
    - End-to-end `open_project` updates recents and never creates `<workspace>/.voss/`.
    - Tests do not clobber the developer's real `~/.config/voss-app/recents.json` (cfg-test override or equivalent).
    - `cargo test -p voss-app-core project::` exits 0.
    - `PROJECT_RECENTS_OK` prints.
  </acceptance_criteria>
  <done>Recents I/O is complete, hermetic in tests, and respects every D-09 / D-10 / T-A5-04 contract. The Rust core is feature-complete; A5-02 can now wire Tauri wrappers.</done>
</task>

</tasks>

<verification>
Run `cargo test -p voss-app-core project:: -- --nocapture` and `cargo build -p voss-app-core` after each task. The wave is done when all three tasks print their tags and `cargo test --workspace` is still green.
</verification>

<success_criteria>
- `ProjectInfo`, `ProjectError`, `RecentsFile` are defined with verified casings and verbatim Display strings.
- `open_project` canonicalizes, derives basename, reads git branch best-effort, updates recents, and never touches `<workspace>/.voss/`.
- `default_cwd(None)` falls back to `home_dir()` then `"/"` (D-11).
- Recents capped at 5, deduped, newest first; corrupt file falls back to empty.
- All A5-RESEARCH §Phase Requirements → Test Map Rust rows are green.
- The IPC contract (function names + payload shapes) is locked for A5-02.
</success_criteria>

<output>
Create `.planning/phases/A5-voss-app-project-open/A5-01-SUMMARY.md` with: tests added/passing count, exact function signatures shipped (so A5-02 can copy without re-deriving), notes on the cfg-test recents-path override mechanism chosen.
</output>
