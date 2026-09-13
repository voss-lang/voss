---
phase: A8-voss-app-workspaces-ux-polish-theming
plan: 03
type: execute
wave: 3
depends_on: [A8-02]
files_modified:
  - apps/voss-app/src/components/workspace/WorkspaceTabBar.tsx
  - apps/voss-app/src/components/workspace/NewWorkspacePicker.tsx
  - apps/voss-app/src/components/workspace/workspace.css
  - apps/voss-app/src/components/workspace/__tests__/WorkspaceTabBar.test.tsx
  - apps/voss-app/src/components/workspace/__tests__/NewWorkspacePicker.test.tsx
  - apps/voss-app/src/workspaces/workspaceShortcuts.ts
  - apps/voss-app/src/workspaces/__tests__/workspaceShortcuts.test.ts
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/__tests__/App.test.tsx
  - apps/voss-app/src/command-palette/registry.ts
  - apps/voss-app/src/command-palette/nativeMenu.ts
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-03-SUMMARY.md
autonomous: true
requirements: [UXP-01, UXP-03, UXP-04, UXP-05, UXP-07, UXP-08, UXP-26, UXP-27]
must_haves:
  truths:
    - "Workspace tabbar lives below titlebar and above pane area"
    - "Accent colors use fixed Warp-style dot palette"
    - "Ctrl+1..9 switches workspaces; Cmd+1..9 remains pane focus"
    - "No settings page or onboarding wizard is introduced"
---

<objective>
Ship the workspace tab bar, new workspace picker, tab context menu, reordering, and workspace shortcuts.
</objective>

<context>
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PATTERNS.md
</context>

<threat_model>
T-A8-05 Workspace chrome causes layout shift or shortcut regression. Mitigation: fixed dimensions, focused tests for Ctrl workspace shortcuts vs Cmd pane shortcuts, and tab hover/drag no-height-change tests.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Build WorkspaceTabBar and context menu</name>
  <files>apps/voss-app/src/components/workspace/WorkspaceTabBar.tsx, apps/voss-app/src/components/workspace/workspace.css, apps/voss-app/src/components/workspace/__tests__/WorkspaceTabBar.test.tsx</files>
  <read_first>
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - Workspace Tab Bar Contract
    - apps/voss-app/src/components/titlebar/Titlebar.tsx - chrome precedent
    - apps/voss-app/src/grid/DotMenu.tsx - popover precedent
    - apps/voss-app/src/command-palette/toast.tsx - feedback surface
  </read_first>
  <action>
    Write component tests first for active/inactive tabs, fixed dot palette, rename action, color picker, close action, last-workspace disabled behavior, and stable dimensions. Implement `WorkspaceTabBar` and compact context popover using Variant B tokens only.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/components/workspace/__tests__/WorkspaceTabBar.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Tab bar is 28px, tabs are 24px, and hover/close reveal does not resize tabs.
    - Fixed eight-color dot palette is rendered; no custom hex input exists.
    - Last workspace close is blocked with `Last workspace stays open`.
    - Running-process close confirmation uses UI-SPEC copy.
  </acceptance_criteria>
  <done>Workspace tab chrome matches A8 UI-SPEC.</done>
</task>

<task type="execute">
  <name>Task 2: Build NewWorkspacePicker and project-open integration</name>
  <files>apps/voss-app/src/components/workspace/NewWorkspacePicker.tsx, apps/voss-app/src/components/workspace/__tests__/NewWorkspacePicker.test.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/components/setup/SetupWindow.tsx - project open copy and recents
    - apps/voss-app/src/project/projectStorage.ts - pickFolder/openProject/defaultCwd
    - apps/voss-app/src/grid/layoutStorage.ts - layout preset listing/loading
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - New Workspace Picker Contract
  </read_first>
  <action>
    Implement centered new workspace picker with workspace name, folder action, shell row, layout row, fixed color dots, `Create workspace`, and `Start empty`. Wire it to existing folder picker/project open/default cwd seams and workspace store. Keep L2 agent selection out of scope.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/components/workspace/__tests__/NewWorkspacePicker.test.tsx src/__tests__/App.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - `+` opens picker; Esc/outside dismisses; Enter submits when valid.
    - Folder workspace uses selected project path and restore/default layout priority.
    - `Start empty` creates a project-less workspace.
    - No onboarding or agent selector UI exists.
  </acceptance_criteria>
  <done>Users can create workspace tabs from UI.</done>
</task>

<task type="execute">
  <name>Task 3: Wire workspace shortcuts and registry/native-menu commands</name>
  <files>apps/voss-app/src/workspaces/workspaceShortcuts.ts, apps/voss-app/src/workspaces/__tests__/workspaceShortcuts.test.ts, apps/voss-app/src/App.tsx, apps/voss-app/src/command-palette/registry.ts, apps/voss-app/src/command-palette/nativeMenu.ts</files>
  <read_first>
    - apps/voss-app/src/command-palette/registry.ts - A7 command catalog
    - apps/voss-app/src/command-palette/chords.ts - chord normalization
    - apps/voss-app/src/App.tsx - capture-phase palette routing
    - apps/voss-app/src/grid/keymap.ts - Cmd+1..9 pane focus contract
  </read_first>
  <action>
    Add workspace commands (`workspace.new`, `workspace.close`, `workspace.next`, `workspace.prev`, `workspace.focus1..9`, `workspace.rename`, `workspace.color`, `profile.switch`) to A7 registry/native-menu model. Implement Ctrl+1..9 and Ctrl+Tab/Ctrl+Shift+Tab routing without stealing Cmd+1..9 pane focus. Wire profile switching entrypoints only if A7 command handlers are available.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- --run src/workspaces src/command-palette src/__tests__/App.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Ctrl workspace shortcuts work and preserve Cmd pane shortcuts.
    - Workspace commands appear in registry/native menu model.
    - Command labels match UI-SPEC copy.
    - Profile switch command uses existing A7 surface instead of a new modal.
  </acceptance_criteria>
  <done>Workspace UI is keyboard and command-palette reachable.</done>
</task>
</tasks>

<verification>
Run focused workspace component tests, command-palette registry tests, and App tests.
</verification>

<success_criteria>
- Users can create, switch, rename, color, reorder, and close workspace tabs.
- Workspace shortcuts and command registry integration satisfy UXP-03..08 and UXP-26..27.
</success_criteria>

