---
phase: A7-voss-app-command-palette-keymap
plan: 01
type: execute
wave: 1
depends_on: [A7-00]
files_modified:
  - apps/voss-app/src/command-palette/chords.ts
  - apps/voss-app/src/command-palette/fuzzy.ts
  - apps/voss-app/src/command-palette/registry.ts
  - apps/voss-app/src/command-palette/__tests__/chords.test.ts
  - apps/voss-app/src/command-palette/__tests__/fuzzy.test.ts
  - apps/voss-app/src/command-palette/__tests__/registry.test.ts
autonomous: true
requirements: [CMD-02, CMD-03, CMD-04, CMD-05]
must_haves:
  truths:
    - "D-01: one typed CommandRegistry is the source for command metadata and handlers"
    - "D-02: current A3/A4 chords migrate to registry dispatch without PTY pass-through regression"
    - "D-07: fuzzy search is case-insensitive substring matching with recency boost and no external dependency"
    - "D-11/D-13/D-15: command ids support profile/override binding lookup and validation later"
  artifacts:
    - path: "apps/voss-app/src/command-palette/registry.ts"
      provides: "Command type, AppContext type shell, registry creation, dispatch, and command catalog"
      contains: "CommandRegistry"
---

<objective>
Create the pure command registry, chord normalizer, fuzzy scoring, and tests that replace the old switch-based keymap as the single command source.
</objective>

<context>
@.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-RESEARCH.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-PATTERNS.md
@apps/voss-app/src/grid/keymap.ts
@apps/voss-app/src/grid/__tests__/keymap.test.ts
</context>

<threat_model>
T-A7-01 Command spoofing or drift. Mitigation: command ids are explicit, registry metadata is typed, and all public surfaces read the same definitions.
T-A7-02 Terminal input breakage. Mitigation: tests assert unmatched chords return false and do not prevent PTY pass-through.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add chord normalization and fuzzy scoring</name>
  <files>apps/voss-app/src/command-palette/chords.ts, apps/voss-app/src/command-palette/fuzzy.ts, apps/voss-app/src/command-palette/__tests__/chords.test.ts, apps/voss-app/src/command-palette/__tests__/fuzzy.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/keymap.ts - current key/code handling
    - apps/voss-app/src/grid/__tests__/keymap.test.ts - expected chord behavior
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md - D-07 and D-10
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - key labels and row behavior
  </read_first>
  <behavior>
    - Test 1: Cmd+D normalizes to `Cmd+D`; Cmd+Shift+D normalizes to `Cmd+Shift+D`.
    - Test 2: Cmd+Backslash, Cmd+Shift+Backslash, Cmd+[ and Cmd+] preserve current A3 behavior.
    - Test 3: non-modified printable keys normalize for tmux prefix dispatch.
    - Test 4: fuzzy search is case-insensitive substring matching.
    - Test 5: recent command ids receive a deterministic score boost over otherwise equal matches.
  </behavior>
  <action>
    Create `chords.ts` with `normalizeChord(evt: KeyboardEvent): string | null`, `formatChord(chord: string): string`, and helpers for prefix-mode keys. Use concrete chord strings such as `Cmd+D`, `Cmd+Shift+D`, `Cmd+\`, `Cmd+Shift+\`, `Cmd+G`, `Cmd+Alt+ArrowRight`, and `%`. Create `fuzzy.ts` with `scoreCommand(query, item, recentIds)` and `rankCommandItems(query, items, recentIds)`. Do not add any package.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/chords.test.ts src/command-palette/__tests__/fuzzy.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - Chord strings preserve all A3/A4 command cases.
    - Unrecognized keyboard events normalize to null or a pass-through prefix key as appropriate.
    - Fuzzy ranking has no external dependency.
    - Tests prove recency boost behavior.
  </acceptance_criteria>
  <done>Chord and fuzzy primitives are deterministic and tested.</done>
</task>

<task type="tdd">
  <name>Task 2: Add typed CommandRegistry and v0 command catalog shell</name>
  <files>apps/voss-app/src/command-palette/registry.ts, apps/voss-app/src/command-palette/__tests__/registry.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/keymap.ts - operations currently mapped by chord
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md - D-01..D-04, D-09, D-11
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - categories and command labels
  </read_first>
  <behavior>
    - Test 1: registry exposes Window, Pane, Layout, Project, Settings, and Help categories.
    - Test 2: command ids are unique.
    - Test 3: dispatch returns true for handled chords and false for unmatched chords.
    - Test 4: registry metadata exposes label/category/chord hints for palette rows.
  </behavior>
  <action>
    Create `registry.ts` with exported `CommandCategory`, `CommandDefinition`, `Command`, `CommandRegistry`, `AppContext`, and `createCommandRegistry(ctx)` or equivalent factory. Include v0 command definitions for existing A3/A4 operations: split right, split below, close pane, equalize panes, cycle layout, focus next/previous, focus index 1-9, directional focus, directional resize, open quick palette, open command palette, switch keymap profile, open project, save layout as, load layout, and help/keybindings. Use category names exactly from A7-UI-SPEC. Handlers may call typed AppContext callbacks but must not import Solid component state directly.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/registry.test.ts && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - `CommandRegistry` is the only new command metadata source.
    - Each command has id, label, category, optional keybinding, and handler.
    - All six v0 categories are present.
    - Dispatch and metadata tests pass.
  </acceptance_criteria>
  <done>The registry can drive keyboard, palette, and native menu surfaces.</done>
</task>
</tasks>

<verification>
Run command-palette unit tests and `pnpm --dir apps/voss-app build`.
</verification>

<success_criteria>
- A7 has a typed single command source with tested chord and fuzzy primitives.
- Existing A3/A4 keymap behavior is represented by registry commands.
</success_criteria>

