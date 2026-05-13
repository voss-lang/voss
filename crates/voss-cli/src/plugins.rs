use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Default)]
pub struct PluginManifest {
    pub id: String,
    pub name: String,
    pub description: String,
    pub enabled: bool,
    pub commands: Vec<String>,
    pub skills: Vec<String>,
    pub agents: Vec<String>,
    pub source: PathBuf,
    pub warnings: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct RawPlugin {
    id: Option<String>,
    name: Option<String>,
    description: Option<String>,
    enabled: Option<bool>,
    #[serde(default)]
    commands: Vec<String>,
    #[serde(default)]
    skills: Vec<String>,
    #[serde(default)]
    agents: Vec<String>,
}

#[derive(Default, Serialize, Deserialize)]
struct EnablementFile {
    #[serde(default)]
    plugins: BTreeMap<String, EnablementEntry>,
}

#[derive(Default, Serialize, Deserialize)]
struct EnablementEntry {
    enabled: bool,
}

pub fn user_plugin_dir() -> PathBuf {
    let base = std::env::var("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| dirs::home_dir().unwrap_or_default().join(".config"));
    base.join("voss").join("plugins")
}

pub fn project_plugin_dir(cwd: &Path) -> PathBuf {
    cwd.join(".voss").join("plugins")
}

pub fn enablement_path() -> PathBuf {
    let base = std::env::var("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| dirs::home_dir().unwrap_or_default().join(".config"));
    base.join("voss").join("plugins.toml")
}

fn load_enablement() -> BTreeMap<String, bool> {
    let path = enablement_path();
    let Ok(text) = std::fs::read_to_string(path) else {
        return BTreeMap::new();
    };
    let Ok(file) = toml::from_str::<EnablementFile>(&text) else {
        return BTreeMap::new();
    };
    file.plugins
        .into_iter()
        .map(|(k, v)| (k, v.enabled))
        .collect()
}

pub fn set_plugin_enabled(plugin_id: &str, enabled: bool) -> anyhow::Result<PathBuf> {
    let path = enablement_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut file = std::fs::read_to_string(&path)
        .ok()
        .and_then(|text| toml::from_str::<EnablementFile>(&text).ok())
        .unwrap_or_default();
    file.plugins
        .insert(plugin_id.to_string(), EnablementEntry { enabled });
    let text = toml::to_string_pretty(&file)?;
    std::fs::write(&path, text)?;
    Ok(path)
}

pub fn load_plugins(
    cwd: &Path,
    command_ids: &[&str],
    skill_ids: &[&str],
    agent_ids: &[&str],
) -> Vec<PluginManifest> {
    let command_ids: BTreeSet<&str> = command_ids.iter().copied().collect();
    let skill_ids: BTreeSet<&str> = skill_ids.iter().copied().collect();
    let agent_ids: BTreeSet<&str> = agent_ids.iter().copied().collect();
    let overrides = load_enablement();
    let mut manifests = Vec::new();
    for root in [project_plugin_dir(cwd), user_plugin_dir()] {
        let Ok(entries) = std::fs::read_dir(root) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|x| x.to_str()) != Some("toml") {
                continue;
            }
            let Ok(text) = std::fs::read_to_string(&path) else {
                continue;
            };
            let Ok(raw) = toml::from_str::<RawPlugin>(&text) else {
                continue;
            };
            let Some(id) = raw.id.filter(|s| !s.trim().is_empty()) else {
                continue;
            };
            let mut warnings = Vec::new();
            let commands = raw
                .commands
                .into_iter()
                .filter(|name| {
                    if command_ids.contains(name.as_str()) {
                        true
                    } else {
                        warnings.push(format!("unknown command: {name}"));
                        false
                    }
                })
                .collect();
            let skills = raw
                .skills
                .into_iter()
                .filter(|name| {
                    if skill_ids.contains(name.as_str()) {
                        true
                    } else {
                        warnings.push(format!("unknown skill: {name}"));
                        false
                    }
                })
                .collect();
            let agents = raw
                .agents
                .into_iter()
                .filter(|name| {
                    if agent_ids.contains(name.as_str()) {
                        true
                    } else {
                        warnings.push(format!("unknown agent: {name}"));
                        false
                    }
                })
                .collect();
            manifests.push(PluginManifest {
                enabled: overrides.get(&id).copied().unwrap_or(raw.enabled.unwrap_or(false)),
                name: raw.name.unwrap_or_else(|| id.clone()),
                description: raw.description.unwrap_or_default(),
                id,
                commands,
                skills,
                agents,
                source: path,
                warnings,
            });
        }
    }
    manifests
}
