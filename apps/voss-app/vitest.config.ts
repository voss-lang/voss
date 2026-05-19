import { defineConfig } from 'vitest/config';
import solidPlugin from 'vite-plugin-solid';

export default defineConfig({
  plugins: [solidPlugin()],
  test: {
    environment: 'jsdom',
    include: ['src/**/__tests__/**/*.test.tsx'],
  },
  resolve: {
    conditions: ['development', 'browser'],
  },
});
