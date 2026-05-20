---
phase: A6-voss-app-session-persist
plan: 03
type: execute
wave: 3
depends_on: [A6-02]
files_modified:
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/pane/scrollbackRegistry.ts
  - apps/voss-app/src/pane/__tests__/scrollbackRegistry.test.ts
  - apps/voss-app/src/grid/SplitNode.tsx
autonomous: true
requirements: [PER-01, PER-02]
must_haves:
  truths:
    - "Scrollback is extracted on demand from xterm buffer.normal, never buffer.active"
    - "Scrollback is stored as plain text with ANSI stripped by xterm line translation"
    - "Restored text is seeded into the pane for context only; live processes are not restarted"
  artifacts:
    - path: "apps/voss-app/src/pane/scrollbackRegistry.ts"
      provides: "Per-pane scrollback extractor registry"
      contains: "getScrollbackSnapshot"
    - path: "apps/voss-app/src/pane/PaneComponent.tsx"
      provides: "Pane registration and restored text seed"
      contains: "buffer.normal"
---

<objective>
Expose a narrow pane-level scrollback seam: the session lifecycle can ask each pane for last-2k normal-buffer lines on quit and pass restored lines back into a fresh pane on launch.
</objective>

<context>
@.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md
@.planning/phases/A6-voss-app-session-persist/A6-RESEARCH.md
@apps/voss-app/src/pane/PaneComponent.tsx
@apps/voss-app/src/grid/SplitNode.tsx
@apps/voss-app/src/grid/tree.ts
</context>

<threat_model>
T-A6-04 Terminal escape persistence. Mitigation: use xterm line `translateToString(true)` from `buffer.normal`, not raw PTY bytes or ANSI-preserving serialization.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add per-pane scrollback registry</name>
  <files>apps/voss-app/src/pane/scrollbackRegistry.ts, apps/voss-app/src/pane/__tests__/scrollbackRegistry.test.ts</files>
  <read_first>
    - apps/voss-app/src/pane/PaneComponent.tsx - xterm ownership and cleanup style
    - .planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md - D-01/D-02/D-03 contracts
  </read_first>
  <action>
    Create `scrollbackRegistry.ts` exporting `registerScrollbackProvider(paneId, provider)`, `unregisterScrollbackProvider(paneId)`, `getScrollbackSnapshot(limit = 2000)`, and a test-only reset helper if needed. A provider returns `string[]`. `getScrollbackSnapshot` returns a `Record<string, string[]>`, caps each provider result to the last `limit` lines, and skips providers that throw after logging a warning. Add tests for registration, unregister cleanup, last-2k capping, thrown provider isolation, and deterministic empty snapshot.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/pane/__tests__/scrollbackRegistry.test.ts --reporter=dot && grep -q 'registerScrollbackProvider' src/pane/scrollbackRegistry.ts && grep -q 'getScrollbackSnapshot' src/pane/scrollbackRegistry.ts && echo SCROLLBACK_REGISTRY_OK</automated>
  </verify>
  <acceptance_criteria>
    - Registry cleanup removes panes on unmount.
    - A failing pane provider does not block other panes.
    - Last-2k capping is enforced.
    - `SCROLLBACK_REGISTRY_OK` prints.
  </acceptance_criteria>
  <done>Session lifecycle can collect scrollback without knowing xterm internals.</done>
</task>

<task type="execute">
  <name>Task 2: Register PaneComponent normal-buffer extraction and restored seed</name>
  <files>apps/voss-app/src/pane/PaneComponent.tsx</files>
  <read_first>
    - apps/voss-app/src/pane/PaneComponent.tsx - current `term` lifecycle, `onData`, `keyHandler`, and cleanup
    - apps/voss-app/src/pane/scrollbackRegistry.ts - registry API from Task 1
    - .planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md - D-02/D-03 and D-09
  </read_first>
  <action>
    Extend `PaneProps` with `id?: string`, `restoredScrollback?: string[]`, and `onFirstInput?: () => void`. In `onMount`, after `term.open(bodyRef)` and before normal interaction, if `restoredScrollback` has lines, write them to the terminal as plain text joined with CRLF and ending with CRLF. Register a scrollback provider under `props.id ?? String(props.index ?? 1)` that reads `term.buffer.normal`, iterates from the visible/history start to the normal-buffer length, converts each line with `translateToString(true)`, drops trailing empty padding if needed, and returns plain strings. Ensure source contains `buffer.normal` and does not use `buffer.active` in the extraction function. In `keyHandler` or `t.onData`, call `onFirstInput` once when the user types into a restored pane.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm exec tsc --noEmit -p . && grep -q 'buffer.normal' src/pane/PaneComponent.tsx && ! grep -n 'getRestoredScrollback.*buffer.active' src/pane/PaneComponent.tsx && grep -q 'restoredScrollback' src/pane/PaneComponent.tsx && echo PANE_SCROLLBACK_OK</automated>
  </verify>
  <acceptance_criteria>
    - `PaneProps` accepts pane id and restored scrollback.
    - Extraction uses `term.buffer.normal`.
    - Restored text is written before normal shell interaction is used for context.
    - First input can notify the parent to dismiss restore UI.
    - TypeScript check exits 0.
    - `PANE_SCROLLBACK_OK` prints.
  </acceptance_criteria>
  <done>Each pane can provide and receive session scrollback.</done>
</task>

<task type="execute">
  <name>Task 3: Thread pane id and restored scrollback through SplitNode</name>
  <files>apps/voss-app/src/grid/SplitNode.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/SplitNode.tsx - current leaf render and banner seam
    - apps/voss-app/src/grid/tree.ts - pane id source
  </read_first>
  <action>
    Add optional props to `SplitNodeView` for `restoredScrollbackByPaneId?: Record<string, string[]>` and `onPaneFirstInput?: (paneId: string) => void`. Thread those props recursively to children. Pass `id={asLeaf().id}`, `restoredScrollback={restoredScrollbackByPaneId?.[asLeaf().id]}`, and `onFirstInput={() => onPaneFirstInput?.(asLeaf().id)}` into `PaneComponent`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm exec tsc --noEmit -p . && grep -q 'restoredScrollbackByPaneId' src/grid/SplitNode.tsx && grep -q 'onPaneFirstInput' src/grid/SplitNode.tsx && echo SPLIT_RESTORE_THREAD_OK</automated>
  </verify>
  <acceptance_criteria>
    - Restored scrollback is keyed by saved pane id.
    - Recursive split children receive the same restore props.
    - Pane first input can be routed to the grid/app layer.
    - `SPLIT_RESTORE_THREAD_OK` prints.
  </acceptance_criteria>
  <done>Restored scrollback reaches the right pane by id.</done>
</task>
</tasks>

<verification>
Run `pnpm --dir apps/voss-app test -- --run src/pane src/grid` and `pnpm --dir apps/voss-app build`.
</verification>

<success_criteria>
- Scrollback extraction follows D-01/D-02/D-03.
- Restored panes can display text and dismiss restore state on input.
</success_criteria>

