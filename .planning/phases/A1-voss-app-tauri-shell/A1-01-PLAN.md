---
phase: A1-voss-app-tauri-shell
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - Cargo.toml
  - pnpm-workspace.yaml
  - package.json
  - crates/voss-app-core/Cargo.toml
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/package.json
  - apps/voss-app/index.html
  - apps/voss-app/vite.config.ts
  - apps/voss-app/tsconfig.json
  - apps/voss-app/src/index.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src-tauri/Cargo.toml
  - apps/voss-app/src-tauri/build.rs
  - apps/voss-app/src-tauri/tauri.conf.json
  - apps/voss-app/src-tauri/capabilities/default.json
  - apps/voss-app/src-tauri/src/main.rs
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src-tauri/icons/
autonomous: false
requirements: [SHL-01, SHL-06]
must_haves:
  truths:
    - "`cargo metadata` lists both `voss-app-core` and `voss-app` as workspace members"
    - "`pnpm install` at repo root resolves the `apps/voss-app` workspace member with no errors"
    - "`pnpm tauri dev` launches a borderless window titled 'Voss ADE' showing a solid #0a0b0e body"
    - "Tauri crate and CLI are pinned to a single 2.x version (no `^`/`~` range)"
  artifacts:
    - path: "Cargo.toml"
      provides: "Root workspace with voss-app-core + voss-app/src-tauri members"
      contains: "crates/voss-app-core"
    - path: "pnpm-workspace.yaml"
      provides: "JS monorepo root declaring apps/* members"
      contains: "apps/*"
    - path: "crates/voss-app-core/src/lib.rs"
      provides: "Empty placeholder crate compiling clean"
      min_lines: 1
    - path: "apps/voss-app/src-tauri/tauri.conf.json"
      provides: "Tauri window config: decorations false, productName/title Voss ADE"
      contains: "Voss ADE"
    - path: "apps/voss-app/src-tauri/Cargo.toml"
      provides: "Pinned tauri 2.x dependency + voss-app-core path dep"
      contains: "voss-app-core"
  key_links:
    - from: "Cargo.toml"
      to: "crates/voss-app-core"
      via: "workspace member entry"
      pattern: "crates/voss-app-core"
    - from: "apps/voss-app/src-tauri/Cargo.toml"
      to: "crates/voss-app-core"
      via: "path dependency (wired, unused in A1)"
      pattern: "voss-app-core.*path"
    - from: "apps/voss-app/src-tauri/tauri.conf.json"
      to: "apps/voss-app (Vite)"
      via: "beforeDevCommand / devUrl"
      pattern: "beforeDevCommand"
---

<objective>
Bootstrap the `apps/voss-app/` Tauri 2 + SolidJS + Tailwind v4 desktop scaffold inside the existing Cargo + pnpm monorepo. Wire the JS workspace root, add the empty `crates/voss-app-core` placeholder crate, register both new Rust members in the root Cargo workspace, and produce a runnable empty "Voss ADE" window.

Purpose: Every later A1 plan (tokens, theme seam, titlebar, build smoke) depends on this scaffold existing and `pnpm tauri dev` launching. This plan delivers the foundation and pins the Tauri version (SHL-01) and ship-name strings (SHL-06).

Output: A runnable empty Tauri window titled "Voss ADE", a wired Cargo + pnpm monorepo, pinned dependency versions.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md
@.planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md
@.planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md
@.planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md

<interfaces>
<!-- Existing root Cargo workspace — surgical edit only. Source: /Users/benjaminmarks/Projects/Voss/Cargo.toml lines 1-20 -->

Root Cargo.toml [workspace].members (existing, 7 entries):
  crates/voss-cli, crates/voss-agent, crates/voss-providers,
  crates/voss-auth, crates/voss-tools, crates/voss-render, crates/voss-bridge

Root [workspace.package]: version = "0.1.0", edition = "2021",
  rust-version = "1.75", license = "MIT" — new crates inherit ALL of these.

Root [workspace.dependencies] already has: serde (with derive), serde_json,
  dirs — src-tauri/Cargo.toml MUST inherit these via { workspace = true },
  do NOT add new [workspace.dependencies] entries.

Toolchain confirmed present (no Wave 0 setup needed): Apple Silicon arm64,
  rustc 1.95 nightly, aarch64-apple-darwin target installed, pnpm 10.32.1,
  node v22.22. Do NOT add a `rustup target add` step — target is present.
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 0: Package legitimacy gate (npm install authorization)</name>
  <read_first>
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("## Package Legitimacy Audit" — all 8 packages marked [ASSUMED], slopcheck was unavailable)
  </read_first>
  <what-built>
    Nothing yet — this gate runs BEFORE any `pnpm create tauri-app` / `pnpm add` / `cargo` fetch in Task 1. RESEARCH.md Package Legitimacy Audit lists 8 npm packages all tagged [ASSUMED] (slopcheck unavailable at research time): @tauri-apps/cli, @tauri-apps/api, create-tauri-app, solid-js, vite-plugin-solid, vite, tailwindcss, @tailwindcss/vite. All are from official orgs (tauri-apps, solidjs, vitejs, tailwindlabs) but [ASSUMED] packages require a blocking human-verify before first install per the package legitimacy protocol.
  </what-built>
  <how-to-verify>
    1. Open npmjs.com and confirm each package belongs to its official org and has a multi-year history:
       - npmjs.com/package/@tauri-apps/cli (org: tauri-apps)
       - npmjs.com/package/@tauri-apps/api (org: tauri-apps)
       - npmjs.com/package/create-tauri-app (org: tauri-apps)
       - npmjs.com/package/solid-js (org: solidjs)
       - npmjs.com/package/vite-plugin-solid (org: solidjs)
       - npmjs.com/package/vite (org: vitejs)
       - npmjs.com/package/tailwindcss (org: tailwindlabs)
       - npmjs.com/package/@tailwindcss/vite (org: tailwindlabs)
    2. Confirm crates.io shows `tauri` 2.11.2 and `tauri-build` 2.6.2 from the tauri-apps org.
    3. Approve to authorize Task 1 to run `pnpm create tauri-app` + `pnpm add` + `cargo fetch`.
  </how-to-verify>
  <resume-signal>Type "approved" to authorize package installs, or name any package to remove/replace.</resume-signal>
  <acceptance_criteria>
    - Human has reviewed all 8 npm packages + 2 crates against their official registry pages
    - Explicit "approved" recorded before Task 1 runs any install command
    - This checkpoint is NOT auto-approvable (ignore workflow.auto_advance — [ASSUMED] gate)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 1: Scaffold Tauri+Solid+Tailwind app and wire the Cargo+pnpm monorepo</name>
  <files>
    Cargo.toml, pnpm-workspace.yaml, package.json,
    crates/voss-app-core/Cargo.toml, crates/voss-app-core/src/lib.rs,
    apps/voss-app/package.json, apps/voss-app/index.html,
    apps/voss-app/vite.config.ts, apps/voss-app/tsconfig.json,
    apps/voss-app/src/index.tsx, apps/voss-app/src/App.tsx,
    apps/voss-app/src-tauri/Cargo.toml, apps/voss-app/src-tauri/build.rs,
    apps/voss-app/src-tauri/tauri.conf.json,
    apps/voss-app/src-tauri/capabilities/default.json,
    apps/voss-app/src-tauri/src/main.rs, apps/voss-app/src-tauri/src/lib.rs,
    apps/voss-app/src-tauri/icons/
  </files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/Cargo.toml (lines 1-20 — the file being surgically edited; existing members + [workspace.package])
    - .planning/phases/A1-voss-app-tauri-shell/A1-PATTERNS.md ("Cargo.toml (root — surgical members edit)", "crates/voss-app-core/Cargo.toml", "crates/voss-app-core/src/lib.rs", "apps/voss-app/src-tauri/Cargo.toml", "apps/voss-app/src-tauri/src/main.rs", "apps/voss-app/src-tauri/build.rs", "apps/voss-app/src-tauri/tauri.conf.json", "apps/voss-app/src-tauri/capabilities/default.json", "apps/voss-app/vite.config.ts", "apps/voss-app/package.json", "pnpm-workspace.yaml and root package.json", "apps/voss-app/src/index.tsx", "apps/voss-app/src/App.tsx" sections — all carry the exact file bodies to write)
    - /Users/benjaminmarks/Projects/Voss/crates/voss-bridge/Cargo.toml (analog for voss-app-core/Cargo.toml — minimal lib crate, workspace inheritance)
    - /Users/benjaminmarks/Projects/Voss/crates/voss-cli/src/main.rs (analog for src-tauri/src/main.rs — one-line delegation entry)
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("## Standard Stack", "Pattern 4: Monorepo Wiring", "## Installation", "Pitfall 4: Cargo Workspace Resolver", "Pitfall 7: missing icons")
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Window Architecture Contract", "Empty Body Contract", "Copywriting Contract")
  </read_first>
  <action>
    Scaffold the app in `apps/voss-app/` (NOT at repo root — RESEARCH primary recommendation). Run `pnpm create tauri-app@latest . --template solid-ts --manager pnpm` inside `apps/voss-app/` (project name `.`), declining any Tailwind prompt (Tailwind v4 added manually next). Then `pnpm add -D tailwindcss@4.3.0 @tailwindcss/vite@4.3.0` and `pnpm add @tauri-apps/plugin-os` (needed by the Wave-3 platform gate; register `tauri-plugin-os` in `src-tauri/Cargo.toml` and `.plugin(tauri_plugin_os::init())` in `lib.rs`).

    Pin exact versions per A1-RESEARCH.md "## Standard Stack": tauri crate `2.11.2`, tauri-build `2.6.2`, @tauri-apps/cli `2.11.2`, @tauri-apps/api `2.11.0`, solid-js `1.9.13`, vite-plugin-solid `2.11.12`, vite `8.0.13`, tailwindcss `4.3.0`, @tailwindcss/vite `4.3.0`. No `^`/`~` ranges on the Tauri crate, tauri-build, @tauri-apps/cli, or @tauri-apps/api (SHL-01 = pinned). Delete any `tailwind.config.js` the scaffold emits (Tailwind v4 uses `@theme inline` in CSS — RESEARCH anti-pattern).

    Surgically edit root `Cargo.toml`: append exactly `"crates/voss-app-core"` and `"apps/voss-app/src-tauri"` to `[workspace].members` (per A1-PATTERNS.md "Cargo.toml (root)"). Touch nothing else in that file (frozen-spike members untouched, D-05).

    Create `crates/voss-app-core/Cargo.toml` (analog: `crates/voss-bridge/Cargo.toml`; `name = "voss-app-core"`, `[lib] name = "voss_app_core"`, workspace-inherited version/edition/rust-version/license, no `[dependencies]`) and `crates/voss-app-core/src/lib.rs` (single doc-comment placeholder line per A1-PATTERNS.md — populated in A2+).

    Create root `pnpm-workspace.yaml` (`packages: ["apps/*"]`) and root `package.json` (`voss-monorepo`, private, `packageManager: "pnpm@10.0.0"`) per A1-PATTERNS.md verbatim.

    Configure `apps/voss-app/src-tauri/Cargo.toml` per A1-PATTERNS.md "apps/voss-app/src-tauri/Cargo.toml": workspace-inherited package metadata, `[lib] name = "voss_app_lib"` + `crate-type = ["staticlib","cdylib","rlib"]`, `tauri-build` build-dep, `tauri` dep, `serde`/`serde_json`/`dirs` as `{ workspace = true }`, `tauri-plugin-os` dep, and `voss-app-core = { path = "../../../crates/voss-app-core" }` (wired, unused in A1 — D-06).

    Write `apps/voss-app/src-tauri/tauri.conf.json` per A1-PATTERNS.md / A1-UI-SPEC.md "Window Architecture Contract": `productName` `"Voss ADE"`, `identifier` `"app.voss-ade"`, `version` `"0.1.0"`, `title` `"Voss ADE"`, `decorations: false`, width 1280 / height 800 / minWidth 800 / minHeight 500, `beforeDevCommand` `"pnpm dev"`, `beforeBuildCommand` `"pnpm build"`, `devUrl` `http://localhost:5173`, `frontendDist` `../dist`, bundle `macOS.signingIdentity: null`. Ensure the scaffold's generated icon set is kept at `src-tauri/icons/` (RESEARCH Pitfall 7); if `pnpm create tauri-app` produced them, leave them; if absent, run `pnpm tauri icon` against the scaffold's source PNG.

    Write `apps/voss-app/src-tauri/capabilities/default.json` with the exact 7-permission list from A1-UI-SPEC.md "Window Controls Contract" / A1-PATTERNS.md (core:default + close/minimize/toggle-maximize/set-fullscreen/is-fullscreen/start-dragging).

    Write `apps/voss-app/src-tauri/src/main.rs` (analog: `crates/voss-cli/src/main.rs`; windows_subsystem attr + one-line `voss_app_lib::run()`), `src-tauri/build.rs` (`tauri_build::build()`), and `src-tauri/src/lib.rs` as a MINIMAL builder for this plan: `tauri::Builder::default().plugin(tauri_plugin_os::init()).run(tauri::generate_context!())`. Do NOT add `get_theme_overrides` here — that command lands in Plan 02; leave the invoke_handler out for now (Plan 02 owns lib.rs's command surface).

    Write `apps/voss-app/vite.config.ts` per A1-PATTERNS.md verbatim (`tailwindcss()` BEFORE `solidPlugin()`, `server.strictPort: true` — RESEARCH Pitfall 3, `watch.ignored: ['**/src-tauri/**']`), `apps/voss-app/package.json` per A1-PATTERNS.md (scripts dev/build/tauri, pinned deps), `apps/voss-app/index.html` (Vite entry importing `/src/index.tsx`, `<div id="root">`), and `tsconfig.json` (Solid JSX: `jsx: "preserve"`, `jsxImportSource: "solid-js"`).

    Write a MINIMAL `apps/voss-app/src/index.tsx` and `apps/voss-app/src/App.tsx` for this plan: `index.tsx` renders `<App/>` into `#root` (NO `invoke` call yet — theme seam is Plan 02; do NOT import `./index.css` yet, that file is created in Plan 02). `App.tsx` = a single full-viewport `<div>` with inline `background: '#0a0b0e'` (the A1-UI-SPEC empty-body color; replaced by token-driven styling + Titlebar in Plans 02/03). This keeps the window launchable now without depending on later plans' files.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo metadata --no-deps --format-version 1 2>/dev/null | grep -q '"voss-app-core"' && cargo metadata --no-deps --format-version 1 2>/dev/null | grep -q '"voss-app"' && cargo check -p voss-app-core 2>&1 | tail -1 && pnpm -C apps/voss-app install --frozen-lockfile=false >/dev/null 2>&1 && grep -E '"@tauri-apps/cli": *"2\.11\.2"' apps/voss-app/package.json && grep -E 'tauri *= *\{ *version *= *"2\.11\.2"' apps/voss-app/src-tauri/Cargo.toml && grep -F 'Voss ADE' apps/voss-app/src-tauri/tauri.conf.json && grep -F '"decorations": false' apps/voss-app/src-tauri/tauri.conf.json && node -e "require('./apps/voss-app/package.json')"</automated>
  </verify>
  <done>
    `cargo metadata` lists `voss-app-core` and `voss-app` members; `voss-app-core` compiles clean; `pnpm install` resolves the workspace; @tauri-apps/cli + tauri crate pinned to exact 2.11.x (no range); tauri.conf.json contains literal `Voss ADE` and `"decorations": false`.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Verify empty Voss ADE window launches</name>
  <read_first>
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Window Architecture Contract", "Empty Body Contract", "Copywriting Contract")
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("Pitfall 2: decorations:false removes rounded corners — intentional", "Pitfall 3: Vite port conflict")
  </read_first>
  <what-built>
    A runnable empty Tauri window. Task 1 scaffolded the app, wired the monorepo, and pinned versions. Running `pnpm tauri dev` from `apps/voss-app/` should open a borderless (no native title bar, sharp corners — intentional per Variant B 0-radius, RESEARCH Pitfall 2) 1280x800 window whose OS window title is "Voss ADE" and whose body is solid dark `#0a0b0e` with no content.
  </what-built>
  <how-to-verify>
    1. From repo root: `cd apps/voss-app && pnpm tauri dev` (first compile is slow — Tauri builds the Rust crate).
    2. Confirm a window opens with NO native macOS title bar / traffic lights (decorations:false; custom controls land in Plan 03 — none visible yet is expected at this stage).
    3. Confirm the window is solid dark (`#0a0b0e`) with no text, no placeholder, no controls.
    4. Confirm the OS window title (Dock / window menu / Mission Control) reads "Voss ADE", not "voss-app".
    5. Confirm sharp (non-rounded) corners — this is intentional Variant B, not a bug.
    6. Quit the dev process.
  </how-to-verify>
  <resume-signal>Type "approved" if the empty Voss ADE window launches as described, or describe what rendered.</resume-signal>
  <acceptance_criteria>
    - `pnpm tauri dev` launches without a Vite port error and without a white/blank-error webview
    - Window has no native decorations; body is uniform `#0a0b0e`; no content
    - OS-level window title string is exactly `Voss ADE` (SHL-06)
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| npm/cargo registry → local build | Untrusted package contents pulled during scaffold/install |
| Tauri webview ↔ Rust IPC | Webview is local content only in this plan; no command exposed yet |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A1-SC | Tampering | npm/cargo installs during scaffold | mitigate | Task 0 blocking-human package-legitimacy gate over all 8 [ASSUMED] npm packages + 2 crates before any install runs; pinned exact versions (no range) prevent silent upgrade drift |
| T-A1-01 | Elevation of Privilege | Tauri command surface | mitigate | No `#[tauri::command]` registered in this plan's `lib.rs` (invoke_handler omitted; `get_theme_overrides` deferred to Plan 02). `capabilities/default.json` whitelists only the 7 window permissions — no fs/shell/exec capability exposed |
| T-A1-02 | Tampering | Webview remote code | mitigate | `frontendDist` is local `../dist`; `devUrl` is localhost:5173 only; no remote origin in tauri.conf. Restrictive CSP is finalized in Plan 04's build-smoke verification |
| T-A1-03 | Spoofing | Cargo workspace resolver mismatch | accept | `apps/voss-app/src-tauri` added as a workspace member (D-05) so it inherits `resolver = "2"` — divergence risk eliminated, not merely accepted (RESEARCH Pitfall 4) |
</threat_model>

<verification>
- `cargo metadata --no-deps` lists `voss-app-core` and `voss-app`.
- `cargo check -p voss-app-core` exits 0 (placeholder crate compiles).
- `pnpm -C apps/voss-app install` resolves with no missing-workspace error.
- Tauri crate + @tauri-apps/cli pinned to `2.11.2` exactly (grep, no `^`/`~`).
- `tauri.conf.json` contains literal `Voss ADE` and `"decorations": false`.
- Human checkpoint: empty borderless `Voss ADE` window launches via `pnpm tauri dev`.
</verification>

<success_criteria>
- Monorepo wired: root Cargo workspace has both new members; root pnpm workspace resolves `apps/voss-app`.
- `crates/voss-app-core` exists as an empty placeholder that compiles clean and is path-dep'd by src-tauri (wired, unused).
- Tauri 2.x pinned exactly (SHL-01).
- Window title + productName = "Voss ADE" (SHL-06).
- `pnpm tauri dev` launches an empty borderless dark window.
</success_criteria>

<output>
Create `.planning/phases/A1-voss-app-tauri-shell/A1-01-SUMMARY.md` when done.
</output>
