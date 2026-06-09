# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: pane-drag-rearrange.spec.ts >> pane drag-rearrange (real browser) >> center drop swaps pane ids between slots
- Location: e2e/pane-drag-rearrange.spec.ts:175:3

# Error details

```
Error: expect(received).toEqual(expected) // deep equality

- Expected  - 5
+ Received  + 5

  Array [
    Object {
-     "w": 690.046875,
+     "w": 466.140625,
      "x": 280,
    },
    Object {
-     "w": 353.46875,
-     "x": 971.046875,
+     "w": 465.421875,
+     "x": 747.140625,
    },
    Object {
-     "w": 354.46875,
-     "x": 1325.515625,
+     "w": 466.421875,
+     "x": 1213.5625,
    },
  ]
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e6]:
      - img [ref=e7]
      - generic [ref=e10]: voss-e2e-proj
    - generic [ref=e12]:
      - generic "Custom layout" [ref=e13]: custom
      - generic [ref=e14]:
        - button "Switch layout to fanout" [ref=e15] [cursor=pointer]: fanout
        - button "Switch layout to pipeline" [ref=e16] [cursor=pointer]: pipeline
        - button "Switch layout to swarm" [ref=e17] [cursor=pointer]: swarm
        - button "Switch layout to watchers" [ref=e18] [cursor=pointer]: watchers
    - group "View mode" [ref=e19]:
      - button "Live Work" [pressed] [ref=e20] [cursor=pointer]
      - button "Run Review" [ref=e21] [cursor=pointer]
    - 'generic "Data source: snapshot" [ref=e22]': snapshot
  - generic [ref=e23]:
    - tab "Test Close Test" [selected] [ref=e25]:
      - generic [ref=e27]: Test
      - button "Close Test" [ref=e29]: ×
    - button "New workspace" [ref=e30]: +
  - generic [ref=e31]:
    - generic [ref=e32]:
      - generic [ref=e33]:
        - generic [ref=e34]:
          - img [ref=e35]
          - generic [ref=e38]: Agents
          - button "Launch agent" [ref=e39] [cursor=pointer]: +
          - button "Collapse sidebar" [ref=e40] [cursor=pointer]: ◀
        - generic [ref=e41]: AGENTS
        - generic [ref=e42]:
          - generic [ref=e43]: No agents running
          - button "Quick-launch agent" [ref=e44] [cursor=pointer]: + Quick-launch agent
        - generic [ref=e45]: ACTIVITY
        - generic [ref=e47]: No activity yet
        - generic [ref=e48]: USAGE
        - generic [ref=e50]: No usage data
      - generic [ref=e51]:
        - region "Run intake" [ref=e52]:
          - generic [ref=e53]:
            - generic [ref=e54]: ▸
            - textbox "Run goal" [ref=e55]:
              - /placeholder: Describe the run goal…
          - generic "Mode" [ref=e56]:
            - generic [ref=e57]:
              - button "Plan" [ref=e58] [cursor=pointer]
              - button "Edit" [ref=e59] [cursor=pointer]
              - button "Auto" [ref=e60] [cursor=pointer]
          - generic [ref=e61]:
            - generic [ref=e62]: team
            - combobox "Team" [ref=e63]:
              - option "solo" [selected]
              - option "core"
              - option "review"
          - generic [ref=e64]:
            - generic [ref=e65]: scope
            - textbox "Scope" [ref=e66]:
              - /placeholder: e.g. tests/**
          - generic [ref=e67]:
            - generic [ref=e68]: budget
            - spinbutton "Budget" [ref=e69]
          - button "Attach context" [ref=e70] [cursor=pointer]: + ctx
          - generic "Run target" [ref=e71]:
            - generic [ref=e72]:
              - button "Voss run" [ref=e73] [cursor=pointer]
              - button "Terminal agent" [ref=e74] [cursor=pointer]
          - button "Start run" [ref=e75] [cursor=pointer]: Start ⏎
        - generic [ref=e76]:
          - generic [ref=e80]:
            - generic [ref=e82]:
              - generic [ref=e83]:
                - generic [ref=e84]:
                  - generic "Shell running" [ref=e85]: ●
                  - generic [ref=e86]: "1"
                - generic "Terminal" [ref=e87]
                - button "Pane menu" [ref=e89]: ⋯
              - generic [ref=e95]:
                - generic:
                  - textbox "Terminal input"
            - generic [ref=e102]:
              - generic [ref=e104]:
                - generic [ref=e105]:
                  - generic [ref=e106]:
                    - generic "Shell running" [ref=e107]: ●
                    - generic [ref=e108]: "2"
                  - generic "voss-e2e-proj" [ref=e109]
                  - button "Pane menu" [ref=e111]: ⋯
                - generic [ref=e117]:
                  - generic:
                    - textbox "Terminal input"
              - generic [ref=e124]:
                - generic [ref=e125]:
                  - generic [ref=e126]:
                    - generic "Shell running" [ref=e127]: ●
                    - generic [ref=e128]: "3"
                  - generic "Terminal" [ref=e129]
                  - button "Pane menu" [ref=e131]: ⋯
                - generic [ref=e137]:
                  - generic:
                    - textbox "Terminal input"
          - generic [ref=e143]: No agent context — focus an agent pane
    - generic [ref=e144]:
      - generic [ref=e145]:
        - generic [ref=e146]: Test
        - generic [ref=e147]: ·
        - button "Org" [ref=e148] [cursor=pointer]
        - generic [ref=e149]: 3 panes
      - button "Ctx" [ref=e151] [cursor=pointer]
  - generic [ref=e152]: could not load keymap settings
```

# Test source

```ts
  96  |         const id = nextCallbackId++;
  97  |         callbacks.set(id, cb);
  98  |         (window as unknown as Record<string, unknown>)[`_${id}`] = cb;
  99  |         return id;
  100 |       },
  101 |       unregisterCallback(id: number) {
  102 |         callbacks.delete(id);
  103 |         delete (window as unknown as Record<string, unknown>)[`_${id}`];
  104 |       },
  105 |       convertFileSrc(p: string) {
  106 |         return p;
  107 |       },
  108 |       metadata: {
  109 |         currentWindow: { label: 'main' },
  110 |         currentWebview: { label: 'main', windowLabel: 'main' },
  111 |       },
  112 |       plugins: {},
  113 |     };
  114 |   });
  115 | }
  116 | 
  117 | type PaneRect = { id: string; x: number; y: number; w: number; h: number };
  118 | 
  119 | /** Visible pane leaves (active workspace only — hidden grids have 0×0 rects). */
  120 | async function paneRects(page: Page): Promise<PaneRect[]> {
  121 |   return page.$$eval('[data-pane-id]', (els) =>
  122 |     els
  123 |       .map((el) => {
  124 |         const r = el.getBoundingClientRect();
  125 |         return {
  126 |           id: el.getAttribute('data-pane-id') ?? '',
  127 |           x: r.x,
  128 |           y: r.y,
  129 |           w: r.width,
  130 |           h: r.height,
  131 |         };
  132 |       })
  133 |       .filter((r) => r.w > 0 && r.h > 0),
  134 |   );
  135 | }
  136 | 
  137 | async function bootThreePanes(page: Page): Promise<PaneRect[]> {
  138 |   await installTauriMock(page);
  139 |   await page.setViewportSize({ width: 1400, height: 900 });
  140 |   await page.goto(APP_URL);
  141 |   await page.waitForSelector('[data-pane-id]', { timeout: 15000 });
  142 | 
  143 |   // ⌘D = pane.splitRight (vscode profile) — build a 3-pane row.
  144 |   await page.keyboard.press('Meta+KeyD');
  145 |   await expect
  146 |     .poll(async () => (await paneRects(page)).length, { timeout: 5000 })
  147 |     .toBe(2);
  148 |   await page.keyboard.press('Meta+KeyD');
  149 |   await expect
  150 |     .poll(async () => (await paneRects(page)).length, { timeout: 5000 })
  151 |     .toBe(3);
  152 | 
  153 |   const rects = await paneRects(page);
  154 |   rects.sort((a, b) => a.x - b.x || a.y - b.y);
  155 |   return rects;
  156 | }
  157 | 
  158 | /** Drag from a pane's header to a point, with threshold-crossing moves. */
  159 | async function dragHeaderTo(
  160 |   page: Page,
  161 |   from: PaneRect,
  162 |   toX: number,
  163 |   toY: number,
  164 | ): Promise<void> {
  165 |   const headerX = from.x + from.w / 2;
  166 |   const headerY = from.y + 11; // middle of the 22px header strip
  167 |   await page.mouse.move(headerX, headerY);
  168 |   await page.mouse.down();
  169 |   await page.mouse.move(headerX + 12, headerY + 4, { steps: 2 }); // cross 5px threshold
  170 |   await page.mouse.move(toX, toY, { steps: 10 });
  171 |   await page.mouse.up();
  172 | }
  173 | 
  174 | test.describe('pane drag-rearrange (real browser)', () => {
  175 |   test('center drop swaps pane ids between slots', async ({ page }) => {
  176 |     const before = await bootThreePanes(page);
  177 |     const [a, b] = before;
  178 | 
  179 |     // Drop A onto B's center (inner 50%) → payload swap.
  180 |     await dragHeaderTo(page, a, b.x + b.w / 2, b.y + b.h / 2);
  181 | 
  182 |     await expect
  183 |       .poll(async () => {
  184 |         const after = (await paneRects(page)).sort(
  185 |           (p, q) => p.x - q.x || p.y - q.y,
  186 |         );
  187 |         return after.map((r) => r.id).slice(0, 2);
  188 |       })
  189 |       .toEqual([b.id, a.id]);
  190 | 
  191 |     // Same panes, same geometry — only the slot contents swapped.
  192 |     const after = (await paneRects(page)).sort(
  193 |       (p, q) => p.x - q.x || p.y - q.y,
  194 |     );
  195 |     expect(after.length).toBe(3);
> 196 |     expect(after.map((r) => ({ x: r.x, w: r.w }))).toEqual(
      |                                                    ^ Error: expect(received).toEqual(expected) // deep equality
  197 |       before.map((r) => ({ x: r.x, w: r.w })),
  198 |     );
  199 |   });
  200 | 
  201 |   test('edge drop re-splits: drag A onto C bottom edge', async ({ page }) => {
  202 |     const before = await bootThreePanes(page);
  203 |     const [a, , c] = before;
  204 | 
  205 |     // Drop A onto C's bottom edge band (outer 25%) → V split, A below C.
  206 |     await dragHeaderTo(page, a, c.x + c.w / 2, c.y + c.h * 0.9);
  207 | 
  208 |     await expect
  209 |       .poll(async () => {
  210 |         const after = await paneRects(page);
  211 |         const movedA = after.find((r) => r.id === a.id);
  212 |         const newC = after.find((r) => r.id === c.id);
  213 |         if (!movedA || !newC) return 'missing';
  214 |         // A now sits BELOW C in C's old column.
  215 |         return movedA.y > newC.y && Math.abs(movedA.x - newC.x) < 2
  216 |           ? 'stacked'
  217 |           : `a=${JSON.stringify(movedA)} c=${JSON.stringify(newC)}`;
  218 |       })
  219 |       .toBe('stacked');
  220 | 
  221 |     // Exactly one structural sync fired for the drop (plus earlier splits).
  222 |     const syncs = await page.evaluate(() => window.__SYNCS__.length);
  223 |     expect(syncs).toBeGreaterThan(0);
  224 |   });
  225 | 
  226 |   test('escape cancels drag without mutation', async ({ page }) => {
  227 |     const before = await bootThreePanes(page);
  228 |     const [a, b] = before;
  229 | 
  230 |     const headerX = a.x + a.w / 2;
  231 |     const headerY = a.y + 11;
  232 |     await page.mouse.move(headerX, headerY);
  233 |     await page.mouse.down();
  234 |     await page.mouse.move(b.x + b.w / 2, b.y + b.h / 2, { steps: 8 });
  235 |     await page.keyboard.press('Escape');
  236 |     await page.mouse.up();
  237 | 
  238 |     const after = (await paneRects(page)).sort(
  239 |       (p, q) => p.x - q.x || p.y - q.y,
  240 |     );
  241 |     expect(after.map((r) => r.id)).toEqual(before.map((r) => r.id));
  242 |   });
  243 | 
  244 |   test('click without movement still focuses the pane', async ({ page }) => {
  245 |     const before = await bootThreePanes(page);
  246 |     const [a] = before;
  247 | 
  248 |     await page.mouse.click(a.x + a.w / 2, a.y + 11);
  249 |     await expect
  250 |       .poll(() =>
  251 |         page.$eval(
  252 |           '.grid-pane-leaf--focused',
  253 |           (el) => el.getAttribute('data-pane-id'),
  254 |         ),
  255 |       )
  256 |       .toBe(a.id);
  257 |   });
  258 | });
  259 | 
```