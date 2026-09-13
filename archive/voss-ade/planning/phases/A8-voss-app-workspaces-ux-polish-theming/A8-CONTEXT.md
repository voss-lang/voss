# Phase A8: voss-app Workspaces, UX Polish, & Theming - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

A8 transforms voss-app from a functional terminal into a daily-driver app by delivering: multi-project **workspace tabs** (Warp-style named/colored tabs with isolated pane trees), a **theme engine** (12 bundled curated themes + custom theme support), **appearance polish** (native vibrancy, CSS transitions, font picker), **accessibility foundations** (high-contrast override layer, `prefers-reduced-motion` global kill switch, minimum font floor, configurable bell), **named setting profiles** (full-settings snapshots for quick context switching), and **platform-native window chrome** (macOS/Windows/Linux each polished).

A8 builds on: A1 (Variant B token system + Rust IO seam), A3 (binary-split tree + never-destroy-panes), A4 (layout presets + save/load), A5 (project open + recents), A6 (session persist), A7 (command registry + palette + toast).

**Out of scope (fenced to other phases):**
- Settings UI (two-pane form surface) — A9 (A8 delivers the engine; A9 delivers the UI to configure it)
- Status bar — A10
- Onboarding wizard — A11
- Editor pane / code highlighting — L4
- Agent pane semantics, cost meter — L2+
- VSCode theme import engine — dropped; curated bundled themes only

</domain>

<decisions>
## Implementation Decisions

Scope (WHAT) is fixed by ROADMAP UXP-01..30. These are HOW decisions from discussion.

### Workspace isolation model
- **D-01:** **All workspaces stay mounted (hidden).** CSS `display: none` / `display: flex` toggle on workspace switch. PTYs keep running in background workspaces. xterm buffers preserved. Instant switch (~0ms). Warp/iTerm2 model. `App.tsx` renders a `<For each={workspaces}>` with per-workspace `<GridRoot>` instances.
- **D-02:** **Workspace state structure = planner's discretion.** Options: each workspace as mini-App instance (own GridStore/project/layout) OR single keyed store. Bounded by D-01 (all mounted, CSS toggle) and existing GridRoot/App.tsx architecture. Planner picks what minimizes GridRoot refactoring.
- **D-03:** **Workspace accent colors = fixed dot palette (Warp-style).** ~8 preset colors (none/neutral, red, orange, green, yellow, cyan, blue, purple) displayed as color dots in tab context menu — matching Warp's UX. Default = auto-derived from project name hash (deterministic, same project always same color). User overrides by clicking a dot. No custom hex picker.
- **D-04:** **`workspaces.json` index + per-workspace session files.** Top-level `~/.config/voss-app/workspaces.json` holds workspace metadata (id, name, projectPath, accentColor, order, activeLayoutPreset). Each project workspace stores pane tree + scrollback in its own `.voss/session.json` (extends A6). Project-less workspaces use `~/.config/voss-app/sessions/<id>.json`. On quit: write all workspace sessions + index. On launch: restore all from index.

### Theme engine
- **D-05:** **12 bundled curated themes, no VSCode import engine.** Ship ROADMAP's 11 (One Dark Pro, Dracula, Catppuccin Mocha, Gruvbox Dark, Tokyo Night, Nord, Monokai Pro, Solarized Dark + Catppuccin Latte, Solarized Light, GitHub Light) plus Variant B as default. Total 12. Hand-curated for quality — no automated VSCode theme parsing.
- **D-06:** **Static JSON theme files in repo.** Each theme = `apps/voss-app/src/themes/<name>.json` with direct CSS var mappings (`--bg-0..3`, `--fg-0..3`, `--border`, `--focus`, accents) + 16 ANSI terminal colors. Build-time bundled. Runtime swap via existing `applyThemeOverrides()` seam in `src/theme/applyTheme.ts`. Hot-swap all panes + chrome in ≤100ms (UXP-14).
- **D-07:** **Custom themes supported.** `.voss/themes/<name>.json` using same schema as bundled themes. Appears in theme picker alongside bundled ones. Power-user escape hatch. Lazy `.voss/` creation on first write (CONCEPT Q7).

### Vibrancy & platform
- **D-08:** **Native vibrancy per platform.** macOS: real `NSVisualEffectView` via Tauri `WindowEffectsConfig` (`UnderWindowBackground` material). Windows: acrylic/mica via Tauri DWM hints. Linux: CSS opacity fallback only (no reliable compositor API). Opacity slider 0.5–1.0 controls webview background alpha. Theme `--bg-0` tokens need `rgba()` support when opacity < 1.0.
- **D-09:** **Full platform polish — all three.** macOS: traffic-light positioning (A1 done) + vibrancy + system light/dark appearance follow + native menu wraps A7 registry (A7 D-04). Windows: acrylic/mica + snap layout support (Win+arrow) + taskbar integration. Linux: `.desktop` file + tray icon + WM_CLASS hints. Equal investment across platforms.
- **D-10:** **OS-native window chrome.** Let each OS handle corner radius and shadow natively. No custom window shape or borderless window hacks. Simplest, most native feel.

### Animation & accessibility
- **D-11:** **CSS transitions only.** 150ms ease for split/close, 200ms for layout preset reflow. Pure CSS `transition` on flex-basis/opacity. No JS animation library. `prefers-reduced-motion` media query disables ALL transitions/animations globally via a single rule (`transition: none !important; animation: none !important`). UXP-22 satisfied.
- **D-12:** **High-contrast = token override layer.** Applied ON TOP of active theme. Forces WCAG AAA contrast ratios (7:1 minimum). Keeps theme hue/character but bumps luminance differences. `--bg-0: #000`, `--fg-0: #fff`, `--focus: #ffff00` (high-vis yellow), dim text bumped. Toggle stored in `settings.json`. Single implementation works across all 12 themes.
- **D-13:** **Font dropdown + live preview.** System monospace font enumeration at runtime (via Tauri/OS font API). Selecting a font previews immediately in all open panes. Size, line-height, letter-spacing sliders. Ligature toggle. JetBrains Mono bundled as guaranteed fallback. Settings persisted to `settings.json`.
- **D-14:** **Profile = full settings snapshot.** Named profiles (e.g., "Work", "Personal", "Presentation") capture ALL settings: appearance (theme, font, opacity, cursor, high-contrast) + terminal (shell, scrollback, bell) + layout defaults. Quick-switch via A7 command palette ("Switch Profile → Work") or workspace tab context menu. Workspace can pin a profile (UXP-27). Stored at `~/.config/voss-app/profiles/<name>.json`.

### Claude's / Planner's Discretion
- Workspace state structure (mini-App vs single keyed store) — bounded by D-01 + existing GridRoot architecture (D-02).
- Workspace tab bar visual design (tab height, font, close-X vs hover-reveal, reorder drag handle) — within Variant B tokens.
- Theme JSON schema exact shape (field names, ANSI color format, metadata fields) — bounded by D-06 (must map to existing CSS vars + 16 ANSI).
- Font enumeration implementation (Tauri plugin vs Rust `font-kit` crate vs platform shell-out) — planner's call.
- Bell behavior configuration UI (visual flash / audible / none / badge-only per UXP-24) — planner picks UX, bounded by per-workspace configurability.
- Cursor customization exact options (block/bar/underline shape, blink rate values per UXP-17) — planner's call, stored in settings.json.
- Pane chrome refinement details (hover states on resize handles, drag affordance per UXP-19) — planner/UI within Variant B tokens.
- Profile schema exact shape — planner designs, bounded by D-14 (captures all settings categories).
- Whether workspace accent color dot picker is inline in tab or in a popover — planner's call per Warp reference.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & cross-A constraints
- `.planning/ROADMAP.md` Phase A8 (~line 1298) — UXP-01..30, proposed success criteria, cross-cutting constraints (tab bar position, A5/A6 extensions, theme engine supersedes A1 Variant B override).

### Product concept (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §10 Q7 — `.voss/` lazy creation (theme write + session write trigger it).
- `apps/voss-app/FEATURES.md` — §L1.3 (layout presets A4 interop), §L1.9 (session persist A6 interop), feature catalog for workspaces/themes/appearance.

### Prior-phase decisions A8 builds on (do not re-litigate)
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-01/D-02 (Variant B CSS-var token system — A8 theme engine layers over it, same `--bg-0..3` / `--fg-0..3` / `--border` / `--focus` var names), D-09 (Rust/Tauri owns persisted IO; `~/.config/voss-app/` path lock for settings/profiles/workspaces.json/sessions/).
- `.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md` — D-04 (never destroy panes — extends to workspace close: confirm if running processes).
- `.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md` — D-07 (layout files at `.voss/layouts/`), D-09 (versioned schema, fail-safe, lazy `.voss/`).
- `.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md` — D-01..D-13 (project state shape, setup window, recents, folder picker). A5's folder-picker becomes "open folder in workspace" in A8.
- `.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md` — D-01..D-12 (session.json per workspace, scrollback on quit, structural auto-save). A6 extends to multi-workspace: per-workspace session files + workspaces.json index (D-04).
- `.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md` — D-01..D-04 (command registry = single source of truth for workspace commands, palette commands like "Switch Profile", "Switch Theme"), D-16 (toast component for theme/font/profile feedback).

### Warp reference (visual inspiration)
- Warp terminal workspace tab bar — color dot palette (none, red, orange, green, yellow, cyan, blue, purple) for workspace accent colors (D-03 reference).

### Source code (A8 substrate)
- `apps/voss-app/src/App.tsx` — current composition root. A8 lifts workspace orchestration here (D-01: `<For each={workspaces}>` with per-workspace GridRoot).
- `apps/voss-app/src/styles/variant-b.css` — CSS var token definitions. Theme engine (D-06) overrides these at runtime via `applyThemeOverrides()`.
- `apps/voss-app/src/theme/applyTheme.ts` — existing `applyThemeOverrides(overrides)` function. Comment already says "Called again by A8 settings UI on runtime theme change." D-06 reuses this seam.
- `apps/voss-app/src/grid/GridRoot.tsx` — per-workspace grid instance. D-01 mounts multiple of these.
- `apps/voss-app/src/grid/sessionPersist.ts` — A6 session auto-save infrastructure. A8 extends to per-workspace sessions.
- `apps/voss-app/src/grid/sessionStorage.ts` — A6 session file read/write. A8 extends path resolution for multi-workspace.
- `apps/voss-app/src-tauri/src/lib.rs` — Tauri command registry + plugin builder. A8 adds vibrancy effects config, font enumeration commands, theme/profile persistence commands, workspace commands.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/voss-app/src/theme/applyTheme.ts` — `applyThemeOverrides()` already iterates CSS vars onto `:root`. Theme switch = load JSON + call this function. ≤100ms hot-swap is achievable.
- `apps/voss-app/src/styles/variant-b.css` — 25 CSS vars already defined. Theme JSON schema maps 1:1 to these vars + adds 16 ANSI terminal colors.
- `apps/voss-app/src/grid/sessionPersist.ts` + `sessionStorage.ts` — A6 session infrastructure. Per-workspace extension = parameterize by workspace ID + project path.
- `apps/voss-app/src/grid/GridRoot.tsx` — self-contained grid component with `controllerRef` API. D-01 mounts multiple instances; each workspace gets its own.
- `apps/voss-app/src/pane/ExitBanner.tsx` / `CloseConfirmBanner.tsx` — Variant B chrome banner precedent. Workspace close-confirm follows same pattern.
- A7 command registry (D-01) — workspace commands ("New Workspace", "Switch Theme", "Switch Profile") register here. A7 toast (D-16) shows theme/profile switch feedback.

### Established Patterns
- **Solid signals = UI SSOT; Rust/Tauri owns persisted IO** (A1 D-09). Workspace metadata, themes, profiles all persisted Rust-side. Frontend reads via Tauri commands.
- **Never destroy panes; app never empty** (A3 D-04). Workspace close confirms if running processes. Last workspace can't be closed (UXP-08).
- **Variant B CSS-var tokens** (A1 D-01/02). Theme engine overrides these vars — same architecture, different values. All existing components automatically retheme.
- **Cross-crate `#[tauri::command]` pattern** (A2-05, A4-03, A5, A6). New A8 commands in `voss-app-core`; thin app wrappers in `apps/voss-app/src-tauri/src/lib.rs`.
- **Atomic write + fail-safe load** (A4 layouts.rs, A6 session.rs). Profile/theme/workspace writes follow same pattern.
- **`.voss/` lazy on first write** (A4 D-09, CONCEPT Q7). `.voss/themes/` created on first custom theme save.

### Integration Points
- New directory `apps/voss-app/src/themes/` — 12 bundled theme JSON files.
- New component `apps/voss-app/src/components/workspace/WorkspaceTabBar.tsx` — tab bar between titlebar and pane area.
- New Rust modules: `crates/voss-app-core/src/themes.rs` (theme loading/listing), `crates/voss-app-core/src/profiles.rs` (profile CRUD), `crates/voss-app-core/src/workspaces.rs` (workspace index persistence), `crates/voss-app-core/src/fonts.rs` (system font enumeration).
- `apps/voss-app/src-tauri/src/lib.rs` — Tauri `WindowEffectsConfig` for vibrancy (D-08), new command registrations.
- `apps/voss-app/src/App.tsx` — workspace orchestrator refactor (D-01).

</code_context>

<specifics>
## Specific Ideas

- **Warp color dot palette** is the reference for workspace accent colors (D-03). ~8 fixed colors as clickable dots — simple, fast, no color picker overhead. Auto-hash gives immediate visual differentiation without user effort.
- **Curated themes > import engine.** Hand-mapped themes guarantee quality. VSCode themes have hundreds of tokens that don't map cleanly to a terminal's ~25 vars. Curating 12 popular themes and mapping them well produces better results than an automated parser that approximates.
- **Theme engine is architecturally trivial.** `applyThemeOverrides()` already exists. Theme switch = read JSON, call function, done. The work is in curating 12 high-quality JSON mappings, not in building an engine.
- **High-contrast as overlay** is the key accessibility insight. One set of overrides works across all 12 themes — no need to create 12 high-contrast theme variants.
- **CSS transitions for animation** matches the app's "terminal-native" character. Terminals don't have springy animations. 150ms ease feels snappy and intentional. The `prefers-reduced-motion` kill switch is a single CSS rule.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within A8 scope. Adjacent capabilities are fenced to their owning phases:
- Settings UI (two-pane form to configure themes/fonts/profiles) — A9
- Status bar — A10
- Onboarding wizard — A11
- VSCode theme import (automated parser) — dropped from scope; revisit if user demand surfaces
- Editor pane syntax highlighting themes — L4
- Agent pane semantics — L2+

</deferred>

---

*Phase: A8-voss-app-workspaces-ux-polish-theming*
*Context gathered: 2026-05-20*
