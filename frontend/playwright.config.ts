import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  workers: 1,
  timeout: 45_000,
  use: { browserName: 'chromium', channel: process.env.CI ? undefined : 'msedge', headless: true, baseURL: 'http://127.0.0.1:4174', screenshot: 'only-on-failure' },
  webServer: [
    { command: 'node ../scripts/serve-static.mjs out 4174', url: 'http://127.0.0.1:4174', reuseExistingServer: false },
    { command: '"..\\.venv\\Scripts\\python.exe" ../scripts/ui-test-server.py', url: 'http://127.0.0.1:8000/api/v1/health', reuseExistingServer: false },
    { command: 'node ../scripts/serve-static.mjs ../website/out 4173', url: 'http://127.0.0.1:4173', reuseExistingServer: false },
  ],
});
