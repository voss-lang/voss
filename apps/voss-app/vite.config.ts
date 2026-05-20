import { defineConfig } from 'vite';
import solidPlugin from 'vite-plugin-solid';
import tailwindcss from '@tailwindcss/vite';

// @ts-expect-error process is a nodejs global
const host = process.env.TAURI_DEV_HOST;

export default defineConfig({
  plugins: [tailwindcss(), solidPlugin()],
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
    host: host || false,
    hmr: host ? { protocol: 'ws', host, port: 5183 } : undefined,
    watch: { ignored: ['**/src-tauri/**'] },
  },
  envPrefix: ['VITE_', 'TAURI_ENV_*'],
  build: {
    // Tauri 2 ships modern WebViews — macOS WKWebView ≥ 16.4 (Safari 16.4+
    // engine), Edge Chromium on Windows. `safari13` triggers a
    // rolldown/esbuild destructuring-transform error against solid-js's
    // compiled output (the runtime supports destructuring but the
    // transformer refuses to lower it for that target). Bump to
    // `safari15` to silence it without dropping any platform Tauri
    // actually runs on.
    // @ts-expect-error process is a nodejs global
    target: process.env.TAURI_ENV_PLATFORM === 'windows' ? 'chrome105' : 'safari15',
    // @ts-expect-error process is a nodejs global
    minify: !process.env.TAURI_ENV_DEBUG ? 'esbuild' : false,
    // @ts-expect-error process is a nodejs global
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
  },
});
