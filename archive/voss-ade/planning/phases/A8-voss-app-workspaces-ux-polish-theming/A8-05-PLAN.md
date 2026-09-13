---
phase: A8-voss-app-workspaces-ux-polish-theming
plan: 05
type: execute
wave: 5
depends_on: [A8-04]
files_modified:
  - apps/voss-app/src/appearance/windowEffects.ts
  - apps/voss-app/src/appearance/__tests__/windowEffects.test.ts
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src-tauri/tauri.conf.json
  - apps/voss-app/src-tauri/icons/*
  - apps/voss-app/src-tauri/resources/*
  - apps/voss-app/src/command-palette/nativeMenu.ts
  - apps/voss-app/src/command-palette/__tests__/nativeMenu.test.ts
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-05-SUMMARY.md
autonomous: true
requirements: [UXP-15, UXP-20, UXP-28, UXP-29, UXP-30]
must_haves:
  truths:
    - "Native effects are platform-gated and fail soft"
    - "Linux uses CSS opacity fallback only"
    - "OS-native corners/shadows are not simulated in web content"
    - "Platform metadata does not add in-app chrome"
---

<objective>
Wire platform-native polish, window effects, metadata, and final native-menu alignment.
</objective>

<context>
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md
</context>

<threat_model>
T-A8-08 Platform-specific effects crash unsupported environments. Mitigation: adapter-level OS gating, tests for no-op fallbacks, and manual runtime checklist for compositor effects.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Add platform-gated window effects adapter</name>
  <files>apps/voss-app/src/appearance/windowEffects.ts, apps/voss-app/src/appearance/__tests__/windowEffects.test.ts, apps/voss-app/src-tauri/src/lib.rs, apps/voss-app/src-tauri/tauri.conf.json</files>
  <read_first>
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md - Tauri effects notes
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - Platform-Native Chrome Contract
    - apps/voss-app/src-tauri/src/lib.rs - current builder and plugins
    - apps/voss-app/src-tauri/tauri.conf.json - window config
  </read_first>
  <action>
    Implement a small adapter for opacity/vibrancy effects. Gate macOS/Windows effects to supported APIs and treat Linux as CSS opacity fallback. Ensure effects fail soft and leave the app opaque/usable. Do not add web-simulated rounded corners or shadows.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/appearance/__tests__/windowEffects.test.ts && cargo build -p voss-app</automated>
  </verify>
  <acceptance_criteria>
    - Unsupported platforms no-op without throwing.
    - Linux path uses CSS alpha fallback only.
    - `--bg-0`/window opacity composition remains token-driven.
    - Native corners/shadows are left to the OS.
  </acceptance_criteria>
  <done>Window effects are isolated and safe across platforms.</done>
</task>

<task type="execute">
  <name>Task 2: Add platform metadata assets and desktop integration hooks</name>
  <files>apps/voss-app/src-tauri/tauri.conf.json, apps/voss-app/src-tauri/icons/*, apps/voss-app/src-tauri/resources/*</files>
  <read_first>
    - apps/voss-app/src-tauri/tauri.conf.json - bundle metadata
    - .planning/ROADMAP.md - UXP-28..30
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - platform metadata boundary
  </read_first>
  <action>
    Add or verify app metadata needed for macOS/Windows/Linux platform-native feel: product name, tray/icon resources where supported, Linux desktop entry/WM_CLASS configuration, and Windows taskbar identity. Keep this as packaging/config metadata; do not add in-app UI for tray/status.
  </action>
  <verify>
    <automated>cargo build -p voss-app && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - macOS, Windows, and Linux metadata paths are represented or explicitly documented if deferred by Tauri packaging limits.
    - No status bar or tray UI appears in the web app.
    - Existing `Voss ADE` ship name remains intact.
  </acceptance_criteria>
  <done>Platform metadata is ready for runtime/manual verification.</done>
</task>

<task type="execute">
  <name>Task 3: Align native menus with A8 registry commands</name>
  <files>apps/voss-app/src/command-palette/nativeMenu.ts, apps/voss-app/src/command-palette/__tests__/nativeMenu.test.ts</files>
  <read_first>
    - apps/voss-app/src/command-palette/nativeMenu.ts - A7 menu model
    - apps/voss-app/src/command-palette/registry.ts - A8 command additions from plan 03
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md - D-09 and A7 D-04 dependency
  </read_first>
  <action>
    Ensure native menu model includes A8 workspace/theme/profile commands through the same registry metadata and remains a no-op in non-Tauri tests. Add tests for menu category placement and accelerators where present.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/nativeMenu.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - A8 commands appear under the correct native menu categories.
    - Native menu action dispatches the same command ids as palette rows.
    - Non-Tauri environments skip menu setup without failing.
  </acceptance_criteria>
  <done>Native menu remains registry-backed after A8 commands land.</done>
</task>
</tasks>

<verification>
Run window-effects tests, native-menu tests, frontend build, and `cargo build -p voss-app`.
</verification>

<success_criteria>
- Platform-native polish is wired with safe fallbacks for UXP-28..30.
- UXP-20 remains OS-native rather than simulated in web content.
</success_criteria>

