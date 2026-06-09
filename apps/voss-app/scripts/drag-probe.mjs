// Throwaway diagnostic probe for the pane-drag bug. Not part of the suite.
import { chromium, webkit } from '@playwright/test';

const engine = process.env.PW_ENGINE === 'webkit' ? webkit : chromium;
const browser = await engine.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

page.on('console', (msg) => console.log(`[console.${msg.type()}]`, msg.text()));
page.on('pageerror', (err) => console.log('[pageerror]', err.message));

await page.addInitScript(() => {
  let nextCallbackId = 1;
  let nextPty = 1;
  window.__SYNCS__ = [];
  const invoke = (cmd, args) => {
    switch (cmd) {
      case 'load_workspaces_index':
        return Promise.resolve({
          version: 1,
          activeWorkspaceId: 'w1',
          workspaces: [
            { id: 'w1', name: 'Test', projectPath: '/tmp/voss-e2e-proj', accentColor: 'blue', order: 0 },
          ],
        });
      case 'open_project':
        return Promise.resolve({ path: args?.path ?? '/tmp/voss-e2e-proj', name: 'voss-e2e-proj', gitBranch: null });
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
        window.__SYNCS__.push(JSON.parse(JSON.stringify(args?.newState ?? null)));
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
      case 'plugin:os|os_type':
        return Promise.resolve('macos');
      case 'plugin:event|listen':
        return Promise.resolve(nextCallbackId++);
      default:
        return Promise.resolve(null);
    }
  };
  const callbacks = new Map();
  window.__TAURI_INTERNALS__ = {
    invoke,
    transformCallback(cb) {
      const id = nextCallbackId++;
      callbacks.set(id, cb);
      window[`_${id}`] = cb;
      return id;
    },
    unregisterCallback(id) {
      callbacks.delete(id);
      delete window[`_${id}`];
    },
    convertFileSrc: (p) => p,
    metadata: {
      currentWindow: { label: 'main' },
      currentWebview: { label: 'main', windowLabel: 'main' },
    },
    plugins: {},
  };
});

await page.goto('http://localhost:5173');
await page.waitForSelector('[data-pane-id]', { timeout: 15000 });
console.log('--- booted, panes:', await page.$$eval('[data-pane-id]', (e) => e.length));

// instrument keydown visibility
await page.evaluate(() => {
  window.addEventListener(
    'keydown',
    (e) => console.debug('[probe] keydown', e.key, e.code, 'meta=' + e.metaKey),
    true,
  );
});

const rects = async () =>
  (
    await page.$$eval('[data-pane-id]', (els) =>
      els
        .map((el) => {
          const r = el.getBoundingClientRect();
          return {
            id: el.getAttribute('data-pane-id'),
            x: r.x,
            y: r.y,
            w: r.width,
            h: r.height,
          };
        })
        .filter((r) => r.w > 0),
    )
  ).sort((a, b) => a.x - b.x || a.y - b.y);

await page.keyboard.press('Meta+KeyD');
await page.waitForTimeout(400);
await page.keyboard.press('Meta+KeyD');
await page.waitForTimeout(400);
console.log('--- 3 panes:', JSON.stringify(await rects(), null, 1));

// drag A header onto B center
const [a, b] = await rects();
const hx = a.x + a.w / 2;
const hy = a.y + 11;
await page.mouse.move(hx, hy);
await page.mouse.down();
await page.mouse.move(hx + 12, hy + 4, { steps: 2 });
await page.mouse.move(b.x + b.w / 2, b.y + b.h / 2, { steps: 10 });
await page.mouse.up();
await page.waitForTimeout(600);
console.log('--- after center drop:', JSON.stringify(await rects(), null, 1));

await browser.close();
