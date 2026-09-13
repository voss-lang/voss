---
phase: A7-voss-app-command-palette-keymap
plan: 04
type: execute
wave: 3
depends_on: [A7-02, A7-03]
files_modified:
  - apps/voss-app/src/command-palette/prefixMode.ts
  - apps/voss-app/src/command-palette/__tests__/prefixMode.test.ts
  - apps/voss-app/src/grid/PaneHeader.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx
  - apps/voss-app/src/App.tsx
autonomous: true
requirements: [CMD-05, CMD-07]
must_haves:
  truths:
    - "D-10: Cmd+B opens a 1.5s tmux prefix window with mapped keys %, \", o, x, c"
    - "D-10: Esc cancels prefix and unrecognized keys cancel plus pass through to PTY"
    - "D-10: focused pane header shows `[Cmd+B...]` while prefix is active"
    - "D-11: prefix mode is active only under tmux profile"
  artifacts:
    - path: "apps/voss-app/src/command-palette/prefixMode.ts"
      provides: "tmux prefix state machine"
      contains: "1500"
---

<objective>
Implement tmux-friendly Cmd+B prefix mode and its focused-pane header indicator.
</objective>

<context>
@.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md
@apps/voss-app/src/grid/PaneHeader.tsx
@apps/voss-app/src/grid/SplitNode.tsx
@apps/voss-app/src/command-palette/registry.ts
</context>

<threat_model>
T-A7-07 Prefix mode traps user input. Mitigation: timeout, Esc cancel, and unknown-key pass-through are all tested.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add tmux prefix state machine</name>
  <files>apps/voss-app/src/command-palette/prefixMode.ts, apps/voss-app/src/command-palette/__tests__/prefixMode.test.ts</files>
  <read_first>
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md - D-10/D-11
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - Tmux Prefix Indicator Contract
    - apps/voss-app/src/command-palette/chords.ts - normalized chord strings
    - apps/voss-app/src/command-palette/registry.ts - mapped command ids
  </read_first>
  <behavior>
    - Test 1: Cmd+B enters prefix mode only when profile is `tmux`.
    - Test 2: `%` dispatches split vertical and clears prefix.
    - Test 3: `"` dispatches split horizontal and clears prefix.
    - Test 4: `o`, `x`, and `c` dispatch next pane, close pane, and new/fork pane command ids.
    - Test 5: timeout after 1500ms clears prefix.
    - Test 6: unknown key returns pass-through and clears prefix.
  </behavior>
  <action>
    Create `prefixMode.ts` with a small state machine that receives normalized key events, active profile, timer callbacks, and registry dispatch function. It must return whether the event was consumed. Map `%` to vertical split, `"` to horizontal split, `o` to focus next pane, `x` to close pane, and `c` to new/fork pane according to the command id chosen in `registry.ts`. Do not implement zoom or scroll mode.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/prefixMode.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - Prefix mode is unavailable under `vscode` profile.
    - All five mapped keys dispatch expected command ids.
    - Timeout/Esc/unknown-key semantics match A7-CONTEXT.
    - Tests pass.
  </acceptance_criteria>
  <done>tmux prefix state machine is deterministic.</done>
</task>

<task type="execute" tdd="true">
  <name>Task 2: Render focused-pane prefix indicator</name>
  <files>apps/voss-app/src/grid/PaneHeader.tsx, apps/voss-app/src/grid/SplitNode.tsx, apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/PaneHeader.tsx - current 22px header segments
    - apps/voss-app/src/grid/SplitNode.tsx - header prop plumbing
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - indicator placement and copy
  </read_first>
  <behavior>
    - Test 1: focused pane header renders `[Cmd+B...]` while prefix is active.
    - Test 2: unfocused panes never render the indicator.
    - Test 3: tmux profile reserves indicator width to avoid header shift.
    - Test 4: indicator disappears after cancel/dispatch/timeout.
  </behavior>
  <action>
    Add a narrow prop such as `prefixActive?: boolean` and `prefixReserved?: boolean` through `SplitNode` to `PaneHeader`. Render `[Cmd+B...]` immediately before the pane menu trigger, color `--accent-amber`, font 11px/400, no border/background. Reserve 72px only under tmux profile as required by A7-UI-SPEC. Wire App prefix state to the focused pane only.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/grid/__tests__/PaneChrome.test.tsx src/command-palette/__tests__/prefixMode.test.ts src/__tests__/App.test.tsx && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - Indicator copy is exactly `[Cmd+B...]`.
    - Indicator appears only on focused pane.
    - Header remains 22px high.
    - Build passes.
  </acceptance_criteria>
  <done>tmux prefix mode is visible and non-disruptive.</done>
</task>
</tasks>

<verification>
Run prefix, pane chrome, and App tests plus TypeScript build.
</verification>

<success_criteria>
- tmux profile supports Cmd+B prefix behavior without trapping unknown PTY input.
- Focused pane communicates prefix state in existing Variant B chrome.
</success_criteria>

