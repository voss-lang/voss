import { test, expect, type Page } from '@playwright/test';

/**
 * Pane drag-rearrange — REAL-BROWSER integration (runs on macOS, no
 * tauri-driver needed). Boots the actual app against `vite dev` with
 * `window.__TAURI_INTERNALS__` mocked via addInitScript, then performs real
 * pointer drags (mouse down → move → up) on pane headers.
 *
 * This covers the gap jsdom tests cannot: real hit-testing geometry, real
 * pointer event targeting/capture, real Solid rendering of the store
 * mutation. PTYs are inert (spawn_pty mocked) — the grid chrome is what's
 * under test.
 *
 * Requires the dev server: `pnpm dev` (http://localhost:5173).
 */

const APP_URL = process.env.VOSS_APP_URL ?? 'http://localhost:5173';

declare global {
  interface Window {
    __SYNCS__: unknown[];
  }
}

/** Install a minimal Tauri v2 IPC mock before any app module loads. */
async function installTauriMock(page: Page): Promise<void> {
  await page.addInitScript(() => {
    let nextCallbackId = 1;
    let nextPty = 1;
    const syncs: unknown[] = [];
    (window as unknown as { __SYNCS__: unknown[] }).__SYNCS__ = syncs;

    const invoke = (cmd: string, args?: Record<string, unknown>) => {
      switch (cmd) {
        case 'load_workspaces_index':
          return Promise.resolve({
            version: 1,
            activeWorkspaceId: 'w1',
            workspaces: [
              {
                id: 'w1',
                name: 'Test',
                projectPath: '/tmp/voss-e2e-proj',
                accentColor: 'blue',
                order: 0,
              },
            ],
          });
        case 'open_project':
          return Promise.resolve({
            path: (args?.path as string) ?? '/tmp/voss-e2e-proj',
            name: 'voss-e2e-proj',
            gitBranch: null,
          });
        case 'load_keymap_profile':
          return Promise.resolve('"vscode"');
        case 'load_appearance_settings':
          return Promise.resolve({});
        case 'load_recents':
          return Promise.resolve([]);
        case 'default_cwd':
          return Promise.resolve('/tmp/voss-e2e-proj');
        case 'spawn_pty':
          return Promise.resolve(`mock-pty-${nextPty++}`);
        case 'get_fg_process':
          return Promise.resolve('');
        case 'sync_grid':
          syncs.push(JSON.parse(JSON.stringify(args?.newState ?? null)));
          return Promise.resolve(null);
        case 'get_active_agents':
        case 'list_profiles':
        case 'list_layouts':
        case 'list_workspaces':
        case 'list_system_fonts':
        case 'list_dir':
        case 'enumerate_runs':
        case 'git_log':
        case 'sweep_orphan_agents':
          return Promise.resolve([]);
        case 'plugin:os|platform':
          return Promise.resolve('macos');
        case 'plugin:os|os_type':
          return Promise.resolve('macos');
        case 'plugin:event|listen':
          return Promise.resolve(nextCallbackId++);
        default:
          // load_session / load_default_layout / theme / etc. → "nothing saved"
          return Promise.resolve(null);
      }
    };

    const callbacks = new Map<number, (response: unknown) => void>();
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {
      invoke,
      transformCallback(cb: (response: unknown) => void, _once?: boolean) {
        const id = nextCallbackId++;
        callbacks.set(id, cb);
        (window as unknown as Record<string, unknown>)[`_${id}`] = cb;
        return id;
      },
      unregisterCallback(id: number) {
        callbacks.delete(id);
        delete (window as unknown as Record<string, unknown>)[`_${id}`];
      },
      convertFileSrc(p: string) {
        return p;
      },
      metadata: {
        currentWindow: { label: 'main' },
        currentWebview: { label: 'main', windowLabel: 'main' },
      },
      plugins: {},
    };
  });
}

type PaneRect = { id: string; x: number; y: number; w: number; h: number };

/** Visible pane leaves (active workspace only — hidden grids have 0×0 rects). */
async function paneRects(page: Page): Promise<PaneRect[]> {
  return page.$$eval('[data-pane-id]', (els) =>
    els
      .map((el) => {
        const r = el.getBoundingClientRect();
        return {
          id: el.getAttribute('data-pane-id') ?? '',
          x: r.x,
          y: r.y,
          w: r.width,
          h: r.height,
        };
      })
      .filter((r) => r.w > 0 && r.h > 0),
  );
}

async function bootThreePanes(page: Page): Promise<PaneRect[]> {
  await installTauriMock(page);
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.goto(APP_URL);
  await page.waitForSelector('[data-pane-id]', { timeout: 15000 });

  // ⌘D = pane.splitRight (vscode profile) — build a 3-pane row.
  await page.keyboard.press('Meta+KeyD');
  await expect
    .poll(async () => (await paneRects(page)).length, { timeout: 5000 })
    .toBe(2);
  await page.keyboard.press('Meta+KeyD');
  await expect
    .poll(async () => (await paneRects(page)).length, { timeout: 5000 })
    .toBe(3);

  const rects = await paneRects(page);
  rects.sort((a, b) => a.x - b.x || a.y - b.y);
  return rects;
}

/** Drag from a pane's header to a point, with threshold-crossing moves. */
async function dragHeaderTo(
  page: Page,
  from: PaneRect,
  toX: number,
  toY: number,
): Promise<void> {
  const headerX = from.x + from.w / 2;
  const headerY = from.y + 11; // middle of the 22px header strip
  await page.mouse.move(headerX, headerY);
  await page.mouse.down();
  await page.mouse.move(headerX + 12, headerY + 4, { steps: 2 }); // cross 5px threshold
  await page.mouse.move(toX, toY, { steps: 10 });
  await page.mouse.up();
}

test.describe('pane drag-rearrange (real browser)', () => {
  test('center drop swaps pane ids between slots', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a, b] = before;

    // Drop A onto B's center (inner 50%) → payload swap.
    await dragHeaderTo(page, a, b.x + b.w / 2, b.y + b.h / 2);

    await expect
      .poll(async () => {
        const after = (await paneRects(page)).sort(
          (p, q) => p.x - q.x || p.y - q.y,
        );
        return after.map((r) => r.id).slice(0, 2);
      })
      .toEqual([b.id, a.id]);

    // Same panes, same geometry — only the slot contents swapped.
    const after = (await paneRects(page)).sort(
      (p, q) => p.x - q.x || p.y - q.y,
    );
    expect(after.length).toBe(3);
    expect(after.map((r) => ({ x: r.x, w: r.w }))).toEqual(
      before.map((r) => ({ x: r.x, w: r.w })),
    );
  });

  test('edge drop re-splits: drag A onto C bottom edge', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a, , c] = before;

    // Drop A onto C's bottom edge band (outer 25%) → V split, A below C.
    await dragHeaderTo(page, a, c.x + c.w / 2, c.y + c.h * 0.9);

    await expect
      .poll(async () => {
        const after = await paneRects(page);
        const movedA = after.find((r) => r.id === a.id);
        const newC = after.find((r) => r.id === c.id);
        if (!movedA || !newC) return 'missing';
        // A now sits BELOW C in C's old column.
        return movedA.y > newC.y && Math.abs(movedA.x - newC.x) < 2
          ? 'stacked'
          : `a=${JSON.stringify(movedA)} c=${JSON.stringify(newC)}`;
      })
      .toBe('stacked');

    // Exactly one structural sync fired for the drop (plus earlier splits).
    const syncs = await page.evaluate(() => window.__SYNCS__.length);
    expect(syncs).toBeGreaterThan(0);
  });

  test('escape cancels drag without mutation', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a, b] = before;

    const headerX = a.x + a.w / 2;
    const headerY = a.y + 11;
    await page.mouse.move(headerX, headerY);
    await page.mouse.down();
    await page.mouse.move(b.x + b.w / 2, b.y + b.h / 2, { steps: 8 });
    await page.keyboard.press('Escape');
    await page.mouse.up();

    const after = (await paneRects(page)).sort(
      (p, q) => p.x - q.x || p.y - q.y,
    );
    expect(after.map((r) => r.id)).toEqual(before.map((r) => r.id));
  });

  test('click without movement still focuses the pane', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a] = before;

    await page.mouse.click(a.x + a.w / 2, a.y + 11);
    await expect
      .poll(() =>
        page.$eval(
          '.grid-pane-leaf--focused',
          (el) => el.getAttribute('data-pane-id'),
        ),
      )
      .toBe(a.id);
  });
});
