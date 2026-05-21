//! A8 appearance settings persistence in `settings.json` (`appearance` section).
//!
//! Follows `themes.rs` / `profiles.rs` flatten pattern — unknown keys preserved.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppearanceSettings {
    #[serde(default = "default_font_family")]
    pub font_family: String,
    #[serde(default = "default_font_size")]
    pub font_size: u32,
    #[serde(default = "default_line_height")]
    pub line_height: f32,
    #[serde(default)]
    pub letter_spacing: f32,
    #[serde(default)]
    pub ligatures: bool,
    #[serde(default = "default_cursor_shape")]
    pub cursor_shape: CursorShape,
    #[serde(default = "default_cursor_blink")]
    pub cursor_blink: CursorBlink,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor_color: Option<String>,
    #[serde(default = "default_bell_behavior")]
    pub bell_behavior: BellBehavior,
    #[serde(default)]
    pub high_contrast_enabled: bool,
    #[serde(default)]
    pub reduced_motion_enabled: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CursorShape {
    Block,
    Bar,
    Underline,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CursorBlink {
    Off,
    Slow,
    Fast,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum BellBehavior {
    Visual,
    Audible,
    #[serde(rename = "none")]
    None,
    Badge,
}

fn default_font_family() -> String {
    "JetBrains Mono".into()
}

fn default_font_size() -> u32 {
    13
}

fn default_line_height() -> f32 {
    1.5
}

fn default_cursor_shape() -> CursorShape {
    CursorShape::Block
}

fn default_cursor_blink() -> CursorBlink {
    CursorBlink::Fast
}

fn default_bell_behavior() -> BellBehavior {
    BellBehavior::Visual
}

impl Default for AppearanceSettings {
    fn default() -> Self {
        Self {
            font_family: default_font_family(),
            font_size: default_font_size(),
            line_height: default_line_height(),
            letter_spacing: 0.0,
            ligatures: false,
            cursor_shape: default_cursor_shape(),
            cursor_blink: default_cursor_blink(),
            cursor_color: None,
            bell_behavior: default_bell_behavior(),
            high_contrast_enabled: false,
            reduced_motion_enabled: false,
        }
    }
}

#[derive(Debug, thiserror::Error)]
pub enum AppearanceError {
    #[error("could not save appearance settings")]
    SaveFailed,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SettingsRoot {
    #[serde(default)]
    appearance: AppearanceSection,
    #[serde(flatten)]
    rest: serde_json::Map<String, serde_json::Value>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppearanceSection {
    #[serde(flatten)]
    fields: serde_json::Map<String, serde_json::Value>,
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

/// Load appearance settings. Missing/corrupt file → defaults.
pub fn load_appearance_settings() -> AppearanceSettings {
    let path = settings_path();
    let raw = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(_) => return AppearanceSettings::default(),
    };
    let root: SettingsRoot = match serde_json::from_str(&raw) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("[voss-app] appearance settings parse failed, using defaults: {e}");
            return AppearanceSettings::default();
        }
    };

    if root.appearance.fields.is_empty() {
        return AppearanceSettings::default();
    }

    let value = serde_json::Value::Object(root.appearance.fields);
    match serde_json::from_value::<AppearanceSettings>(value) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] appearance settings invalid, using defaults: {e}");
            AppearanceSettings::default()
        }
    }
}

/// Persist appearance settings, preserving unknown `settings.json` keys.
pub fn save_appearance_settings(settings: &AppearanceSettings) -> Result<(), AppearanceError> {
    let path = settings_path();
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| {
            eprintln!("[voss-app] appearance settings mkdir failed: {e}");
            AppearanceError::SaveFailed
        })?;
    }

    let mut root: SettingsRoot = std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();

    let value = serde_json::to_value(settings).map_err(|e| {
        eprintln!("[voss-app] appearance settings serialize failed: {e}");
        AppearanceError::SaveFailed
    })?;
    if let serde_json::Value::Object(patch) = value {
        for (key, val) in patch {
            root.appearance.fields.insert(key, val);
        }
    }

    let json = serde_json::to_string_pretty(&root).map_err(|e| {
        eprintln!("[voss-app] settings serialize failed: {e}");
        AppearanceError::SaveFailed
    })?;
    std::fs::write(&path, json).map_err(|e| {
        eprintln!("[voss-app] appearance settings write failed: {e}");
        AppearanceError::SaveFailed
    })?;
    Ok(())
}

#[cfg(test)]
thread_local! {
    static TEST_SETTINGS_PATH: std::cell::RefCell<Option<PathBuf>> =
        const { std::cell::RefCell::new(None) };
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn isolate_settings() -> tempfile::TempDir {
        let dir = tempdir().unwrap();
        TEST_SETTINGS_PATH.with(|p| {
            *p.borrow_mut() = Some(dir.path().join("settings.json"));
        });
        dir
    }

    #[test]
    fn load_returns_defaults_when_missing() {
        let _dir = isolate_settings();
        assert_eq!(load_appearance_settings(), AppearanceSettings::default());
    }

    #[test]
    fn save_and_load_round_trip_preserves_unknown_keys() {
        let _dir = isolate_settings();
        let path = settings_path();
        std::fs::write(
            &path,
            r##"{"theme":{"bg":"#111"},"appearance":{"activeThemeId":"nord"}}"##,
        )
        .unwrap();

        let mut settings = AppearanceSettings::default();
        settings.font_size = 14;
        settings.high_contrast_enabled = true;
        save_appearance_settings(&settings).unwrap();

        let raw = std::fs::read_to_string(&path).unwrap();
        let value: serde_json::Value = serde_json::from_str(&raw).unwrap();
        assert_eq!(value["theme"]["bg"], "#111");
        assert_eq!(value["appearance"]["activeThemeId"], "nord");
        assert_eq!(value["appearance"]["fontSize"], 14);
        assert_eq!(value["appearance"]["highContrastEnabled"], true);

        let loaded = load_appearance_settings();
        assert_eq!(loaded.font_size, 14);
        assert!(loaded.high_contrast_enabled);
    }
}
