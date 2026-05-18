---
phase: A1-voss-app-tauri-shell
plan: 02
subsystem: ui
tags: [tauri, solid, tailwind, theme, css-vars, ipc, settings]

requires:
  - phase: A1-01
    provides: Tauri+Solid+Tailwind scaffold; src-tauri/src/lib.rs minimal builder with tauri_plugin_os::init(); src/index.tsx with placeholder render; src/App.tsx with inline #0a0b0e placeholder
provides:
  - Full Variant B token taxonomy on :root in apps/voss-app/src/styles/variant-b.css (verbatim from sketch 001 / A1-UI-SPEC.md Color Token Table)
  - Tailwind v4 @theme inline mapping in apps/voss-app/src/index.css (generates bg-bg-0 / text-fg-0 / border-border / text-accent-* / font-mono utilities)
  - Global base styles + scrollbar contract in index.css (8px webkit scrollbar with --bg-3 thumb at 4px radius — sole carve-out from 0-radius rule)
  - get_theme_overrides Tauri command in src-tauri/src/lib.rs — reads ~/.config/voss-app/settings.json via dirs::home_dir().join(".config"), returns bare HashMap (silent fallback on absent / unreadable / malformed)
  - applyTheme.ts utility exporting applyThemeOverrides(overrides) — standalone for A8 settings UI reuse
  - index.tsx invoke seam — invoke('get_theme_overrides') before render, applyThemeOverrides on resolve, console.error on reject, render() in .finally() so overrides apply before first paint (RESEARCH Pitfall 6 eliminated)
affects: [A1-03, A1-04, A2, A3, A4, A8]

tech-stack:
  added: []
  patterns:
    - "Single source of truth: :root CSS vars defined once in variant-b.css, mapped to Tailwind via @theme inline (NOT bare @theme — RESEARCH Pitfall 5)."
    - "Rust file read for user config: dirs::home_dir().join('.config').join('voss-app') — NOT dirs::config_dir() (which on macOS resolves to ~/Library/Application Support; RESEARCH Pitfall 8)."
    - "Silent-fallback contract: get_theme_overrides returns bare HashMap (not Result<_, String>) so absent / unreadable / malformed all collapse to HashMap::new() + an eprintln stderr line. T-A1-01 mitigation."
    - "Theme apply runs BEFORE render via Promise.finally() so no flash on boot (RESEARCH Pitfall 6)."

key-files:
  created:
    - apps/voss-app/src/styles/variant-b.css
    - apps/voss-app/src/index.css
    - apps/voss-app/src/theme/applyTheme.ts
  modified:
    - apps/voss-app/src/index.tsx (added invoke + applyThemeOverrides + finally(render); kept ./index.css import)
    - apps/voss-app/src-tauri/src/lib.rs (added SettingsFile struct + settings_path() + #[tauri::command] get_theme_overrides + .invoke_handler registration; preserved .plugin(tauri_plugin_os::init()) from Plan 01)
    - apps/voss-app/src/App.tsx (1-line plan-defect patch: background literal '#0a0b0e' -> 'var(--bg-0)' so the token system actually drives the paint surface; Plan 02 frontmatter listed App.tsx as untouched, but UI-SPEC Empty Body Contract requires var(--bg-0) -- without this fix, settings override changed :root --bg-0 but the full-viewport div ignored it and visual verification of Path 2 failed)

key-decisions:
  - Plan 02 frontmatter omitted apps/voss-app/src/App.tsx from files_modified but UI-SPEC Empty Body Contract requires `background: var(--bg-0)`. Caught during Task 3 visual verification (Path 2 settings override produced no visual change because App.tsx had the literal hex from Plan 01's minimal placeholder). 1-line surgical fix applied in flight; documented here as a plan-defect note for the GSD audit trail. Plan A1-03 (titlebar) doesn't touch App.tsx either, so the fix logically belongs in A1-02.
  - get_theme_overrides returns HashMap directly, NOT Result<HashMap, String> — UI-SPEC Copywriting Contract requires silent fallback to Variant B. Error UI is forbidden in A1.
  - settings_path() comment intentionally avoids the literal string `config_dir()` so the verify guard `! grep -q 'config_dir()' lib.rs` stays clean while still documenting the macOS / Linux divergence.
  - Theme apply happens BEFORE render() (Promise.finally) — eliminates the boot flash described in RESEARCH Pitfall 6.

patterns-established:
  - "Token consumer pattern: components (later panes, titlebar) reach colors via var(--bg-0) / Tailwind utilities. Never raw hex (sole exceptions: macOS traffic-light circles in A1-03)."
  - "Settings file shape: { theme: { '--token': 'value', ... } } — top-level theme object only, all other keys ignored by serde."

requirements-completed: [SHL-02]

duration: ~40min (including in-flight icon padding fix + plan-defect App.tsx patch + 3-path human verification)
completed: 2026-05-18
---

# Phase A1, Plan 02: Variant B Tokens + Theme Override Seam Summary

**Implemented the locked Variant B token taxonomy on `:root`, mapped it into Tailwind v4 via `@theme inline`, and shipped the Rust→webview `get_theme_overrides` command with absent/malformed silent fallback verified end-to-end.**

## Performance

- **Tasks:** 3 (Tasks 1+2 auto; Task 3 blocking human-verify, 3 paths)
- **Files created:** 3 (variant-b.css, index.css, applyTheme.ts)
- **Files modified:** 3 (index.tsx, lib.rs, App.tsx [plan defect])
- **Wave:** 2

## Accomplishments

- Variant B token system live: 4 bg + 4 fg + 2 border + focus pair + 6 accent + 4 role-semantic CSS vars on `:root`, all values verbatim from sketch 001 / A1-UI-SPEC Color Token Table.
- Tailwind v4 utilities auto-generated from tokens via `@theme inline` (`bg-bg-0`, `text-fg-0`, `border-border`, `text-accent-*`, `font-mono`).
- `get_theme_overrides` Tauri command reads `~/.config/voss-app/settings.json` and returns the `theme` map (or empty HashMap on absent/malformed) — never a `Result::Err`, never a panic.
- `invoke()` runs before `render()` so overrides apply before first paint (no boot flash).
- All 3 theme paths verified visually + in console.

## Verify Output (Task 1 + 2 acceptance, Task 3 human verification)

### Grep + build (Tasks 1+2 automated)
```
=== variant-b.css hex ===
  --bg-0: #0a0b0e;
  --fg-0: #e8eaf0;
  --focus:      #5a7cff;
=== @theme inline ===
@theme inline {  (present in index.css, no bare @theme)
=== index.tsx ===
import './index.css' OK
invoke OK
get_theme_overrides OK
=== lib.rs ===
fn get_theme_overrides OK
home_dir().join('.config') OK
no config_dir() OK
generate_handler![get_theme_overrides] OK
tauri_plugin_os::init() preserved OK
=== applyTheme.ts ===
export function applyThemeOverrides OK
=== cargo check -p voss-app ===
Finished `dev` profile [unoptimized + debuginfo] target(s) in 7m 14s (incremental from A1-01)
=== pnpm build ===
dist/index.html                  0.39 kB
dist/assets/index-Duk9ysOu.css   6.53 kB
dist/assets/index-DxUJJmjM.js   13.13 kB
✓ built in 4.20s
```

### Task 3 human-verify (3 theme paths)
**Path 1 — absent settings.json:**
- Window bg = `#0a0b0e` pure Variant B
- No console error
- DevTools selected element: `<div style="height:100vh;width:100vw;background:var(--bg-0)">` (after App.tsx fix)

**Path 2 — valid override `{"theme":{"--bg-0":"#1a1a2e","--accent-green":"#50fa7b"}}`:**
- Window bg = `#1a1a2e` purple-black (visibly distinct from `#0a0b0e`)
- No source rebuild — same binary, JSON file is only diff
- Confirms runtime theme swap path

**Path 3 — malformed JSON `{bad`:**
- Window bg = `#0a0b0e` (silent fallback to Variant B)
- Terminal stderr printed exactly: `[voss-app] failed to parse settings: key must be a string at line 1 column 2`
- No error dialog, no crash, no red in webview console
- Confirms T-A1-01 mitigation (Tampering on settings.json)

## In-Flight Issues Caught

1. **App.tsx plan-defect**: A1-02 frontmatter listed only 5 files_modified; App.tsx was not among them. But UI-SPEC Empty Body Contract requires `background: var(--bg-0)`, and Plan 01 had landed a placeholder `background: '#0a0b0e'` literal. Without patching App.tsx, the override seam was invisible visually (Path 2 looked identical to Path 1 — :root --bg-0 swapped but the literal hex on the paint surface ignored it). 1-line in-flight fix applied. Future GSD plan-checker should catch "var(--*) on the body paint surface" as a required link in the A1-02 verify chain.
2. **Icon padding fix (A1-01 followup, not A1-02 work)**: After first launch, user flagged the Dock icon as "way bigger/fatter" than peers. Apple Big Sur icon grid requires ~10% safe-area inset on a 1024 canvas (content area ~824). Source PNG was full-bleed. Repadded via Pillow (`820×820` content centered on `1024×1024` transparent canvas, 102px offsets) and re-ran `pnpm tauri icon`. Tauri rebuilt the binary on next launch with the new `icon.icns`.

## Deferred (per plan scope)

- 22px titlebar + macOS traffic lights + preset switcher + platform gate via tauri-plugin-os — Plan A1-03.
- `pnpm tauri build` smoke + restrictive CSP on `app.security.csp` — Plan A1-04.
- Full settings system (typed loader, font/shell/keymap/theme UI) — A8 (reuses applyThemeOverrides + the same settings.json path).
