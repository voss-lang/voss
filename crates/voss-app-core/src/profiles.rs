//! A8 settings profile persistence — full snapshots at
//! `~/.config/voss-app/profiles/<name>.json` and active profile id in
//! `settings.json`.
//!
//! Follows `keymap.rs` (settings flatten) and `session.rs` (atomic writes,
//! fail-safe loads).

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

pub const CURRENT_PROFILE_VERSION: u32 = 1;

/// Full settings snapshot (appearance, terminal, layout defaults, etc.).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfileFile {
    pub version: u32,
    #[serde(flatten)]
    pub settings: serde_json::Map<String, serde_json::Value>,
}

#[derive(Debug, thiserror::Error)]
pub enum ProfileError {
    #[error("profile name cannot contain /, \\ or ..")]
    InvalidName,
    #[error("could not save profile")]
    SaveFailed,
    #[error("could not save profile settings")]
    SettingsSaveFailed,
}

// --- Settings (active profile id) --------------------------------------------

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SettingsProfiles {
    #[serde(default)]
    appearance: AppearanceSection,
    #[serde(flatten)]
    rest: serde_json::Map<String, serde_json::Value>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppearanceSection {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    active_profile_id: Option<String>,
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

#[cfg(not(test))]
fn profiles_dir() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("profiles")
}

#[cfg(test)]
fn profiles_dir() -> PathBuf {
    TEST_PROFILES_DIR.with(|p| {
        p.borrow()
            .clone()
            .expect("tests must set TEST_PROFILES_DIR")
    })
}

// --- Path helpers ------------------------------------------------------------

pub fn profile_path(name: &str) -> Result<PathBuf, ProfileError> {
    validate_profile_name(name)?;
    Ok(profiles_dir().join(format!("{name}.json")))
}

pub fn validate_profile_name(name: &str) -> Result<(), ProfileError> {
    if name.is_empty() {
        return Err(ProfileError::InvalidName);
    }
    if name.contains('/') || name.contains('\\') || name.contains("..") || name.contains(':') {
        return Err(ProfileError::InvalidName);
    }
    if name.starts_with('.') {
        return Err(ProfileError::InvalidName);
    }
    if name.ends_with(".json") {
        return Err(ProfileError::InvalidName);
    }
    if name.chars().any(|c| c.is_control()) {
        return Err(ProfileError::InvalidName);
    }
    Ok(())
}

// --- Profile I/O -------------------------------------------------------------

/// List profile names (stems of `*.json`). Missing directory → empty list.
pub fn list_profiles() -> Vec<String> {
    let dir = profiles_dir();
    if !dir.exists() {
        return Vec::new();
    }
    let read = match std::fs::read_dir(&dir) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("[voss-app] profile list failed: {e}");
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

/// Load `profiles/<name>.json`. Returns `None` for missing, corrupt, or
/// unsupported files.
pub fn load_profile(name: &str) -> Option<ProfileFile> {
    let path = profile_path(name).ok()?;
    if !path.exists() {
        return None;
    }
    let raw = std::fs::read_to_string(&path).ok()?;
    match parse_profile(&raw) {
        Ok(p) => Some(p),
        Err(reason) => {
            eprintln!("[voss-app] profile ignored ({name}): {reason}");
            None
        }
    }
}

/// Save a profile snapshot, creating `profiles/` on first write.
pub fn save_profile(name: &str, profile: &ProfileFile) -> Result<(), ProfileError> {
    let path = profile_path(name)?;
    let json = serde_json::to_string_pretty(profile).map_err(|e| {
        eprintln!("[voss-app] profile serialize failed: {e}");
        ProfileError::SaveFailed
    })?;
    atomic_write(&path, &json)
}

// --- Active profile id in settings.json --------------------------------------

/// Load `appearance.activeProfileId`. Missing/corrupt → `None`.
pub fn load_active_profile_id() -> Option<String> {
    let path = settings_path();
    let raw = std::fs::read_to_string(&path).ok()?;
    let settings: SettingsProfiles = serde_json::from_str(&raw).ok()?;
    settings.appearance.active_profile_id
}

/// Persist `appearance.activeProfileId`, preserving unknown settings keys.
pub fn save_active_profile_id(id: Option<&str>) -> Result<(), ProfileError> {
    let path = settings_path();
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| {
            eprintln!("[voss-app] settings mkdir failed: {e}");
            ProfileError::SettingsSaveFailed
        })?;
    }
    let mut settings: SettingsProfiles = std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();
    settings.appearance.active_profile_id = id.map(str::to_string);
    let json = serde_json::to_string_pretty(&settings).map_err(|e| {
        eprintln!("[voss-app] settings serialize failed: {e}");
        ProfileError::SettingsSaveFailed
    })?;
    std::fs::write(&path, json).map_err(|e| {
        eprintln!("[voss-app] settings write failed: {e}");
        ProfileError::SettingsSaveFailed
    })?;
    Ok(())
}

// --- Internal helpers --------------------------------------------------------

fn parse_profile(raw: &str) -> Result<ProfileFile, &'static str> {
    let value: serde_json::Value = serde_json::from_str(raw).map_err(|_| "invalid JSON")?;
    let version = value.get("version").and_then(|v| v.as_u64());
    match version {
        Some(v) if v == CURRENT_PROFILE_VERSION as u64 => {
            serde_json::from_value(value).map_err(|_| "invalid profile file")
        }
        Some(_) => Err("unsupported version"),
        None => Err("missing version"),
    }
}

fn atomic_write(path: &Path, json: &str) -> Result<(), ProfileError> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| {
            eprintln!("[voss-app] profile mkdir failed: {e}");
            ProfileError::SaveFailed
        })?;
    }
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, json).map_err(|e| {
        eprintln!("[voss-app] profile write tmp failed: {e}");
        ProfileError::SaveFailed
    })?;
    std::fs::rename(&tmp, path).map_err(|e| {
        eprintln!("[voss-app] profile rename failed: {e}");
        ProfileError::SaveFailed
    })?;
    Ok(())
}

// --- Tests -------------------------------------------------------------------

#[cfg(test)]
thread_local! {
    static TEST_SETTINGS_PATH: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
    static TEST_PROFILES_DIR: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn sample_profile() -> ProfileFile {
        ProfileFile {
            version: CURRENT_PROFILE_VERSION,
            settings: serde_json::Map::from_iter([(
                "appearance".into(),
                serde_json::json!({"themeId": "variant-b"}),
            )]),
        }
    }

    fn isolate() -> tempfile::TempDir {
        let dir = tempdir().unwrap();
        TEST_SETTINGS_PATH.with(|p| {
            *p.borrow_mut() = Some(dir.path().join("settings.json"));
        });
        TEST_PROFILES_DIR.with(|p| {
            *p.borrow_mut() = Some(dir.path().join("profiles"));
        });
        dir
    }

    #[test]
    fn profile_round_trips() {
        let _d = isolate();
        let profile = sample_profile();
        save_profile("work", &profile).unwrap();
        assert_eq!(load_profile("work"), Some(profile));
    }

    #[test]
    fn load_missing_profile_returns_none() {
        let _d = isolate();
        assert!(load_profile("missing").is_none());
    }

    #[test]
    fn corrupt_profile_returns_none() {
        let _d = isolate();
        let dir = profiles_dir();
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("bad.json"), "not json").unwrap();
        assert!(load_profile("bad").is_none());
    }

    #[test]
    fn active_profile_id_round_trips() {
        let _d = isolate();
        save_active_profile_id(Some("work")).unwrap();
        assert_eq!(load_active_profile_id().as_deref(), Some("work"));
    }

    #[test]
    fn save_active_profile_preserves_unknown_settings() {
        let _d = isolate();
        let path = settings_path();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(
            &path,
            r##"{"theme":{"bg":"#111"},"appearance":{"activeThemeId":"nord"}}"##,
        )
        .unwrap();

        save_active_profile_id(Some("personal")).unwrap();

        let raw = std::fs::read_to_string(&path).unwrap();
        assert!(raw.contains("\"theme\""));
        assert!(raw.contains("\"activeThemeId\":\"nord\""));
        assert!(raw.contains("\"activeProfileId\":\"personal\""));
    }

    #[test]
    fn invalid_profile_name_rejected() {
        let _d = isolate();
        assert!(save_profile("..", &sample_profile()).is_err());
    }
}
