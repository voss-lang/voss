---
phase: A6-voss-app-session-persist
plan: 04
type: execute
wave: 4
depends_on: [A6-03]
files_modified:
  - apps/voss-app/src/grid/sync.ts
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/grid/sessionPersist.ts
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/grid/__tests__/sessionPersist.test.ts
autonomous: true
requirements: [PER-01, PER-02, PER-03, PER-04, PER-05, PER-06]
must_haves:
  truths:
    - "Session restore priority is session.json, then default.json, then fresh pane"
    - "D-10/D-11: restore data is resolved before GridRoot mounts panes so a fresh shell is not spawned and then replaced"
    - "Structural auto-save writes tree/session state without reading xterm buffers"
    - "D-04/D-06: structural auto-save writes the same session file with null scrollback"
    - "D-05: quit save prevents close, captures scrollback once, writes session, then allows close via reentry guard"
    - "Project-less accepted state persists in global-session.json and can bypass setup on relaunch"
  artifacts:
    - path: "apps/voss-app/src/grid/sessionPersist.ts"
      provides: "Session lifecycle orchestration helpers"
      contains: "installCloseSessionSave"
    - path: "apps/voss-app/src/App.tsx"
      provides: "Restore priority and session lifecycle wiring"
      contains: "loadSession"
---

<objective>
Wire session persistence into the app lifecycle: restore on launch, debounce tree-only saves after structural changes, and block quit long enough to save scrollback.
</objective>

<context>
@.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md
@.planning/phases/A6-voss-app-session-persist/A6-RESEARCH.md
@apps/voss-app/src/App.tsx
@apps/voss-app/src/grid/GridRoot.tsx
@apps/voss-app/src/grid/sync.ts
@apps/voss-app/src/grid/sessionCommands.ts
@apps/voss-app/src/grid/sessionStorage.ts
@apps/voss-app/src/pane/scrollbackRegistry.ts
</context>

<threat_model>
T-A6-05 Quit data loss. Mitigation: close-request handler calls `preventDefault()` before async work, captures scrollback once, and only closes after save resolves.
T-A6-06 Infinite close loop. Mitigation: reentry guard lets the second close request pass after a successful save.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Add structural-change subscription for debounced tree-only save</name>
  <files>apps/voss-app/src/grid/sync.ts, apps/voss-app/src/grid/sessionPersist.ts, apps/voss-app/src/grid/__tests__/sessionPersist.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/sync.ts - current `markStructuralChange`
    - apps/voss-app/src/grid/sessionCommands.ts - `buildSessionFile`
    - apps/voss-app/src/grid/sessionStorage.ts - save wrappers
  </read_first>
  <action>
    Extend `sync.ts` with a small listener API such as `subscribeStructuralChange(listener)` that is called by `markStructuralChange(state)` after the Rust mirror sync is scheduled. Implement `sessionPersist.ts` with `installStructuralSessionAutosave(options)` that subscribes to structural changes, debounces around 2 seconds, builds a session with scrollback map `{}` or null entries only, and calls `saveSession` or `saveGlobalSession` based on current project/project-less state. Return a cleanup function that clears the debounce timer and unsubscribes. Add tests with fake timers proving multiple structural changes collapse to one save and no xterm scrollback provider is called in this path.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/sessionPersist.test.ts --reporter=dot && grep -q 'subscribeStructuralChange' src/grid/sync.ts && grep -q 'installStructuralSessionAutosave' src/grid/sessionPersist.ts && echo SESSION_AUTOSAVE_OK</automated>
  </verify>
  <acceptance_criteria>
    - Structural changes trigger a debounced session save.
    - Debounce collapses repeated changes into one save.
    - Autosave does not read xterm scrollback.
    - Cleanup unsubscribes and clears timers.
    - `SESSION_AUTOSAVE_OK` prints.
  </acceptance_criteria>
  <done>Crash-safe tree-only autosave is available.</done>
</task>

<task type="execute">
  <name>Task 2: Extend GridController for applying restored sessions</name>
  <files>apps/voss-app/src/grid/GridRoot.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/GridRoot.tsx - controllerRef, snapshot, applyLoadedLayout
    - apps/voss-app/src/grid/sessionCommands.ts - `applySessionFile`
    - apps/voss-app/src/grid/SplitNode.tsx - restored scrollback threading from A6-03
  </read_first>
  <action>
    Add controller methods and initial-state props needed by App-level restore, for example `initialSession?: SessionFile`, `applySession(session)`, and `snapshot()`. On first render, `GridRoot` must initialize from `initialSession` when provided so saved panes mount directly and no throwaway default pane/PTY is spawned before restore. `applySession` must call the pure `applySessionFile`, set `store.root`, `store.focusedId`, report the restored `activeLayout` through `onLayoutChange`, and store/forward `restoredScrollbackByPaneId` to `SplitNodeView`. Add a local signal or store for restore banner line counts keyed by pane id; expose a way for first input to clear the pane id. Do not start any old process or serialize PTY ids.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm exec tsc --noEmit -p . && grep -q 'applySession' src/grid/GridRoot.tsx && grep -q 'restoredScrollbackByPaneId' src/grid/GridRoot.tsx && echo GRID_SESSION_APPLY_OK</automated>
  </verify>
  <acceptance_criteria>
    - Restored session sets root and focused pane from saved session before panes mount when `initialSession` is available.
    - Active layout is restored from session active preset.
    - Restored scrollback is available to panes by id.
    - No PTY/process id appears in restored state.
    - `GRID_SESSION_APPLY_OK` prints.
  </acceptance_criteria>
  <done>GridRoot can apply a restored session.</done>
</task>

<task type="execute">
  <name>Task 3: Wire App restore priority and close-request full save</name>
  <files>apps/voss-app/src/App.tsx, apps/voss-app/src/grid/sessionPersist.ts</files>
  <read_first>
    - apps/voss-app/src/App.tsx - activeLayout and A4 default layout flow
    - apps/voss-app/src/grid/sessionStorage.ts - load/save wrappers
    - apps/voss-app/src/pane/scrollbackRegistry.ts - full quit capture
    - Tauri v2 docs: `getCurrentWindow().onCloseRequested`
  </read_first>
  <action>
    In `App.tsx`, after A5 project/project-less state is known but before rendering `GridRoot`, resolve initial grid data in this order for project mode: `loadSession(project.path)`, then `loadDefaultLayout(project.path)`, then fresh pane. Keep a small boot/loading branch while this async restore decision is pending, so no default PTY starts before the selected session/default state is known. For project-less mode, load `loadGlobalSession()` and only bypass setup when `projectLessAccepted` is true. Pass the resolved session/default/fresh decision into `GridRoot` through explicit initial props. Install structural autosave with project path or global mode. Install a close-request handler through `getCurrentWindow().onCloseRequested`: immediately `event.preventDefault()` unless a reentry flag is set; collect `getScrollbackSnapshot(2000)`; build a full session; save project/global target; set reentry flag; call `getCurrentWindow().close()`. On save failure, keep the window open and log the error rather than dropping the user's quit-time scrollback silently; the user can retry quit or force-kill. Test/source-assert this behavior.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm exec tsc --noEmit -p . && grep -q 'onCloseRequested' src/App.tsx src/grid/sessionPersist.ts && grep -q 'preventDefault' src/App.tsx src/grid/sessionPersist.ts && grep -q 'getScrollbackSnapshot' src/App.tsx src/grid/sessionPersist.ts && grep -q 'loadDefaultLayout' src/App.tsx && echo APP_SESSION_LIFECYCLE_OK</automated>
  </verify>
  <acceptance_criteria>
    - Project restore priority is session, then default layout, then fresh, resolved before `GridRoot` mounts panes.
    - Global project-less session can bypass setup only when `projectLessAccepted` is true.
    - Close-request handler prevents close before async save.
    - Full quit save includes scrollback snapshot capped to 2,000 lines.
    - Reentry guard prevents close-loop.
    - `APP_SESSION_LIFECYCLE_OK` prints.
  </acceptance_criteria>
  <done>App lifecycle persists and restores sessions.</done>
</task>
</tasks>

<verification>
Run `pnpm --dir apps/voss-app test -- --run src/grid src/App` and `pnpm --dir apps/voss-app build`.
</verification>

<success_criteria>
- Session restore wins over default layout.
- Structural autosave preserves tree/focus/preset cheaply.
- Quit save captures scrollback without recurring CPU cost.
</success_criteria>
