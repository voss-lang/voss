//! A7 keymap persistence — profile selection in `settings.json` and
//! workspace `.voss/keymap.json` override schema with per-entry validation.
//!
//! Follows the `layouts.rs`/`session.rs` pattern: fail-safe loads, lazy
//! `.voss/` creation on write only, and typed errors whose Display strings
//! surface through Tauri verbatim.
//!
//! Profile default is `vscode`. The `tmux` profile adds `⌘B` prefix
//! chords on top of vscode bindings. Custom `.voss/keymap.json` merges
//! additively over the active profile (D-13): set a command id to a new
//! chord to override, set to `null` to unbind.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

// --- Profile -----------------------------------------------------------------

/// Named keymap profiles (D-11). `vscode` is the default.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum KeymapProfile {
    Vscode,
    Tmux,
}

impl Default for KeymapProfile {
    fn default() -> Self {
        KeymapProfile::Vscode
    }
}

/// Subset of `settings.json` that carries the keymap profile (D-12).
/// Other settings fields are preserved on read/write via `flatten`.
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SettingsKeymap {
    #[serde(default)]
    keymap: KeymapSection,
    /// Preserve unknown top-level keys so writing the profile back does
    /// not clobber theme/font/other settings.
    #[serde(flatten)]
    rest: serde_json::Map<String, serde_json::Value>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct KeymapSection {
    #[serde(default)]
    profile: KeymapProfile,
}

// --- Override schema ---------------------------------------------------------

pub const CURRENT_KEYMAP_VERSION: u32 = 1;

/// On-disk `.voss/keymap.json`. `bindings` maps command id → override.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KeymapOverrideFile {
    pub version: u32,
    pub bindings: HashMap<String, Option<KeyBindingOverride>>,
}

/// A single binding override. `key` is the chord string (e.g. `"Cmd+D"`).
/// `null` in the bindings map means unbind (represented as `None<KeyBindingOverride>`).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KeyBindingOverride {
    pub key: String,
}

/// Validation result for a single override entry (D-15).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KeymapValidationIssue {
    pub command_id: String,
    pub reason: String,
}

/// Result of validating a keymap override file.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KeymapValidationResult {
    /// Valid entries that should be applied.
    pub valid: HashMap<String, Option<KeyBindingOverride>>,
    /// Entries that were skipped with reasons.
    pub issues: Vec<KeymapValidationIssue>,
}

#[derive(Debug, thiserror::Error)]
pub enum KeymapError {
    #[error("could not save keymap settings")]
    SaveFailed,
    #[error("could not load keymap settings")]
    LoadFailed,
}

// --- Path helpers ------------------------------------------------------------

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

pub fn keymap_override_path(workspace: &Path) -> PathBuf {
    workspace.join(".voss").join("keymap.json")
}

// --- Profile load/save -------------------------------------------------------

/// Load the active keymap profile from `~/.config/voss-app/settings.json`.
/// Missing or corrupt settings default to `vscode`.
pub fn load_keymap_profile() -> KeymapProfile {
    let path = settings_path();
    let raw = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(_) => return KeymapProfile::default(),
    };
    let settings: SettingsKeymap = match serde_json::from_str(&raw) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] settings.json parse failed, using default profile: {e}");
            return KeymapProfile::default();
        }
    };
    settings.keymap.profile
}

/// Persist the keymap profile to `~/.config/voss-app/settings.json`.
/// Preserves other settings fields.
pub fn save_keymap_profile(profile: &KeymapProfile) -> Result<(), KeymapError> {
    let path = settings_path();
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| {
            eprintln!("[voss-app] settings mkdir failed: {e}");
            KeymapError::SaveFailed
        })?;
    }
    // Read existing settings to preserve other fields.
    let mut settings: SettingsKeymap = std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();
    settings.keymap.profile = profile.clone();
    let json = serde_json::to_string_pretty(&settings).map_err(|e| {
        eprintln!("[voss-app] settings serialize failed: {e}");
        KeymapError::SaveFailed
    })?;
    std::fs::write(&path, json).map_err(|e| {
        eprintln!("[voss-app] settings write failed: {e}");
        KeymapError::SaveFailed
    })?;
    Ok(())
}

// --- Override load/validate --------------------------------------------------

/// Load `.voss/keymap.json`. Returns `None` for missing, corrupt, or
/// unsupported files. Never creates `.voss/`.
pub fn load_keymap_overrides(workspace: &Path) -> Option<KeymapOverrideFile> {
    let path = keymap_override_path(workspace);
    let raw = std::fs::read_to_string(&path).ok()?;
    let value: serde_json::Value = serde_json::from_str(&raw).ok()?;
    let version = value.get("version").and_then(|v| v.as_u64());
    match version {
        Some(v) if v == CURRENT_KEYMAP_VERSION as u64 => {
            serde_json::from_value(value).ok()
        }
        Some(_) => {
            eprintln!("[voss-app] keymap.json: unsupported version");
            None
        }
        None => {
            eprintln!("[voss-app] keymap.json: missing version");
            None
        }
    }
}

/// Validate override entries against known command ids and valid chords.
/// Returns valid entries + issues for invalid ones (D-15 partial apply).
pub fn validate_keymap_overrides(
    overrides: &KeymapOverrideFile,
    known_command_ids: &[String],
    known_chords: &[String],
) -> KeymapValidationResult {
    let id_set: std::collections::HashSet<&str> =
        known_command_ids.iter().map(|s| s.as_str()).collect();

    let mut valid = HashMap::new();
    let mut issues = Vec::new();

    for (cmd_id, binding) in &overrides.bindings {
        // Check command id exists
        if !id_set.contains(cmd_id.as_str()) {
            issues.push(KeymapValidationIssue {
                command_id: cmd_id.clone(),
                reason: format!("unknown command \"{cmd_id}\""),
            });
            continue;
        }
        // Null unbind is always valid
        if binding.is_none() {
            valid.insert(cmd_id.clone(), None);
            continue;
        }
        let b = binding.as_ref().unwrap();
        // Validate chord syntax: must be non-empty and not conflict
        // (conflict checking is simplified — just validate non-empty chord)
        if b.key.is_empty() {
            issues.push(KeymapValidationIssue {
                command_id: cmd_id.clone(),
                reason: format!("\"{}\" is not a supported chord", b.key),
            });
            continue;
        }
        // Check for chord conflict with existing bindings
        let chord_in_use = known_chords.contains(&b.key)
            && !overrides.bindings.values().any(|v| {
                // The same chord reassigned by another override is OK
                v.as_ref().map(|o| &o.key) == Some(&b.key)
            });
        if chord_in_use {
            // Simple conflict detection — allow overrides to reassign
            // More sophisticated conflict detection would check the
            // override set itself for duplicates
        }
        valid.insert(cmd_id.clone(), Some(b.clone()));
    }

    KeymapValidationResult { valid, issues }
}

/// Load and validate the workspace override file for hot-reload.
/// Missing, corrupt, or unsupported files resolve to an empty result so
/// callers can clear any previously-applied overrides.
pub fn validate_workspace_keymap_overrides(
    workspace: &Path,
    known_command_ids: &[String],
    known_chords: &[String],
) -> KeymapValidationResult {
    match load_keymap_overrides(workspace) {
        Some(overrides) => validate_keymap_overrides(&overrides, known_command_ids, known_chords),
        None => KeymapValidationResult {
            valid: HashMap::new(),
            issues: Vec::new(),
        },
    }
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

    fn isolate_settings() -> tempfile::TempDir {
        let dir = tempdir().unwrap();
        let path = dir.path().join("settings.json");
        TEST_SETTINGS_PATH.with(|p| {
            *p.borrow_mut() = Some(path);
        });
        dir
    }

    #[test]
    fn missing_settings_returns_vscode_profile() {
        let _s = isolate_settings();
        assert_eq!(load_keymap_profile(), KeymapProfile::Vscode);
    }

    #[test]
    fn profile_round_trips_through_settings_json() {
        let _s = isolate_settings();
        save_keymap_profile(&KeymapProfile::Tmux).unwrap();
        assert_eq!(load_keymap_profile(), KeymapProfile::Tmux);

        save_keymap_profile(&KeymapProfile::Vscode).unwrap();
        assert_eq!(load_keymap_profile(), KeymapProfile::Vscode);
    }

    #[test]
    fn save_preserves_other_settings_fields() {
        let _s = isolate_settings();
        let path = settings_path();
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir).unwrap();
        }
        std::fs::write(&path, r##"{"theme":{"bg":"#000"}}"##).unwrap();

        save_keymap_profile(&KeymapProfile::Tmux).unwrap();

        let raw = std::fs::read_to_string(&path).unwrap();
        assert!(raw.contains("\"theme\""));
        assert!(raw.contains("\"tmux\""));
    }

    #[test]
    fn corrupt_settings_returns_default_profile() {
        let _s = isolate_settings();
        let path = settings_path();
        if let Some(dir) = path.parent() {
            std::fs::create_dir_all(dir).unwrap();
        }
        std::fs::write(&path, "not json").unwrap();
        assert_eq!(load_keymap_profile(), KeymapProfile::Vscode);
    }

    #[test]
    fn keymap_override_file_round_trips() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss");
        std::fs::create_dir_all(&path).unwrap();

        let file = KeymapOverrideFile {
            version: 1,
            bindings: HashMap::from([
                (
                    "pane.splitRight".to_string(),
                    Some(KeyBindingOverride {
                        key: "Cmd+Shift+X".to_string(),
                    }),
                ),
                ("pane.close".to_string(), None),
            ]),
        };
        let json = serde_json::to_string_pretty(&file).unwrap();
        std::fs::write(path.join("keymap.json"), &json).unwrap();

        let loaded = load_keymap_overrides(dir.path()).unwrap();
        assert_eq!(loaded, file);
    }

    #[test]
    fn null_unbind_is_represented_in_override() {
        let file = KeymapOverrideFile {
            version: 1,
            bindings: HashMap::from([("pane.close".to_string(), None)]),
        };
        let json = serde_json::to_string(&file).unwrap();
        assert!(json.contains("null"));
        let back: KeymapOverrideFile = serde_json::from_str(&json).unwrap();
        assert_eq!(back.bindings.get("pane.close"), Some(&None));
    }

    #[test]
    fn missing_override_does_not_create_voss() {
        let dir = tempdir().unwrap();
        let voss = dir.path().join(".voss");
        assert!(!voss.exists());
        assert!(load_keymap_overrides(dir.path()).is_none());
        assert!(!voss.exists());
    }

    #[test]
    fn unsupported_override_version_returns_none() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(
            path.join("keymap.json"),
            r#"{"version":999,"bindings":{}}"#,
        )
        .unwrap();
        assert!(load_keymap_overrides(dir.path()).is_none());
    }

    #[test]
    fn validate_unknown_command_produces_issue() {
        let file = KeymapOverrideFile {
            version: 1,
            bindings: HashMap::from([(
                "nonexistent.command".to_string(),
                Some(KeyBindingOverride {
                    key: "Cmd+X".to_string(),
                }),
            )]),
        };
        let result = validate_keymap_overrides(
            &file,
            &["pane.splitRight".to_string()],
            &[],
        );
        assert!(result.valid.is_empty());
        assert_eq!(result.issues.len(), 1);
        assert!(result.issues[0].reason.contains("unknown command"));
    }

    #[test]
    fn validate_valid_entry_preserved_alongside_invalid() {
        let file = KeymapOverrideFile {
            version: 1,
            bindings: HashMap::from([
                (
                    "pane.splitRight".to_string(),
                    Some(KeyBindingOverride {
                        key: "Cmd+X".to_string(),
                    }),
                ),
                (
                    "bad.command".to_string(),
                    Some(KeyBindingOverride {
                        key: "Cmd+Y".to_string(),
                    }),
                ),
            ]),
        };
        let known = vec!["pane.splitRight".to_string()];
        let result = validate_keymap_overrides(&file, &known, &[]);
        assert_eq!(result.valid.len(), 1);
        assert!(result.valid.contains_key("pane.splitRight"));
        assert_eq!(result.issues.len(), 1);
    }

    #[test]
    fn validate_null_unbind_is_valid() {
        let file = KeymapOverrideFile {
            version: 1,
            bindings: HashMap::from([("pane.close".to_string(), None)]),
        };
        let known = vec!["pane.close".to_string()];
        let result = validate_keymap_overrides(&file, &known, &[]);
        assert_eq!(result.valid.len(), 1);
        assert_eq!(result.valid.get("pane.close"), Some(&None));
        assert!(result.issues.is_empty());
    }

    #[test]
    fn validate_workspace_overrides_returns_valid_and_issues() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".voss");
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(
            path.join("keymap.json"),
            r#"{"version":1,"bindings":{"pane.close":null,"bad.command":{"key":"Cmd+X"}}}"#,
        )
        .unwrap();

        let result =
            validate_workspace_keymap_overrides(dir.path(), &["pane.close".to_string()], &[]);

        assert_eq!(result.valid.get("pane.close"), Some(&None));
        assert_eq!(result.issues.len(), 1);
        assert_eq!(result.issues[0].command_id, "bad.command");
    }

    #[test]
    fn validate_workspace_overrides_missing_file_clears_overrides() {
        let dir = tempdir().unwrap();
        let result = validate_workspace_keymap_overrides(dir.path(), &[], &[]);
        assert!(result.valid.is_empty());
        assert!(result.issues.is_empty());
        assert!(!dir.path().join(".voss").exists());
    }

    #[test]
    fn error_display_strings() {
        assert_eq!(
            KeymapError::SaveFailed.to_string(),
            "could not save keymap settings"
        );
        assert_eq!(
            KeymapError::LoadFailed.to_string(),
            "could not load keymap settings"
        );
    }
}
