---
phase: A5-voss-app-project-open
plan: 02
type: execute
wave: 2
depends_on: [A5-01]
files_modified:
  - apps/voss-app/src-tauri/Cargo.toml
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src-tauri/capabilities/default.json
  - apps/voss-app/package.json
autonomous: true
requirements: [WS-01, WS-02, WS-04, WS-05, WS-06]
must_haves:
  truths:
    - "tauri-plugin-dialog is registered on the builder AND dialog:allow-open is in the capabilities file (both required — either alone fails silently)"
    - "Three new #[tauri::command] wrappers (open_project, load_recents, default_cwd) delegate to voss-app-core::project"
    - "Frontend can invoke('open_project', { path }) and receive ProjectInfo with camelCase gitBranch key"
    - "@tauri-apps/plugin-dialog JS bindings are installed and version-matched to the Rust crate"
  artifacts:
    - path: "apps/voss-app/src-tauri/Cargo.toml"
      provides: "tauri-plugin-dialog dependency"
      contains: "tauri-plugin-dialog"
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "Plugin registration + three project commands in generate_handler!"
      contains: "open_project"
    - path: "apps/voss-app/src-tauri/capabilities/default.json"
      provides: "dialog:allow-open permission"
      contains: "dialog:allow-open"
    - path: "apps/voss-app/package.json"
      provides: "@tauri-apps/plugin-dialog dependency"
      contains: "@tauri-apps/plugin-dialog"
---

<objective>
Wire the A5-01 Rust core through Tauri to the webview. Three coordinated edits land together (RESEARCH Pitfall 1): plugin builder registration, capability permission, and JS plugin install. Plus the three `#[tauri::command]` wrappers that bridge `voss-app-core::project` into `tauri::generate_handler!`.

Purpose: Make the project-open IPC surface invokable from the frontend. A5-03 (typed invoke wrappers) and A5-05 (composition) both depend on this surface existing.
Output: `cargo build -p voss-app` clean, `pnpm --filter voss-app install` clean, and the three new commands callable from JS.
</objective>

<context>
@.planning/phases/A5-voss-app-project-open/A5-SPEC.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A5-voss-app-project-open/A5-RESEARCH.md
@.planning/phases/A5-voss-app-project-open/A5-PATTERNS.md
@.planning/phases/A5-voss-app-project-open/A5-01-PLAN.md
@apps/voss-app/src-tauri/Cargo.toml
@apps/voss-app/src-tauri/src/lib.rs
@apps/voss-app/src-tauri/capabilities/default.json
@apps/voss-app/package.json

<interfaces>
<!-- Three new #[tauri::command] wrappers — exact shapes A5-03 will invoke. -->

From apps/voss-app/src-tauri/src/lib.rs (this plan adds):

use voss_app_core::project::{self, ProjectInfo};
// ... and import ProjectError into scope if used, OR just propagate via Display

#[tauri::command]
fn open_project(path: String) -> Result<ProjectInfo, String> {
    project::open_project(std::path::Path::new(&path)).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_recents() -> Vec<String> {
    project::list_recents()
}

#[tauri::command]
fn default_cwd(project_path: Option<String>) -> String {
    project::default_cwd(project_path.as_deref().map(std::path::Path::new))
}

// Builder additions:
tauri::Builder::default()
    .plugin(tauri_plugin_os::init())          // existing
    .plugin(tauri_plugin_dialog::init())      // A5 adds
    // ... existing .manage / .invoke_handler with open_project, load_recents, default_cwd appended

From the analog A4-03 wrappers in the same file (lines 166-197) — clone style verbatim.
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Webview → Rust IPC | All three new commands accept untrusted strings; Rust validates (canonicalize, is_dir) |
| Tauri permission ACL | Plugin commands require explicit `dialog:allow-open` allowlist; missing → silent IPC denial |
| Plugin version skew | Rust `tauri-plugin-dialog` 2.x must match JS `@tauri-apps/plugin-dialog` ^2 IPC surface; mismatch → silent payload corruption |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A5-02-WIRE | Tampering | three-edit coordination (Cargo, lib.rs, capabilities) | mitigate | Single plan lands all three together (RESEARCH Pitfall 1); verify command tests grep for all three sites; `cargo build -p voss-app` + capability JSON parse before declaring done |
| T-A5-02-CASE | Tampering | snake_case ↔ camelCase parameter mapping | mitigate | Wrapper signatures match the `<interfaces>` block byte-for-byte; RESEARCH Pitfall 5 documents the failure mode (Rust receives default values silently); A5-03 tests assert the JS-side camelCase keys |
| T-A5-02-PERM | Elevation of privilege | dialog permission scope | mitigate | Only `dialog:allow-open` is added (not `dialog:default` which also grants `allow-message` + `allow-save`); minimal surface per RESEARCH §Pattern 1 |
| T-A5-03 | Information disclosure / DoS | path traversal via untrusted webview input | mitigate | Inherited from A5-01: `open_project` canonicalize + is_dir validates; wrapper just `.map_err(|e| e.to_string())` propagates |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add tauri-plugin-dialog (Rust + JS) and register the plugin</name>
  <files>apps/voss-app/src-tauri/Cargo.toml, apps/voss-app/src-tauri/src/lib.rs, apps/voss-app/package.json</files>
  <read_first>
    - apps/voss-app/src-tauri/Cargo.toml line 17 (`tauri-plugin-os = "2.3.2"`) — pin-style precedent
    - apps/voss-app/src-tauri/src/lib.rs line ~202 — `tauri::Builder::default().plugin(tauri_plugin_os::init())` — the registration site
    - apps/voss-app/package.json — current `@tauri-apps/*` dep set
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Standard Stack — `tauri-plugin-dialog = "2"` (Rust), `@tauri-apps/plugin-dialog: "^2"` (npm), both [OK] in the Package Legitimacy Audit
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md Pitfall 1 — three coordinated edits warning
  </read_first>
  <action>
    Edit `apps/voss-app/src-tauri/Cargo.toml`: append to `[dependencies]`:

      tauri-plugin-dialog = "2"

    Pin to the major `^2` per A5-RESEARCH. Do NOT add feature flags — `open({ directory: true })` works on the default feature set. The A5-00 MSRV bump (>=1.77.2) is the precondition that makes this build cleanly.

    Edit `apps/voss-app/src-tauri/src/lib.rs`: in the `tauri::Builder::default()` chain (around line 202), add `.plugin(tauri_plugin_dialog::init())` directly after the existing `.plugin(tauri_plugin_os::init())` call. Order matters cosmetically only — keep the `os` plugin first to minimize diff churn.

    Edit `apps/voss-app/package.json`: append to `dependencies` (NOT `devDependencies`):

      "@tauri-apps/plugin-dialog": "^2"

    Run `pnpm --filter voss-app install` to write lockfile. The slopcheck-resolved version at research time was `^2.7.1`, but the `^2` range is what gets pinned in `package.json` per RESEARCH lock.

    **Do NOT** add commands to `generate_handler!` in this task — that lands in Task 2 alongside the wrapper definitions, so the build between tasks remains valid.

    Run `cargo build -p voss-app` after the Cargo + lib.rs edits to confirm the plugin links cleanly under the new MSRV. If `cargo build` fails on MSRV, return to A5-00 and confirm the rust-version bump landed.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q '^tauri-plugin-dialog' apps/voss-app/src-tauri/Cargo.toml && grep -q 'tauri_plugin_dialog::init()' apps/voss-app/src-tauri/src/lib.rs && grep -q '"@tauri-apps/plugin-dialog"' apps/voss-app/package.json && cargo build -p voss-app --quiet 2>&1 | tail -10 && echo PROJECT_PLUGIN_OK</automated>
  </verify>
  <acceptance_criteria>
    - `tauri-plugin-dialog = "2"` appears in `apps/voss-app/src-tauri/Cargo.toml`.
    - `.plugin(tauri_plugin_dialog::init())` appears in the `Builder::default()` chain in `apps/voss-app/src-tauri/src/lib.rs`.
    - `"@tauri-apps/plugin-dialog": "^2"` is in `apps/voss-app/package.json` dependencies.
    - `cargo build -p voss-app` exits 0 under the new MSRV.
    - `PROJECT_PLUGIN_OK` prints.
  </acceptance_criteria>
  <done>Plugin Rust + JS are installed and the plugin is on the builder chain. Capability allowlist + commands land in Task 2.</done>
</task>

<task type="auto">
  <name>Task 2: Add dialog:allow-open capability and register open_project / load_recents / default_cwd</name>
  <files>apps/voss-app/src-tauri/capabilities/default.json, apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/capabilities/default.json lines 5-12 — current `core:*` permission array; the A5 addition is appended in-place
    - apps/voss-app/src-tauri/src/lib.rs lines 154-220 — A4-03 cross-crate wrapper block + `generate_handler!` registry (existing 13 commands; A5 brings it to 16)
    - apps/voss-app/src-tauri/src/lib.rs lines 18-30 — `settings_path()` idiom (already cloned by A5-01's `recents_path`; no edits needed here, but confirms the precedent)
    - crates/voss-app-core/src/project.rs — A5-01 `ProjectInfo`, `open_project`, `list_recents`, `default_cwd` signatures
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Pattern 1 — `dialog:allow-open` is the minimal permission for `open()` (RESEARCH explicitly states `dialog:default` is also valid but adds unneeded `allow-message` + `allow-save`)
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Pattern 2 — the verified wrapper template (lines ~254-271)
  </read_first>
  <action>
    Edit `apps/voss-app/src-tauri/capabilities/default.json`: append `"dialog:allow-open"` to the `"permissions"` array. Minimal surface per RESEARCH Pattern 1 — explicitly do NOT use `dialog:default` (which would also enable `allow-message` and `allow-save`, neither needed in A5).

    Edit `apps/voss-app/src-tauri/src/lib.rs`:

    1. Add `use voss_app_core::project::{self, ProjectInfo};` near the top (after the existing `use voss_app_core::{...}` imports). The existing `use std::path::Path;` is reusable.

    2. Add a comment block matching the A4-03 cross-crate-wrappers section header style (around line 154), naming A5 as the wave and explaining why the wrappers live here (the cross-crate `generate_handler!` constraint).

    3. Add the three wrappers exactly per the `<interfaces>` block:

      #[tauri::command]
      fn open_project(path: String) -> Result<ProjectInfo, String> {
          project::open_project(Path::new(&path)).map_err(|e| e.to_string())
      }

      #[tauri::command]
      fn load_recents() -> Vec<String> {
          project::list_recents()
      }

      #[tauri::command]
      fn default_cwd(project_path: Option<String>) -> String {
          project::default_cwd(project_path.as_deref().map(Path::new))
      }

    Note: Rust `project_path` (snake_case) maps to JS `projectPath` (camelCase) — Tauri auto-converts (RESEARCH Pitfall 5). A5-03 tests assert the JS side sends `projectPath`.

    4. Append `open_project, load_recents, default_cwd` to the `tauri::generate_handler![ ... ]` macro at the end of the existing list (after the A4-03 layout block). Keep grouping comments if present (PTY block, grid block, layouts block, project block).

    Run `cargo build -p voss-app` to confirm the wrappers compile and the macro expansion is valid. Run `cargo test -p voss-app-core project::` to confirm the core tests still pass (nothing in core changed; sanity check).

    **Do not** edit the frontend in this task — A5-03 owns `projectStorage.ts`. **Do not** call the dialog plugin from Rust — A5-RESEARCH Anti-Pattern: the dialog `open()` runs on the **frontend**; the Rust command receives the already-selected path.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q '"dialog:allow-open"' apps/voss-app/src-tauri/capabilities/default.json && grep -q 'fn open_project' apps/voss-app/src-tauri/src/lib.rs && grep -q 'fn load_recents' apps/voss-app/src-tauri/src/lib.rs && grep -q 'fn default_cwd' apps/voss-app/src-tauri/src/lib.rs && grep -q 'use voss_app_core::project' apps/voss-app/src-tauri/src/lib.rs && grep -E 'generate_handler!' apps/voss-app/src-tauri/src/lib.rs | head -5 && grep -E 'open_project,|load_recents,|default_cwd' apps/voss-app/src-tauri/src/lib.rs | grep -v '^#' | grep -c -E 'open_project|load_recents|default_cwd' && cargo build -p voss-app --quiet 2>&1 | tail -10 && python3 -c "import json,sys; d=json.load(open('apps/voss-app/src-tauri/capabilities/default.json')); assert 'dialog:allow-open' in d['permissions'], d; print('CAP_OK')" && echo PROJECT_COMMANDS_OK</automated>
  </verify>
  <acceptance_criteria>
    - `dialog:allow-open` is in `capabilities/default.json` `permissions` array and the JSON parses cleanly.
    - `dialog:default` is NOT used (minimal-permission discipline).
    - Three `#[tauri::command]` wrappers (`open_project`, `load_recents`, `default_cwd`) exist in `src-tauri/src/lib.rs` with the exact signatures from `<interfaces>`.
    - All three commands are registered in `tauri::generate_handler![ ... ]`.
    - `cargo build -p voss-app` exits 0.
    - `cargo test -p voss-app-core project::` still exits 0 (no regression).
    - `PROJECT_COMMANDS_OK` and `CAP_OK` print.
  </acceptance_criteria>
  <done>The IPC surface (plugin + capability + three command wrappers) is wired. The frontend can now `invoke('open_project', { path })` and `invoke('plugin:dialog|open', { directory: true })` without permission denials. A5-03 can land the typed JS wrappers next.</done>
</task>

</tasks>

<verification>
Run `cargo build -p voss-app` and `cargo test -p voss-app-core project::`. Both must exit 0 after the wave is complete.
</verification>

<success_criteria>
- Three coordinated edits (Cargo, lib.rs, capabilities) land in the same wave (RESEARCH Pitfall 1).
- `tauri-plugin-dialog` Rust + JS pinned to `^2` and version-matched.
- `dialog:allow-open` is the only new permission (minimal surface).
- Three wrappers exist and are reachable via `tauri::generate_handler!`.
- No frontend code is touched in this wave.
- T-A5-02-WIRE, T-A5-02-CASE, T-A5-02-PERM mitigations all observable in the diff.
</success_criteria>

<output>
Create `.planning/phases/A5-voss-app-project-open/A5-02-SUMMARY.md` with: cargo build cache time delta (libgit2 vendored adds first-clean-build cost), exact Tauri capability JSON diff, and the final generate_handler! macro count (should be 16: existing 13 + 3 A5 commands).
</output>
