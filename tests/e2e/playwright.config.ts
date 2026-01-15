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

    // Optional SOCKS5 proxy (legacy, not used for production anymore)
    // Production now uses SSH local port forwarding instead
    ...(process.env.PROXY_SERVER ? {
      proxy: {
        server: process.env.PROXY_SERVER,
      },
    } : {}),

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

    // E2Eテストモードを有効化（localStorageに設定）
    storageState: {
      origins: [
        {
          origin: process.env.FRONTEND_URL || 'http://frontend-test:3000',
          localStorage: [
            { name: 'e2e-test-mode', value: 'true' },
          ],
        },
      ],
    },
  },

  // テスト実行前にサーバーを起動しない (既存のコンテナを使用)

  // ブラウザ設定
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // E2Eテストモード環境変数
        contextOptions: {
          // Note: We'll set VITE_E2E_TEST_MODE via extraHTTPHeaders since contextOptions doesn't support env vars
          // Instead, the frontend will check localStorage for test mode
        },
      },
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
