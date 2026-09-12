import { defineConfig } from '@playwright/test';

const APP_URL = process.env.VOSS_APP_URL ?? 'http://localhost:5173';

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  reporter: 'list',
  // Auto-start vite dev server if not already running. Reuses existing server
  // on port 5173 when present (e.g. `pnpm dev` in another terminal). The dev
  webServer: {
    command: 'pnpm dev',
    url: APP_URL,
    reuseExistingServer: true,
    timeout: 60_000,
    cwd: '.',
  },
});
