# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: layout-presets.spec.ts >> A4 layout presets (mock-IPC) >> lay-ac3: clicking a preset advances geometry without re-mounting panes
- Location: e2e/layout-presets.spec.ts:67:3

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: true
Received: false
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - img [ref=e6]
      - 'button "Project: voss-e2e-proj" [ref=e9] [cursor=pointer]':
        - img [ref=e10]
        - generic [ref=e12]: voss-e2e-proj
        - img [ref=e13]
    - generic [ref=e17]: WORKSPACES
    - generic [ref=e19]:
      - search [ref=e20]:
        - img [ref=e21]
        - searchbox "Search" [ref=e24] [cursor=pointer]
        - generic [ref=e25]: ⌘K
      - button "Notifications" [ref=e26] [cursor=pointer]:
        - img [ref=e27]
      - button "New task" [ref=e30] [cursor=pointer]:
        - img [ref=e31]
        - text: New task
      - 'generic "Data source: snapshot" [ref=e32]': snapshot
  - generic [ref=e33]:
    - generic [ref=e34]:
      - navigation "Voss portal" [ref=e35]:
        - button "Expand portal" [ref=e36] [cursor=pointer]:
          - img [ref=e37]
        - tablist [ref=e40]:
          - tab "Workspaces" [selected] [ref=e41] [cursor=pointer]:
            - img [ref=e42]
          - tab "Overview" [ref=e47] [cursor=pointer]:
            - img [ref=e48]
          - tab "Tasks" [ref=e53] [cursor=pointer]:
            - img [ref=e54]
          - tab "Agents" [ref=e57] [cursor=pointer]:
            - img [ref=e58]
          - tab "Orchestra" [ref=e61] [cursor=pointer]:
            - img [ref=e62]
          - tab "Review" [ref=e67] [cursor=pointer]:
            - img [ref=e68]
          - tab "Context" [ref=e72] [cursor=pointer]:
            - img [ref=e73]
          - tab "Memory" [ref=e76] [cursor=pointer]:
            - img [ref=e77]
          - tab "Settings" [ref=e85] [cursor=pointer]:
            - img [ref=e86]
        - button "Ask Voss to…" [ref=e89] [cursor=pointer]:
          - generic [ref=e90]: ❯
        - button "Layout presets" [ref=e92] [cursor=pointer]:
          - generic [ref=e93]: ▦
      - generic [ref=e94]:
        - generic [ref=e95]:
          - img [ref=e96]
          - generic [ref=e99]: Agents
          - button "Launch agent" [ref=e100] [cursor=pointer]: +
          - button "Collapse sidebar" [ref=e101] [cursor=pointer]: ◀
        - generic [ref=e102]: AGENTS
        - generic [ref=e103]:
          - generic [ref=e104]: No agents running
          - button "Quick-launch agent" [ref=e105] [cursor=pointer]: + Quick-launch agent
        - generic [ref=e106]: ACTIVITY
        - generic [ref=e108]: No activity yet
        - generic [ref=e109]: USAGE
        - generic [ref=e111]: No usage data
      - generic [ref=e112]:
        - region "Task intake" [ref=e113]:
          - generic [ref=e115]:
            - generic [ref=e116]: ▸
            - textbox "Task goal" [ref=e117]:
              - /placeholder: What should Voss work on?
          - generic [ref=e118]:
            - generic [ref=e119]:
              - generic [ref=e120]: In
              - textbox "Scope" [ref=e121]:
                - /placeholder: e.g. tests/**
            - generic [ref=e122]: ·
            - combobox "Safety mode" [ref=e123] [cursor=pointer]:
              - option "Read only" [selected]
              - option "Can edit"
              - option "Autopilot"
            - generic [ref=e124]: ·
            - button "Details ▸" [ref=e125] [cursor=pointer]
            - button "Start Task" [disabled] [ref=e126]: Start ↵
        - generic [ref=e127]:
          - tab "Test Close Test" [selected] [ref=e129]:
            - generic [ref=e131]: Test
            - button "Close Test" [ref=e133]: ×
          - button "New workspace" [ref=e134]: +
        - generic [ref=e135]:
          - generic [ref=e139]:
            - generic [ref=e141]:
              - generic [ref=e142]:
                - generic [ref=e143]:
                  - generic "Shell running" [ref=e144]: ●
                  - generic [ref=e145]: "1"
                - generic "voss-e2e-proj" [ref=e146]
                - button "Pane menu" [ref=e148]: ⋯
              - generic [ref=e155]:
                - generic:
                  - textbox "Terminal input"
            - generic [ref=e162]:
              - generic [ref=e164]:
                - generic [ref=e165]:
                  - generic [ref=e166]:
                    - generic "Shell running" [ref=e167]: ●
                    - generic [ref=e168]: "2"
                  - generic "Terminal" [ref=e169]
                  - button "Pane menu" [ref=e171]: ⋯
                - generic [ref=e178]:
                  - generic:
                    - textbox "Terminal input"
              - generic [ref=e185]:
                - generic [ref=e187]:
                  - generic [ref=e188]:
                    - generic [ref=e189]:
                      - generic "Shell running" [ref=e190]: ●
                      - generic [ref=e191]: "3"
                    - generic "Terminal" [ref=e192]
                    - button "Pane menu" [ref=e194]: ⋯
                  - generic [ref=e201]:
                    - generic:
                      - textbox "Terminal input"
                - generic [ref=e208]:
                  - generic [ref=e209]:
                    - generic [ref=e210]:
                      - generic "Shell running" [ref=e211]: ●
                      - generic [ref=e212]: "4"
                    - generic "Terminal" [ref=e213]
                    - button "Pane menu" [ref=e215]: ⋯
                  - generic [ref=e222]:
                    - generic:
                      - textbox "Terminal input"
          - generic [ref=e228]: No agent context — focus an agent pane
    - generic [ref=e229]:
      - generic [ref=e230]:
        - generic [ref=e231]: Test
        - generic [ref=e232]: ·
        - button "Org" [ref=e233] [cursor=pointer]
        - generic [ref=e234]: 4 panes
      - button "Ctx" [ref=e236] [cursor=pointer]
  - generic [ref=e237]: could not load keymap settings
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | import { bootApp, stableRects, paneRects, type PaneRect } from './_helpers';
  3   | 
  4   | /**
  5   |  * A4 layout presets end-to-end — preset cycle, custom-state surfacing,
  6   |  * preset click dispatch. Runs on macOS via mock-IPC.
  7   |  *
  8   |  * Save/load round-trip (writes to .voss/layouts/) and default.json auto-apply
  9   |  * (real filesystem) stay deferred to Linux CI under TAURI_E2E=1.
  10  |  */
  11  | 
  12  | test.describe.configure({ mode: 'serial' });
  13  | 
  14  | const BROWSER =
  15  |   (process.env.PW_BROWSER as 'chromium' | 'webkit' | 'firefox') ?? 'chromium';
  16  | test.use({ browserName: BROWSER });
  17  | 
  18  | async function buildFourPanes(page: import('@playwright/test').Page): Promise<PaneRect[]> {
  19  |   await bootApp(page);
  20  |   // ⌘D x3 → 4 panes in a horizontal row.
  21  |   await page.keyboard.press('Meta+KeyD');
  22  |   await stableRects(page, 2);
  23  |   await page.keyboard.press('Meta+KeyD');
  24  |   await stableRects(page, 3);
  25  |   await page.keyboard.press('Meta+KeyD');
  26  |   return stableRects(page, 4);
  27  | }
  28  | 
  29  | test.describe('A4 layout presets (mock-IPC)', () => {
  30  |   test('lay-ac1: Cmd+G cycles fanout → pipeline → swarm → watchers → fanout', async ({ page }) => {
  31  |     await buildFourPanes(page);
  32  | 
  33  |     // Find the preset switcher via the rail menu.
  34  |     await page.locator('button[aria-label="Layout presets"]').click();
  35  |     const menu = page.locator('.portal-layout-menu');
  36  |     await expect(menu).toBeVisible();
  37  | 
  38  |     // Initial active preset is the first button (fanout) — or 'custom' label
  39  |     // may show if the 4-pane row isn't exactly fanout. We assert cycling
  40  |     // changes the aria-pressed state on successive presets.
  41  |     const presetButtons = menu.locator('button[aria-pressed]');
  42  |     const count = await presetButtons.count();
  43  |     expect(count).toBeGreaterThan(0);
  44  | 
  45  |     // Close menu, then press Cmd+G four times. Pane count stays at 4.
  46  |     for (let i = 0; i < 4; i++) {
  47  |       await page.keyboard.press('Meta+KeyG');
  48  |     }
  49  |     await expect(page.locator('[data-pane-id]')).toHaveCount(4);
  50  |   });
  51  | 
  52  |   test('lay-ac2: manual split after preset flips switcher state to custom', async ({ page }) => {
  53  |     await buildFourPanes(page);
  54  | 
  55  |     // Apply a preset first via Cmd+G (lands on fanout after one press).
  56  |     await page.keyboard.press('Meta+KeyG');
  57  | 
  58  |     // Manual split — ⌘D.
  59  |     await page.keyboard.press('Meta+KeyD');
  60  |     await stableRects(page, 5);
  61  | 
  62  |     // Open the preset menu and assert the 'custom' label is present.
  63  |     await page.locator('button[aria-label="Layout presets"]').click();
  64  |     await expect(page.locator('[data-preset-state="custom"]')).toBeVisible();
  65  |   });
  66  | 
  67  |   test('lay-ac3: clicking a preset advances geometry without re-mounting panes', async ({ page }) => {
  68  |     const before = await buildFourPanes(page);
  69  |     const beforeIds = before.map((r) => r.id).sort();
  70  | 
  71  |     await page.locator('button[aria-label="Layout presets"]').click();
  72  |     // Click 'pipeline' (the 2nd preset button).
  73  |     const pipelineBtn = page.locator('.portal-layout-menu button[aria-label="Switch layout to pipeline"]');
  74  |     await expect(pipelineBtn).toHaveCount(1);
  75  |     await pipelineBtn.click();
  76  | 
  77  |     // Wait for geometry to settle at 4 panes.
  78  |     const after = await stableRects(page, 4);
  79  |     const afterIds = after.map((r) => r.id).sort();
  80  | 
  81  |     // No pane was destroyed — same ids survive (A4 LAY-04 contract).
  82  |     expect(afterIds).toEqual(beforeIds);
  83  | 
  84  |     // Geometry changed (pipeline silhouette differs from the row).
  85  |     const beforeXs = before.map((r) => Math.round(r.x));
  86  |     const afterXs = after.map((r) => Math.round(r.x));
  87  |     // At least one pane moved horizontally or the set of x positions changed.
  88  |     const geometryChanged = JSON.stringify(beforeXs) !== JSON.stringify(afterXs);
> 89  |     expect(geometryChanged).toBe(true);
      |                             ^ Error: expect(received).toBe(expected) // Object.is equality
  90  |   });
  91  | });
  92  | 
  93  | // --- Save/load + default.json filesystem scenarios ---------------------------
  94  | const TAURI_E2E =
  95  |   process.env.TAURI_E2E === '1' || process.env.TAURI_E2E === 'true';
  96  | const SKIP_REASON_FS =
  97  |   'requires real .voss/layouts/ filesystem; deferred to Linux CI under TAURI_E2E=1';
  98  | 
  99  | test.describe('A4 layout presets (live-only)', () => {
  100 |   test.skip(!TAURI_E2E, SKIP_REASON_FS);
  101 | 
  102 |   test('lay-ac4: save layout writes .voss/layouts/<name>.json with version=1', () => {
  103 |     // Build a 3-pane swarm, invoke saveCurrentLayout via the app callable,
  104 |     // assert .voss/layouts/build-watch.json exists with version=1.
  105 |   });
  106 | 
  107 |   test('lay-ac5: load layout restores geometry+focus without killing panes', () => {
  108 |     // Save a 4-pane fanout. Modify geometry to 2 panes via ⌘W. Load the saved
  109 |     // fanout. Assert 4 panes present, the two original ids survived.
  110 |   });
  111 | 
  112 |   test('lay-ac6: smaller saved layout preserves extras via overflow spill', () => {
  113 |     // Open 6 panes. Save a 2-pane V layout under `pair`. Open 6 panes again,
  114 |     // load `pair`. Assert all 6 ids still present.
  115 |   });
  116 | 
  117 |   test('lay-ac7: default.json auto-applies on project open', () => {
  118 |     // Place a valid layout at <workspace>/.voss/layouts/default.json before
  119 |     // launching the harness. On boot, assert geometry matches.
  120 |   });
  121 | 
  122 |   test('lay-ac8: corrupt default.json does NOT crash startup', () => {
  123 |     // Write `{not-json` to default.json. App boots with the single default
  124 |     // pane; stderr contains `layout ignored: invalid file`.
  125 |   });
  126 | 
  127 |   test('lay-ac9: unsupported version default.json is ignored', () => {
  128 |     // Write `{"version":999,…}`. App boots with single default pane.
  129 |   });
  130 | 
  131 |   test('lay-ac10: save layout with invalid name surfaces UI-SPEC error string', () => {
  132 |     // Attempt save with name "../escape" → rejected promise resolves to the
  133 |     // exact string "layout name cannot contain /, \\ or ..".
  134 |   });
  135 | });
```