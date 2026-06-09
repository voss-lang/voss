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

await page.keyboard.press('Meta+KeyD');
await page.waitForTimeout(800);
console.log('--- after Meta+D, panes:', await page.$$eval('[data-pane-id]', (e) => e.length));

await page.keyboard.press('Meta+Backslash');
await page.waitForTimeout(800);
console.log('--- after Meta+\\, panes:', await page.$$eval('[data-pane-id]', (e) => e.length));

await browser.close();
