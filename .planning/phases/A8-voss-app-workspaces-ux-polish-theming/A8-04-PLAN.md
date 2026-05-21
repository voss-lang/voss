---
phase: A8-voss-app-workspaces-ux-polish-theming
plan: 04
type: execute
wave: 4
depends_on: [A8-01, A8-02, A8-03]
files_modified:
  - apps/voss-app/src/appearance/settings.ts
  - apps/voss-app/src/appearance/fontStorage.ts
  - apps/voss-app/src/appearance/windowEffects.ts
  - apps/voss-app/src/appearance/__tests__/settings.test.ts
  - apps/voss-app/src/appearance/__tests__/fontStorage.test.ts
  - apps/voss-app/src/themes/themeRuntime.ts
  - apps/voss-app/src/themes/__tests__/themeRuntime.test.ts
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/pane/pane.css
  - apps/voss-app/src/grid/DragHandle.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx
  - apps/voss-app/src/index.css
  - crates/voss-app-core/src/fonts.rs
  - apps/voss-app/src-tauri/src/lib.rs
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-04-SUMMARY.md
autonomous: true
requirements: [UXP-12, UXP-14, UXP-15, UXP-16, UXP-17, UXP-18, UXP-19, UXP-21, UXP-22, UXP-23, UXP-24]
must_haves:
  truths:
    - "Theme/font/profile changes preview live without remounting panes"
    - "Reduced motion globally disables transitions and animations"
    - "Minimum font size floor is 10px"
    - "Pane chrome polish never changes pane layout dimensions"
---

<objective>
Wire live theme/font/cursor/bell settings, accessibility overlays, transitions, and pane chrome polish.
</objective>

<context>
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PATTERNS.md
</context>

<threat_model>
T-A8-06 Theme/font preview remounts terminal panes or loses buffers. Mitigation: runtime update tests and no GridRoot remount on theme/font apply.
T-A8-07 Accessibility controls pass visually but fail user preference. Mitigation: automated contrast, font floor, and reduced-motion tests.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Apply themes and ANSI colors to live xterm instances</name>
  <files>apps/voss-app/src/themes/themeRuntime.ts, apps/voss-app/src/themes/__tests__/themeRuntime.test.ts, apps/voss-app/src/pane/PaneComponent.tsx, apps/voss-app/src/theme/applyTheme.ts</files>
  <read_first>
    - apps/voss-app/src/pane/PaneComponent.tsx - current xterm theme literals
    - apps/voss-app/src/theme/applyTheme.ts - CSS variable seam
    - apps/voss-app/src/pane/scrollbackRegistry.ts - module-level registry pattern
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - Theme Contract
  </read_first>
  <action>
    Add a theme runtime service that applies CSS vars and broadcasts xterm theme updates to live panes without remounting them. Replace hardcoded xterm colors with theme-derived values. Support hover preview and cancel-to-committed-theme behavior for theme picker rows.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/themes src/pane</automated>
  </verify>
  <acceptance_criteria>
    - Theme switch updates root vars and xterm ANSI colors.
    - Terminal instances are not disposed/remounted during theme preview/apply.
    - Esc/cancel restores the committed theme after preview.
    - Theme apply path stays under the existing `applyThemeOverrides()` seam.
  </acceptance_criteria>
  <done>Theme hot-swap reaches chrome and terminal panes.</done>
</task>

<task type="execute">
  <name>Task 2: Add font, cursor, bell, and high-contrast settings runtime</name>
  <files>apps/voss-app/src/appearance/settings.ts, apps/voss-app/src/appearance/fontStorage.ts, apps/voss-app/src/appearance/__tests__/settings.test.ts, apps/voss-app/src/appearance/__tests__/fontStorage.test.ts, crates/voss-app-core/src/fonts.rs, apps/voss-app/src-tauri/src/lib.rs, apps/voss-app/src/pane/PaneComponent.tsx</files>
  <read_first>
    - apps/voss-app/package.json - current dependencies
    - apps/voss-app/src/pane/PaneComponent.tsx - xterm font/cursor/bell options
    - crates/voss-app-core/src/project.rs - simple command helper pattern
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md - D-12/D-13
  </read_first>
  <action>
    Implement appearance settings helpers for font family/size/line-height/letter-spacing/ligatures, cursor shape/blink/color, bell behavior, high-contrast toggle, and reduced-motion toggle. Add Rust font enumeration with JetBrains Mono fallback. Enforce 10px minimum font size and safe fallback when selected font is unavailable.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/appearance src/pane && cargo test -p voss-app-core fonts</automated>
  </verify>
  <acceptance_criteria>
    - Font size below 10px is clamped to 10px.
    - Font preview updates open panes.
    - Cursor shapes are block/bar/underline only.
    - Bell options are visual flash, audible, none, badge only.
    - High contrast overlay passes core 7:1 contrast tests.
  </acceptance_criteria>
  <done>Appearance and accessibility settings are live and validated.</done>
</task>

<task type="execute">
  <name>Task 3: Add CSS transitions, reduced-motion kill switch, and pane chrome polish</name>
  <files>apps/voss-app/src/index.css, apps/voss-app/src/pane/pane.css, apps/voss-app/src/grid/DragHandle.tsx, apps/voss-app/src/grid/SplitNode.tsx, apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/DragHandle.tsx - resize handle behavior
    - apps/voss-app/src/grid/SplitNode.tsx - pane layout and close banners
    - apps/voss-app/src/pane/pane.css - scrollbar and terminal CSS
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - Pane Chrome Polish Contract
  </read_first>
  <action>
    Add only the allowed CSS transitions and global reduced-motion kill switch. Refine resize handle hover state, focus indicator consistency across themes, bell visual flash, and theme-aware scrollbars. Do not add badges, extra rows, gradients, or pane-level theme overrides.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/grid/__tests__/PaneChrome.test.tsx src/themes && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - Reduced motion disables all transitions/animations globally.
    - Hover/focus states do not change pane dimensions.
    - Pane chrome remains 0px radius and token-only.
    - No status bar, badges, or agent/cost semantics are introduced.
  </acceptance_criteria>
  <done>A8 polish improves feel without destabilizing terminal layout.</done>
</task>
</tasks>

<verification>
Run focused appearance/theme/pane tests plus frontend build.
</verification>

<success_criteria>
- UXP-12/14/15/16/17/18/19/21/22/23/24 are covered by automated tests where possible.
- Manual visual review remains only for subjective platform/vibrancy quality.
</success_criteria>

