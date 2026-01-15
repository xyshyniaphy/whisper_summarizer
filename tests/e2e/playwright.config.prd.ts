import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2Eテスト設定 - Production
 *
 * Production serverに対するE2Eテストを実行する。
 * SOCKS5 proxy経由で接続し、localhost auth bypassを利用する。
 */
export default defineConfig({
  testDir: './tests',
  timeout: 30 * 1000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,

  reporter: [
    ['html', { outputFolder: '/app/data/playwright-report', open: 'never' }],
    ['list'],
  ],

  outputDir: '/app/data/screenshots/failures',

  use: {
    baseURL: process.env.FRONTEND_URL || 'https://w.198066.xyz',
    proxy: {
      server: process.env.PROXY_SERVER || 'socks5://localhost:3480',
    },
    actionTimeout: 10000,
    navigationTimeout: 15000,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    storageState: {
      origins: [
        {
          origin: process.env.FRONTEND_URL || 'https://w.198066.xyz',
          localStorage: [
            { name: 'e2e-test-mode', value: 'true' },
          ],
        },
      ],
    },
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
