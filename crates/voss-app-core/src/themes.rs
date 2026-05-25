//! A8 custom theme persistence — workspace `.voss/themes/<name>.json` and
//! active theme id in `settings.json`.
//!
//! Bundled themes live in the frontend repo; this module handles user-authored
//! custom themes only. Follows `keymap.rs` (settings flatten) and `session.rs`
//! (atomic tmp+rename writes, fail-safe loads).

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

pub const CURRENT_THEME_VERSION: u32 = 1;

/// On-disk custom theme schema (aligns with TS `CustomTheme` concept).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CustomThemeFile {
    pub version: u32,
    pub id: String,
    pub name: String,
    pub appearance: ThemeAppearance,
    pub css_vars: HashMap<String, String>,
    pub ansi: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub selection: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor_text: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ThemeAppearance {
    Dark,
    Light,
}

#[derive(Debug, thiserror::Error)]
pub enum ThemeError {
    #[error("theme name cannot contain /, \\ or ..")]
    InvalidName,
    #[error("could not save theme")]
    SaveFailed,
    #[error("could not save theme settings")]
    SettingsSaveFailed,
}

// --- Settings (active theme id) ----------------------------------------------

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SettingsThemes {
    #[serde(default)]
    appearance: AppearanceSection,
    #[serde(flatten)]
    rest: serde_json::Map<String, serde_json::Value>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppearanceSection {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    active_theme_id: Option<String>,
    #[serde(flatten)]
    rest: serde_json::Map<String, serde_json::Value>,
}

#[cfg(not(test))]
fn settings_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("settings.json")
}

#[cfg(test)]
fn settings_path() -> PathBuf {
    TEST_SETTINGS_PATH.with(|p| {
        p.borrow()
            .clone()
            .expect("tests must set TEST_SETTINGS_PATH")
    })
}

// --- Path helpers ------------------------------------------------------------

pub fn custom_theme_path(workspace: &Path, name: &str) -> Result<PathBuf, ThemeError> {
    validate_theme_name(name)?;
    Ok(workspace
        .join(".voss")
        .join("themes")
        .join(format!("{name}.json")))
}

pub fn validate_theme_name(name: &str) -> Result<(), ThemeError> {
    if name.is_empty() {
        return Err(ThemeError::InvalidName);
    }
    if name.contains('/') || name.contains('\\') || name.contains("..") || name.contains(':') {
        return Err(ThemeError::InvalidName);
    }
    if name.starts_with('.') {
        return Err(ThemeError::InvalidName);
    }
    if name.ends_with(".json") {
        return Err(ThemeError::InvalidName);
    }
    if name.chars().any(|c| c.is_control()) {
        return Err(ThemeError::InvalidName);
    }
    Ok(())
}

// --- Custom theme I/O --------------------------------------------------------

/// List custom theme names (stems of `*.json`) under `.voss/themes/`.
/// Missing directory → empty list. Never creates `.voss/`.
pub fn list_custom_themes(workspace: &Path) -> Vec<String> {
    let dir = workspace.join(".voss").join("themes");
    if !dir.exists() {
        return Vec::new();
    }
    let read = match std::fs::read_dir(&dir) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("[voss-app] custom theme list failed: {e}");
            return Vec::new();
        }
    };
    let mut names = Vec::new();
    for entry in read.flatten() {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
            names.push(stem.to_string());
        }
    }
    names.sort();
    names
}

/// Load `.voss/themes/<name>.json`. Returns `None` for missing, corrupt, or
/// unsupported files. Never creates directories.
pub fn load_custom_theme(workspace: &Path, name: &str) -> Option<CustomThemeFile> {
    let path = custom_theme_path(workspace, name).ok()?;
    if !path.exists() {
        return None;
    }
    let raw = std::fs::read_to_string(&path).ok()?;
    match parse_custom_theme(&raw) {
        Ok(t) => Some(t),
        Err(reason) => {
            eprintln!("[voss-app] custom theme ignored ({name}): {reason}");
            None
        }
    }
}

/// Save a custom theme to `.voss/themes/<name>.json` (lazy `.voss/` creation).
pub fn save_custom_theme(
    workspace: &Path,
    name: &str,
    theme: &CustomThemeFile,
) -> Result<(), ThemeError> {
    let path = custom_theme_path(workspace, name)?;
    let json = serde_json::to_string_pretty(theme).map_err(|e| {
        eprintln!("[voss-app] custom theme serialize failed: {e}");
        ThemeError::SaveFailed
    })?;
    atomic_write(&path, &json)
}

// --- Active theme id in settings.json ----------------------------------------

/// Load `appearance.activeThemeId` from settings. Missing/corrupt → `None`.
pub fn load_active_theme_id() -> Option<String> {
    let path = settings_path();
    let raw = std::fs::read_to_string(&path).ok()?;
    let settings: SettingsThemes = serde_json::from_str(&raw).ok()?;
    settings.appearance.active_theme_id
}

/// Persist `appearance.activeThemeId`, preserving unknown settings keys.
pub fn save_active_theme_id(id: Option<&str>) -> Result<(), ThemeError> {
    let path = settings_path();
    let mut settings: SettingsThemes = std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();
    settings.appearance.active_theme_id = id.map(str::to_string);
    let json = serde_json::to_string_pretty(&settings).map_err(|e| {
        eprintln!("[voss-app] settings serialize failed: {e}");
        ThemeError::SettingsSaveFailed
    })?;
    settings_atomic_write(&path, &json)
}

// --- Internal helpers --------------------------------------------------------

fn parse_custom_theme(raw: &str) -> Result<CustomThemeFile, &'static str> {
    let value: serde_json::Value = serde_json::from_str(raw).map_err(|_| "invalid JSON")?;
    let version = value.get("version").and_then(|v| v.as_u64());
    match version {
        Some(v) if v == CURRENT_THEME_VERSION as u64 => {
            let theme: CustomThemeFile =
                serde_json::from_value(value).map_err(|_| "invalid theme file")?;
            if theme.ansi.len() != 16 {
                return Err("ansi must contain 16 colors");
            }
            if theme.id.is_empty() || theme.name.is_empty() {
                return Err("missing id or name");
            }
            Ok(theme)
        }
        Some(_) => Err("unsupported version"),
        None => Err("missing version"),
    }
}

fn atomic_write(path: &Path, json: &str) -> Result<(), ThemeError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| {
            eprintln!("[voss-app] custom theme mkdir failed: {e}");
            ThemeError::SaveFailed
        })?;
    }
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, json).map_err(|e| {
        eprintln!("[voss-app] custom theme write tmp failed: {e}");
        ThemeError::SaveFailed
    })?;
    std::fs::rename(&tmp, path).map_err(|e| {
        eprintln!("[voss-app] custom theme rename failed: {e}");
        ThemeError::SaveFailed
    })?;
    Ok(())
}

fn settings_atomic_write(path: &Path, json: &str) -> Result<(), ThemeError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| {
            eprintln!("[voss-app] settings mkdir failed: {e}");
            ThemeError::SettingsSaveFailed
        })?;
    }
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, json).map_err(|e| {
        eprintln!("[voss-app] settings write tmp failed: {e}");
        ThemeError::SettingsSaveFailed
    })?;
    std::fs::rename(&tmp, path).map_err(|e| {
        eprintln!("[voss-app] settings rename failed: {e}");
        ThemeError::SettingsSaveFailed
    })?;
    Ok(())
}

// --- Tests -------------------------------------------------------------------

#[cfg(test)]
thread_local! {
    static TEST_SETTINGS_PATH: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn sample_theme() -> CustomThemeFile {
        CustomThemeFile {
            version: CURRENT_THEME_VERSION,
            id: "my-theme".into(),
            name: "My Theme".into(),
            appearance: ThemeAppearance::Dark,
            css_vars: HashMap::from([("--bg-0".into(), "#000000".into())]),
            ansi: (0..16).map(|i| format!("#{:06x}", i)).collect(),
            selection: None,
            cursor: None,
            cursor_text: None,
        }
    }

    fn isolate_settings() -> tempfile::TempDir {
        let dir = tempdir().unwrap();
        let path = dir.path().join("settings.json");
        TEST_SETTINGS_PATH.with(|p| {
            *p.borrow_mut() = Some(path);
        });
        dir
    }

    #[test]
    fn custom_theme_round_trips() {
        let dir = tempdir().unwrap();
        let theme = sample_theme();
        save_custom_theme(dir.path(), "my-theme", &theme).unwrap();
        let loaded = load_custom_theme(dir.path(), "my-theme").unwrap();
        assert_eq!(loaded, theme);
    }

    #[test]
    fn load_missing_theme_returns_none() {
        let dir = tempdir().unwrap();
        assert!(load_custom_theme(dir.path(), "nope").is_none());
        assert!(!dir.path().join(".voss").exists());
    }

    #[test]
    fn list_missing_dir_returns_empty() {
        let dir = tempdir().unwrap();
        assert!(list_custom_themes(dir.path()).is_empty());
    }

    #[test]
    fn corrupt_theme_returns_none() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss").join("themes");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(path.join("bad.json"), "not json").unwrap();
        assert!(load_custom_theme(dir.path(), "bad").is_none());
    }

    #[test]
    fn unsupported_theme_version_returns_none() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss").join("themes");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(
            path.join("old.json"),
            r#"{"version":999,"id":"x","name":"X","appearance":"dark","cssVars":{},"ansi":[]}"#,
        )
        .unwrap();
        assert!(load_custom_theme(dir.path(), "old").is_none());
    }

    #[test]
    fn active_theme_id_round_trips() {
        let _s = isolate_settings();
        save_active_theme_id(Some("variant-b")).unwrap();
        assert_eq!(load_active_theme_id().as_deref(), Some("variant-b"));
        save_active_theme_id(None).unwrap();
        assert!(load_active_theme_id().is_none());
    }

    #[test]
    fn save_active_theme_preserves_other_settings() {
        let _s = isolate_settings();
        let path = settings_path();
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir).unwrap();
        }
        std::fs::write(
            &path,
            r##"{"keymap":{"profile":"tmux"},"appearance":{"highContrastEnabled":true}}"##,
        )
        .unwrap();

        save_active_theme_id(Some("dracula")).unwrap();

        let raw = std::fs::read_to_string(&path).unwrap();
        let value: serde_json::Value = serde_json::from_str(&raw).unwrap();
        assert_eq!(value["keymap"]["profile"], "tmux");
        assert_eq!(value["appearance"]["highContrastEnabled"], true);
        assert_eq!(value["appearance"]["activeThemeId"], "dracula");
    }

    #[test]
    fn save_custom_theme_creates_voss_on_write_only() {
        let dir = tempdir().unwrap();
        assert!(!dir.path().join(".voss").exists());
        save_custom_theme(dir.path(), "t", &sample_theme()).unwrap();
        assert!(dir
            .path()
            .join(".voss")
            .join("themes")
            .join("t.json")
            .exists());
    }

    #[test]
    fn invalid_theme_name_rejected() {
        let dir = tempdir().unwrap();
        assert!(save_custom_theme(dir.path(), "../x", &sample_theme()).is_err());
    }
}
