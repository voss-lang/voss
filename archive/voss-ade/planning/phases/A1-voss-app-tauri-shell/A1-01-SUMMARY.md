---
phase: A1-voss-app-tauri-shell
plan: 01
subsystem: ui
tags: [tauri, solid, tailwind, monorepo, cargo, pnpm, scaffold]

requires:
  - phase: pre-A1
    provides: existing Cargo workspace (7 frozen-spike crates) + frozen toolchain (rustc 1.95 nightly, pnpm 10.32.1, node 22.22)
provides:
  - apps/voss-app/ Tauri 2 + SolidJS + Tailwind v4 scaffold (pinned versions)
  - crates/voss-app-core empty placeholder crate (compiles clean, path-dep'd by src-tauri, unused in A1)
  - root pnpm workspace (packages: apps/*)
  - root Cargo workspace extended with crates/voss-app-core + apps/voss-app/src-tauri
  - tauri.conf.json with productName/title "Voss ADE", decorations:false, 1280x800, signingIdentity:null
  - capabilities/default.json with 7 window perms (core:default + close/min/toggle-max/set-fullscreen/is-fullscreen/start-dragging)
  - tauri-plugin-os registered (consumed by Plan 03 platform gate)
affects: [A1-02, A1-03, A1-04, A1-05, A2, A3]

tech-stack:
  added:
    - tauri 2.11.2 (crate)
    - tauri-build 2.6.2
    - tauri-plugin-os 2.3.2
    - "@tauri-apps/cli 2.11.2"
    - "@tauri-apps/api 2.11.0"
    - "@tauri-apps/plugin-os 2.3.2"
    - solid-js 1.9.13
    - vite-plugin-solid 2.11.12
    - vite 8.0.13
    - tailwindcss 4.3.0
    - "@tailwindcss/vite 4.3.0"
  patterns:
    - workspace-inherited crate metadata (version/edition/rust-version/license)
    - workspace-shared deps via `{ workspace = true }` for serde / serde_json / dirs
    - pinned-exact (no ^/~) for Tauri crate + CLI per SHL-01

key-files:
  created:
    - pnpm-workspace.yaml
    - package.json (root)
    - crates/voss-app-core/Cargo.toml
    - crates/voss-app-core/src/lib.rs
    - apps/voss-app/package.json
    - apps/voss-app/index.html
    - apps/voss-app/vite.config.ts
    - apps/voss-app/tsconfig.json
    - apps/voss-app/src/index.tsx
    - apps/voss-app/src/App.tsx
    - apps/voss-app/src/vite-env.d.ts
    - apps/voss-app/src-tauri/Cargo.toml
    - apps/voss-app/src-tauri/build.rs
    - apps/voss-app/src-tauri/tauri.conf.json
    - apps/voss-app/src-tauri/capabilities/default.json
    - apps/voss-app/src-tauri/src/main.rs
    - apps/voss-app/src-tauri/src/lib.rs
    - apps/voss-app/src-tauri/icons/ (full set: 32x32, 128x128, 128x128@2x, icon.icns, icon.ico, Windows store logos — copied from create-tauri-app scaffold)
    - apps/voss-app/src-tauri/.gitignore
    - apps/voss-app/.gitignore
  modified:
    - Cargo.toml (root — surgical: appended "crates/voss-app-core" and "apps/voss-app/src-tauri" to [workspace].members; nothing else touched)

key-decisions:
  - Scaffold harvested from pnpm create tauri-app@latest --template solid-ts in /tmp, then files written verbatim from PATTERNS.md/UI-SPEC.md (icons + .gitignore + vite-env.d.ts kept from scaffold; all configs hand-written to honor exact pins + plan contracts).
  - lib.rs is MINIMAL for Plan 01 — only `tauri_plugin_os::init()` plugin registered; no `invoke_handler` and no `get_theme_overrides` command (those land in Plan 02).
  - App.tsx is MINIMAL for Plan 01 — single full-viewport `<div>` with inline `background: '#0a0b0e'` (no Titlebar, no theme imports, no `index.css`); satisfies UI-SPEC Empty Body Contract and avoids dependence on Plan 02 files.
  - tauri-plugin-os installed now (not Plan 03) so Plan 03 platform gate can `platform()` without further dep changes.
  - tauri-plugin-os Rust crate + JS package pinned to 2.3.2 exact (matching latest stable; SHL-01 only requires Tauri crate + CLI pin but exact pin applied consistently).
  - bundle.macOS.signingIdentity = null — explicitly unsigned dev posture; codesign deferred to A10.
  - app.security.csp = null in tauri.conf.json — restrictive CSP is Plan 04 work (T-A1-02 mitigation).

patterns-established:
  - "Workspace member addition is surgical (append only) — frozen-spike crates untouched per D-05."
  - "Tauri config split: tauri.conf.json owns window/bundle/build contract; capabilities/default.json owns IPC permission allow-list (7 entries, window-only — no fs/shell/exec)."
  - "Frontend Tailwind v4 plugin chain: tailwindcss() BEFORE solidPlugin() in vite plugins array; @theme inline CSS deferred to Plan 02 (no index.css yet)."

requirements-completed: [SHL-01, SHL-06]

duration: ~25min
completed: 2026-05-18
---

# Phase A1, Plan 01: Tauri+Solid+Tailwind Scaffold + Monorepo Wiring Summary

**Bootstrapped `apps/voss-app/` Tauri 2.11.2 + SolidJS 1.9.13 + Tailwind v4 desktop scaffold inside the existing Cargo + pnpm monorepo, with the empty `crates/voss-app-core` placeholder crate wired as a path dep and version pins enforced for SHL-01.**

## Performance

- **Tasks:** 2 (Task 0 human-verify approved; Task 1 auto-executed)
- **Files created:** 18 (configs, sources, icons dir)
- **Files modified:** 1 (root Cargo.toml — surgical members append)
- **Wave:** 1

## Accomplishments

- Empty borderless Voss ADE window scaffolded and ready to launch via `pnpm tauri dev` (Task 2 = pending human launch + visual verify).
- Cargo workspace metadata lists both `voss-app-core` and `voss-app` (9 members total: 7 frozen-spike + 2 A1 additions).
- `cargo check -p voss-app-core` exits 0 — placeholder crate compiles clean.
- `pnpm install` resolves the 2-project workspace with 90 packages, no errors.
- Tauri crate + CLI pinned to exact `2.11.2` (no `^`/`~` range) — SHL-01 truth verified by grep.
- `tauri.conf.json` contains literal `"Voss ADE"` (productName + window title) and `"decorations": false` — SHL-06 + D-03 verified.

## Verify Output (Task 1 acceptance)

```
=== pin grep: @tauri-apps/cli 2.11.2 ===
    "@tauri-apps/cli": "2.11.2",
=== pin grep: tauri = 2.11.2 ===
tauri = { version = "2.11.2", features = [] }
=== title grep: Voss ADE ===
  "productName": "Voss ADE",
        "title": "Voss ADE",
=== decorations grep ===
        "decorations": false,
=== package.json valid JSON ===
OK
=== cargo metadata ===
voss-app-core: True
voss-app: True
=== cargo check -p voss-app-core ===
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 3.52s
ALL VERIFY OK
```

## Pending

- **Task 2 (blocking human-verify):** Human must run `cd apps/voss-app && pnpm tauri dev` and confirm the borderless `#0a0b0e` Voss ADE window launches with the OS-level title `Voss ADE`. First compile is slow (Tauri downloads + builds the Rust crate graph).
- After Task 2 approval: Plan 02 lands `index.css` + `variant-b.css` + `applyTheme.ts` + `get_theme_overrides` command + `invoke()` in `index.tsx`. Plan 03 lands the 22px Titlebar + WindowControls + PresetSwitcher (platform-gated via tauri-plugin-os already installed here).

## Deferred (per plan scope)

- Theme seam (Solid + Rust `get_theme_overrides`) — Plan 02.
- Titlebar + traffic lights + preset switcher — Plan 03.
- Build smoke (`pnpm tauri build` exits 0, signing posture finalized) — Plan 04.
- Restrictive CSP on tauri.conf.json `app.security.csp` — Plan 04 (T-A1-02 mitigation).
- Code-signing certificate procurement — A10 (Apple Developer ID + Windows Authenticode; human-action clock should already be ticking per RESEARCH human-action note).
