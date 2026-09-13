---
phase: A1-voss-app-tauri-shell
plan: 02
type: execute
wave: 2
depends_on: ["A1-01"]
files_modified:
  - apps/voss-app/src/styles/variant-b.css
  - apps/voss-app/src/index.css
  - apps/voss-app/src/theme/applyTheme.ts
  - apps/voss-app/src/index.tsx
  - apps/voss-app/src-tauri/src/lib.rs
autonomous: false
requirements: [SHL-02]
must_haves:
  truths:
    - "Webview :root computed styles expose the full Variant B token set (--bg-0..3, --fg-0..3, --border, --focus, accents) with sketch-001 hex values verbatim"
    - "Tailwind utilities bg-bg-0 / text-fg-0 / border-border resolve to the Variant B CSS vars"
    - "With no settings.json present, the app renders pure Variant B (no error, no crash)"
    - "Placing ~/.config/voss-app/settings.json with a theme object changes the corresponding :root vars after relaunch"
    - "get_theme_overrides returns an empty map (not an error) for absent OR malformed settings.json"
  artifacts:
    - path: "apps/voss-app/src/styles/variant-b.css"
      provides: "Variant B token definitions — single source of truth"
      contains: "#0a0b0e"
    - path: "apps/voss-app/src/index.css"
      provides: "Tailwind v4 @theme inline mapping + global base styles"
      contains: "@theme inline"
    - path: "apps/voss-app/src/theme/applyTheme.ts"
      provides: "Reusable CSS-var applicator (consumed again by A8)"
      exports: ["applyThemeOverrides"]
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "get_theme_overrides Tauri command + builder registration"
      contains: "get_theme_overrides"
  key_links:
    - from: "apps/voss-app/src/index.css"
      to: "apps/voss-app/src/styles/variant-b.css"
      via: "@import + @theme inline var() references"
      pattern: "@import.*variant-b"
    - from: "apps/voss-app/src/index.tsx"
      to: "get_theme_overrides (Rust)"
      via: "invoke() before first render"
      pattern: "invoke.*get_theme_overrides"
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "~/.config/voss-app/settings.json"
      via: "dirs::home_dir().join('.config') (NOT config_dir)"
      pattern: "home_dir.*\\.config"
---

<objective>
Implement the locked Variant B token system (D-01, D-02) and the Rust→webview theme-override seam (D-08, D-09). Define every Variant B CSS custom property verbatim from sketch 001, map them into Tailwind v4 via `@theme inline`, add the `get_theme_overrides` Tauri command that reads `~/.config/voss-app/settings.json`, and apply any overrides to `:root` before first paint.

Purpose: SHL-02 (Solid+Tailwind scaffold with Variant B tokens). The token system is the shared aesthetic foundation every later A-phase consumes — A2-A9 must never re-define it. The settings seam is the clean A1→A8 boundary (full settings system lands in A8 on top of this read seam).

Output: Variant B token CSS, Tailwind utility generation, a 30-LOC Rust settings-read command, runtime theme-swap-via-config-file capability.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md
@.planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md
@.planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md
@.planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md
@.planning/phases/A1-voss-app-tauri-shell/A1-01-SUMMARY.md

<interfaces>
<!-- Rust file-read analog from the existing codebase. Source: crates/voss-auth/src/file_store.rs -->

crates/voss-auth/src/file_store.rs establishes the in-repo pattern:
  - fn home() -> PathBuf via dirs::home_dir().unwrap_or_default()
  - std::fs::read + serde_json parse with .ok()? silent-failure chains

CRITICAL divergence (A1-PATTERNS.md "src/lib.rs" section + A1-UI-SPEC.md
"Theme Override System Contract"):
  - Settings path = dirs::home_dir().join(".config").join("voss-app")
    .join("settings.json") — NOT dirs::config_dir() (macOS config_dir()
    returns ~/Library/Application Support — RESEARCH Pitfall 8).
  - get_theme_overrides swallows read/parse errors -> returns HashMap::new()
    (NOT Result::Err) and eprintln!s — UI-SPEC Copywriting Contract requires
    silent fallback to Variant B, no error UI.

From Plan A1-01 (already created): src-tauri/src/lib.rs currently has a
  minimal builder with .plugin(tauri_plugin_os::init()) and NO invoke_handler.
  This plan ADDS the get_theme_overrides command + invoke_handler.
  src/index.tsx currently renders <App/> with NO invoke call. This plan
  ADDS the invoke + index.css import.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Variant B token CSS + Tailwind v4 @theme inline mapping</name>
  <files>apps/voss-app/src/styles/variant-b.css, apps/voss-app/src/index.css, apps/voss-app/src/index.tsx</files>
  <read_first>
    - apps/voss-app/src/index.tsx (the file being modified — current minimal render from Plan A1-01)
    - .planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md ("apps/voss-app/src/styles/variant-b.css", "apps/voss-app/src/index.css", "apps/voss-app/src/index.tsx" sections — exact file bodies)
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Color Token Table", "CSS Variable to Tailwind Mapping Contract", "Typography", "Scrollbar Contract" — token values are authoritative)
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("Pattern 1: Tailwind v4 + CSS Variable Theming", "## Variant B Token Values (from sketch 001)", "Pitfall 5: @theme vs @theme inline")
    - .planning/sketches/001-voss-grid-shell/index.html (token-value source of truth — confirm hex/spacing verbatim)
  </read_first>
  <action>
    Create `apps/voss-app/src/styles/variant-b.css` with the full Variant B token taxonomy on `:root` (D-02 — NOT a minimal palette): background scale `--bg-0:#0a0b0e` `--bg-1:#11131a` `--bg-2:#171a23` `--bg-3:#1f232e`; `--border:#262b38` `--border-bright:#353b4a`; `--focus:#5a7cff` `--focus-glow:rgba(90,124,255,0.18)`; foreground `--fg-0:#e8eaf0` `--fg-1:#aab0c0` `--fg-2:#6a7080` `--fg-3:#444a5a`; accents `--accent-green:#6fd28f` `--accent-amber:#e8b86c` `--accent-red:#e87b7b` `--accent-cyan:#6cc7d4` `--accent-magenta:#c084d4` `--accent-blue:#7aa2ff`; role-semantic `--user-msg:#8ab4ff` `--assistant:#b8c0d0` `--tool:#c084d4` `--reviewer:#e8b86c`; `--font-mono` and `--font-ui` stacks; `--radius-none:0px`; `--titlebar-height:22px`; `--scrollbar-width:8px`. Values MUST be verbatim from A1-UI-SPEC.md Color Token Table / A1-RESEARCH.md Variant B Token Values — no substitutions.

    Create `apps/voss-app/src/index.css`: `@import "tailwindcss";` then `@import "./styles/variant-b.css";` then the `@theme inline { }` block from A1-UI-SPEC.md "CSS Variable to Tailwind Mapping Contract" verbatim (use `@theme inline`, NOT bare `@theme` — RESEARCH Pitfall 5 forbids the double-`var()` chain). Add the global base styles from A1-PATTERNS.md "index.css" section: `box-sizing: border-box` + `border-radius: 0` reset, `html, body` with `background: var(--bg-0)` / `color: var(--fg-0)` / `font-family: var(--font-mono)` / `font-size: 13px` / `line-height: 1.5` / `user-select: none`, and the webkit scrollbar rules (8px width, `--bg-3` thumb with the `border-radius: 4px` scrollbar-thumb exception per A1-UI-SPEC Scrollbar Contract).

    Modify `apps/voss-app/src/index.tsx` to add `import './index.css';` (now that the file exists). Keep the render call. The `invoke` wiring is added in Task 2 — do not add it here.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -F "#0a0b0e" apps/voss-app/src/styles/variant-b.css && grep -F "#e8eaf0" apps/voss-app/src/styles/variant-b.css && grep -F "#5a7cff" apps/voss-app/src/styles/variant-b.css && grep -F "@theme inline" apps/voss-app/src/index.css && grep -Fq '@import "./styles/variant-b.css"' apps/voss-app/src/index.css && grep -Fq "import './index.css'" apps/voss-app/src/index.tsx && ! grep -E '@theme[^i]' apps/voss-app/src/index.css | grep -v 'inline' | grep -q '@theme' ; pnpm -C apps/voss-app build 2>&1 | tail -2</automated>
  </verify>
  <done>
    `variant-b.css` contains the verbatim Variant B hex set; `index.css` imports it and maps tokens via `@theme inline` (no bare `@theme`); `index.tsx` imports `index.css`; `pnpm build` (tsc + vite build) exits 0.
  </done>
</task>

<task type="auto">
  <name>Task 2: get_theme_overrides Rust command + Solid apply-before-render seam</name>
  <files>apps/voss-app/src-tauri/src/lib.rs, apps/voss-app/src/theme/applyTheme.ts, apps/voss-app/src/index.tsx</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs (the file being modified — current minimal builder from Plan A1-01)
    - apps/voss-app/src/index.tsx (the file being modified — render + index.css import from Task 1)
    - /Users/benjaminmarks/Projects/Voss/crates/voss-auth/src/file_store.rs (lines 12-39 — in-repo home_dir + std::fs + serde_json analog)
    - .planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md ("apps/voss-app/src-tauri/src/lib.rs", "apps/voss-app/src/theme/applyTheme.ts", "apps/voss-app/src/index.tsx" sections — exact bodies + the error-swallow divergence note)
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Theme Override System Contract", "Copywriting Contract" error-state row)
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("Pattern 3: Rust Settings Read Command", "Pitfall 6: Theme flash on mount", "Pitfall 8: ~/.config vs ~/Library")
  </read_first>
  <action>
    Modify `apps/voss-app/src-tauri/src/lib.rs` (preserve the `.plugin(tauri_plugin_os::init())` line added in Plan A1-01): add `use std::collections::HashMap; use std::path::PathBuf; use serde::{Deserialize, Serialize};`, a `#[derive(Debug, Deserialize, Serialize, Default)] struct SettingsFile { theme: Option<HashMap<String,String>> }`, a `fn settings_path() -> PathBuf` that returns `dirs::home_dir().unwrap_or_default().join(".config").join("voss-app").join("settings.json")` (MUST use `home_dir().join(".config")`, NOT `dirs::config_dir()` — RESEARCH Pitfall 8 / A1-UI-SPEC Theme Override System Contract), and a `#[tauri::command] fn get_theme_overrides() -> HashMap<String,String>` that: returns `HashMap::new()` if the path does not exist; on read error `eprintln!`s and returns `HashMap::new()`; on parse error `eprintln!`s and returns `HashMap::new()`; otherwise returns `settings.theme.unwrap_or_default()`. The command returns a bare `HashMap` (NOT `Result<_,String>`) so failures are silently swallowed per A1-UI-SPEC Copywriting Contract. Register it: `.invoke_handler(tauri::generate_handler![get_theme_overrides])` on the builder chain.

    Create `apps/voss-app/src/theme/applyTheme.ts` exporting `applyThemeOverrides(overrides: Record<string,string>): void` that iterates entries and calls `document.documentElement.style.setProperty(key, value)` (A1-PATTERNS.md "applyTheme.ts" verbatim — standalone so A8's settings UI reuses it).

    Modify `apps/voss-app/src/index.tsx`: before the `render()` call, `invoke<Record<string,string>>('get_theme_overrides')`, on resolve call `applyThemeOverrides(overrides)`, on reject `console.error` and continue (silent fallback to baked Variant B — A1-UI-SPEC Copywriting Contract), and call `render(() => <App/>, root)` in `.finally()` so overrides apply before first paint (RESEARCH Pitfall 6 — invoke-before-render eliminates the theme flash). Keep the `import './index.css';` from Task 1.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q 'fn get_theme_overrides' apps/voss-app/src-tauri/src/lib.rs && grep -Eq 'home_dir\(\).*join\("\.config"\)|join\("\.config"\)' apps/voss-app/src-tauri/src/lib.rs && ! grep -q 'config_dir()' apps/voss-app/src-tauri/src/lib.rs && grep -q 'generate_handler!\[get_theme_overrides\]' apps/voss-app/src-tauri/src/lib.rs && grep -q 'tauri_plugin_os::init()' apps/voss-app/src-tauri/src/lib.rs && grep -q 'export function applyThemeOverrides' apps/voss-app/src/theme/applyTheme.ts && grep -q "invoke" apps/voss-app/src/index.tsx && grep -q 'get_theme_overrides' apps/voss-app/src/index.tsx && cargo check -p voss-app 2>&1 | tail -1 && pnpm -C apps/voss-app build 2>&1 | tail -1</automated>
  </verify>
  <done>
    `lib.rs` has `get_theme_overrides` using `home_dir().join(".config")` (no `config_dir()`), returning a bare `HashMap` (silent fallback), registered via `generate_handler!`, with the os plugin preserved; `applyTheme.ts` exports `applyThemeOverrides`; `index.tsx` invokes the command and applies overrides before render; `cargo check -p voss-app` and `pnpm build` exit 0.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify Variant B tokens render + config-file theme swap</name>
  <files>(none — verification-only checkpoint; uses a throwaway ~/.config/voss-app/settings.json that is deleted at the end, no repo files modified)</files>
  <read_first>
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Color Token Table", "Theme Override System Contract", "Typography" HiDPI note)
    - .planning/phases/A1-voss-app-tauri-shell/A1-VALIDATION.md ("Manual-Only Verifications" table)
  </read_first>
  <action>Pause for the human to run `pnpm tauri dev` and exercise three theme paths described in &lt;how-to-verify&gt;: (1) absent settings.json → pure Variant B, (2) valid theme override → colors swap without rebuild, (3) malformed JSON → silent fallback. No code is written; this checkpoint validates Task 1 + Task 2 behavior and the T-A1-01 malformed-input mitigation.</action>
  <verify>Human types "approved" after confirming pure Variant B with no settings, color swap on valid override without rebuild, and silent fallback on malformed JSON (console-only, no error UI, no crash).</verify>
  <done>All three theme paths confirmed by the human; throwaway settings.json removed; explicit approval recorded.</done>
  <what-built>
    The full Variant B token system on `:root`, Tailwind v4 utilities generated from those tokens, and the Rust→webview theme-override seam. With no settings file the app is pure Variant B; with `~/.config/voss-app/settings.json` containing a `theme` object, the matching `:root` vars change after relaunch (zero rebuild).
  </what-built>
  <how-to-verify>
    1. Ensure no settings file: `rm -f ~/.config/voss-app/settings.json`. Then `cd apps/voss-app && pnpm tauri dev`.
    2. Open the webview DevTools; on `:root` confirm computed `--bg-0` = `#0a0b0e`, `--fg-0` = `#e8eaf0`, `--focus` = `#5a7cff`, `--border` = `#262b38` (spot-check against A1-UI-SPEC Color Token Table). Confirm no console error about settings.
    3. Quit. Create `~/.config/voss-app/settings.json` containing `{"theme":{"--bg-0":"#1a1a2e","--accent-green":"#50fa7b"}}`. Relaunch `pnpm tauri dev`.
    4. Confirm the window background changed to `#1a1a2e` and DevTools `:root --bg-0` now reads `#1a1a2e` — no rebuild was performed.
    5. Quit. Write malformed JSON (e.g. `{bad`) to the settings file. Relaunch. Confirm the app falls back to pure Variant B silently (background back to `#0a0b0e`), only a console `eprintln`/error line, NO visible error UI, NO crash.
    6. `rm -f ~/.config/voss-app/settings.json` to restore the default dev path.
  </how-to-verify>
  <resume-signal>Type "approved" if pure Variant B renders, the config override swaps colors without rebuild, and malformed JSON falls back silently — or describe the deviation.</resume-signal>
  <acceptance_criteria>
    - Absent settings.json -> pure Variant B, no console error, no crash
    - settings.json `theme` override changes the corresponding `:root` vars after relaunch with no rebuild
    - Malformed settings.json -> silent fallback to Variant B (console-only log, no error UI, no crash) — confirms T-A1-01 mitigation
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `~/.config/voss-app/settings.json` → Rust | Untrusted/possibly-malformed user file crosses into the process |
| Rust IPC → webview | `get_theme_overrides` result crosses to the webview and is written to CSS vars |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A1-01 | Tampering | settings.json parse in `get_theme_overrides` | mitigate | Strict `serde` deserialize into `SettingsFile` (only an optional `theme` map is read; all other keys ignored). Malformed/absent/unreadable → `eprintln!` + `HashMap::new()`, never panic, never error UI (A1-UI-SPEC Copywriting Contract). Verified by Task 3 malformed-JSON step |
| T-A1-02 | Tampering | Theme value → CSS injection | mitigate | Override values are written only via `element.style.setProperty(--token, value)`. The CSS parser sanitizes/rejects invalid declarations; there is no `eval`, no `innerHTML`, no shell-out path. Only `--*` custom-property keys are applied |
| T-A1-03 | Information Disclosure / Path Traversal | settings path resolution | mitigate | Path is fixed: `home_dir().join(".config").join("voss-app").join("settings.json")`. No user-controlled path segment; settings keys never participate in the filesystem path, so crafted keys cannot traverse |
| T-A1-04 | Elevation of Privilege | Tauri command surface | mitigate | Only `get_theme_overrides` is exposed (read-only, no args, no fs-write). `capabilities/default.json` (from Plan A1-01) exposes no fs/shell/exec capability — minimal command surface |
</threat_model>

<verification>
- `variant-b.css` contains verbatim Variant B hex values (`#0a0b0e`, `#e8eaf0`, `#5a7cff`).
- `index.css` uses `@theme inline` (no bare `@theme` double-`var()` chain).
- `lib.rs` `get_theme_overrides` uses `home_dir().join(".config")`, not `config_dir()`; returns bare `HashMap`; registered via `generate_handler!`; os plugin preserved.
- `cargo check -p voss-app` + `pnpm -C apps/voss-app build` exit 0.
- Human checkpoint: pure Variant B with no settings; config override swaps colors without rebuild; malformed JSON falls back silently.
</verification>

<success_criteria>
- Full Variant B token taxonomy on `:root` with sketch-001 values verbatim (SHL-02, D-02).
- Tailwind utilities generated from the tokens via `@theme inline` (D-01).
- `get_theme_overrides` command reads `~/.config/voss-app/settings.json`, silent-falls-back to Variant B on absent/malformed (D-08, D-09).
- Overrides applied to `:root` before first paint (no theme flash).
</success_criteria>

<output>
Create `.planning/phases/A1-voss-app-tauri-shell/A1-02-SUMMARY.md` when done.
</output>
