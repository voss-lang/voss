---
phase: A5-voss-app-project-open
plan: 05
type: execute
wave: 4
depends_on: [A5-03, A5-04]
files_modified:
  - apps/voss-app/src/components/titlebar/Titlebar.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/__tests__/App.test.tsx
autonomous: true
requirements: [WS-01, WS-02, WS-03, WS-04, WS-05, WS-06, WS-07]
must_haves:
  truths:
    - "App.tsx owns project: Signal<ProjectInfo|null> and projectLessAccepted: Signal<boolean>"
    - "Titlebar always renders; body slot conditionally renders SetupWindow vs GridRoot via <Show>"
    - "Titlebar displays project.name when a project is open, falls back to 'Voss ADE' otherwise (CONCEPT §10 Q1)"
    - "On successful open_project, applyDefaultLayout(info.path) runs and its failure does not block the open (D-12)"
    - "Selecting a different project while panes exist does NOT remount GridRoot — pane identities survive (D-13, SPEC Req-8)"
    - "Flipping from project-less (true) to project-open (true) does NOT remount GridRoot (RESEARCH Pattern 4 note)"
    - "projectLessAccepted is session-only, never persisted (D-04)"
  artifacts:
    - path: "apps/voss-app/src/components/titlebar/Titlebar.tsx"
      provides: "projectName?: string prop with 'Voss ADE' fallback"
      contains: "projectName"
    - path: "apps/voss-app/src/App.tsx"
      provides: "project + projectLessAccepted signals, conditional setup branch, openProject handler, default-layout hook"
      contains: "projectLessAccepted"
    - path: "apps/voss-app/src/__tests__/App.test.tsx"
      provides: "Integration suite for setup-vs-grid branching, applyDefaultLayout hook, pane preservation across project change"
      contains: "App"
---

<objective>
Compose A5-01 (Rust core) + A5-02 (IPC) + A5-03 (JS wrappers) + A5-04 (SetupWindow) into App.tsx, and add the `projectName` prop to Titlebar. This is the integration wave — everything before this was substrate.

Purpose: Make SPEC requirements 1, 4, 7, and 8 observable end-to-end. Wire the D-12 default-layout hook so opening a project applies `.voss/layouts/default.json` automatically. Preserve A5-13 (no PTY destruction on project change).
Output: A green `pnpm vitest run src/__tests__/App.test.tsx` and an interactive app that shows the setup window on launch, opens projects via the picker, and updates the titlebar.
</objective>

<context>
@.planning/phases/A5-voss-app-project-open/A5-SPEC.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A5-voss-app-project-open/A5-RESEARCH.md
@.planning/phases/A5-voss-app-project-open/A5-PATTERNS.md
@.planning/phases/A5-voss-app-project-open/A5-03-PLAN.md
@.planning/phases/A5-voss-app-project-open/A5-04-PLAN.md
@apps/voss-app/src/App.tsx
@apps/voss-app/src/components/titlebar/Titlebar.tsx
@apps/voss-app/src/components/setup/SetupWindow.tsx
@apps/voss-app/src/project/projectStorage.ts

<interfaces>
Composition entry points — A5-06 acceptance suite reads off these.

From apps/voss-app/src/App.tsx (this plan extends):

  import { createSignal, Show } from 'solid-js';
  import SetupWindow from './components/setup/SetupWindow';
  import {
    pickFolder, openProject, listRecents,
    type ProjectInfo,
  } from './project/projectStorage';

  // INSIDE the App() function body, parallel to the existing activeLayout signal:
  const [project, setProject] = createSignal<ProjectInfo | null>(null);
  const [projectLessAccepted, setProjectLessAccepted] = createSignal(false);
  const [recents, setRecents] = createSignal<string[]>([]);

  // The composition predicate — once true, the body slot mounts GridRoot
  // and stays mounted for the rest of the session (D-13 / Pattern 4 note).
  const showGrid = () => project() !== null || projectLessAccepted();

  // openProject handler (D-12 ordering: setProject -> microtask flush -> applyDefaultLayout)
  const handleOpenFolder = async () => {
    const picked = await pickFolder();
    if (!picked) return;
    try {
      const info = await openProject(picked);
      setProject(info);
      setProjectLessAccepted(true);
      // Refresh recents from Rust (which just updated them)
      setRecents(await listRecents());
      // Yield one microtask so the <Show> branch mounts GridRoot and
      // gridController is assigned BEFORE applyDefaultLayout reads it.
      await Promise.resolve();
      await applyDefaultLayout(info.path).catch((e) => {
        console.warn('default layout skipped:', e);
      });
    } catch (e) {
      console.error('open_project failed:', e);
    }
  };

From apps/voss-app/src/components/titlebar/Titlebar.tsx (this plan extends):

  export type TitlebarProps = {
    activeLayout?: ActiveLayout;
    layoutDisabled?: boolean;
    onLayoutSelect?: (preset: LayoutPreset) => void;
    projectName?: string;        // A5 adds — defaults to 'Voss ADE' when undefined
  };

  // Display site (current line ~60):
  // BEFORE:  Voss ADE
  // AFTER:   {props.projectName ?? 'Voss ADE'}
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Signal ownership | App.tsx is the SSOT for project state; Titlebar and SetupWindow are reflectors |
| Grid lifecycle | GridRoot must mount exactly once after the first project-or-projectless decision; never unmount on project change |
| Default-layout hook | Failures must be non-blocking; A4-03 already returns Ok(None) for missing/invalid |
| Recents listing | listRecents() reads from disk; failure is silent (D-10) — UI handles `[]` fallback |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A5-02 | Tampering / DoS | PTY destruction on project change | mitigate | Conditional render is one-way (showGrid() becomes true and stays true); changing project()/setProject does not toggle the predicate. Integration test asserts a synthetic pane id present before setProject is still present after (D-13 / SPEC Req-8). |
| T-A5-D12 | DoS / Repudiation | Default-layout hook blocks project open on bad file | mitigate | applyDefaultLayout call is wrapped in .catch with console.warn; A4-03 already returns Ok(None) on missing/invalid; A5-06 acceptance asserts no throw bubbles out of handleOpenFolder for any A4-03 error variant. |
| T-A5-MOUNT | Tampering | gridController undefined when default-layout hook reads it | mitigate | `await Promise.resolve()` between setProject and applyDefaultLayout yields a microtask so Solid flushes the <Show> branch and the controllerRef callback runs first; existing `if (!gridController) return false` guard in applyDefaultLayout is the second line of defense (RESEARCH §Planning Implications / Single-pane integration risk). |
| T-A5-PERSIST | Repudiation | projectLessAccepted accidentally persisted | mitigate | Test asserts no call to settings.json or any persistence boundary contains the literal 'projectLessAccepted'; signal lives only in component closure (D-04). |
| T-A5-FALLBACK | Information disclosure | Titlebar shows undefined / blank instead of 'Voss ADE' fallback | mitigate | Titlebar prop default-empty-props pattern preserved; explicit `?? 'Voss ADE'` at display site; existing pre-A5 tests rendering `<Titlebar />` still pass. |
</threat_model>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Extend Titlebar.tsx with projectName prop (default 'Voss ADE')</name>
  <files>apps/voss-app/src/components/titlebar/Titlebar.tsx</files>
  <read_first>
    - apps/voss-app/src/components/titlebar/Titlebar.tsx (entire file) — current default-empty-props pattern (lines 17-23), hardcoded display site (line ~60), drag-region constraint (lines 43-46)
    - apps/voss-app/src/components/titlebar/__tests__/Titlebar.test.tsx (if it exists — list the dir first) — confirm the `<Titlebar />` bare-render contract is tested so we don't regress
    - .planning/phases/A5-voss-app-project-open/A5-PATTERNS.md §Titlebar.tsx section — optional prop pattern + fallback rule + landmine #1
    - apps/voss-app/CONCEPT.md §10 Q1 — 'Voss ADE' is the fallback brand when no project is open
  </read_first>
  <behavior>
    - Test 1: `<Titlebar />` (no props) renders 'Voss ADE' in the title region (legacy contract preserved)
    - Test 2: `<Titlebar projectName="my-project" />` renders 'my-project' in the title region
    - Test 3: `<Titlebar projectName={undefined} />` renders 'Voss ADE' (explicit undefined falls back)
    - Test 4: `<Titlebar projectName="" />` renders ... — planner decision: empty string should also fall back to 'Voss ADE' (use `?? 'Voss ADE' || 'Voss ADE'` or equivalent; document the choice in a code comment).
  </behavior>
  <action>
    Edit `apps/voss-app/src/components/titlebar/Titlebar.tsx`:

    1. Add `projectName?: string;` to `TitlebarProps`.
    2. Change the hardcoded `Voss ADE` text (around line 60) to `{props.projectName ?? 'Voss ADE'}`. For the empty-string edge case use `{(props.projectName && props.projectName.length > 0) ? props.projectName : 'Voss ADE'}` to cover both undefined and empty-string fallback paths.
    3. Preserve the `data-tauri-drag-region` attribute exactly where it is — do not move it onto a child element (A5-PATTERNS line 303 drag-region constraint).
    4. Remove the A1 placeholder comment at line ~43 that names A5 as the seam (the seam now exists). Replace with a one-line comment: `// projectName: A5-05 wires this from App.tsx project() signal; 'Voss ADE' is the project-less / pre-open fallback (CONCEPT §10 Q1).`
    5. **Critical landmine**: keep the `= {}` default for `TitlebarProps` (line 23 area) so bare `<Titlebar />` renders still work for any pre-A5 test (PATTERNS Landmine #7).

    Add (or extend) tests in `apps/voss-app/src/components/titlebar/__tests__/Titlebar.test.tsx`. If the file does not exist, create it cloning the PresetSwitcher.test.tsx mount/dispose pattern. Cover all four behavior cases above.

    No changes to App.tsx in this task — Task 2 wires the prop.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/components/titlebar/__tests__/Titlebar.test.tsx --reporter=dot 2>&1 | tail -20 && pnpm exec tsc --noEmit -p . 2>&1 | tail -10 && grep -q 'projectName' src/components/titlebar/Titlebar.tsx && grep -q "'Voss ADE'" src/components/titlebar/Titlebar.tsx && echo TITLEBAR_PROJECT_OK</automated>
  </verify>
  <acceptance_criteria>
    - TitlebarProps has `projectName?: string`.
    - Display site uses `props.projectName ?? 'Voss ADE'` (with empty-string also falling back).
    - Bare `<Titlebar />` still renders 'Voss ADE' (legacy contract).
    - data-tauri-drag-region remains on the outer text div.
    - `pnpm vitest run` for Titlebar passes.
    - `pnpm exec tsc --noEmit -p .` passes.
    - TITLEBAR_PROJECT_OK prints.
  </acceptance_criteria>
  <done>Titlebar accepts a project name and falls back to the brand string. App.tsx (Task 2) can pass `project()?.name`.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Add project + projectLessAccepted signals, <Show> branch, openProject handler, and D-12 default-layout hook in App.tsx</name>
  <files>apps/voss-app/src/App.tsx, apps/voss-app/src/__tests__/App.test.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (entire file) — current composition: activeLayout signal, gridController, A4-04 callable closures (saveCurrentLayout, loadLayoutByName, applyDefaultLayout), `void` suppression lines
    - apps/voss-app/src/components/setup/SetupWindow.tsx (from A5-04) — props contract
    - apps/voss-app/src/project/projectStorage.ts (from A5-03) — pickFolder, openProject, listRecents, ProjectInfo
    - apps/voss-app/src/components/titlebar/Titlebar.tsx (after Task 1) — projectName prop
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Pattern 4 (Solid <Show>) + §Planning Implications (Single-pane integration risk + microtask ordering)
    - .planning/phases/A5-voss-app-project-open/A5-CONTEXT.md D-01..D-04, D-12, D-13
    - .planning/phases/A5-voss-app-project-open/A5-PATTERNS.md Landmine #2 — DO NOT remove `void saveCurrentLayout;` and `void loadLayoutByName;`; DO remove `void applyDefaultLayout;` because A5-05 now wires it
  </read_first>
  <behavior>
    - Test 1: On initial mount with no project, SetupWindow is rendered and GridRoot is NOT rendered (SPEC Req-1, AC #1)
    - Test 2: Titlebar shows 'Voss ADE' on initial mount (project()?.name is undefined → fallback)
    - Test 3: After invoking the onStartProjectLess callback exposed via SetupWindow, GridRoot mounts and Titlebar still shows 'Voss ADE' (project still null, but showGrid() flipped via projectLessAccepted)
    - Test 4: Invoking handleOpenFolder with mocked pickFolder returning '/tmp/x' and mocked openProject returning a ProjectInfo with name='x' → setProject runs, GridRoot mounts, Titlebar shows 'x', applyDefaultLayout is called with '/tmp/x'
    - Test 5: When applyDefaultLayout rejects, handleOpenFolder does not throw and project state remains open (SPEC Req-7, AC #10)
    - Test 6: When pickFolder returns null (user cancel), no setProject call, SetupWindow remains visible
    - Test 7: When openProject rejects (e.g. 'project not found'), error is console.errored, project remains null, SetupWindow remains visible
    - Test 8: Pane preservation — synthesize the post-mount scenario (showGrid is already true, gridController is set), then call setProject({...}) for a NEW project. Assert: GridRoot DOM node identity is unchanged (no remount); gridController reference is unchanged. (D-13 / SPEC Req-8 / T-A5-02 mitigation.)
    - Test 9: Microtask ordering — applyDefaultLayout is NOT called before setProject; verify via mock ordering that setProject resolves before applyDefaultLayout begins (T-A5-MOUNT)
    - Test 10: listRecents is called after openProject succeeds and the returned array is stored in recents state (so SetupWindow can render them on subsequent visits — though A5-05 does not re-show SetupWindow after first project open in the same session)
  </behavior>
  <action>
    Edit `apps/voss-app/src/App.tsx`:

    1. Add imports per `<interfaces>`: `createSignal, Show` from `solid-js`, `SetupWindow` default, and `pickFolder, openProject, listRecents, type ProjectInfo` from `./project/projectStorage`.

    2. Inside the App() body, parallel to the existing `activeLayout` signal (lines 37-44 area), declare the three new signals:
       - `const [project, setProject] = createSignal<ProjectInfo | null>(null);`
       - `const [projectLessAccepted, setProjectLessAccepted] = createSignal(false);`
       - `const [recents, setRecents] = createSignal<string[]>([]);`

    3. Add a `showGrid()` accessor: `const showGrid = () => project() !== null || projectLessAccepted();`.

    4. Define `handleOpenFolder` exactly per the `<interfaces>` block. Define `handleOpenRecent = (path: string) => { void openProject(path).then((info) => { setProject(info); setProjectLessAccepted(true); return listRecents().then(setRecents); }).catch((e) => console.error('open_recent failed:', e)); };`.

    5. On initial mount, kick off a `listRecents()` fetch so the SetupWindow shows recents from prior sessions (use Solid's `onMount` or a top-level `void listRecents().then(setRecents).catch(() => setRecents([]));`).

    6. Replace the existing unconditional `<GridRoot ... />` mount with the conditional branch from RESEARCH §Pattern 4:

       <Show
         when={showGrid()}
         fallback={
           <SetupWindow
             recents={recents()}
             onOpenProject={handleOpenFolder}
             onOpenRecent={handleOpenRecent}
             onStartProjectLess={() => setProjectLessAccepted(true)}
           />
         }
       >
         <div style={{ flex: '1', 'min-height': '0', background: 'var(--bg-0)' }}>
           <GridRoot
             activeLayout={activeLayout}
             onLayoutChange={(next) => setActiveLayout(next)}
             controllerRef={(c) => { gridController = c; }}
           />
         </div>
       </Show>

    7. Pass `projectName={project()?.name}` to the always-on Titlebar.

    8. Remove the `void applyDefaultLayout;` suppression line (A5-05 now USES it). KEEP `void saveCurrentLayout;` and `void loadLayoutByName;` (A7 still owns those seams per PATTERNS Landmine #2).

    9. Threading the resolved cwd into pane creation (CONTEXT D-11): per A5-PATTERNS §grid/operations.ts the cleanest approach is to call `default_cwd` from operations.ts when splitFocused / forkFocused make a new pane. That is a "maybe" plan per PATTERNS line 463 — defer to a future small change since SPEC Req-4 / AC #7 is satisfied as long as PROJECT-LESS panes "use home directory as default cwd". For A5-05, **invoke `defaultCwd(project()?.path ?? null)` once during onMount and cache the result; pass it as a `projectCwd` prop into GridRoot** for future pane spawns to read. If GridRoot does not currently accept a `projectCwd` prop, add it as `projectCwd?: string` (optional, undefined preserves legacy behavior). Operations.ts wiring can stay TODO — the test that matters is "project-less default cwd resolves to home via Rust" which is already covered by A5-01 default_cwd tests.

    Create `apps/voss-app/src/__tests__/App.test.tsx`. This is the integration test file:

    - Mock `@tauri-apps/api/core` and `@tauri-apps/plugin-dialog` via `vi.hoisted` (clone projectStorage.test.ts shape).
    - Mock GridRoot if its mount lifecycle is expensive — create a tiny stub component so the test focuses on App.tsx branching, not grid internals. Use `vi.mock('../grid/GridRoot', () => ({ default: (props: any) => <div data-testid="grid-root">...stub...</div> }));`.
    - Mount App, drive the ten behavior cases above. For Test 8 (pane preservation), query `document.querySelector('[data-testid="grid-root"]')` before and after `setProject` (or simulate by calling the recents-open handler twice with different paths) and assert reference equality.
    - Assert no test path persists `projectLessAccepted` (T-A5-PERSIST) by checking the mocked `invoke` was never called with a 'save_settings' or similar command.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/__tests__/App.test.tsx --reporter=dot 2>&1 | tail -40 && pnpm exec tsc --noEmit -p . 2>&1 | tail -10 && grep -q 'projectLessAccepted' src/App.tsx && grep -q 'SetupWindow' src/App.tsx && grep -q 'pickFolder' src/App.tsx && grep -q 'applyDefaultLayout' src/App.tsx && grep -q 'projectName' src/App.tsx && ! grep -q 'void applyDefaultLayout' src/App.tsx && grep -q 'void saveCurrentLayout' src/App.tsx && grep -q 'void loadLayoutByName' src/App.tsx && echo APP_COMPOSITION_OK</automated>
  </verify>
  <acceptance_criteria>
    - Three new signals (project, projectLessAccepted, recents) live in App.tsx.
    - SetupWindow renders when showGrid() is false; GridRoot when true. <Show> branching is one-way (RESEARCH §Pattern 4 note).
    - handleOpenFolder orchestrates pickFolder → openProject → setProject → listRecents → applyDefaultLayout in the exact order.
    - applyDefaultLayout failure does not throw and does not unset project.
    - User-cancel and Rust-error branches keep project null and SetupWindow visible.
    - Pane identity preserved across project changes (T-A5-02 mitigation).
    - The `void applyDefaultLayout;` suppression line is removed; `void saveCurrentLayout;` and `void loadLayoutByName;` are kept.
    - Titlebar receives `projectName={project()?.name}` and falls back to 'Voss ADE' when undefined.
    - APP_COMPOSITION_OK prints.
  </acceptance_criteria>
  <done>SPEC Req-1, Req-4, Req-7, Req-8 are observable in unit tests. The app composition wave is complete. A5-06 closes with acceptance + visual checkpoint.</done>
</task>

</tasks>

<verification>
Run `pnpm --filter voss-app test` and `pnpm --filter voss-app exec tsc --noEmit -p .`. Both must exit 0. Then build the app via `pnpm --filter voss-app build` to confirm there are no runtime composition errors.
</verification>

<success_criteria>
- App.tsx is the SSOT for project + projectLessAccepted + recents.
- SetupWindow and GridRoot are mutually exclusive via <Show>; project state changes inside the GridRoot branch do not remount.
- D-12 default-layout hook fires after every successful open and never blocks.
- Titlebar reflects project.name with brand fallback.
- All A5-RESEARCH §Phase Requirements → Test Map jsdom rows are green.
</success_criteria>

<output>
Create `.planning/phases/A5-voss-app-project-open/A5-05-SUMMARY.md` with: App.tsx diff line count, ordering trace for the open-project happy path, confirmation that pane preservation test passed (D-13), and the exact line numbers in App.tsx that were `void`-suppressed before vs. after.
</output>
