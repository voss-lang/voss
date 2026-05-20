---
phase: A5-voss-app-project-open
plan: 03
type: execute
wave: 3
depends_on: [A5-02]
files_modified:
  - apps/voss-app/src/project/projectStorage.ts
  - apps/voss-app/src/project/__tests__/projectStorage.test.ts
autonomous: true
requirements: [WS-01, WS-02, WS-05, WS-06]
must_haves:
  truths:
    - "Typed JS wrappers exist for pickFolder, openProject, listRecents, defaultCwd"
    - "JS invoke payload keys are camelCase (projectPath), Rust receives snake_case (project_path) — Tauri auto-converts"
    - "pickFolder is the only function that touches @tauri-apps/plugin-dialog; everything else goes through @tauri-apps/api/core invoke"
    - "Wrapper tests prove command names + payload shapes via vi.hoisted invoke mocks (A4-04 pattern)"
  artifacts:
    - path: "apps/voss-app/src/project/projectStorage.ts"
      provides: "pickFolder, openProject, listRecents, defaultCwd typed wrappers + ProjectInfo type + UI-SPEC copy constants"
      contains: "openProject"
    - path: "apps/voss-app/src/project/__tests__/projectStorage.test.ts"
      provides: "vitest unit suite for invoke command names, payload shapes, dialog cancel, error propagation"
      contains: "openProject"
---

<objective>
Create the typed frontend invoke wrappers + the `pickFolder` helper that calls `@tauri-apps/plugin-dialog`. Mirror the A4-04 `layoutStorage.ts` style verbatim (the gold-standard template in `apps/voss-app/src/grid/layoutStorage.ts`).

Purpose: Give A5-05 (App.tsx composition) a typed, testable seam so the App.tsx open-project handler is a five-line orchestration, not a tangle of `invoke()` calls. Also fix camelCase mapping at the wrapper boundary so the rest of the frontend never types a Tauri payload key.
Output: A green `pnpm vitest run src/project/__tests__/projectStorage.test.ts` and a `tsc --noEmit` clean module.
</objective>

<context>
@.planning/phases/A5-voss-app-project-open/A5-SPEC.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A5-voss-app-project-open/A5-RESEARCH.md
@.planning/phases/A5-voss-app-project-open/A5-PATTERNS.md
@.planning/phases/A5-voss-app-project-open/A5-02-PLAN.md
@apps/voss-app/src/grid/layoutStorage.ts
@apps/voss-app/src/grid/__tests__/layoutStorage.test.ts

<interfaces>
Typed JS wrappers — A5-05 composition reads off these signatures.

From apps/voss-app/src/project/projectStorage.ts (this plan creates):

  import { invoke } from '@tauri-apps/api/core';
  import { open as openDialog } from '@tauri-apps/plugin-dialog';

  export type ProjectInfo = {
    path: string;
    name: string;
    gitBranch: string | null;
  };

  export type RecentsFile = { version: 1; recents: string[] };

  // UI-SPEC copy constants — this file is the SSOT for setup-window copy
  // until a separate A5-UI-SPEC exists (PATTERNS line 369-370).
  export const OPEN_PROJECT_LABEL = 'Open project';
  export const START_PROJECT_LESS_LABEL = 'Start without project';
  export const RECENTS_HEADING = 'Recent projects';

  export async function pickFolder(): Promise<string | null>;
  export async function openProject(path: string): Promise<ProjectInfo>;
  export async function listRecents(): Promise<string[]>;
  export async function defaultCwd(projectPath: string | null): Promise<string>;

From the analog apps/voss-app/src/grid/layoutStorage.ts (clone verbatim, swap names):

  export async function saveLayout(workspacePath: string, name: string, layout: LayoutFile): Promise<void> {
    await invoke('save_layout', { workspacePath, name, layout });
  }
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Webview → Rust IPC | All payloads validated Rust-side; JS just passes through |
| Dialog cancel signal | open() resolves to null on cancel; wrapper must propagate null, not throw |
| Rust error strings | open_project Rust errors come back as Error rejections with the Display string; wrapper re-throws unchanged |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A5-02-CASE (carry) | Tampering | snake_case / camelCase parameter mapping | mitigate | Wrapper test asserts invoke('default_cwd', { projectPath: null }) (camelCase key) explicitly; same for open_project with `path`. RESEARCH Pitfall 5 documents the silent-default-value failure mode. |
| T-A5-03 (carry) | Information disclosure | path traversal / stale recent | accept | Surface raised one layer down: A5-01 Rust open_project returns ProjectError::NotFound; wrapper just re-throws. A5-05 handler logs to console.warn for now (SPEC silent on error UI). |
| T-A5-DIALOG-NULL | DoS via untyped return | dialog cancel path | mitigate | pickFolder explicitly returns null on cancel; test case "pickFolder returns null on cancel" locks the contract |
</threat_model>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Create projectStorage.ts wrappers + types + copy constants</name>
  <files>apps/voss-app/src/project/projectStorage.ts, apps/voss-app/src/project/__tests__/projectStorage.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/layoutStorage.ts — entire file (~67 lines) is the template; clone structure verbatim
    - apps/voss-app/src/grid/__tests__/layoutStorage.test.ts — entire file (~139 lines) is the test template; clone `vi.hoisted` idiom verbatim
    - apps/voss-app/src-tauri/src/lib.rs — A5-02 command signatures (especially the Option String -> JS string|null mapping for default_cwd)
    - apps/voss-app/vitest.config.ts — confirms `environment: 'jsdom'` and the test glob
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md §Code Examples — verified pickFolder, openProject, listRecents, defaultCwd shapes (RESEARCH ~415-445)
    - .planning/phases/A5-voss-app-project-open/A5-PATTERNS.md §projectStorage.ts — analog mapping and the camelCase contract
  </read_first>
  <behavior>
    - Test 1: pickFolder() calls openDialog({ directory: true, multiple: false }) and returns the resolved string when the user picks a folder
    - Test 2: pickFolder() returns null when the dialog returns null (user cancel)
    - Test 3: pickFolder() returns null when the dialog returns an array (defensive — multiple:false should never return an array, but assert wrapper robustness)
    - Test 4: openProject('/some/path') calls invoke('open_project', { path: '/some/path' }) and returns the ProjectInfo
    - Test 5: openProject propagates a Rust error string verbatim via invoke rejection ("project not found" must surface unchanged so A5-05 can console.warn it)
    - Test 6: listRecents() calls invoke('load_recents') with no payload and returns the string[]
    - Test 7: defaultCwd(null) calls invoke('default_cwd', { projectPath: null }) — camelCase projectPath is the contract (T-A5-02-CASE)
    - Test 8: defaultCwd('/some/path') calls invoke('default_cwd', { projectPath: '/some/path' })
    - Test 9: OPEN_PROJECT_LABEL === 'Open project', START_PROJECT_LESS_LABEL === 'Start without project', RECENTS_HEADING === 'Recent projects' (locked copy)
  </behavior>
  <action>
    Create `apps/voss-app/src/project/` directory. Create `apps/voss-app/src/project/projectStorage.ts` with the imports, types, and exports from the `<interfaces>` block.

    pickFolder returns null if openDialog returns anything that isn't a string (covers cancel + the array defensive case): assign `const result = await openDialog({ directory: true, multiple: false });` then `return typeof result === 'string' ? result : null;`.

    openProject(path) returns `invoke<ProjectInfo>('open_project', { path })`.

    listRecents() returns `invoke<string[]>('load_recents')`.

    defaultCwd(projectPath) returns `invoke<string>('default_cwd', { projectPath })`.

    Add a header doc comment (clone the layoutStorage.ts:1-22 style) that calls out: (a) the camelCase contract for projectPath, (b) the dialog-returns-null-on-cancel contract, (c) the UI-SSOT note that this file owns setup-window copy until a separate A5-UI-SPEC exists.

    Create `apps/voss-app/src/project/__tests__/projectStorage.test.ts`. Clone the layoutStorage.test.ts structure verbatim. Use `vi.hoisted` with two mocks: `invoke` from `@tauri-apps/api/core` and `open` from `@tauri-apps/plugin-dialog`. Add three describe blocks per the A4-04 pattern: copy constants, invoke bridges, error propagation. Cover the nine behavior cases above. Use `mockResolvedValueOnce(...)` and `mockRejectedValueOnce(...)`.

    Run `pnpm exec tsc --noEmit -p .` and `pnpm vitest run src/project/__tests__/projectStorage.test.ts --reporter=dot` from `apps/voss-app/`. Both must exit 0.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/project/__tests__/projectStorage.test.ts --reporter=dot 2>&1 | tail -30 && pnpm exec tsc --noEmit -p . 2>&1 | tail -10 && grep -q 'export async function openProject' src/project/projectStorage.ts && grep -q 'export async function pickFolder' src/project/projectStorage.ts && grep -q 'export async function listRecents' src/project/projectStorage.ts && grep -q 'export async function defaultCwd' src/project/projectStorage.ts && grep -q 'projectPath' src/project/projectStorage.ts && grep -q 'OPEN_PROJECT_LABEL' src/project/projectStorage.ts && echo PROJECT_STORAGE_OK</automated>
  </verify>
  <acceptance_criteria>
    - projectStorage.ts exports the four async functions with the exact signatures from the `<interfaces>` block.
    - JS payload keys are camelCase (projectPath, not project_path); a test asserts the exact `invoke` arg shape for defaultCwd(null).
    - pickFolder returns null on dialog cancel and on array-shaped returns (defensive).
    - openProject rejection re-throws the Rust Display string unchanged.
    - The three copy constants exist and match the locked strings byte-for-byte.
    - `pnpm vitest run src/project/__tests__/projectStorage.test.ts` exits 0.
    - `pnpm exec tsc --noEmit` exits 0.
    - PROJECT_STORAGE_OK prints.
  </acceptance_criteria>
  <done>The typed JS bridge for project open is shipped. A5-05 can compose it into App.tsx; A5-04 can render SetupWindow with the locked copy constants imported from here.</done>
</task>

</tasks>

<verification>
Run `pnpm --filter voss-app exec tsc --noEmit -p .` and `pnpm --filter voss-app test -- src/project`. Both must exit 0.
</verification>

<success_criteria>
- A5-05 can `import { pickFolder, openProject, listRecents, defaultCwd, ProjectInfo } from './project/projectStorage'` and have all types resolved.
- A5-04 can `import { OPEN_PROJECT_LABEL, START_PROJECT_LESS_LABEL, RECENTS_HEADING } from '../project/projectStorage'` for setup-window copy.
- camelCase / snake_case mapping is locked at the JS boundary (T-A5-02-CASE mitigation).
- Dialog cancel returns null; never throws (T-A5-DIALOG-NULL mitigation).
</success_criteria>

<output>
Create `.planning/phases/A5-voss-app-project-open/A5-03-SUMMARY.md` with: test counts (~9 cases), wrapper line count vs. layoutStorage.ts (sanity check the pattern was cloned faithfully), and a note flagging that all four wrappers depend on the A5-02 IPC surface being live (caught by `pnpm exec tsc` only at build time, not at unit test time since invoke is mocked).
</output>
