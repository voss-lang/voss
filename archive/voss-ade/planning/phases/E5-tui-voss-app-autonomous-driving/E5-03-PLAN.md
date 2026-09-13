---
phase: E5-tui-voss-app-autonomous-driving
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/package.json
  - pnpm-lock.yaml
  - apps/voss-app/wdio.conf.mjs
  - apps/voss-app/src/project/projectStorage.ts
  - apps/voss-app/src/components/setup/SetupWindow.tsx
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/e2e-tauri/command-palette.wdio.mjs
  - apps/voss-app/e2e-tauri/project-open.wdio.mjs
  - apps/voss-app/e2e-tauri/themes.wdio.mjs
autonomous: true
requirements: [D-04, D-05, D-06]
user_setup: []
must_haves:
  truths:
    - "D-04: The desktop Tauri-driver proof uses a WebDriver client, not Playwright against tauri-driver"
    - "D-05: The selected preserved contracts are command-palette, project-open/setup, and themes"
    - "D-05: Each selected contract asserts real DOM/CSS/app state and contains no page.evaluate(() => void 0) empty green"
    - "D-05: Project-open native dialog is controlled only behind an explicit Tauri e2e test seam"
    - "D-06: Desktop e2e runs with VOSS_SERVE_FAKE_TURN=1 and no provider credentials"
  artifacts:
    - path: "apps/voss-app/wdio.conf.mjs"
      provides: "Tauri-driver WebDriver runner config for selected app contracts"
      contains: "tauri:options"
    - path: "apps/voss-app/e2e-tauri/command-palette.wdio.mjs"
      provides: "Command palette Tauri contract port"
      contains: "Run command"
    - path: "apps/voss-app/e2e-tauri/project-open.wdio.mjs"
      provides: "Setup/project-open Tauri contract port"
      contains: "voss:e2e:pickFolder"
    - path: "apps/voss-app/e2e-tauri/themes.wdio.mjs"
      provides: "Theme runtime Tauri contract port"
      contains: "--focus"
  key_links:
    - from: "apps/voss-app/wdio.conf.mjs"
      to: "tauri-driver"
      via: "WebDriver host 127.0.0.1:4444 and capability tauri:options.application"
      pattern: "tauri:options"
    - from: "apps/voss-app/src/project/projectStorage.ts"
      to: "apps/voss-app/e2e-tauri/project-open.wdio.mjs"
      via: "window.__VOSS_TAURI_E2E__ plus localStorage voss:e2e:pickFolder"
      pattern: "voss:e2e:pickFolder"
---

<objective>
Create the desktop app contract runner for E5 D-04, D-05, and D-06. Official Tauri WebDriver documentation uses `tauri-driver` with WebDriver clients such as WebdriverIO/Selenium; the existing Playwright files remain the contract source, but the Linux Tauri app proof is driven through WebDriver.

Purpose: Turn the first three app contracts into real Tauri-driver checks without adding visible product UI or live desktop credentials.
Output: WDIO runner config, package script/dependencies, non-visual test seams, and three Tauri contract specs.
</objective>

<execution_context>
@$HOME/.codex/get-shit-done/workflows/execute-plan.md
@$HOME/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-CONTEXT.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-RESEARCH.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-UI-SPEC.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-VALIDATION.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-PATTERNS.md

@apps/voss-app/package.json
@apps/voss-app/vite.config.ts
@apps/voss-app/src/App.tsx
@apps/voss-app/src/project/projectStorage.ts
@apps/voss-app/src/components/setup/SetupWindow.tsx
@apps/voss-app/src/grid/GridRoot.tsx
@apps/voss-app/src/command-palette/CommandPalette.tsx
@apps/voss-app/src/themes/themeRuntime.ts
@apps/voss-app/src/themes/themeCatalog.ts
@apps/voss-app/e2e/command-palette.spec.ts
@apps/voss-app/e2e/project-open.spec.ts
@apps/voss-app/e2e/themes.spec.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add WDIO Tauri-driver runner and package script</name>
  <files>apps/voss-app/package.json, pnpm-lock.yaml, apps/voss-app/wdio.conf.mjs</files>
  <read_first>
    - apps/voss-app/package.json (scripts and devDependencies)
    - pnpm-lock.yaml (workspace lockfile update target)
    - apps/voss-app/src-tauri/tauri.conf.json (productName and app config)
    - .planning/phases/E5-tui-voss-app-autonomous-driving/E5-RESEARCH.md (planner addendum on Tauri WebDriver)
  </read_first>
  <action>
    Add a `test:e2e:tauri` script to `apps/voss-app/package.json` with value `wdio run ./wdio.conf.mjs`. Add the smallest WebDriverIO dev dependency set needed for a local runner: `@wdio/cli`, `@wdio/local-runner`, `@wdio/mocha-framework`, `@wdio/globals`, `expect-webdriverio`, and `webdriverio`. Use `pnpm --dir apps/voss-app add -D ...` so `pnpm-lock.yaml` records exact resolved versions; do not add runtime dependencies.

    Create `apps/voss-app/wdio.conf.mjs`. Configure `host: "127.0.0.1"`, `port: 4444`, `specs: ["./e2e-tauri/*.wdio.mjs"]`, `maxInstances: 1`, `framework: "mocha"`, `mochaOpts.timeout: 60000`, and one capability with `'tauri:options': { application: process.env.TAURI_APP_BINARY }`. At config load, throw a clear error if `TAURI_APP_BINARY` is missing. In a `before` hook, execute a browser script that sets `window.__VOSS_TAURI_E2E__ = true`. Do not spawn `tauri-driver` in this config; E5-04 owns process startup in CI so failures are visible in workflow logs.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app exec wdio --version && pnpm --dir apps/voss-app run test:e2e:tauri -- --help</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/package.json` contains `"test:e2e:tauri": "wdio run ./wdio.conf.mjs"`.
    - `apps/voss-app/package.json` devDependencies contain `@wdio/cli`, `@wdio/local-runner`, `@wdio/mocha-framework`, `@wdio/globals`, `expect-webdriverio`, and `webdriverio`.
    - `apps/voss-app/wdio.conf.mjs` contains `host: '127.0.0.1'` or `host: "127.0.0.1"`, `port: 4444`, and `tauri:options`.
    - `apps/voss-app/wdio.conf.mjs` reads `process.env.TAURI_APP_BINARY` and fails fast when absent.
    - `pnpm-lock.yaml` changes include the WDIO packages.
  </acceptance_criteria>
  <done>The app has a Tauri-driver-compatible WebDriver runner and script, with dependency additions justified by the E5 research addendum.</done>
</task>

<task type="auto">
  <name>Task 2: Add non-visual project-open and grid selectors</name>
  <files>apps/voss-app/src/project/projectStorage.ts, apps/voss-app/src/components/setup/SetupWindow.tsx, apps/voss-app/src/grid/GridRoot.tsx</files>
  <read_first>
    - apps/voss-app/src/project/projectStorage.ts (pickFolder, copy constants)
    - apps/voss-app/src/components/setup/SetupWindow.tsx (main element and action buttons)
    - apps/voss-app/src/grid/GridRoot.tsx (root returned element)
    - apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx (existing setup/grid selector expectations)
    - .planning/phases/E5-tui-voss-app-autonomous-driving/E5-UI-SPEC.md (test hooks allowed, no visible UI changes)
  </read_first>
  <action>
    In `projectStorage.ts`, add a small internal helper that reads `(window as any).__VOSS_TAURI_E2E__ === true` and then `window.localStorage.getItem("voss:e2e:pickFolder")`. At the start of `pickFolder()`, if that gate is true and the stored value is a non-empty string, return it instead of opening the native dialog. If the gate is false or the value is missing, keep the existing `openDialog({ directory: true, multiple: false })` behavior byte-for-byte.

    In `SetupWindow.tsx`, add `data-testid="setup-window"` to the existing top-level `<main aria-label="Project setup">`. Do not change copy, layout, colors, spacing, or button labels.

    In `GridRoot.tsx`, add `data-testid="grid-root"` and `data-project-cwd={props.projectCwd ?? ""}` to the root grid element returned by the component. Do not use these attributes for production CSS selectors.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test -- src/project/__tests__/projectStorage.test.ts src/components/setup/__tests__/SetupWindow.test.tsx src/project/__tests__/a5-acceptance.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - `projectStorage.ts` contains `__VOSS_TAURI_E2E__` and `voss:e2e:pickFolder`.
    - Existing `OPEN_PROJECT_LABEL`, `START_PROJECT_LESS_LABEL`, and `RECENTS_HEADING` strings are unchanged.
    - `SetupWindow.tsx` contains `data-testid="setup-window"`.
    - `GridRoot.tsx` contains `data-testid="grid-root"` and `data-project-cwd`.
    - No CSS file references `data-testid` or `data-project-cwd`.
    - The targeted Vitest command exits 0.
  </acceptance_criteria>
  <done>The app exposes stable non-visual selectors and a gated folder-picker seam for Tauri e2e without changing normal user behavior.</done>
</task>

<task type="auto">
  <name>Task 3: Port three preserved contracts to Tauri-driver WDIO specs</name>
  <files>apps/voss-app/e2e-tauri/command-palette.wdio.mjs, apps/voss-app/e2e-tauri/project-open.wdio.mjs, apps/voss-app/e2e-tauri/themes.wdio.mjs</files>
  <read_first>
    - apps/voss-app/e2e/command-palette.spec.ts (contract names and assertion intent)
    - apps/voss-app/e2e/project-open.spec.ts (contract names and native dialog blocker)
    - apps/voss-app/e2e/themes.spec.ts (contract names; note older 12-theme comment)
    - apps/voss-app/src/command-palette/CommandPalette.tsx (data-testid selectors and exact input hint text)
    - apps/voss-app/src/themes/themeCatalog.ts (current bundled theme IDs and default)
    - apps/voss-app/wdio.conf.mjs
  </read_first>
  <action>
    Create `apps/voss-app/e2e-tauri/command-palette.wdio.mjs`. Import `{ browser, $, $$, expect }` from `@wdio/globals`. Add tests named with the preserved contract IDs: `cmd-ac2: Cmd+Shift+P opens full mode with all command categories` and `cmd-ac3: all six categories findable in full palette`. Drive the app by dispatching a real KeyboardEvent for Ctrl+Shift+P from `browser.execute`, then assert `[data-testid="command-palette"]` is displayed, `[data-testid="palette-input"]` has input hint `Run command`, typing `split` shows a `[data-testid="palette-row"]` containing `Split Right`, and the row list includes at least one command from Window, Pane, Layout, Project, Settings, and Help across targeted searches.

    Create `apps/voss-app/e2e-tauri/project-open.wdio.mjs`. Before clicking, create a temp project directory path from `process.env.VOSS_E2E_PROJECT_DIR || "/tmp/voss-e5-project"` using Node `fs.mkdirSync(..., { recursive: true })`, set `localStorage.setItem("voss:e2e:pickFolder", path)` inside the app, assert `[data-testid="setup-window"]` is displayed and `[data-testid="grid-root"]` is absent, click the `Open project` button, then assert `[data-testid="grid-root"]` appears and its `data-project-cwd` equals the temp path. Add a second test for `Start without project` asserting grid mounts and the titlebar still contains `Voss ADE`.

    Create `apps/voss-app/e2e-tauri/themes.wdio.mjs`. Read computed styles from `document.documentElement` and assert default Voss Ignite theme variables are present: `--focus` equals `#ff5b1f` and `--bg-0` is non-empty. Assert the titlebar live chip starts in snapshot state by locating text `snapshot`. Do not hardcode the old 12-theme count from the Playwright stub; the source catalog currently owns the count.

    Across all three specs, no test may pass by only calling `browser.execute(() => undefined)` or `page.evaluate(() => void 0)`. Each test must have at least one WDIO DOM/CSS assertion.
  </action>
  <verify>
    <automated>test -f apps/voss-app/e2e-tauri/command-palette.wdio.mjs && test -f apps/voss-app/e2e-tauri/project-open.wdio.mjs && test -f apps/voss-app/e2e-tauri/themes.wdio.mjs && ! rg -n "page\\.evaluate\\(\\(\\) => void 0\\)|browser\\.execute\\(\\(\\) => undefined\\)" apps/voss-app/e2e-tauri</automated>
  </verify>
  <acceptance_criteria>
    - All three files exist under `apps/voss-app/e2e-tauri/`.
    - Contract names `cmd-ac2`, `cmd-ac3`, `setup window visible`, `click Open project`, `Start without project`, and `theme-ac` appear in the WDIO files.
    - `rg -n "page\\.evaluate\\(\\(\\) => void 0\\)|browser\\.execute\\(\\(\\) => undefined\\)" apps/voss-app/e2e-tauri` returns no matches.
    - `command-palette.wdio.mjs` asserts `data-testid="command-palette"`, `palette-input`, `Run command`, and `Split Right`.
    - `project-open.wdio.mjs` uses `voss:e2e:pickFolder` and asserts `data-project-cwd`.
    - `themes.wdio.mjs` asserts `--focus` equals `#ff5b1f` and never asserts the stale value `12` for bundled themes.
    - The verify command fails fast with a missing `TAURI_APP_BINARY` message before any false green; E5-04 supplies a real binary in CI.
  </acceptance_criteria>
  <done>Three preserved app contracts have real Tauri-driver/WebDriver assertion ports and no empty green tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
| --- | --- |
| WDIO runner -> Tauri webview | WebDriver commands interact with the running desktop app through `tauri-driver`. |
| test seam -> native dialog | The folder picker is replaced only when `window.__VOSS_TAURI_E2E__ === true` and localStorage carries an explicit path. |
| desktop CI -> provider services | CI must run fake/local app proof with no model provider secrets. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
| --- | --- | --- | --- | --- |
| T-E5-07 | Spoofing | Playwright files mistaken for Tauri-driver proof | mitigate | WDIO runner is named `test:e2e:tauri`; selected specs live under `e2e-tauri` and use `tauri:options.application`. |
| T-E5-08 | Tampering | folder picker seam changes normal app behavior | mitigate | Seam requires `window.__VOSS_TAURI_E2E__ === true`; normal `openDialog` path remains unchanged. |
| T-E5-09 | Information Disclosure | desktop CI provider credentials | mitigate | E5-04 workflow sets `VOSS_SERVE_FAKE_TURN=1` and no provider secrets; this plan adds no secret reads. |
| T-E5-10 | Repudiation | empty green desktop tests | mitigate | Each WDIO spec has explicit DOM/CSS assertions and grep gates ban empty execute/evaluate no-op calls. |
</threat_model>

<verification>
- `pnpm --dir apps/voss-app test -- src/project/__tests__/projectStorage.test.ts src/components/setup/__tests__/SetupWindow.test.tsx src/project/__tests__/a5-acceptance.test.tsx` exits 0.
- `pnpm --dir apps/voss-app build` exits 0.
- With a real debug Tauri binary and `tauri-driver` running on 127.0.0.1:4444, `VOSS_SERVE_FAKE_TURN=1 TAURI_APP_BINARY=<path> pnpm --dir apps/voss-app run test:e2e:tauri -- --spec e2e-tauri/command-palette.wdio.mjs,e2e-tauri/project-open.wdio.mjs,e2e-tauri/themes.wdio.mjs` exits 0.
- `rg -n "page\\.evaluate\\(\\(\\) => void 0\\)|browser\\.execute\\(\\(\\) => undefined\\)" apps/voss-app/e2e-tauri` returns no matches.
</verification>

<success_criteria>
- D-04: desktop app proof uses the Linux-compatible `tauri-driver` WebDriver path.
- D-05: at least three preserved app contract intents have green Tauri-driver ports.
- D-06: desktop e2e is compatible with fake/local proof and introduces no live credential requirement.
- E5-UI-SPEC: added selectors are non-visual and token/style contracts are unchanged.
</success_criteria>

<output>
Create `.planning/phases/E5-tui-voss-app-autonomous-driving/E5-03-SUMMARY.md` when done.
</output>
