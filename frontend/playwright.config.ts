import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for Vajra Stream E2E tests.
 *
 * - Base URL: http://localhost:3009 (vite dev server)
 * - Auto-starts `npm run dev` if server not running
 * - Headless by default; set PWDEBUG=1 for step-through
 * - Traces/screenshots on failure
 *
 * Note: backend (port 8008) is NOT auto-started. Tests that hit
 * /api/* will fail unless the backend is running. Future: add
 * a second webServer entry + a fixture that skips API tests when
 * backend isn't available.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3009',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3009',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
