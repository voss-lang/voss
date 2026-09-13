---
phase: A9
plan: "01"
title: "Rust settings backend — types, load/save/merge, Tauri commands"
wave: 1
depends_on: []
files_modified:
  - crates/voss-app-core/src/settings.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src-tauri/src/lib.rs
autonomous: true
requirements: []
must_haves:
  truths:
    - "UserSettings + WorkspaceSettings serde structs with #[serde(default)] for every field"
    - "load_user_settings reads ~/.config/voss-app/settings.json, returns defaults on missing/corrupt (D-08)"
    - "load_workspace_settings reads .voss/settings.json, returns None if absent"
    - "merge_settings shallow-merges workspace over user (D-07), workspace keys overwrite at top level"
    - "save_user_settings atomic write + fail-safe (A4 layouts.rs pattern)"
    - "save_workspace_settings lazy .voss/ creation (CONCEPT Q7)"
    - "open_settings_json uses tauri::api::shell::open to open file in OS editor (D-13)"
    - "Tauri commands registered in apps/voss-app/src-tauri/src/lib.rs (cross-crate pattern)"
---

# A9-01: Rust Settings Backend

## Objective

Build the Rust-side settings module (`settings.rs`) with typed structs, load/save/merge logic, and Tauri commands. This is the persistence layer that the frontend settings UI (A9-03) will call.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Corrupt settings.json crashes app | `#[serde(default)]` on every field; corrupt file → log warning, return defaults (D-08) |
| Race condition on settings write | Atomic write (write-to-tmp, rename) — same pattern as layouts.rs |
| Path traversal via workspace path | Validate workspace_path is absolute, under project root |
| Secrets in settings.json | Settings schema contains no credential fields; telemetry flags are booleans only |

## Tasks

### Task 1: Create `settings.rs` with typed structs

<read_first>
- crates/voss-app-core/src/layouts.rs (pattern for serde structs, error types, atomic write)
- crates/voss-app-core/src/session.rs (pattern for load with fail-safe defaults)
- crates/voss-app-core/src/lib.rs (module registration pattern)
- apps/voss-app/src/styles/variant-b.css (token var names for theme defaults)
</read_first>

<action>
Create `crates/voss-app-core/src/settings.rs`:

1. Define `CURRENT_SETTINGS_VERSION: u32 = 1`.

2. Define `UserSettings` struct with fields matching CFG-01..07 categories:
   - `version: u32`
   - `theme: String` (default "variant-b")
   - `font_family: String` (default "JetBrains Mono")
   - `font_size: f32` (default 14.0)
   - `font_line_height: f32` (default 1.5)
   - `cursor_style: String` (default "block") — "block" | "bar" | "underline"
   - `opacity: f32` (default 1.0) — 0.5–1.0
   - `high_contrast: bool` (default false)
   - `default_shell: Option<String>` (default None = use $SHELL)
   - `scrollback_size: u32` (default 10_000)
   - `cursor_blink: bool` (default true)
   - `bell: String` (default "visual") — "visual" | "audible" | "none"
   - `default_preset: Option<String>` (default None)
   - `border_visible: bool` (default true)
   - `focus_follows_mouse: bool` (default false)
   - `keymap_profile: String` (default "vscode") — NOTE: A7 already persists this in settings.json via keymap.rs; A9 adds it to the typed struct so the UI can read/write it through the unified settings API; keymap.rs load/save remains the authority for the profile value during A7's hot-reload cycle
   - `telemetry_crash_reports: bool` (default false, D-14/CONCEPT Q9)
   - `telemetry_usage_analytics: bool` (default false, D-14/CONCEPT Q9)
   - `auto_update: bool` (default true, D-16 placeholder — non-functional)

3. All fields get `#[serde(default)]` + `#[serde(rename_all = "camelCase")]`.

4. Define `WorkspaceSettings` — same fields but ALL wrapped in `Option<T>` (workspace only overrides what it sets). Also `#[serde(rename_all = "camelCase")]`.

5. Define `MergedSettings` — same shape as `UserSettings`. Built by `merge_settings(user: &UserSettings, workspace: &WorkspaceSettings) -> MergedSettings` using shallow key merge (D-07): for each field, if workspace `Option` is `Some`, use it; else use user value.

6. Define `SettingsError` enum matching `LayoutError` pattern: `Io`, `Parse`, `NotFound`.

7. Implement:
   - `pub fn settings_path() -> PathBuf` — resolves `~/.config/voss-app/settings.json`
   - `pub fn workspace_settings_path(workspace: &Path) -> PathBuf` — `workspace/.voss/settings.json`
   - `pub fn load_user_settings() -> UserSettings` — read file, parse, default on error (D-08)
   - `pub fn load_workspace_settings(workspace: &Path) -> Option<WorkspaceSettings>` — None if missing
   - `pub fn save_user_settings(settings: &UserSettings) -> Result<(), SettingsError>` — atomic write
   - `pub fn save_workspace_settings(workspace: &Path, settings: &WorkspaceSettings) -> Result<(), SettingsError>` — lazy `.voss/` mkdir (CONCEPT Q7)
   - `pub fn merge_settings(user: &UserSettings, workspace: &WorkspaceSettings) -> MergedSettings`
   - `pub fn overridable_keys() -> &'static [&'static str]` — returns list of keys that are workspace-overridable (D-06): appearance/terminal/layout fields. NOT keybindings/telemetry/updates.
</action>

<acceptance_criteria>
- `cargo test -p voss-app-core -- settings` passes with tests for: load defaults on missing file, load defaults on corrupt JSON, save + reload roundtrip, workspace merge overrides user, workspace None fields fall through, version field preserved
- `cargo build -p voss-app-core` exits 0
- `grep -c 'serde(default)' crates/voss-app-core/src/settings.rs` >= 15 (one per field)
- `grep 'rename_all.*camelCase' crates/voss-app-core/src/settings.rs` finds matches for both `UserSettings` and `WorkspaceSettings`
</acceptance_criteria>

### Task 2: Add Tauri commands + register in app

<read_first>
- crates/voss-app-core/src/settings.rs (just created)
- crates/voss-app-core/src/lib.rs (module registration + pub use pattern)
- apps/voss-app/src-tauri/src/lib.rs (command registration — cross-crate pattern from A2-05)
- crates/voss-app-core/src/keymap.rs (A7 Tauri command pattern for settings-adjacent IO)
</read_first>

<action>
1. Add to `settings.rs`:
   - `#[tauri::command] pub async fn get_merged_settings(workspace_path: Option<String>) -> Result<serde_json::Value, String>` — loads user + optional workspace, merges, returns as JSON Value
   - `#[tauri::command] pub async fn get_user_settings() -> Result<serde_json::Value, String>`
   - `#[tauri::command] pub async fn get_workspace_settings(workspace_path: String) -> Result<serde_json::Value, String>`
   - `#[tauri::command] pub async fn update_user_setting(key: String, value: serde_json::Value) -> Result<(), String>` — loads, updates single key, saves
   - `#[tauri::command] pub async fn update_workspace_setting(workspace_path: String, key: String, value: serde_json::Value) -> Result<(), String>`
   - `#[tauri::command] pub async fn reset_workspace_setting(workspace_path: String, key: String) -> Result<(), String>` — removes key from workspace settings
   - `#[tauri::command] pub async fn open_settings_json(file_path: String, app: tauri::AppHandle) -> Result<(), String>` — uses `tauri::api::shell::open` (or `opener::open` depending on Tauri 2 API) to open in OS default editor

2. Update `crates/voss-app-core/src/lib.rs`:
   - Add `pub mod settings;`
   - Add `pub use settings::{...}` for types and commands

3. Update `apps/voss-app/src-tauri/src/lib.rs`:
   - Add app-level `#[tauri::command]` wrappers delegating to `voss_app_core::settings::*` (same cross-crate pattern as A2-05 PTY, A4-03 layouts, A7-03 keymap)
   - Register all settings commands in `tauri::generate_handler![]`
</action>

<acceptance_criteria>
- `cargo build -p voss-app-core` exits 0
- `cargo build --manifest-path apps/voss-app/src-tauri/Cargo.toml` exits 0
- `grep 'get_merged_settings\|update_user_setting\|open_settings_json' apps/voss-app/src-tauri/src/lib.rs` finds all three commands registered
- `cargo test -p voss-app-core -- settings` passes (existing tests from Task 1 unbroken)
</acceptance_criteria>

### Task 3: Frontend invoke wrappers (`settingsStorage.ts`)

<read_first>
- apps/voss-app/src/command-palette/keymapStorage.ts (pattern for Tauri invoke wrappers)
- apps/voss-app/src/grid/layoutStorage.ts (pattern for typed invoke wrappers)
</read_first>

<action>
Create `apps/voss-app/src/settings/settingsStorage.ts`:

1. TypeScript types mirroring Rust structs:
   - `MergedSettings` — all fields required (matches `UserSettings` shape)
   - `WorkspaceSettingsOverrides` — all fields optional (matches `WorkspaceSettings`)

2. Tauri invoke wrappers:
   - `getMergedSettings(workspacePath?: string): Promise<MergedSettings>`
   - `getUserSettings(): Promise<MergedSettings>`
   - `getWorkspaceSettings(workspacePath: string): Promise<WorkspaceSettingsOverrides | null>`
   - `updateUserSetting(key: string, value: unknown): Promise<void>`
   - `updateWorkspaceSetting(workspacePath: string, key: string, value: unknown): Promise<void>`
   - `resetWorkspaceSetting(workspacePath: string, key: string): Promise<void>`
   - `openSettingsJson(filePath: string): Promise<void>`
   - `OVERRIDABLE_KEYS: readonly string[]` — static list matching Rust `overridable_keys()`

3. Error constants: `SETTINGS_LOAD_FAILED`, `SETTINGS_SAVE_FAILED`.
</action>

<acceptance_criteria>
- `npx tsc --noEmit` exits 0 (apps/voss-app)
- `grep 'invoke(' apps/voss-app/src/settings/settingsStorage.ts | wc -l` >= 7 (one per command)
- File exports `MergedSettings`, `WorkspaceSettingsOverrides`, `getMergedSettings`, `updateUserSetting`, `openSettingsJson`, `OVERRIDABLE_KEYS`
</acceptance_criteria>
