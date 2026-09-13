---
phase: A8-voss-app-workspaces-ux-polish-theming
plan: 01
type: execute
wave: 1
depends_on: [A8-00]
files_modified:
  - apps/voss-app/src/themes/schema.ts
  - apps/voss-app/src/themes/themeCatalog.ts
  - apps/voss-app/src/themes/bundled/*.json
  - apps/voss-app/src/themes/__tests__/schema.test.ts
  - apps/voss-app/src/themes/__tests__/themeCatalog.test.ts
  - apps/voss-app/src/appearance/profiles.ts
  - apps/voss-app/src/appearance/__tests__/profiles.test.ts
  - crates/voss-app-core/src/themes.rs
  - crates/voss-app-core/src/profiles.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src-tauri/src/lib.rs
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-01-SUMMARY.md
autonomous: true
requirements: [UXP-09, UXP-10, UXP-11, UXP-12, UXP-13, UXP-14, UXP-21, UXP-25, UXP-26, UXP-27]
must_haves:
  truths:
    - "A8 ships 12 curated themes, not a VSCode import engine"
    - "Theme runtime uses existing CSS variable seam"
    - "Profile is a full settings snapshot"
    - "Corrupt custom themes/profiles fail safe and do not block boot"
---

<objective>
Build the pure theme, high-contrast, and profile substrate that later UI and command surfaces consume.
</objective>

<context>
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PATTERNS.md
</context>

<threat_model>
T-A8-01 Theme import scope creep. Mitigation: schema/catalog tests assert bundled curated themes and custom schema only; no VSCode tokenColors parser or import UI.
T-A8-02 Corrupt user-authored files block boot. Mitigation: Rust and TS loaders fail safe, skip invalid custom files, and preserve existing settings fields.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Define theme schema, bundled catalog, and high-contrast overlay</name>
  <files>apps/voss-app/src/themes/schema.ts, apps/voss-app/src/themes/themeCatalog.ts, apps/voss-app/src/themes/bundled/*.json, apps/voss-app/src/themes/__tests__/schema.test.ts, apps/voss-app/src/themes/__tests__/themeCatalog.test.ts</files>
  <read_first>
    - apps/voss-app/src/theme/applyTheme.ts - CSS variable application seam
    - apps/voss-app/src/styles/variant-b.css - required token names
    - apps/voss-app/src/pane/PaneComponent.tsx - current hardcoded xterm colors to replace later
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - theme and high-contrast contracts
  </read_first>
  <action>
    Write failing tests first for theme validation, 12 bundled theme IDs, required CSS variables, 16 ANSI colors, light/dark metadata, high-contrast overlay ordering, and no VSCode import fields. Implement schema/catalog modules and bundled JSON theme files. Include Variant B as the default bundled theme. Keep component code free of raw colors.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/themes</automated>
  </verify>
  <acceptance_criteria>
    - Catalog exposes exactly the 12 A8 themes from UI-SPEC.
    - Every bundled theme validates against required CSS vars plus `ansi[0..15]`.
    - High-contrast overlay applies after the selected theme and reaches 7:1 for core pairs.
    - No VSCode `tokenColors` import path or parser exists.
  </acceptance_criteria>
  <done>Theme catalog and contrast overlay are testable without UI.</done>
</task>

<task type="execute">
  <name>Task 2: Add Rust theme/profile IO and Tauri wrappers</name>
  <files>crates/voss-app-core/src/themes.rs, crates/voss-app-core/src/profiles.rs, crates/voss-app-core/src/lib.rs, apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - crates/voss-app-core/src/session.rs - locked write + fail-safe load pattern
    - crates/voss-app-core/src/keymap.rs - settings.json preservation pattern
    - apps/voss-app/src-tauri/src/lib.rs - app-crate wrapper pattern
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md - D-05..D-07, D-12, D-14
  </read_first>
  <action>
    Implement `themes.rs` for custom theme load/list validation under `.voss/themes/<name>.json` and `profiles.rs` for `~/.config/voss-app/profiles/<name>.json` full settings snapshots. Add Tauri wrappers for list/load/save theme/profile operations and active theme/profile persistence in settings.json while preserving unknown keys.
  </action>
  <verify>
    <automated>cargo test -p voss-app-core themes profiles && cargo build -p voss-app</automated>
  </verify>
  <acceptance_criteria>
    - Missing/corrupt/unsupported custom themes and profiles do not panic.
    - Writes create parent directories only on write.
    - settings.json unknown fields survive theme/profile updates.
    - Tauri wrappers are thin and registered in `generate_handler!`.
  </acceptance_criteria>
  <done>Rust-side IO exists for A8 theme/profile state.</done>
</task>

<task type="execute">
  <name>Task 3: Add frontend profile snapshot helpers</name>
  <files>apps/voss-app/src/appearance/profiles.ts, apps/voss-app/src/appearance/__tests__/profiles.test.ts</files>
  <read_first>
    - apps/voss-app/src/command-palette/keymapStorage.ts - invoke wrapper style
    - apps/voss-app/src/themes/schema.ts - theme ids and settings shape
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - profile row and copy contract
  </read_first>
  <action>
    Add typed frontend helpers for listing, loading, saving, applying, and previewing full settings profiles. Keep profile switching independent from the A9 settings form. Do not auto-create example profiles for real users.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/appearance src/themes</automated>
  </verify>
  <acceptance_criteria>
    - Profile helpers use Tauri invoke wrappers and stable copy constants.
    - Active/pinned labels are data fields, not visual badges baked into state.
    - No A9 two-pane settings UI is introduced.
  </acceptance_criteria>
  <done>Profile data is ready for command/tab context surfaces.</done>
</task>
</tasks>

<verification>
Run focused frontend tests, Rust theme/profile tests, and `cargo build -p voss-app`.
</verification>

<success_criteria>
- Theme/profile substrate satisfies UXP-09..14 and UXP-25..27 without UI scope creep.
- High-contrast overlay foundation exists for UXP-21.
</success_criteria>

