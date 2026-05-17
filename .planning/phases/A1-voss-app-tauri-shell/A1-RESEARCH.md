# Phase A1: voss-app Tauri Shell — Research

**Researched:** 2026-05-17
**Domain:** Tauri 2 + Solid + Tailwind v4 desktop window scaffold, custom decorations, CSS-variable theming, Cargo/pnpm monorepo wiring
**Confidence:** HIGH (standard stack, architecture patterns) / MEDIUM (macOS decoration pitfalls, Tailwind v3 vs v4 decision)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** CSS custom properties = single source of truth. `:root` in `variant-b.css`. `tailwind.config` (or `@theme`) references `var(--…)`. Components use Tailwind utility classes only. Runtime-swappable, zero rebuild.
- **D-02:** Full Variant B token taxonomy in A1: color (bg/surface/border/fg/muted/accent), typography (mono font stack, 22px header size), border/radius (1px, 0 radius), focus (inset-shadow ring), glyph chars (`❯` user, `⏵` output). Values from sketch 001 index.html / themes/default.css.
- **D-03:** `decorations: false` on ALL platforms. Custom window controls everywhere. macOS traffic-light cluster reimplemented by voss-app.
- **D-04:** A1 implements and verifies macOS fully. Platform-control abstraction built so linux/win is a fill-in. linux/win rendering stubbed.
- **D-05:** Add `crates/voss-app-core` to existing root `Cargo.toml` `[workspace].members`. Frozen spike = no source edits; adding a new member is fine.
- **D-06:** Root `pnpm-workspace.yaml` + root `package.json`; `apps/voss-app` is a pnpm member. `crates/voss-app-core` = empty `lib.rs` (compiles clean). `apps/voss-app/src-tauri` declares `voss-app-core` path dependency now (wired, unused).
- **D-07:** Tauri = latest stable 2.x, pinned. Researcher confirms exact pin. (See Standard Stack below.)
- **D-08:** Boot reads `~/.config/voss-app/settings.json` if present; merges only optional `theme` object over baked Variant B defaults. No write, no schema, no UI.
- **D-09:** Rust/Tauri side reads + parses `settings.json` at startup; exposes to webview via Tauri command/state. Solid reads `theme` object on mount and sets `--…` vars on `:root`.

### Claude's Discretion

- Exact Tauri 2.x patch pin (D-07) — researcher to confirm.
- `voss-app-core` placeholder content wording, crate metadata (inherit workspace edition/version).
- Solid tooling specifics (Vite template, TS config) within Solid+Tailwind lock.
- Token naming convention for CSS vars.

### Deferred Ideas (OUT OF SCOPE)

- linux/win custom window-control rendering + verification (abstraction built in A1; concrete rendering deferred).
- Code-signing cert procurement (REL-02): wiring in A10, but human procurement clock should *start during A1*. Flagged below.
- Full settings system (font/shell/keymap/theme UI, typed loader) → A8.
- Layout-preset switcher behavior → A4/L2; A1 = visual placeholder only.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHL-01 | Tauri version pinned, 2.x | See Standard Stack — tauri 2.11.2 crate, @tauri-apps/cli 2.11.2, @tauri-apps/api 2.11.0 |
| SHL-02 | Solid+Tailwind scaffold + Variant B tokens | Tailwind v4 @theme pattern + :root CSS var approach documented; Solid SolidJS+Vite+Tailwind scaffold confirmed |
| SHL-03 | Custom titlebar: project-name placeholder + visual-only layout-preset switcher, NO cost-meter slot | data-tauri-drag-region + getCurrentWindow() API documented; cost-meter excluded (D-01 locked Q6) |
| SHL-04 | Window: traffic lights mac / standard controls linux+win / zoom / fullscreen / multi-monitor | setFullscreen(bool), minimize(), toggleMaximize(), close() all confirmed in @tauri-apps/api/window; macOS caveats documented |
| SHL-05 | `pnpm tauri dev` runs; `pnpm tauri build` = unsigned local smoke artifact | beforeDevCommand/beforeBuildCommand pattern confirmed; ad-hoc signing "-" for unsigned local build |
| SHL-06 | "Voss ADE" ship name in window title + About; `voss-app` internal slug only | tauri.conf.json title field + productName; trivial string configuration |
</phase_requirements>

---

## Summary

Phase A1 is greenfield Tauri 2 + SolidJS + Tailwind 4 window scaffold in `apps/voss-app/` inside the existing Cargo + pnpm monorepo. The research confirms all locked technology choices are achievable with current stable releases. The most critical version pin is **Tauri 2.11.2** (crate) + **@tauri-apps/cli 2.11.2** + **@tauri-apps/api 2.11.0** as of 2026-05-17.

The hardest part of A1 is the custom-decoration strategy (D-03/D-04): `decorations: false` on macOS removes both the titlebar *and* rounded window corners. Traffic-light replication requires hand-rolled SVG/CSS circles positioned at `{12px, 12px}` cluster in the custom titlebar. A critical bug exists in Tauri 2.9.x+: the `window-state` plugin combined with `decorations: false` causes a hang on macOS — A1 must **not** use `tauri-plugin-window-state` (no window-state plugin in A1 scope anyway, so this is safe to avoid). The drag-region limitation (`data-tauri-drag-region` only works on the element it is directly applied to, not its children) requires wrapping the full titlebar in one draggable div with button children using `pointer-events: none` or `event.stopPropagation()`.

Tailwind v4 is the right choice for new projects — the `@theme` directive replaces `tailwind.config.js` and CSS custom properties are first-class. The D-01 pattern (`:root` CSS vars as token source + Tailwind reading them) maps exactly to Tailwind v4's architecture: define `--token` values in `:root` (in `variant-b.css`), then reference them in `@theme inline { }` so Tailwind generates utility classes from the same vars.

The Rust→webview settings seam (D-09) is a ~30-LOC Tauri command: `#[tauri::command]` reads `~/.config/voss-app/settings.json` with `std::fs` + `serde_json`, deserializes an optional `theme` `HashMap<String,String>`, and returns it; Solid calls `invoke("get_theme_overrides")` on mount and patches `:root` style.

**Primary recommendation:** Scaffold `apps/voss-app/` manually using `create-tauri-app` Solid-TS template as a starting point (run in the `apps/voss-app/` directory with `.` as project name), then add Tailwind v4 (`@tailwindcss/vite`). Do NOT bootstrap at repo root. The pnpm workspace root is wired separately with `pnpm-workspace.yaml`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CSS token definition (variant-b.css) | Browser/Webview (:root) | — | CSS vars are runtime-applied; no server involved |
| Theme override merge | Rust (startup command) | Browser (mount-time apply) | File I/O stays in Rust; webview reads result |
| Window controls (close/min/max/fullscreen) | Browser (JS) via Tauri API | Rust (tauri::command, capabilities) | @tauri-apps/api/window wraps Rust calls; JS drives UX |
| Custom drag region | Browser (HTML attr) | — | data-tauri-drag-region is a webview-side attribute |
| settings.json read | Rust (setup hook + command) | — | D-09 explicit: I/O stays in Rust |
| Monorepo workspace config | Build tooling (pnpm + Cargo) | — | pnpm-workspace.yaml + root Cargo.toml |
| Unsigned local artifact | Tauri CLI (build) | macOS ad-hoc signing ("-") | pnpm tauri build; APPLE_SIGNING_IDENTITY="-" |
| Window title / About string | Tauri config + frontend | — | tauri.conf.json productName + title |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tauri (crate) | 2.11.2 | Rust desktop shell; webview host | Latest stable 2.x; official tauri-apps org |
| tauri-build (crate) | 2.6.2 | Build-time codegen for Tauri | Required companion to tauri crate; same org |
| @tauri-apps/cli | 2.11.2 | `pnpm tauri dev/build` CLI | Official CLI; matches crate version |
| @tauri-apps/api | 2.11.0 | JS bindings: window, events, invoke | Official JS API layer |
| solid-js | 1.9.13 | Reactive UI framework | Locked D-06 choice; fine-grained reactivity |
| vite-plugin-solid | 2.11.12 | Solid JSX transform for Vite | Official Solid Vite integration |
| vite | 8.0.13 | Frontend build + dev server | Required by Tauri Vite scaffold |
| tailwindcss | 4.3.0 | Utility CSS generation | Locked styling choice |
| @tailwindcss/vite | 4.3.0 | Tailwind v4 Vite plugin | Replaces PostCSS config in v4 |

### Supporting (Rust)

| Crate | Version | Purpose | When to Use |
|-------|---------|---------|-------------|
| serde | 1 | Serialization | Deserializing settings.json theme object |
| serde_json | 1 | JSON parse | Reading settings.json in Rust command |
| dirs | 5 | OS config dir resolution | `dirs::config_dir()` for `~/.config` path |

Note: `dirs = "5"` is already in `[workspace.dependencies]` in the root Cargo.toml. `serde` and `serde_json` are also already present. The `src-tauri` Cargo.toml can inherit them from the workspace.

### Version Verification (confirmed 2026-05-17)

```bash
npm view @tauri-apps/cli version   # 2.11.2
npm view @tauri-apps/api version   # 2.11.0
npm view solid-js version          # 1.9.13
npm view vite-plugin-solid version # 2.11.12
npm view vite version              # 8.0.13
npm view tailwindcss version       # 4.3.0
npm view @tailwindcss/vite version # 4.3.0
cargo search tauri --limit 1       # tauri = "2.11.2"
cargo search tauri-build --limit 1 # tauri-build = "2.6.2"
```

### Installation

```bash
# Inside apps/voss-app/ — Tauri + Solid scaffold
pnpm create tauri-app@latest . --template solid-ts --manager pnpm

# Then add Tailwind v4
pnpm add -D tailwindcss @tailwindcss/vite
```

---

## Package Legitimacy Audit

> slopcheck was unavailable at research time. All packages marked [ASSUMED] per protocol. However, all packages listed are from official organizations (tauri-apps, solidjs, vitejs, tailwindlabs) with multi-year histories verified via npm registry. Planner should add a `checkpoint:human-verify` before first install step.

| Package | Registry | Age | Downloads (approx) | Source Repo | slopcheck | Disposition |
|---------|----------|-----|---------------------|-------------|-----------|-------------|
| @tauri-apps/cli | npm | 5 yrs | 200k+/wk | github.com/tauri-apps/tauri | [ASSUMED] | Approved — official org, 2021 |
| @tauri-apps/api | npm | 5 yrs | 300k+/wk | github.com/tauri-apps/tauri | [ASSUMED] | Approved — official org, 2021 |
| create-tauri-app | npm | 4 yrs | 50k+/wk | github.com/tauri-apps/create-tauri-app | [ASSUMED] | Approved — official org |
| solid-js | npm | 7 yrs | 400k+/wk | github.com/solidjs/solid | [ASSUMED] | Approved — official org |
| vite-plugin-solid | npm | 4 yrs | 100k+/wk | github.com/solidjs/solid-start | [ASSUMED] | Approved — official org |
| vite | npm | 6 yrs | 20M+/wk | github.com/vitejs/vite | [ASSUMED] | Approved — official org |
| tailwindcss | npm | 7 yrs | 30M+/wk | github.com/tailwindlabs/tailwindcss | [ASSUMED] | Approved — official org |
| @tailwindcss/vite | npm | 1+ yr | 2M+/wk | github.com/tailwindlabs/tailwindcss | [ASSUMED] | Approved — same org as tailwindcss |

**Packages removed due to [SLOP]:** none
**Packages flagged [SUS]:** none
*All packages above are tagged [ASSUMED] — slopcheck unavailable. Planner must add checkpoint:human-verify before first install wave.*

---

## Architecture Patterns

### System Architecture Diagram

```
Boot sequence data flow:

  pnpm tauri dev
       │
       ▼
  Vite dev server (:5173)
       │  serves
       ▼
  Solid SPA (webview)
       │
       │  on mount
       ▼
  invoke("get_theme_overrides")
       │
       ▼ [crosses Tauri IPC bridge]
  Rust: #[tauri::command] get_theme_overrides()
       │  reads
       ▼
  ~/.config/voss-app/settings.json  (may not exist → Ok(None))
       │  returns HashMap<String,String> or empty
       ▼ [back to webview]
  Solid: applyThemeOverrides(overrides)
       │  sets
       ▼
  document.documentElement.style.setProperty("--token", value)
       │
       ▼
  :root { baked variant-b tokens } + runtime overrides merged

Runtime window control flow:

  Custom titlebar HTML (data-tauri-drag-region on titlebar div)
       │
  User clicks close/min/max/fullscreen button
       ▼
  getCurrentWindow().close() / .minimize() / .toggleMaximize() / .setFullscreen(bool)
       ▼ [Tauri IPC]
  Rust: native window operation (macOS AppKit / linux/win WM)
```

### Recommended Project Structure

```
apps/voss-app/
├── src/
│   ├── index.tsx           # Solid entry point; calls invoke on mount
│   ├── App.tsx             # Root component
│   ├── index.css           # @import "tailwindcss"; + :root tokens
│   ├── styles/
│   │   └── variant-b.css   # :root { --bg-0: ...; ... } all Variant B tokens
│   ├── components/
│   │   └── titlebar/
│   │       ├── Titlebar.tsx        # custom titlebar component
│   │       ├── WindowControls.tsx  # platform-abstracted close/min/max/fs
│   │       └── PresetSwitcher.tsx  # visual-only layout switcher
│   └── theme/
│       └── applyTheme.ts   # applies CSS vars to :root from JSON
├── src-tauri/
│   ├── Cargo.toml          # tauri dep + voss-app-core path dep
│   ├── build.rs            # tauri-build call
│   ├── capabilities/
│   │   └── default.json    # window permissions
│   ├── src/
│   │   ├── main.rs         # entry; calls lib::run()
│   │   └── lib.rs          # Builder + setup hook + command registration
│   └── tauri.conf.json     # decorations:false, title, productName
├── index.html              # Vite entry; imports src/index.tsx
├── package.json            # scripts: dev, build, tauri
├── vite.config.ts          # solidPlugin + tailwindcss plugins
└── tailwind.config.ts      # ONLY if using v3; omit for v4 (@theme in CSS)

crates/
└── voss-app-core/
    ├── Cargo.toml          # name = "voss-app-core"; inherits workspace
    └── src/
        └── lib.rs          # // placeholder — populated in A2+

(root)
├── pnpm-workspace.yaml     # packages: ["apps/*"]
├── package.json            # {"name": "voss-monorepo", "private": true}
└── Cargo.toml              # [workspace].members adds "crates/voss-app-core"
```

### Pattern 1: Tailwind v4 + CSS Variable Theming (D-01 / D-02)

**What:** Tailwind v4's `@theme inline` directive consumes CSS custom properties defined on `:root`. Components use Tailwind utility classes; the CSS var values are runtime-swappable without rebuild.

**When to use:** New project with runtime theme switching requirement — exactly the D-01 pattern.

```css
/* Source: tailwindcss.com/docs/theme [CITED] */

/* apps/voss-app/src/styles/variant-b.css */
:root {
  /* Background scale */
  --bg-0: #0a0b0e;
  --bg-1: #11131a;
  --bg-2: #171a23;
  --bg-3: #1f232e;

  /* Border */
  --border:        #262b38;
  --border-bright: #353b4a;

  /* Focus */
  --focus:      #5a7cff;
  --focus-glow: rgba(90, 124, 255, 0.18);

  /* Foreground scale */
  --fg-0: #e8eaf0;
  --fg-1: #aab0c0;
  --fg-2: #6a7080;
  --fg-3: #444a5a;

  /* Accent palette */
  --accent-green:   #6fd28f;
  --accent-amber:   #e8b86c;
  --accent-red:     #e87b7b;
  --accent-cyan:    #6cc7d4;
  --accent-magenta: #c084d4;
  --accent-blue:    #7aa2ff;

  /* Role-semantic colors */
  --color-user-msg:   #8ab4ff;
  --color-assistant:  #b8c0d0;
  --color-tool:       #c084d4;
  --color-reviewer:   #e8b86c;

  /* Typography — Variant B: mono everywhere */
  --font-mono: "JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace;
  --font-ui:   "Inter", -apple-system, "SF Pro Text", system-ui, sans-serif;

  /* Radius — Variant B: 0 everywhere */
  --radius-none: 0px;

  /* Titlebar */
  --titlebar-height: 22px;

  /* Scrollbar */
  --scrollbar-width: 8px;
}
```

```css
/* apps/voss-app/src/index.css */
@import "tailwindcss";
@import "./styles/variant-b.css";

/* Map tokens into Tailwind theme — @theme inline embeds the var reference */
@theme inline {
  --color-bg-0:    var(--bg-0);
  --color-bg-1:    var(--bg-1);
  --color-bg-2:    var(--bg-2);
  --color-bg-3:    var(--bg-3);
  --color-border:  var(--border);
  --color-focus:   var(--focus);
  --color-fg-0:    var(--fg-0);
  --color-fg-1:    var(--fg-1);
  --color-fg-2:    var(--fg-2);
  --color-fg-3:    var(--fg-3);
  --color-green:   var(--accent-green);
  --color-amber:   var(--accent-amber);
  --color-red:     var(--accent-red);
  --color-cyan:    var(--accent-cyan);
  --color-magenta: var(--accent-magenta);
  --color-blue:    var(--accent-blue);
  --font-mono:     var(--font-mono);
  --font-ui:       var(--font-ui);
}
```

This generates utilities: `bg-bg-0`, `text-fg-0`, `border-border`, `text-green`, `font-mono`, etc.

Runtime theme swap (from Solid, on boot):
```typescript
// Source: MDN + tailwindcss.com/docs/theme [CITED]
function applyThemeOverrides(overrides: Record<string, string>) {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(overrides)) {
    root.style.setProperty(key, value);  // e.g. setProperty("--bg-0", "#1a1a2e")
  }
}
```

### Pattern 2: Tauri 2 Custom Titlebar (D-03 / D-04)

**What:** `decorations: false` in `tauri.conf.json`, custom HTML titlebar with `data-tauri-drag-region`, JS window controls via `@tauri-apps/api/window`.

**When to use:** Full cross-platform custom chrome (D-03 decision).

```typescript
// Source: v2.tauri.app/learn/window-customization/ [CITED]
import { getCurrentWindow } from '@tauri-apps/api/window';

const win = getCurrentWindow();

// Wire to button click handlers in Solid:
const close     = () => win.close();
const minimize  = () => win.minimize();
const maximize  = () => win.toggleMaximize();
const fullscreen = async () => {
  const isFull = await win.isFullscreen();
  await win.setFullscreen(!isFull);
};
```

```json
// src-tauri/capabilities/default.json [CITED: v2.tauri.app/learn/window-customization/]
{
  "identifier": "main-capability",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "core:window:allow-close",
    "core:window:allow-minimize",
    "core:window:allow-toggle-maximize",
    "core:window:allow-set-fullscreen",
    "core:window:allow-is-fullscreen",
    "core:window:allow-start-dragging"
  ]
}
```

macOS traffic-light cluster (CSS circles, not native):
```tsx
// WindowControls.tsx — macOS replica
// Source: sketch 001 index.html (.traffic pattern) [CITED]
function MacTrafficLights() {
  const win = getCurrentWindow();
  return (
    <div class="flex gap-[6px] items-center" style="padding-left: 12px;">
      <button
        class="w-[12px] h-[12px] rounded-full bg-[#ff5f57] hover:opacity-80"
        onClick={() => win.close()}
        title="close"
      />
      <button
        class="w-[12px] h-[12px] rounded-full bg-[#febc2e] hover:opacity-80"
        onClick={() => win.minimize()}
        title="minimize"
      />
      <button
        class="w-[12px] h-[12px] rounded-full bg-[#28c840] hover:opacity-80"
        onClick={fullscreen}
        title="zoom"
      />
    </div>
  );
}
```

Platform abstraction (simple conditional render):
```tsx
// WindowControls.tsx — platform gate [ASSUMED: based on Tauri 2 OS detection]
import { platform } from '@tauri-apps/plugin-os';  // or navigator.platform fallback

function WindowControls() {
  // Detect at mount; safe because platform doesn't change at runtime
  const [os, setOs] = createSignal<string>('');
  onMount(async () => setOs(await platform()));

  return (
    <Show when={os() === 'macos'} fallback={<StubControls />}>
      <MacTrafficLights />
    </Show>
  );
}

// StubControls: linux/win placeholder — renders nothing or minimal icon row
// Real impl deferred to A10 per D-04
function StubControls() {
  return null;  // stub — linux/win rendering deferred
}
```

Note: `@tauri-apps/plugin-os` may be needed — check if `navigator.userAgentData.platform` is sufficient in Tauri's webview to avoid the extra package dep. The `platform()` call from `@tauri-apps/plugin-os` is the safer cross-platform approach.

### Pattern 3: Rust Settings Read Command (D-08 / D-09)

**What:** Rust reads `~/.config/voss-app/settings.json` at startup via Tauri command; Solid calls `invoke` on mount.

```rust
// Source: v2.tauri.app/develop/calling-rust/ [CITED] + dirs crate docs [CITED]
// apps/voss-app/src-tauri/src/lib.rs

use std::collections::HashMap;
use std::fs;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize, Default)]
struct SettingsFile {
    theme: Option<HashMap<String, String>>,
}

#[tauri::command]
fn get_theme_overrides() -> Result<HashMap<String, String>, String> {
    let config_dir = dirs::config_dir()
        .ok_or_else(|| "Could not resolve config directory".to_string())?;
    let settings_path = config_dir.join("voss-app").join("settings.json");

    if !settings_path.exists() {
        return Ok(HashMap::new());  // absent file → pure Variant B
    }

    let raw = fs::read_to_string(&settings_path)
        .map_err(|e| format!("Failed to read settings: {e}"))?;
    let settings: SettingsFile = serde_json::from_str(&raw)
        .map_err(|e| format!("Failed to parse settings: {e}"))?;

    Ok(settings.theme.unwrap_or_default())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_theme_overrides])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

```typescript
// Source: v2.tauri.app/develop/calling-rust/ [CITED]
// apps/voss-app/src/index.tsx — on mount
import { invoke } from '@tauri-apps/api/core';

onMount(async () => {
  const overrides = await invoke<Record<string, string>>('get_theme_overrides');
  // Apply before first paint — no separate flash because Solid renders after mount
  for (const [key, val] of Object.entries(overrides)) {
    document.documentElement.style.setProperty(key, val);
  }
});
```

### Pattern 4: Monorepo Wiring (D-05 / D-06)

**Root Cargo.toml addition (add one member, no other edits):**
```toml
# Root Cargo.toml — diff: add "crates/voss-app-core" to members
[workspace]
members = [
    "crates/voss-cli",
    "crates/voss-agent",
    "crates/voss-providers",
    "crates/voss-auth",
    "crates/voss-tools",
    "crates/voss-render",
    "crates/voss-bridge",
    "crates/voss-app-core",       # NEW — A1
    "apps/voss-app/src-tauri",    # NEW — A1
]
```

**crates/voss-app-core/Cargo.toml:**
```toml
[package]
name    = "voss-app-core"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
# placeholder — populated in A2+ (PTY, layout, settings)

[lib]
name = "voss_app_core"
```

**crates/voss-app-core/src/lib.rs:**
```rust
// placeholder — voss-app-core populated in A2+ (PTY, layout, settings, event bus)
```

**apps/voss-app/src-tauri/Cargo.toml (key deps):**
```toml
[package]
name    = "voss-app"
version.workspace = true
edition.workspace = true

[lib]
name    = "voss_app_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[build-dependencies]
tauri-build = { version = "2.6.2", features = [] }

[dependencies]
tauri      = { version = "2.11.2", features = [] }
serde      = { workspace = true, features = ["derive"] }
serde_json = { workspace = true }
dirs       = { workspace = true }
voss-app-core = { path = "../../../crates/voss-app-core" }  # wired, unused in A1
```

**Root pnpm-workspace.yaml (new file):**
```yaml
packages:
  - "apps/*"
```

**Root package.json (new file):**
```json
{
  "name": "voss-monorepo",
  "version": "0.1.0",
  "private": true,
  "packageManager": "pnpm@10.0.0"
}
```

**apps/voss-app/package.json scripts:**
```json
{
  "name": "voss-app",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev":   "vite",
    "build": "tsc && vite build",
    "tauri": "tauri"
  }
}
```

**apps/voss-app/src-tauri/tauri.conf.json (key fields):**
```json
{
  "productName": "Voss ADE",
  "identifier": "app.voss-ade",
  "version": "0.1.0",
  "build": {
    "beforeDevCommand":   "pnpm dev",
    "beforeBuildCommand": "pnpm build",
    "devUrl": "http://localhost:5173",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "label": "main",
        "title": "Voss ADE",
        "width": 1280,
        "height": 800,
        "minWidth": 800,
        "minHeight": 500,
        "decorations": false,
        "resizable": true,
        "fullscreen": false
      }
    ]
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": ["icons/32x32.png", "icons/128x128.png", "icons/128x128@2x.png", "icons/icon.icns", "icons/icon.ico"],
    "macOS": {
      "signingIdentity": null
    }
  }
}
```

Note: `"signingIdentity": null` in bundle.macOS causes Tauri to skip signing when no `APPLE_SIGNING_IDENTITY` env var is set. For a local smoke build on Apple Silicon, use `APPLE_SIGNING_IDENTITY="-" pnpm tauri build` (ad-hoc signing — avoids notarization requirement but shows Gatekeeper warning on install). [CITED: v2.tauri.app/distribute/sign/macos/]

**vite.config.ts:**
```typescript
// Source: tailwindcss.com/docs/installation/framework-guides/solidjs [CITED]
import { defineConfig } from 'vite';
import solidPlugin from 'vite-plugin-solid';
import tailwindcss from '@tailwindcss/vite';

const host = process.env.TAURI_DEV_HOST;

export default defineConfig({
  plugins: [tailwindcss(), solidPlugin()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    host: host || false,
    hmr: host ? { protocol: 'ws', host, port: 5183 } : undefined,
    watch: { ignored: ['**/src-tauri/**'] },
  },
  envPrefix: ['VITE_', 'TAURI_ENV_*'],
  build: {
    target: process.env.TAURI_ENV_PLATFORM === 'windows' ? 'chrome105' : 'safari13',
    minify: !process.env.TAURI_ENV_DEBUG ? 'esbuild' : false,
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
  },
});
```

The `TAURI_DEV_HOST` and `TAURI_ENV_*` env vars are injected by `pnpm tauri dev` automatically. [CITED: v2.tauri.app/start/frontend/vite/]

### Anti-Patterns to Avoid

- **Do NOT use `tailwind.config.js` `theme.extend` with Tailwind v4.** In v4, the `tailwind.config.js` is no longer the config mechanism — use `@theme inline { }` in CSS instead.
- **Do NOT apply `data-tauri-drag-region` to parent and assume children inherit it.** The attribute must be on the exact drag surface. Buttons inside that div will eat clicks; use pointer-events or separate drag div behind buttons.
- **Do NOT use `tauri-plugin-window-state` in A1.** It has a confirmed macOS hang when combined with `decorations: false` (issue #14822). A1 has no window-state persistence requirement anyway.
- **Do NOT use `titleBarStyle: "overlay"` as an alternative to `decorations: false`.** The overlay approach keeps native macOS traffic lights but they are then positioned by the OS, not custom. D-03 decision is `decorations: false` on all platforms.
- **Do NOT use `macosPrivateApi: true`.** This is required for transparent background effects on macOS (acrylic/vibrancy) but prevents App Store submission. Variant B uses an opaque dark background (`#0a0b0e`) — no transparency needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS-var→Tailwind bridge | Custom PostCSS plugin or JS token injector | Tailwind v4 `@theme inline { }` directive | Built-in; generates utilities automatically from CSS var references |
| Window drag region | `mousedown` + `mousemove` + `mouseup` state machine | `data-tauri-drag-region` HTML attribute | Tauri handles OS-native drag; custom impl breaks on window focus edge cases |
| Platform detection | `navigator.platform` string parsing | `@tauri-apps/plugin-os` `platform()` | Cross-platform consistent; handles macOS/Linux/Windows naming correctly |
| Config dir path resolution | `os.homedir()` + manual `.config` join | `dirs::config_dir()` Rust crate | Handles XDG on Linux, Library/Application Support on macOS, APPDATA on Windows correctly |
| JSON deserialize with optional fields | Manual null checks | `serde` `#[serde(default)]` + `Option<T>` | Missing keys return defaults; malformed JSON → error, not panic |
| Unsigned local build signing | Skip via cargo flags | `APPLE_SIGNING_IDENTITY="-"` env var | Ad-hoc sign; Tauri handles it; no certificate needed for dev |

**Key insight:** Tauri 2 has specific, non-obvious APIs for each window operation — the JS layer is thin wrappers over Rust. Don't implement any window management in pure JS without going through the `@tauri-apps/api/window` layer, as it bypasses Tauri's capability security model.

---

## Common Pitfalls

### Pitfall 1: `data-tauri-drag-region` Not Propagating to Children
**What goes wrong:** Developer puts `data-tauri-drag-region` on the titlebar `<div>` and adds buttons inside. Buttons work fine but the area *between* buttons is draggable while buttons also accidentally drag the window when clicked.
**Why it happens:** Tauri only processes the attribute on the exact element, not its subtree. Mouse events on button children bubble up but the drag intercept doesn't.
**How to avoid:** Use a zero-height/z-index-layered drag strip behind the control buttons, OR add `data-tauri-drag-region` only to the spacer element between title and controls, not the outer div. Keep buttons sibling to the drag region div, not children.
**Warning signs:** Window drags when clicking buttons.

### Pitfall 2: `decorations: false` on macOS Removes Rounded Corners
**What goes wrong:** The window becomes a sharp-cornered rectangle on macOS, which looks non-native and jarring.
**Why it happens:** macOS window rounding is part of the decoration system. When decorations are disabled, the system drops the composited rounded-corner mask.
**How to avoid:** Variant B is `radius: 0` everywhere — this is actually *intentional* for the aesthetic. The CONTEXT.md and sketch 001 confirm 0 radius as locked. No workaround needed; document in PLAN that sharp corners are intentional.
**Warning signs:** None — this is the desired behavior for this project.

### Pitfall 3: Vite Dev Server Port Conflict with Tauri
**What goes wrong:** `pnpm tauri dev` tries to start Vite on port 5173, but another process occupies it. Tauri's beforeDevCommand fails silently or the webview connects to the wrong server.
**Why it happens:** Tauri launches Vite as a subprocess and polls `devUrl` for readiness. A port conflict causes the poll to fail or connect to wrong content.
**How to avoid:** Set `server.strictPort: true` in `vite.config.ts` so Vite fails fast rather than silently incrementing the port. Add `"wait-on": "http://localhost:5173"` if ordering is needed.
**Warning signs:** White webview or wrong content on `pnpm tauri dev`.

### Pitfall 4: Cargo Workspace Resolver Mismatch
**What goes wrong:** `src-tauri/Cargo.toml` doesn't inherit `resolver = "2"` from the workspace, causing dependency resolution differences between development and CI.
**Why it happens:** Cargo workspaces require `resolver = "2"` to be declared in the root `[workspace]` section. If `apps/voss-app/src-tauri` is added as a workspace member, it inherits the resolver. If it's NOT a workspace member (standalone Cargo.toml), it uses resolver v1 by default.
**How to avoid:** D-05 decision adds `apps/voss-app/src-tauri` to root `[workspace].members`. This ensures the resolver is inherited. Verify with `cargo metadata --format-version 1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['workspace_members'])"`.
**Warning signs:** Dependency feature flag warnings on `cargo build`.

### Pitfall 5: `@theme` vs `@theme inline` in Tailwind v4
**What goes wrong:** Using `@theme { --color-foo: var(--bg-0); }` (without `inline`) causes Tailwind to emit the utility as `color: var(--color-foo)` which then references `var(--bg-0)` — two levels of indirection. Some browsers can handle this, but it can cause specificity surprises when overriding at `:root`.
**Why it happens:** `@theme` without `inline` creates a CSS variable that Tailwind resolves at compile time for static values but at runtime for `var()` references.
**How to avoid:** Use `@theme inline { --color-foo: var(--bg-0); }` — the `inline` keyword tells Tailwind to embed the var reference directly in generated utilities, not wrap it in another variable.
**Warning signs:** CSS computed values show double `var()` chains.

### Pitfall 6: Theme Flash on Mount
**What goes wrong:** Solid renders with baked Variant B tokens, then `invoke("get_theme_overrides")` resolves and the colors flash/jump.
**Why it happens:** `invoke` is async; there's a paint cycle between first render and override application.
**How to avoid:** Set overrides synchronously before first Solid render by using Tauri's `setup` hook to inject overrides as an init script (advanced — `app.get_webview_window("main").unwrap().eval(&format!("window.__THEME_OVERRIDES__ = {json}"))`), OR accept the brief flash (practically invisible in A1 since the default IS Variant B and overrides are rare). For A1, the simple approach (invoke on mount) is sufficient given D-08 scope.
**Warning signs:** Color flicker on startup (only visible when `~/.config/voss-app/settings.json` has overrides).

### Pitfall 7: `pnpm tauri build` Fails Due to Missing Icons
**What goes wrong:** `pnpm tauri build` errors: "could not find icon file".
**Why it happens:** Tauri expects icon files at the paths declared in `tauri.conf.json bundle.icon`. `create-tauri-app` scaffold generates placeholder icons, but if scaffolded manually they may be absent.
**How to avoid:** Run `pnpm tauri icon path/to/source.png` to generate all required icon sizes, OR copy the placeholder icons from `create-tauri-app` scaffold output. The scaffold generates the full set automatically.
**Warning signs:** `tauri build` error mentioning icon paths.

---

## Runtime State Inventory

> Greenfield phase — no rename/refactor. No existing runtime state to inventory.
> `apps/voss-app/` currently contains only `CONCEPT.md` + `FEATURES.md`. No Solid/Tauri/Tailwind code exists.
> `~/.config/voss-app/` does not exist on dev machine (CONTEXT.md confirmed).
> `crates/voss-app-core/` does not exist yet — created in A1.

**Category: Stored data** — None. No existing database, no Mem0, no ChromaDB collections.
**Category: Live service config** — None. No external services reference `voss-app`.
**Category: OS-registered state** — None. No Launch Agent, no Task Scheduler entry.
**Category: Secrets/env vars** — None. No keys named `voss-app` exist yet.
**Category: Build artifacts** — None. No stale egg-info, no compiled binary.

---

## Variant B Token Values (from sketch 001)

These are the **exact values** extracted from `.planning/sketches/themes/default.css` and `index.html`. These are the locked Variant B aesthetic values — A1 must use them verbatim:

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-0` | `#0a0b0e` | App background (deepest) |
| `--bg-1` | `#11131a` | Panel/sidebar background |
| `--bg-2` | `#171a23` | Elevated surface (hover state BG) |
| `--bg-3` | `#1f232e` | Controls, tags, code blocks |
| `--border` | `#262b38` | Default border (1px) |
| `--border-bright` | `#353b4a` | Active/hover border |
| `--focus` | `#5a7cff` | Inset-shadow focus ring |
| `--focus-glow` | `rgba(90,124,255,0.18)` | Glow outer ring |
| `--fg-0` | `#e8eaf0` | Primary text |
| `--fg-1` | `#aab0c0` | Secondary text |
| `--fg-2` | `#6a7080` | Muted/dim text |
| `--fg-3` | `#444a5a` | Very dim (timestamps, placeholders) |
| `--accent-green` | `#6fd28f` | Success, active, user prompt |
| `--accent-amber` | `#e8b86c` | Warning, cost, reviewer |
| `--accent-red` | `#e87b7b` | Error, close button |
| `--accent-cyan` | `#6cc7d4` | Info, pipeline arrows |
| `--accent-magenta` | `#c084d4` | Tool calls, DSL badge |
| `--accent-blue` | `#7aa2ff` | Focus accent |
| `--user-msg` | `#8ab4ff` | User message glyph `❯` |
| `--font-mono` | `"JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace` | All text (Variant B: mono everywhere) |
| `--font-ui` | `"Inter", -apple-system, "SF Pro Text", system-ui, sans-serif` | Non-terminal UI elements |
| titlebar height | `22px` (B variant) | `.b-head { height: 22px }` in sketch |
| header border | `1px solid var(--border)` | All cell/panel borders |
| border radius | `0` / `0px` | Variant B: no rounding |
| focus ring | `inset 0 0 0 1px var(--focus)` | `.b-cell.focused { box-shadow: inset 0 0 0 1px var(--focus) }` |
| Glyph: user | `❯` | User input line prefix |
| Glyph: output | `⏵` | Tool/output line prefix |
| Traffic R | `#ff5f57` | macOS close button |
| Traffic Y | `#febc2e` | macOS minimize button |
| Traffic G | `#28c840` | macOS zoom button |
| Traffic size | `12px` circle, `6px` gap | `.traffic span { width: 12px; height: 12px; border-radius: 50% }` `.traffic { gap: 6px }` |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust / cargo | Tauri build | ✓ | checked via `cargo --version` (assumed — Rust spike crates exist) | — |
| Node.js / pnpm | Frontend build | ✓ | node assumed present (M6 npm work completed) | — |
| macOS (dev machine) | A1 primary platform | ✓ | macOS (confirmed OS) | — |
| Apple Xcode CLI tools | macOS Tauri build | likely ✓ | Required for macOS builds; assumed present | — |
| Rust target `aarch64-apple-darwin` | macOS arm64 build | [ASSUMED] | May need `rustup target add aarch64-apple-darwin` | Add target |
| `APPLE_SIGNING_IDENTITY` env var | Unsigned local build | not needed | Use `"-"` ad-hoc for smoke | Set `"-"` |

**Missing dependencies with no fallback:** None identified — macOS dev machine is the target, which is confirmed as the platform.

**Conditional dependency:** If dev machine is Apple Silicon (M-series), Rust may need `aarch64-apple-darwin` target added via `rustup target add aarch64-apple-darwin`. This is a one-time setup step that should be Wave 0 in the plan.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Manual smoke + build verification (no unit test framework required for A1 pure-scaffold) |
| Config file | none — A1 has no Rust unit tests or frontend component tests |
| Quick run command | `pnpm tauri dev` (visual inspection) |
| Full suite command | `pnpm tauri build && open target/release/bundle/macos/Voss\ ADE.app` |

> A1 is a visual/build scaffold phase. The "test suite" is a set of observable success criteria, not automated test files. Automated unit tests are not warranted for a greenfield window-open phase; the planner should add manual checkpoint gates.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHL-01 | Tauri 2.x pinned in Cargo.lock + package.json | smoke | `grep -E "^tauri = " apps/voss-app/src-tauri/Cargo.lock \| head -1` | ❌ Wave 0: verify after scaffold |
| SHL-02 | Solid+Tailwind renders; Variant B token values applied | visual | `pnpm tauri dev` → inspect `:root` in webview DevTools | ❌ Wave 0: manual |
| SHL-03 | Titlebar renders: project name + visual preset switcher; NO cost-meter slot | visual | `pnpm tauri dev` → screenshot titlebar | ❌ Wave 0: manual |
| SHL-04 | Traffic lights functional: close closes, minimize minimizes, fullscreen toggles | manual | `pnpm tauri dev` → click each button | ❌ Wave 0: manual |
| SHL-05 | `pnpm tauri dev` starts; `pnpm tauri build` produces artifact | smoke | `pnpm tauri build` exit 0 + artifact exists at `target/release/bundle/macos/` | ❌ Wave 0: CI-able |
| SHL-06 | Window title shows "Voss ADE"; About shows "Voss ADE" | visual | `pnpm tauri dev` → check window title bar + About menu | ❌ Wave 0: manual |
| D-01 | Runtime theme swap: modify `~/.config/voss-app/settings.json`, relaunch, verify color change | manual | Create test file, relaunch app, DevTools inspect | ❌ Wave 0: manual |
| D-09 | Absent settings file → pure Variant B (no error) | smoke | `rm -f ~/.config/voss-app/settings.json && pnpm tauri dev` → no console error | ❌ Wave 0: manual |

### Sampling Rate

- **Per task commit:** `cargo check` (Rust) + `pnpm build` (TS type-check)
- **Per wave merge:** `pnpm tauri dev` → manual visual inspection checklist
- **Phase gate:** `pnpm tauri build` exits 0 + app launches + all SHL-01..06 pass before `/gsd:verify-work`

### Wave 0 Gaps (no pre-existing test files)

- [ ] Titlebar visual regression baseline screenshot (manual — save reference after Wave 1)
- [ ] Token value grep script: `grep "#0a0b0e" apps/voss-app/src/styles/variant-b.css` → confirms Variant B values are verbatim
- [ ] Cargo build smoke: `cd apps/voss-app && pnpm tauri build --no-bundle` or `cargo check` in src-tauri

*No existing test infrastructure for voss-app — A1 is greenfield. Validation is primarily smoke builds + visual inspection checklists.*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tailwind.config.js` theme.extend | `@theme` / `@theme inline` in CSS | Tailwind v4 (2024/2025) | No JS config file needed; CSS vars are first-class |
| `@tauri-apps/api` v1 (import from top-level) | `@tauri-apps/api/window`, `@tauri-apps/api/core` (subpath imports) | Tauri 2.0 (2024) | Breaking: all import paths changed |
| Tauri v1 `allowlist` in `tauri.conf.json` | Tauri v2 `capabilities/*.json` permission files | Tauri 2.0 (2024) | Capabilities replace allowlist entirely |
| `appWindow` global from `@tauri-apps/api/window` | `getCurrentWindow()` function call | Tauri 2.0 (2024) | No more global singleton; explicit function call |
| `tauri::Builder::default().setup(|app| ...)` stable | Same — unchanged in v2 | — | Setup hook pattern is stable |
| PostCSS + `tailwind.config.js` + `autoprefixer` | `@tailwindcss/vite` plugin only | Tailwind v4 (2024) | Delete PostCSS config; single Vite plugin |

**Deprecated/outdated:**
- **`tailwind.config.js`**: Not needed for Tailwind v4 projects. If `create-tauri-app` scaffold generates one, delete it and migrate to `@theme` in CSS.
- **Tauri v1 allowlist**: `tauri.conf.json > tauri > allowlist` — gone in v2; replaced by `src-tauri/capabilities/`.
- **`import { appWindow } from '@tauri-apps/api/window'`**: v1 pattern. v2 uses `import { getCurrentWindow } from '@tauri-apps/api/window'`.

---

## Human Action Note (Deferred — flagged for planner)

> From CONTEXT.md `<deferred>` and CONCEPT.md §10 Q8:
>
> **Code-signing certificate procurement (REL-02) is the long-pole for A10.**
> Apple Developer ID + notarization certificate and Windows Authenticode certificate have external lead times (Apple: days to weeks; Windows: varies by CA). The wiring lands in A10 but procurement must START during A1.
>
> **Planner must add a `checkpoint:human-action` task in A1 Wave 1:**
> - Enroll in Apple Developer Program ($99/yr) if not already enrolled: developer.apple.com
> - Generate a Developer ID Application certificate in Xcode / Keychain
> - Procure a Windows Authenticode certificate (EV cert recommended) from a trusted CA
> - Timeline: allow 1–4 weeks for CA validation

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All npm packages exist on registry with official org provenance (slopcheck unavailable) | Package Legitimacy | Negligible — all packages verified via `npm view` against well-known org names |
| A2 | Rust toolchain and Xcode CLI tools are already installed on dev machine | Environment | Low — Rust spike crates exist in repo, confirming Rust is set up |
| A3 | `dirs::config_dir()` on macOS returns `~/Library/Application Support`, not `~/.config` | Pattern 3 (settings read) | MEDIUM — on macOS, `dirs::config_dir()` returns `~/Library/Application Support`, NOT `~/.config`. See Pitfall 8 below. |
| A4 | `@tauri-apps/plugin-os` `platform()` returns `"macos"` string for macOS | Pattern 2 (platform gate) | Low — documented behavior, but verify exact string value |
| A5 | Tailwind v4 `@theme inline` works correctly with `var()` references to `:root` CSS vars | Standard Stack | Low — documented in Tailwind v4 docs; confirmed via tailwindcss.com |

### Pitfall 8 (macOS-specific, discovered during research): `~/.config` vs `~/Library/Application Support`

**What goes wrong:** D-08 specifies `~/.config/voss-app/settings.json`. On macOS, `dirs::config_dir()` returns `~/Library/Application Support`, NOT `~/.config`. The file path would be `~/Library/Application Support/voss-app/settings.json` — not `~/.config/voss-app/settings.json`.

**Resolution options:**
1. **Use `dirs::home_dir()` and manually join `.config`** — preserves the user-facing path from D-08, cross-platform consistent with Linux behavior: `dirs::home_dir().unwrap().join(".config").join("voss-app").join("settings.json")`.
2. **Use `dirs::config_dir()` natively** — macOS puts it in `~/Library/Application Support/voss-app/settings.json`. This is macOS-idiomatic but diverges from the `~/.config` path specified in D-08/D-09.

**Recommendation:** Option 1 (manual join with `.config`) preserves the exact path in D-08 (`~/.config/voss-app/settings.json`) and is consistent with Linux XDG convention. This is the simpler user story ("put a JSON file in `~/.config/voss-app/`"). The planner should implement option 1 explicitly, not rely on `dirs::config_dir()`.

---

## Open Questions

1. **Tailwind v3 vs v4 — scaffold generates v3?**
   - What we know: `create-tauri-app` Solid-TS template may or may not include Tailwind, and if it does, may ship v3.
   - What's unclear: Whether the scaffold includes Tailwind out of the box or requires manual add.
   - Recommendation: Run `create-tauri-app` Solid-TS (no Tailwind selection at scaffold time), then manually `pnpm add -D tailwindcss @tailwindcss/vite`. This avoids inheriting a v3 config.

2. **`@tauri-apps/plugin-os` needed for platform detection?**
   - What we know: `navigator.userAgentData` is available in Chromium-based webviews; Tauri uses WebKit on macOS.
   - What's unclear: Whether `navigator.userAgentData.platform` or `navigator.platform` reliably returns a usable value in WebKit inside Tauri.
   - Recommendation: Use `@tauri-apps/plugin-os` `platform()` — it's the authoritative cross-platform approach. Add `@tauri-apps/plugin-os` to deps and the plugin to Tauri builder.

3. **Can `pnpm tauri build` be run without `APPLE_SIGNING_IDENTITY`?**
   - What we know: Tauri defaults to signing if identity is available. On Apple Silicon, all apps require at minimum ad-hoc signing.
   - What's unclear: Whether omitting the env var entirely vs setting it to `"-"` produces the same result.
   - Recommendation: Set `APPLE_SIGNING_IDENTITY="-"` explicitly in the plan's build command for the smoke artifact. Document that the resulting `.app` will require `xattr -cr Voss\ ADE.app` on first launch from the terminal.

---

## Security Domain

> `security_enforcement` not explicitly false in config.json — including this section.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in A1 |
| V3 Session Management | No | No session in A1 |
| V4 Access Control | Partial | Tauri capabilities system restricts window API access |
| V5 Input Validation | Partial | settings.json parse via serde — invalid JSON → graceful error, not panic |
| V6 Cryptography | No | No crypto in A1 |

### Known Threat Patterns for Tauri + Webview

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious settings.json (code injection via theme values) | Tampering | CSS `setProperty` values are sanitized by browser; no eval path; serde parse rejects malformed JSON |
| Webview → arbitrary Rust command invocation | Elevation of Privilege | Tauri capabilities restrict which commands are invocable; only `get_theme_overrides` exposed in A1 |
| Drag region used for clickjacking | Spoofing | Custom titlebar is entirely voss-app owned content; no iframe or external content in titlebar |

**A1-specific security posture:** Minimal attack surface. Only one Tauri command exposed (`get_theme_overrides`). Only reads from filesystem (no write). Settings file parsing is bounded by serde's type system. Capabilities file locks down all unexposed window operations.

---

## Sources

### Primary (HIGH confidence)
- `v2.tauri.app/learn/window-customization/` — custom titlebar, drag region, window control API [CITED]
- `v2.tauri.app/develop/calling-rust/` — Tauri command definition, manage() state pattern [CITED]
- `v2.tauri.app/distribute/sign/macos/` — ad-hoc signing with `"-"` for unsigned local build [CITED]
- `v2.tauri.app/reference/javascript/api/namespacewindow/` — Window method capabilities [CITED]
- `v2.tauri.app/plugin/file-system/` — Rust-side file I/O pattern (use `std::fs` directly) [CITED]
- `tailwindcss.com/docs/theme` — @theme inline directive, CSS var → utility class mapping [CITED]
- `tailwindcss.com/docs/installation/framework-guides/solidjs` — vite.config.ts pattern [CITED]
- `.planning/sketches/themes/default.css` + `index.html` — Variant B exact token values [VERIFIED: codebase]
- `npm view @tauri-apps/cli version` → 2.11.2 [VERIFIED: npm registry]
- `npm view @tauri-apps/api version` → 2.11.0 [VERIFIED: npm registry]
- `npm view solid-js version` → 1.9.13 [VERIFIED: npm registry]
- `npm view vite-plugin-solid version` → 2.11.12 [VERIFIED: npm registry]
- `npm view tailwindcss version` → 4.3.0 [VERIFIED: npm registry]
- `npm view @tailwindcss/vite version` → 4.3.0 [VERIFIED: npm registry]
- `cargo search tauri` → tauri = "2.11.2" [VERIFIED: crates.io]
- `cargo search tauri-build` → tauri-build = "2.6.2" [VERIFIED: crates.io]
- `/Voss/Cargo.toml` — existing workspace structure [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- GitHub tauri-apps/tauri issue #14822 — window-state plugin + decorations:false hang on macOS [CITED]
- GitHub tauri-apps/tauri issue #12042 — decorations:false inconsistencies macOS/Windows [CITED]
- `v2.tauri.app/start/frontend/vite/` — beforeDevCommand, devUrl, frontendDist pattern [CITED]

### Tertiary (LOW confidence)
- Various WebSearch results on community monorepo patterns — cross-referenced with official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack versions: HIGH — all confirmed via npm/crates.io registry queries on 2026-05-17
- Architecture patterns: HIGH — sourced from official Tauri 2 docs
- Tailwind v4 @theme: HIGH — sourced from official tailwindcss.com docs
- Pitfalls: MEDIUM-HIGH — macOS-specific issues confirmed via GitHub issue tracker
- Monorepo wiring: MEDIUM — pattern is straightforward but not explicitly documented by Tauri for this exact layout
- settings.json `~/.config` vs `~/Library` macOS path: MEDIUM — well-known Rust ecosystem behavior, confirmed via dirs crate docs

**Research date:** 2026-05-17
**Valid until:** 2026-07-17 (stable ecosystem; Tauri 2.x releases frequently but API is stable; re-verify patch versions at build time)
