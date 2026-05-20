---
phase: A7-voss-app-command-palette-keymap
plan: 03
type: execute
wave: 2
depends_on: [A7-01]
files_modified:
  - crates/voss-app-core/src/keymap.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src/command-palette/keymapStorage.ts
  - apps/voss-app/src/command-palette/toast.tsx
  - apps/voss-app/src/command-palette/__tests__/keymapStorage.test.ts
  - apps/voss-app/src/command-palette/__tests__/toast.test.tsx
autonomous: true
requirements: [CMD-05, CMD-06]
must_haves:
  truths:
    - "D-12: active profile persists at ~/.config/voss-app/settings.json under keymap.profile"
    - "D-13: .voss/keymap.json additively merges overrides and null unbinds commands"
    - "D-14: workspace keymap changes hot-reload through a Rust-side watcher/event path"
    - "D-15: invalid entries are skipped, valid entries still apply, and errors surface as toasts"
    - "D-16: A7 ships a minimal Variant B toast stack"
  artifacts:
    - path: "crates/voss-app-core/src/keymap.rs"
      provides: "Rust keymap settings/override schema, validation, and IO"
      contains: "KeymapProfile"
---

<objective>
Implement the keymap persistence/validation surface and minimal toast feedback system for profile switches and override errors.
</objective>

<context>
@.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-RESEARCH.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md
@crates/voss-app-core/src/project.rs
@crates/voss-app-core/src/layouts.rs
@apps/voss-app/src-tauri/src/lib.rs
</context>

<threat_model>
T-A7-05 User-edited JSON disables all shortcuts. Mitigation: per-entry validation with partial apply and profile-default fallback.
T-A7-06 Filesystem side effects on load. Mitigation: reading `.voss/keymap.json` never creates `.voss`; only save/write paths create parents.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add Rust keymap settings, override schema, and validation</name>
  <files>crates/voss-app-core/src/keymap.rs, crates/voss-app-core/src/lib.rs</files>
  <read_first>
    - crates/voss-app-core/src/project.rs - settings/recents path idiom
    - crates/voss-app-core/src/layouts.rs - workspace JSON validation/fail-safe pattern
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md - D-12..D-15
  </read_first>
  <behavior>
    - Test 1: missing settings returns profile `vscode`.
    - Test 2: settings JSON round-trips `keymap.profile = "tmux"`.
    - Test 3: `.voss/keymap.json` version 1 accepts binding object and null unbind.
    - Test 4: unknown command id and invalid chord produce validation issues without rejecting valid entries.
    - Test 5: reading missing override does not create `.voss`.
  </behavior>
  <action>
    Add `crates/voss-app-core/src/keymap.rs` with `KeymapProfile`, settings structs that extend the existing settings shape compatibly, `KeymapOverrideFile { version: 1, bindings }`, `KeyBindingOverride`, `KeymapValidationIssue`, `load_keymap_profile`, `save_keymap_profile`, `load_keymap_overrides`, and `validate_keymap_overrides`. Validation receives known command ids and valid chord syntax from the frontend or a serializable command catalog and returns valid bindings plus issues. Export `pub mod keymap` from `lib.rs`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core keymap -- --nocapture && grep -q 'pub enum KeymapProfile' crates/voss-app-core/src/keymap.rs && grep -q 'KeymapValidationIssue' crates/voss-app-core/src/keymap.rs && echo A7_KEYMAP_RUST_OK</automated>
  </verify>
  <acceptance_criteria>
    - Profile defaults to `vscode`.
    - `tmux` persists and reloads.
    - Null unbind is represented.
    - Invalid entries return issues but valid entries are preserved.
    - `A7_KEYMAP_RUST_OK` prints.
  </acceptance_criteria>
  <done>Rust keymap schema and validation are available.</done>
</task>

<task type="execute" tdd="true">
  <name>Task 2: Add Tauri/frontend keymap bridge and event listener</name>
  <files>apps/voss-app/src-tauri/src/lib.rs, apps/voss-app/src/command-palette/keymapStorage.ts, apps/voss-app/src/command-palette/__tests__/keymapStorage.test.ts</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs - existing wrapper/handler registration pattern
    - apps/voss-app/src/command-palette/registry.ts - command ids and chord metadata
    - crates/voss-app-core/src/keymap.rs - Rust API from Task 1
  </read_first>
  <behavior>
    - Test 1: `loadKeymapProfile` invokes `load_keymap_profile`.
    - Test 2: `saveKeymapProfile("tmux")` invokes `save_keymap_profile`.
    - Test 3: `watchWorkspaceKeymap` listens for `voss://keymap-updated` or the chosen exact event name.
    - Test 4: invalid update payload routes issues to toast callbacks.
  </behavior>
  <action>
    Add app-level Tauri command wrappers for `load_keymap_profile`, `save_keymap_profile`, `load_keymap_overrides`, and a watcher registration command such as `watch_keymap_overrides`. Use camelCase payload keys. In `keymapStorage.ts`, add thin `invoke` wrappers and an event listener using `@tauri-apps/api/event.listen`. Pick one event name and document it in the file; the event payload must contain effective bindings and validation issues.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/keymapStorage.test.ts && cargo build -p voss-app</automated>
  </verify>
  <acceptance_criteria>
    - Tauri commands are registered in `generate_handler!`.
    - Frontend wrappers use exact command names and payload keys.
    - Watch event listener is typed and unlistens on cleanup.
    - Build passes.
  </acceptance_criteria>
  <done>Frontend can load/save profile and receive workspace override updates.</done>
</task>

<task type="execute" tdd="true">
  <name>Task 3: Add minimal Variant B toast stack</name>
  <files>apps/voss-app/src/command-palette/toast.tsx, apps/voss-app/src/command-palette/__tests__/toast.test.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - Toast Contract and copywriting
    - apps/voss-app/src/grid/CloseConfirmBanner.tsx - dense feedback chrome
    - apps/voss-app/src/App.tsx - provider mount point
  </read_first>
  <behavior>
    - Test 1: success toast uses `Keymap updated`.
    - Test 2: invalid entry toast uses `Keymap entry ignored`.
    - Test 3: max three visible toasts are rendered.
    - Test 4: error toasts expose assertive live-region behavior.
  </behavior>
  <action>
    Implement a minimal toast provider/store and `ToastStack` component. Support `success`, `warning`, `error`, and `info` severities with the exact A7-UI-SPEC copy. Mount the stack once in `App.tsx` and expose `showToast` through AppContext. Do not build a notification center or settings surface.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/toast.test.tsx src/__tests__/App.test.tsx && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - Toast stack is fixed bottom-right, token-only, radius 0.
    - Error/warning/success/info rails use A7-approved tokens.
    - Keymap validation errors render as toasts.
    - Tests and build pass.
  </acceptance_criteria>
  <done>Keymap feedback has a minimal approved UI surface.</done>
</task>
</tasks>

<verification>
Run keymap Rust tests, keymapStorage/toast Vitest, and `cargo build -p voss-app`.
</verification>

<success_criteria>
- Keymap profile and workspace overrides can be loaded, validated, and applied partially.
- Invalid keymap entries surface as toasts without breaking valid bindings.
</success_criteria>

