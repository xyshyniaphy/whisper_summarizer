import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2Eテスト設定
 * 
 * ユーザーフローの自動テストを実行する。
 */
export default defineConfig({
  // テストディレクトリ
  testDir: './tests',

  // 各テストの最大実行時間
  timeout: 30 * 1000,

  // 並列実行しない (データベース競合を避けるため)
  fullyParallel: false,
  workers: 1,

  // 失敗時のリトライ回数
  retries: process.env.CI ? 2 : 0,

  // レポーター
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],

  // 共通設定
  use: {
    // ベースURL
    baseURL: 'http://localhost:3000',

    // トレース記録 (失敗時のみ)
    trace: 'on-first-retry',

    // スクリーンショット (失敗時のみ)
    screenshot: 'only-on-failure',

    // ビデオ録画 (失敗時のみ)
    video: 'retain-on-failure',
  },

  // テスト実行前にサーバーを起動
  webServer: {
    command: 'echo "開発環境は別途起動してください"',
    url: 'http://localhost:3000',
    timeout: 120 * 1000,
    reuseExistingServer: !process.env.CI,
  },

  // ブラウザ設定
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // 必要に応じて他のブラウザを追加
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],
})
