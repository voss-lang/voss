# Phase A1: voss-app Tauri Shell - Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 18 (new/modified)
**Analogs found:** 4 / 18 (Rust crate patterns only — all frontend files are greenfield)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `Cargo.toml` (root, members edit) | config | batch | self (existing file, surgical edit) | exact |
| `pnpm-workspace.yaml` (root, new) | config | — | greenfield, no analog | none |
| `package.json` (root, new) | config | — | greenfield, no analog | none |
| `crates/voss-app-core/Cargo.toml` | config | — | `crates/voss-bridge/Cargo.toml` | role-match |
| `crates/voss-app-core/src/lib.rs` | utility | — | `crates/voss-bridge/src/lib.rs` | role-match |
| `apps/voss-app/src-tauri/Cargo.toml` | config | — | `crates/voss-cli/Cargo.toml` | role-match |
| `apps/voss-app/src-tauri/build.rs` | config | — | greenfield, no analog | none |
| `apps/voss-app/src-tauri/src/main.rs` | utility | request-response | `crates/voss-cli/src/main.rs` | role-match |
| `apps/voss-app/src-tauri/src/lib.rs` | service | request-response | `crates/voss-auth/src/file_store.rs` | partial (file-I/O + serde pattern) |
| `apps/voss-app/src-tauri/tauri.conf.json` | config | — | greenfield, no analog | none |
| `apps/voss-app/src-tauri/capabilities/default.json` | config | — | greenfield, no analog | none |
| `apps/voss-app/vite.config.ts` | config | — | greenfield, no analog | none |
| `apps/voss-app/index.html` | config | — | greenfield, no analog | none |
| `apps/voss-app/package.json` | config | — | greenfield, no analog | none |
| `apps/voss-app/src/index.css` | utility | — | greenfield, no analog | none |
| `apps/voss-app/src/styles/variant-b.css` | utility | — | greenfield, no analog | none |
| `apps/voss-app/src/index.tsx` | component | request-response | greenfield, no analog | none |
| `apps/voss-app/src/App.tsx` | component | request-response | greenfield, no analog | none |
| `apps/voss-app/src/theme/applyTheme.ts` | utility | transform | greenfield, no analog | none |
| `apps/voss-app/src/components/titlebar/Titlebar.tsx` | component | event-driven | greenfield, no analog | none |
| `apps/voss-app/src/components/titlebar/WindowControls.tsx` | component | event-driven | greenfield, no analog | none |
| `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx` | component | event-driven | greenfield, no analog | none |

---

## Pattern Assignments

### `Cargo.toml` (root — surgical members edit)

**Analog:** self — the existing file is the template. One surgical change: append two new member strings to `[workspace].members`.

**Existing members block** (`/Users/benjaminmarks/Projects/Voss/Cargo.toml` lines 1-11):
```toml
[workspace]
resolver = "2"
members = [
    "crates/voss-cli",
    "crates/voss-agent",
    "crates/voss-providers",
    "crates/voss-auth",
    "crates/voss-tools",
    "crates/voss-render",
    "crates/voss-bridge",
]
```

**Change:** append exactly two new members — touch nothing else:
```toml
    "crates/voss-app-core",       # NEW — A1
    "apps/voss-app/src-tauri",    # NEW — A1
```

**Workspace package metadata** (`/Users/benjaminmarks/Projects/Voss/Cargo.toml` lines 13-20) — new crates inherit all of this:
```toml
[workspace.package]
version = "0.1.0"
edition = "2021"
rust-version = "1.75"
license = "MIT"
description = "Voss compiler and agent CLI"
repository = "https://github.com/bm9797/Voss"
homepage = "https://github.com/bm9797/Voss"
```

**Workspace dependencies already present** (`/Users/benjaminmarks/Projects/Voss/Cargo.toml` lines 27-56) — `src-tauri/Cargo.toml` should inherit these via `{ workspace = true }`:
- `serde = { version = "1", features = ["derive"] }` — use `{ workspace = true }`
- `serde_json = "1"` — use `{ workspace = true }`
- `dirs = "5"` — use `{ workspace = true }`

No new `[workspace.dependencies]` entries needed.

---

### `crates/voss-app-core/Cargo.toml` (config)

**Analog:** `crates/voss-bridge/Cargo.toml` — minimal library crate with no binary, workspace inheritance, no deps beyond what the crate needs.

**Pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-bridge/Cargo.toml` lines 1-10):
```toml
[package]
name = "voss-bridge"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true

[lib]
path = "src/lib.rs"
```

**Apply as:** replace `voss-bridge` with `voss-app-core`, add explicit `name` under `[lib]`, and omit `[dependencies]` entirely (placeholder crate has none):
```toml
[package]
name    = "voss-app-core"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
# placeholder — populated in A2+ (PTY, layout, settings, event bus)

[lib]
name = "voss_app_core"
path = "src/lib.rs"
```

---

### `crates/voss-app-core/src/lib.rs` (utility — placeholder)

**Analog:** `crates/voss-bridge/src/lib.rs` — minimal lib.rs with module declarations and a version function. The `voss-app-core` version is even simpler: just a placeholder comment.

**Bridge pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-bridge/src/lib.rs` lines 1-11):
```rust
//! voss-bridge — LSP-framed JSON-RPC over stdio to the Python bridge server.

pub mod framing;
pub mod jsonrpc;

pub use framing::{read_frame, write_frame};
pub use jsonrpc::PyBridge;

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
```

**Apply as:** strip all content, keep only a doc comment and one-line placeholder:
```rust
//! voss-app-core — placeholder crate. Populated in A2+ (PTY, layout, settings, event bus).
```

---

### `apps/voss-app/src-tauri/Cargo.toml` (config)

**Analog:** `crates/voss-cli/Cargo.toml` — the most complex Cargo.toml in the workspace; shows workspace inheritance pattern for a binary crate with path deps.

**Workspace inheritance pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-cli/Cargo.toml` lines 1-9):
```toml
[package]
name = "voss-cli"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
description.workspace = true
repository.workspace = true
homepage.workspace = true
```

**Path dependency pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-cli/Cargo.toml` line 19):
```toml
voss-agent = { path = "../voss-agent" }
```

**Apply as** (Tauri-specific additions — not in any analog, use RESEARCH.md values):
```toml
[package]
name    = "voss-app"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true

[lib]
name       = "voss_app_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[build-dependencies]
tauri-build = { version = "2.6.2", features = [] }

[dependencies]
tauri         = { version = "2.11.2", features = [] }
serde         = { workspace = true, features = ["derive"] }
serde_json    = { workspace = true }
dirs          = { workspace = true }
voss-app-core = { path = "../../../crates/voss-app-core" }
```

---

### `apps/voss-app/src-tauri/src/main.rs` (utility — entry point)

**Analog:** `crates/voss-cli/src/main.rs` — one-line entry delegating to lib::run().

**Pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-cli/src/main.rs` lines 1-4):
```rust
#[tokio::main]
async fn main() -> std::process::ExitCode {
    voss_cli::run(std::env::args_os()).await
}
```

**Apply as** (Tauri pattern, mobile entry point macro added, no async):
```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    voss_app_lib::run()
}
```

---

### `apps/voss-app/src-tauri/src/lib.rs` (service — Tauri command + file I/O)

**Analog:** `crates/voss-auth/src/file_store.rs` — the closest in-repo pattern for reading a config JSON file from a home-dir path with `dirs::home_dir()`, `std::fs::read_to_string`, and `serde_json` deserialization with graceful `Option` fallback.

**Home-dir path construction pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-auth/src/file_store.rs` lines 12-14):
```rust
fn home() -> PathBuf {
    dirs::home_dir().unwrap_or_default()
}
```

**File read + serde_json parse pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-auth/src/file_store.rs` lines 24-39):
```rust
pub fn read_anthropic() -> Option<AnthropicOAuthCreds> {
    let bytes = std::fs::read(anthropic_path()).ok()?;
    let blob: serde_json::Value = serde_json::from_slice(&bytes).ok()?;
    // ... field extraction
}
```

**Serde struct with optional fields pattern** (`/Users/benjaminmarks/Projects/Voss/crates/voss-auth/src/file_store.rs` lines 42-63 — write side, shows the JSON shape pattern):
```rust
let bytes = serde_json::to_vec_pretty(&blob)?;
std::fs::write(&path, bytes)?;
```

**Error handling style** — the codebase consistently uses `.ok()?` for file read failures and `.map_err(|e| format!("...{e}"))` for recoverable errors that should bubble. `file_store.rs` uses the `Option` `?`-chain; the Tauri command variant uses `Result<T, String>`.

**Apply as** (combine home_dir pattern with RESEARCH.md Pattern 3 command shape):
```rust
use std::collections::HashMap;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize, Default)]
struct SettingsFile {
    theme: Option<HashMap<String, String>>,
}

fn settings_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("settings.json")
    // NOTE: use home_dir().join(".config"), NOT dirs::config_dir()
    // dirs::config_dir() on macOS returns ~/Library/Application Support, not ~/.config
    // See RESEARCH.md Pitfall 8 and UI-SPEC.md Theme Override System Contract
}

#[tauri::command]
fn get_theme_overrides() -> HashMap<String, String> {
    let path = settings_path();
    if !path.exists() {
        return HashMap::new();
    }
    let raw = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] failed to read settings: {e}");
            return HashMap::new();
        }
    };
    let settings: SettingsFile = match serde_json::from_str(&raw) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("[voss-app] failed to parse settings: {e}");
            return HashMap::new();
        }
    };
    settings.theme.unwrap_or_default()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_theme_overrides])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

Key differences from RESEARCH.md Pattern 3: error handling swallows errors to `eprintln!` and returns empty map (matches UI-SPEC.md Copywriting Contract: "error must be silently swallowed and logged to console only") rather than propagating `Result<_, String>`.

---

### `apps/voss-app/src-tauri/build.rs` (config — Tauri build script)

**Analog:** None in codebase. Greenfield. Use RESEARCH.md standard boilerplate.

```rust
fn main() {
    tauri_build::build()
}
```

---

### `apps/voss-app/src-tauri/tauri.conf.json` (config)

**Analog:** None in codebase. Greenfield. Use RESEARCH.md Pattern 4 values exactly. Key fields from UI-SPEC.md Window Architecture Contract:

```json
{
  "productName": "Voss ADE",
  "identifier": "app.voss-ade",
  "version": "0.1.0",
  "build": {
    "beforeDevCommand": "pnpm dev",
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
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ],
    "macOS": {
      "signingIdentity": null
    }
  }
}
```

---

### `apps/voss-app/src-tauri/capabilities/default.json` (config)

**Analog:** None in codebase. Greenfield. Use RESEARCH.md Pattern 2 + UI-SPEC.md Window Controls Contract permissions list exactly:

```json
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

---

### `apps/voss-app/vite.config.ts` (config)

**Analog:** None in codebase. Greenfield. Use RESEARCH.md Pattern 4 exactly:

```typescript
import { defineConfig } from 'vite';
import solidPlugin from 'vite-plugin-solid';
import tailwindcss from '@tailwindcss/vite';

const host = process.env.TAURI_DEV_HOST;

export default defineConfig({
  plugins: [tailwindcss(), solidPlugin()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,   // fail fast on port conflict — see RESEARCH Pitfall 3
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

Note: `tailwindcss()` must come BEFORE `solidPlugin()` in the plugins array.

---

### `apps/voss-app/src/styles/variant-b.css` (utility — CSS token definitions)

**Analog:** None in codebase. Greenfield. Use UI-SPEC.md Color Token Table + RESEARCH.md Pattern 1 values verbatim. All values sourced from `.planning/sketches/themes/default.css` and `.planning/sketches/001-voss-grid-shell/index.html`.

```css
/* Variant B token definitions — single source of truth (CONTEXT D-01, D-02) */
/* DO NOT use raw hex values in component code — use these CSS vars only     */

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

  /* Accent palette — reserved for specific roles (see UI-SPEC.md) */
  --accent-green:   #6fd28f;
  --accent-amber:   #e8b86c;
  --accent-red:     #e87b7b;
  --accent-cyan:    #6cc7d4;
  --accent-magenta: #c084d4;
  --accent-blue:    #7aa2ff;

  /* Role-semantic colors */
  --user-msg:  #8ab4ff;
  --assistant: #b8c0d0;
  --tool:      #c084d4;
  --reviewer:  #e8b86c;

  /* Typography — Variant B: mono everywhere */
  --font-mono: "JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace;
  --font-ui:   "Inter", -apple-system, "SF Pro Text", system-ui, sans-serif;

  /* Radius — Variant B: 0 everywhere (exceptions: traffic-light circles 50%, scrollbar thumb 4px) */
  --radius-none: 0px;

  /* Titlebar */
  --titlebar-height: 22px;

  /* Scrollbar */
  --scrollbar-width: 8px;
}
```

---

### `apps/voss-app/src/index.css` (utility — Tailwind entry + theme mapping)

**Analog:** None in codebase. Greenfield. Use RESEARCH.md Pattern 1 + UI-SPEC.md CSS Variable to Tailwind Mapping Contract. The `@theme inline` block is the exact contract from UI-SPEC.md lines 196-227.

```css
@import "tailwindcss";
@import "./styles/variant-b.css";

/* Map tokens into Tailwind v4 utilities — @theme inline embeds var reference directly */
/* Generates: bg-bg-0, text-fg-0, border-border, text-accent-green, font-mono, etc.  */
@theme inline {
  /* Backgrounds */
  --color-bg-0:          var(--bg-0);
  --color-bg-1:          var(--bg-1);
  --color-bg-2:          var(--bg-2);
  --color-bg-3:          var(--bg-3);
  /* Borders */
  --color-border:        var(--border);
  --color-border-bright: var(--border-bright);
  /* Focus */
  --color-focus:         var(--focus);
  /* Foreground */
  --color-fg-0:          var(--fg-0);
  --color-fg-1:          var(--fg-1);
  --color-fg-2:          var(--fg-2);
  --color-fg-3:          var(--fg-3);
  /* Accents */
  --color-accent-green:   var(--accent-green);
  --color-accent-amber:   var(--accent-amber);
  --color-accent-red:     var(--accent-red);
  --color-accent-cyan:    var(--accent-cyan);
  --color-accent-magenta: var(--accent-magenta);
  --color-accent-blue:    var(--accent-blue);
  /* Role semantic */
  --color-user-msg:  var(--user-msg);
  --color-tool:      var(--tool);
  --color-reviewer:  var(--reviewer);
  /* Fonts */
  --font-mono: var(--font-mono);
  --font-ui:   var(--font-ui);
}

/* Global base styles */
*, *::before, *::after {
  box-sizing: border-box;
  border-radius: 0;           /* Variant B: 0 radius everywhere */
  border-width: 0;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: var(--bg-0);
  color: var(--fg-0);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  user-select: none;          /* terminal apps: no text selection on chrome */
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bg-3); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-bright); }
```

---

### `apps/voss-app/src/index.tsx` (component — Solid entry point + onMount invoke)

**Analog:** None in codebase. Greenfield. Use RESEARCH.md Pattern 3 (Solid side) + RESEARCH.md Pattern 4 (`pnpm-workspace.yaml` structure context):

```tsx
import { render } from 'solid-js/web';
import { invoke } from '@tauri-apps/api/core';
import App from './App';
import './index.css';

const root = document.getElementById('root');
if (!root) throw new Error('No #root element');

// Apply theme overrides from settings.json before first render
// invoke resolves fast (sync file read on Rust side); if settings absent, returns {}
invoke<Record<string, string>>('get_theme_overrides')
  .then((overrides) => {
    for (const [key, val] of Object.entries(overrides)) {
      document.documentElement.style.setProperty(key, val);
    }
  })
  .catch((e) => {
    // Silently swallow — fall back to pure Variant B (see UI-SPEC Copywriting Contract)
    console.error('[voss-app] theme override error:', e);
  })
  .finally(() => {
    render(() => <App />, root);
  });
```

Note: invoke before render (not onMount) eliminates the theme flash described in RESEARCH.md Pitfall 6, while keeping the pattern simple for A1 scope.

---

### `apps/voss-app/src/App.tsx` (component — root layout)

**Analog:** None in codebase. Greenfield.

```tsx
import Titlebar from './components/titlebar/Titlebar';

export default function App() {
  return (
    <div
      style={{
        display: 'flex',
        'flex-direction': 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
      }}
    >
      <Titlebar />
      {/* Body — intentionally empty in A1. Grid and PTY panes land in A2/A3. */}
      <div style={{ flex: '1', background: 'var(--bg-0)' }} />
    </div>
  );
}
```

---

### `apps/voss-app/src/theme/applyTheme.ts` (utility — CSS var applicator)

**Analog:** None in codebase. Greenfield. Extracted as a standalone utility so future callers (A8 settings UI) can reuse it.

```typescript
/**
 * Apply CSS variable overrides to :root.
 * Called once on boot from index.tsx (from get_theme_overrides result).
 * Called again by A8 settings UI on runtime theme change.
 */
export function applyThemeOverrides(overrides: Record<string, string>): void {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(overrides)) {
    root.style.setProperty(key, value);
  }
}
```

---

### `apps/voss-app/src/components/titlebar/Titlebar.tsx` (component — custom titlebar)

**Analog:** None in codebase. Greenfield. Pattern from RESEARCH.md Pattern 2 + UI-SPEC.md Titlebar Contract.

Critical layout rule from UI-SPEC.md: `data-tauri-drag-region` on SPACER divs only — NOT on the outer titlebar container. Window control buttons and preset switcher are siblings to drag regions, not children.

```tsx
import WindowControls from './WindowControls';
import PresetSwitcher from './PresetSwitcher';

export default function Titlebar() {
  return (
    <div
      style={{
        display: 'flex',
        'align-items': 'center',
        height: 'var(--titlebar-height)',    /* 22px — locked by CONTEXT D-02 */
        'flex-shrink': '0',
        background: 'var(--bg-0)',
        'border-bottom': '1px solid var(--border)',
        overflow: 'hidden',
      }}
    >
      {/* Window controls — platform-switched (mac: traffic lights; others: stub) */}
      <WindowControls />

      {/* Left drag spacer — fills space between controls and project name */}
      {/* data-tauri-drag-region on spacer only; buttons are NOT children */}
      <div data-tauri-drag-region style={{ flex: '1' }} />

      {/* Project name placeholder — shows "Voss ADE" until A5 opens a project */}
      <div
        style={{
          'flex-shrink': '0',
          color: 'var(--fg-1)',
          'font-size': '11px',
          'font-family': 'var(--font-mono)',
          'font-weight': '400',
          'pointer-events': 'none',   /* part of drag surface visually */
        }}
      >
        Voss ADE
      </div>

      {/* Right drag spacer */}
      <div data-tauri-drag-region style={{ flex: '1' }} />

      {/* Preset switcher — visual only in A1 */}
      <PresetSwitcher />
    </div>
  );
}
```

---

### `apps/voss-app/src/components/titlebar/WindowControls.tsx` (component — platform-switched window controls)

**Analog:** None in codebase. Greenfield. Pattern from RESEARCH.md Pattern 2 + UI-SPEC.md Window Controls Contract.

```tsx
import { createSignal, onMount, Show } from 'solid-js';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { platform } from '@tauri-apps/plugin-os';

// macOS traffic-light colors — hardcoded per OS convention (NOT token vars)
// Source: UI-SPEC.md "macOS Traffic-Light Colors" table
const TRAFFIC_CLOSE    = '#ff5f57';
const TRAFFIC_MINIMIZE = '#febc2e';
const TRAFFIC_ZOOM     = '#28c840';

function MacTrafficLights() {
  const win = getCurrentWindow();
  const [isFullscreen, setIsFullscreen] = createSignal(false);

  onMount(async () => {
    setIsFullscreen(await win.isFullscreen());
  });

  const handleZoom = async () => {
    const next = !isFullscreen();
    setIsFullscreen(next);
    await win.setFullscreen(next);
  };

  return (
    // gap: 6px — named spacing exception (UI-SPEC Dimension 5); padding-left: 12px
    <div
      style={{
        display: 'flex',
        gap: '6px',
        'align-items': 'center',
        'padding-left': '12px',
        'flex-shrink': '0',
      }}
    >
      <button
        title="close"
        onClick={() => win.close()}
        style={{
          width: '12px', height: '12px',
          'border-radius': '50%',   /* exception: circles only */
          background: TRAFFIC_CLOSE,
          border: 'none', cursor: 'pointer', padding: '0',
        }}
      />
      <button
        title="minimize"
        onClick={() => win.minimize()}
        style={{
          width: '12px', height: '12px',
          'border-radius': '50%',
          background: TRAFFIC_MINIMIZE,
          border: 'none', cursor: 'pointer', padding: '0',
        }}
      />
      <button
        title="zoom"
        onClick={handleZoom}
        style={{
          width: '12px', height: '12px',
          'border-radius': '50%',
          background: TRAFFIC_ZOOM,
          border: 'none', cursor: 'pointer', padding: '0',
        }}
      />
    </div>
  );
}

// Stub for linux/win — renders nothing. Replaced in A10 soak / CI matrix (CONTEXT D-04).
function StubControls() {
  return null;
}

export default function WindowControls() {
  const [os, setOs] = createSignal('');
  onMount(async () => {
    try {
      setOs(await platform());
    } catch {
      setOs('unknown');
    }
  });

  return (
    <Show when={os() === 'macos'} fallback={<StubControls />}>
      <MacTrafficLights />
    </Show>
  );
}
```

Note: `@tauri-apps/plugin-os` must be added as a dependency and registered with the Tauri builder. Planner should add `tauri-plugin-os` to `src-tauri/Cargo.toml` and call `.plugin(tauri_plugin_os::init())` in `lib.rs`.

---

### `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx` (component — visual-only layout switcher)

**Analog:** None in codebase. Greenfield.

```tsx
import { createSignal } from 'solid-js';
import { For } from 'solid-js';

const PRESETS = ['fanout', 'pipeline', 'swarm', 'watchers'] as const;
type Preset = typeof PRESETS[number];

export default function PresetSwitcher() {
  // Default active: 'pipeline' — matches sketch default (UI-SPEC Titlebar Contract)
  const [active, setActive] = createSignal<Preset>('pipeline');

  return (
    // Visual only — clicking updates state only, no layout geometry changes (CONTEXT D-04)
    <div
      style={{
        display: 'flex',
        border: '1px solid var(--border)',
        overflow: 'hidden',
        'flex-shrink': '0',
        'margin-right': '10px',  /* base spacing — header horizontal padding */
      }}
    >
      <For each={PRESETS}>
        {(preset) => (
          <button
            onClick={() => setActive(preset)}
            style={{
              background: active() === preset ? 'var(--focus)' : 'transparent',
              color: active() === preset ? 'white' : 'var(--fg-2)',
              border: 'none',
              'border-right': preset !== 'watchers' ? '1px solid var(--border)' : 'none',
              padding: '4px 10px',          /* base spacing (10px) named exception */
              'font-family': 'var(--font-mono)',
              'font-size': '11px',
              cursor: 'pointer',
              'line-height': '1',
            }}
            // Hover handled inline — Solid components don't have CSS modules
          >
            {preset}
          </button>
        )}
      </For>
    </div>
  );
}
```

---

### `apps/voss-app/package.json` (config — app package)

**Analog:** None in codebase (no JS packages exist yet). Greenfield. Use RESEARCH.md Pattern 4:

```json
{
  "name": "voss-app",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev":   "vite",
    "build": "tsc && vite build",
    "tauri": "tauri"
  },
  "dependencies": {
    "@tauri-apps/api": "2.11.0",
    "@tauri-apps/plugin-os": "2.x",
    "solid-js": "1.9.13"
  },
  "devDependencies": {
    "@tauri-apps/cli": "2.11.2",
    "@tailwindcss/vite": "4.3.0",
    "tailwindcss": "4.3.0",
    "typescript": "^5.0.0",
    "vite": "8.0.13",
    "vite-plugin-solid": "2.11.12"
  }
}
```

---

### `pnpm-workspace.yaml` (root, new) and root `package.json` (new)

**Analog:** None in codebase. Greenfield. Use RESEARCH.md Pattern 4 values verbatim.

`pnpm-workspace.yaml`:
```yaml
packages:
  - "apps/*"
```

Root `package.json`:
```json
{
  "name": "voss-monorepo",
  "version": "0.1.0",
  "private": true,
  "packageManager": "pnpm@10.0.0"
}
```

---

## Shared Patterns

### Cargo Workspace Inheritance (Rust files)
**Source:** `crates/voss-cli/Cargo.toml`, `crates/voss-bridge/Cargo.toml`
**Apply to:** `crates/voss-app-core/Cargo.toml`, `apps/voss-app/src-tauri/Cargo.toml`

All crates in the workspace inherit `version`, `edition`, `rust-version`, `license` from `[workspace.package]`. Pattern is established across all 7 existing crates. No crate declares these values independently.

```toml
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
```

Shared dependencies (`serde`, `serde_json`, `dirs`) are already in `[workspace.dependencies]` — always use `{ workspace = true }` for these.

### File Read + serde_json Deserialize (Rust)
**Source:** `crates/voss-auth/src/file_store.rs` lines 12-39
**Apply to:** `apps/voss-app/src-tauri/src/lib.rs`

The codebase pattern for reading a user config file:
1. Construct path using `dirs::home_dir().unwrap_or_default()` (not `dirs::config_dir()`)
2. `std::fs::read_to_string(&path).ok()` or `std::fs::read(&path).ok()?` for silent failure
3. `serde_json::from_str(&raw)` / `serde_json::from_slice(&bytes)` for parsing
4. Use `Option` chains (`?`) for functions returning `Option`, `map_err` for `Result`-returning commands

**Critical divergence for `src/lib.rs`:** The Tauri command swallows errors and returns `HashMap::new()` (not `None`) because UI-SPEC.md requires silent fallback to Variant B — no error surfaces to the user.

### Error Handling Style (Rust)
**Source:** All crates — consistent pattern
**Apply to:** `apps/voss-app/src-tauri/src/lib.rs`

The codebase uses:
- `eprintln!("message: {e}")` for non-fatal errors (no tracing subscriber needed in A1 — this is a shell, not a server)
- `.ok()?` / `.ok().unwrap_or_default()` for "silent on failure" paths
- No `panic!` in production code paths — graceful degradation

### CSS Variables as Single Source of Truth (Frontend)
**Source:** RESEARCH.md Pattern 1 + UI-SPEC.md Token System Architecture
**Apply to:** All `*.tsx` component files

Components MUST use Tailwind utility classes (`bg-bg-0`, `text-fg-0`) or `var(--token)` in inline styles for one-off values. Components MUST NOT use raw hex values (`#0a0b0e`). The only exceptions are the macOS traffic-light colors (`#ff5f57`, `#febc2e`, `#28c840`) which are hardcoded OS-convention values, not theme tokens.

### `data-tauri-drag-region` Placement (Frontend)
**Source:** RESEARCH.md Pitfall 1 + UI-SPEC.md Titlebar Contract
**Apply to:** `Titlebar.tsx`

`data-tauri-drag-region` must appear ONLY on the spacer `<div>` elements that fill empty areas. Window controls and PresetSwitcher are siblings to drag regions, never children. This is a mandatory structural constraint — violation causes button clicks to also drag the window.

---

## No Analog Found

All files below are greenfield. The planner should reference RESEARCH.md code examples and UI-SPEC.md contracts for these (cited in the Pattern Assignments above).

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pnpm-workspace.yaml` | config | — | No JS/pnpm workspace exists yet in repo |
| `package.json` (root) | config | — | No JS/pnpm workspace exists yet in repo |
| `apps/voss-app/src-tauri/build.rs` | config | — | No Tauri crates exist in repo |
| `apps/voss-app/src-tauri/tauri.conf.json` | config | — | No Tauri crates exist in repo |
| `apps/voss-app/src-tauri/capabilities/default.json` | config | — | No Tauri crates exist in repo |
| `apps/voss-app/vite.config.ts` | config | — | No Vite projects exist in repo |
| `apps/voss-app/index.html` | config | — | No frontend exists in repo |
| `apps/voss-app/package.json` | config | — | No JS packages exist in repo |
| `apps/voss-app/src/index.css` | utility | — | No CSS exists in repo |
| `apps/voss-app/src/styles/variant-b.css` | utility | — | No CSS exists in repo |
| `apps/voss-app/src/index.tsx` | component | request-response | No Solid/TS/React code exists in repo |
| `apps/voss-app/src/App.tsx` | component | request-response | No frontend components exist in repo |
| `apps/voss-app/src/theme/applyTheme.ts` | utility | transform | No frontend utilities exist in repo |
| `apps/voss-app/src/components/titlebar/Titlebar.tsx` | component | event-driven | No frontend components exist in repo |
| `apps/voss-app/src/components/titlebar/WindowControls.tsx` | component | event-driven | No frontend components exist in repo |
| `apps/voss-app/src/components/titlebar/PresetSwitcher.tsx` | component | event-driven | No frontend components exist in repo |

---

## Metadata

**Analog search scope:** `crates/` (all 7 frozen spike crates — voss-cli, voss-agent, voss-providers, voss-auth, voss-tools, voss-render, voss-bridge); `apps/voss-app/` (checked — contains only CONCEPT.md + FEATURES.md, no code)
**Files scanned:** 15 Rust source files + 8 Cargo.toml files
**Pattern extraction date:** 2026-05-17
**Note:** This phase is ~90% greenfield. The Rust-side patterns (file read, serde, workspace config, lib.rs structure, main.rs delegation) map cleanly to existing crate analogs. All frontend files (Solid, Tailwind, Vite) are fully greenfield with no in-repo analogs — RESEARCH.md code examples serve as the reference for those.
