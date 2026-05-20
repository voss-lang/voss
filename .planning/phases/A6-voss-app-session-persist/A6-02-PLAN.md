---
phase: A6-voss-app-session-persist
plan: 02
type: execute
wave: 2
depends_on: [A6-01]
files_modified:
  - apps/voss-app/src/grid/sessionStorage.ts
  - apps/voss-app/src/grid/sessionCommands.ts
  - apps/voss-app/src/grid/__tests__/sessionStorage.test.ts
  - apps/voss-app/src/grid/__tests__/sessionCommands.test.ts
autonomous: true
requirements: [PER-01, PER-02, PER-03, PER-04, PER-05]
must_haves:
  truths:
    - "Frontend session storage wrappers are thin Tauri invoke calls"
    - "Pure session transforms serialize only GridState, active preset, project-less flag, and per-pane scrollback"
    - "Session restore preserves saved pane ids because restore happens before live user panes exist"
  artifacts:
    - path: "apps/voss-app/src/grid/sessionStorage.ts"
      provides: "TypeScript SessionFile type and Tauri invoke wrappers"
      contains: "saveSession"
    - path: "apps/voss-app/src/grid/sessionCommands.ts"
      provides: "Pure build/apply helpers for session snapshots"
      contains: "buildSessionFile"
---

<objective>
Add frontend session types, invoke wrappers, and pure snapshot/restore helpers so app lifecycle code can save and restore without embedding serialization rules inline.
</objective>

<context>
@.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md
@.planning/phases/A6-voss-app-session-persist/A6-PATTERNS.md
@apps/voss-app/src/grid/layoutStorage.ts
@apps/voss-app/src/grid/layoutCommands.ts
@apps/voss-app/src/grid/tree.ts
</context>

<threat_model>
T-A6-03 State over-serialization. Mitigation: pure clone helpers whitelist only canonical tree fields plus explicit scrollback arrays; PTY ids, process names, and foreground state cannot enter the session file.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add sessionStorage invoke wrappers and copy constants</name>
  <files>apps/voss-app/src/grid/sessionStorage.ts, apps/voss-app/src/grid/__tests__/sessionStorage.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/layoutStorage.ts - exact wrapper/test style
    - apps/voss-app/src-tauri/src/lib.rs - command names from A6-01
    - crates/voss-app-core/src/session.rs - wire shape from A6-01
  </read_first>
  <action>
    Create `sessionStorage.ts` exporting TypeScript types `SessionPane` and `SessionFile` matching the Rust JSON shape: `version: 1`, `activePreset`, `grid`, `panes`, and `projectLessAccepted`. Add `saveSession(workspacePath, session)`, `loadSession(workspacePath)`, `saveGlobalSession(session)`, and `loadGlobalSession()` wrappers using `invoke()` with exact command names and payload keys. Add constants for `SESSION_SAVE_FAILED`, `SESSION_LOAD_FAILED`, `SESSION_INVALID_FILE`, and `SESSION_UNSUPPORTED_VERSION` if those strings are surfaced from Rust. Add tests mirroring `layoutStorage.test.ts` that assert exact invoke names, payload keys, null load handling, and rejected error strings.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/sessionStorage.test.ts --reporter=dot && grep -q \"invoke('save_session'\" src/grid/sessionStorage.ts && grep -q \"invoke('load_global_session'\" src/grid/sessionStorage.ts && echo SESSION_STORAGE_OK</automated>
  </verify>
  <acceptance_criteria>
    - Wrapper command names exactly match A6-01 Tauri commands.
    - `saveSession` payload contains `{ workspacePath, session }`.
    - `loadSession` returns `SessionFile | null`.
    - Tests cover project and global paths.
    - `SESSION_STORAGE_OK` prints.
  </acceptance_criteria>
  <done>Frontend can call the Rust session commands.</done>
</task>

<task type="tdd">
  <name>Task 2: Add pure session snapshot and restore helpers</name>
  <files>apps/voss-app/src/grid/sessionCommands.ts, apps/voss-app/src/grid/__tests__/sessionCommands.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/layoutCommands.ts - canonical clone and load transform style
    - apps/voss-app/src/grid/tree.ts - `TreeNode`, `PaneLeaf`, `collectLeaves`, `recomputeIndices`
    - .planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md - schema bounds and restore priority
  </read_first>
  <action>
    Create `sessionCommands.ts` with pure functions. Add `buildSessionFile(root, focusedId, activeLayout, scrollbackByPaneId, projectLessAccepted)` that returns a `SessionFile` with canonical tree fields only, active preset null for `custom`, one `SessionPane` per leaf, and scrollback arrays capped to 2,000 lines. Add `applySessionFile(session)` returning `{ root, focusedId, activeLayout, restoredScrollbackByPaneId }`, preserving saved pane ids and recomputing indices. Add tests for: custom active layout serializes as null; named preset survives; scrollback caps at 2,000; missing pane scrollback becomes null; extra scrollback ids are ignored; runtime-only fields injected into leaves are not serialized.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/sessionCommands.test.ts --reporter=dot && grep -q 'buildSessionFile' src/grid/sessionCommands.ts && grep -q 'applySessionFile' src/grid/sessionCommands.ts && grep -q '2000' src/grid/sessionCommands.ts && echo SESSION_COMMANDS_OK</automated>
  </verify>
  <acceptance_criteria>
    - Scrollback is capped to 2,000 lines at serialization.
    - Runtime-only pane fields cannot appear in the resulting session object.
    - `applySessionFile` returns a valid tree and focused id.
    - `SESSION_COMMANDS_OK` prints.
  </acceptance_criteria>
  <done>Session serialization rules are pure and tested.</done>
</task>
</tasks>

<verification>
Run the two new Vitest files and `pnpm --dir apps/voss-app build`.
</verification>

<success_criteria>
- The frontend has a typed session persistence API.
- Snapshot and restore logic is pure, tested, and free of xterm/Tauri concerns.
</success_criteria>

