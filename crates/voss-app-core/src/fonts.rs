//! System monospace font enumeration (A8 D-13).
//!
//! Returns a sorted, deduplicated list of font family names with
//! **JetBrains Mono** always present as the guaranteed fallback.

use std::collections::BTreeSet;
use std::path::Path;

const GUARANTEED_FONT: &str = "JetBrains Mono";

const COMMON_MONO: &[&str] = &[
    "JetBrains Mono",
    "SF Mono",
    "Menlo",
    "Monaco",
    "Courier New",
    "Consolas",
    "Lucida Console",
    "Ubuntu Mono",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Source Code Pro",
    "Fira Code",
    "Cascadia Mono",
    "Cascadia Code",
    "IBM Plex Mono",
    "Inconsolata",
    "Roboto Mono",
    "PT Mono",
    "Andale Mono",
    "Courier",
];

/// List monospace-capable system fonts. Always includes [`GUARANTEED_FONT`].
pub fn list_system_fonts() -> Vec<String> {
    let mut names = BTreeSet::new();
    names.insert(GUARANTEED_FONT.to_string());

    for name in COMMON_MONO {
        names.insert((*name).to_string());
    }

    for dir in font_scan_dirs() {
        scan_font_dir(&dir, &mut names);
    }

    let mut fonts: Vec<String> = names.into_iter().collect();
    if let Some(pos) = fonts.iter().position(|f| f == GUARANTEED_FONT) {
        if pos != 0 {
            fonts.remove(pos);
            fonts.insert(0, GUARANTEED_FONT.to_string());
        }
    }
    fonts
}

fn font_scan_dirs() -> Vec<std::path::PathBuf> {
    let mut dirs = Vec::new();

    if let Some(home) = dirs::home_dir() {
        dirs.push(home.join("Library/Fonts"));
        dirs.push(home.join(".local/share/fonts"));
        dirs.push(home.join(".fonts"));
    }

    #[cfg(target_os = "macos")]
    {
        dirs.push(Path::new("/System/Library/Fonts").to_path_buf());
        dirs.push(Path::new("/Library/Fonts").to_path_buf());
    }

    #[cfg(target_os = "linux")]
    {
        dirs.push(Path::new("/usr/share/fonts").to_path_buf());
        dirs.push(Path::new("/usr/local/share/fonts").to_path_buf());
    }

    #[cfg(target_os = "windows")]
    {
        if let Some(windir) = std::env::var_os("WINDIR") {
            dirs.push(Path::new(&windir).join("Fonts"));
        }
    }

    dirs
}

fn scan_font_dir(dir: &Path, out: &mut BTreeSet<String>) {
    if !dir.is_dir() {
        return;
    }
    let read = match std::fs::read_dir(dir) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("[voss-app] font scan skipped {}: {e}", dir.display());
            return;
        }
    };

    for entry in read.flatten() {
        let path = entry.path();
        if path.is_dir() {
            scan_font_dir(&path, out);
            continue;
        }
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        if !matches!(ext.as_str(), "ttf" | "otf" | "ttc" | "otc") {
            continue;
        }
        if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
            let family = stem.split('-').next().unwrap_or(stem).trim();
            if !family.is_empty() {
                out.insert(family.to_string());
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn list_system_fonts_always_includes_jetbrains_mono() {
        let fonts = list_system_fonts();
        assert!(fonts.iter().any(|f| f == GUARANTEED_FONT));
        assert_eq!(fonts[0], GUARANTEED_FONT);
    }

    #[test]
    fn list_system_fonts_is_unique_with_guaranteed_first() {
        let fonts = list_system_fonts();
        assert_eq!(fonts[0], GUARANTEED_FONT);
        let mut deduped = fonts.clone();
        deduped.sort();
        deduped.dedup();
        assert_eq!(fonts.len(), deduped.len());
    }
}
