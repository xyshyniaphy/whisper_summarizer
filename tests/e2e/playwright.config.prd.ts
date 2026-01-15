import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2Eテスト設定 - Production
 *
 * Production serverに対するE2Eテストを実行する。
 * SSH local port forwardingでCloudflareをバイパスし、localhost auth bypassを利用する。
 *
 * 接続フロー:
 * 1. SSH tunnel: localhost:8130 → server:localhost:3080 (nginx)
 * 2. テストは http://localhost:8130 にアクセス
 * 3. サーバーは 127.0.0.1 からのリクエストとして認識
 * 4. localhost auth bypass がトリガーされ、テストユーザーでログイン
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
    baseURL: process.env.FRONTEND_URL || 'http://localhost:8130',
    actionTimeout: 10000,
    navigationTimeout: 15000,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    storageState: {
      origins: [
        {
          origin: process.env.FRONTEND_URL || 'http://localhost:8130',
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
