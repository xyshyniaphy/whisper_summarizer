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
    ['html', { outputFolder: '/app/data/playwright-report', open: 'never' }],
    ['list'],
  ],

  // 成果物（スクリーンショット、ビデオ、トレース）の出力先
  // 失敗時のスクリーンショット等はここに出力される
  outputDir: '/app/data/screenshots/failures',

  // 共通設定
  use: {
    // ベースURL (Docker Compose内のサービス名またはホストのアドレス)
    baseURL: process.env.FRONTEND_URL || 'http://frontend-test:3000',

    // アクションタイムアウト (click, fill etc.)
    actionTimeout: 10000,
    // ナビゲーションタイムアウト
    navigationTimeout: 15000,

    // トレース記録 (失敗時のみ)
    trace: 'on-first-retry',

    // スクリーンショット (失敗時のみ)
    screenshot: 'only-on-failure',

    // ビデオ録画 (失敗時のみ)
    video: 'retain-on-failure',
  },

  // テスト実行前にサーバーを起動しない (既存のコンテナを使用)

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
