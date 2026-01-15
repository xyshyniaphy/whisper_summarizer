/**
 * Theme Toggle E2E Tests
 *
 * Tests for theme toggle with Jotai atoms.
 * Tests real Jotai themeAtom state management.
 */

import { test, expect } from '@playwright/test'

test.describe('Theme Toggle', () => {
  test.beforeEach(async ({ page }) => {
    // E2Eテストモードフラグを設定
    await page.goto('/login')
    await page.evaluate(() => {
      // Safety check: this only works when accessing via localhost
      if (window.location.hostname === 'localhost' ||
          window.location.hostname === '127.0.0.1') {
        localStorage.setItem('e2e-test-mode', 'true')
      } else {
        console.warn('[E2E] Cannot enable test mode on non-localhost hostname')
      }
    })
    await page.reload()

    // APIルートのモック設定
    await setupMockRoutes(page)

    // E2EテストモードでGoogle OAuthログインをモック
    await page.click('button:has-text("使用 Google 继续")')
    await expect(page).toHaveURL(/\/transcriptions/)
  })

  test('テーマ切替ボタンが表示される', async ({ page }) => {
    // テーマ切替ボタンが表示されることを確認
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await expect(themeToggle).toBeVisible()
  })

  test('デフォルトはライトモード', async ({ page }) => {
    // デフォルトでライトモードが適用されていることを確認
    const html = page.locator('html')
    await expect(html).not.toHaveClass('dark')
  })

  test('テーマ切替ボタンでダークモードに切り替わる', async ({ page }) => {
    // テーマ切替ボタンをクリック
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.click()

    // ダークモードが適用されることを確認
    const html = page.locator('html')
    await expect(html).toHaveClass('dark')

    // ダークモードのスタイルが適用されていることを確認
    const body = page.locator('body')
    await expect(body).toHaveCSS('background-color', /rgb\(17, 24, 39\)|rgb\(31, 41, 55\)/)
  })

  test('テーマ切替ボタンでライトモードに切り替わる', async ({ page }) => {
    // まずダークモードに切り替え
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.click()
    await expect(page.locator('html')).toHaveClass('dark')

    // もう一度クリックしてライトモードに戻す
    await themeToggle.click()

    // ライトモードが適用されることを確認
    const html = page.locator('html')
    await expect(html).not.toHaveClass('dark')
  })

  test('テーマ状態がlocalStorageに保存される', async ({ page }) => {
    // ダークモードに切り替え
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.click()

    // localStorageにテーマ状態が保存されていることを確認
    const theme = await page.evaluate(() => {
      return localStorage.getItem('theme')
    })
    expect(theme).toBe('dark')

    // ページをリロード
    await page.reload()

    // ダークモードが保持されていることを確認
    const html = page.locator('html')
    await expect(html).toHaveClass('dark')
  })

  test('テーマ状態がページ間で保持される', async ({ page }) => {
    // ダークモードに切り替え
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.click()

    // 転写詳細ページに遷移
    await page.goto('/transcriptions/test-transcription-1')

    // ダークモードが保持されていることを確認
    const html = page.locator('html')
    await expect(html).toHaveClass('dark')

    // テーマ切替ボタンがまだ表示されていることを確認
    await expect(themeToggle).toBeVisible()
  })

  test('システムテーマ設定に従う', async ({ page }) => {
    // システムテーマ設定をクリア
    await page.evaluate(() => {
      localStorage.removeItem('theme')
    })

    // ページをリロード
    await page.reload()

    // システムテーマが適用されることを確認
    // （デフォルトではライトモード）
    const html = page.locator('html')
    await expect(html).not.toHaveClass('dark')
  })

  test('テーマアイコンが切り替わる', async ({ page }) => {
    // ライトモード：太陽アイコンが表示される
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    const sunIcon = themeToggle.locator('svg[data-lucide="sun"]')
    const moonIcon = themeToggle.locator('svg[data-lucide="moon"]')

    // ライトモードでは太陽アイコンが表示される
    await expect(sunIcon).toBeVisible()
    await expect(moonIcon).not.toBeVisible()

    // ダークモードに切り替え
    await themeToggle.click()

    // ダークモードでは月アイコンが表示される
    await expect(sunIcon).not.toBeVisible()
    await expect(moonIcon).toBeVisible()
  })

  test('ダークモードでコンポーネントのスタイルが正しく適用される', async ({ page }) => {
    // ダークモードに切り替え
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.click()

    // ナイティブのスタイルがダークモード用に変更されることを確認
    const card = page.locator('.bg-white.dark\\:bg-gray-800').first()
    await expect(card).toBeVisible()

    // テキストの色がダークモード用に変更されることを確認
    const text = page.locator('.text-gray-900.dark\\:text-gray-100').first()
    await expect(text).toBeVisible()
  })

  test('テーマ切替中にトランジションアニメーションが適用される', async ({ page }) => {
    // テーマ切替ボタンをクリック
    const themeToggle = page.locator('[data-testid="theme-toggle"]')
    await themeToggle.click()

    // トランジションクラスが適用されていることを確認
    const html = page.locator('html')
    await expect(html).toHaveClass(/transition-colors|duration-200/)
  })
})

/**
 * モックルートを設定するヘルパー関数
 */
async function setupMockRoutes(page: any) {
  // 転写一覧取得
  await page.route('**/api/transcriptions', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 0,
          page: 1,
          page_size: 10,
          total_pages: 0,
          data: []
        })
      })
    } else {
      await route.continue()
    }
  })

  // 転写詳細取得
  await page.route('**/api/transcriptions/test-transcription-1', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-transcription-1',
          file_name: 'test_audio.m4a',
          stage: 'completed',
          language: 'zh',
          duration_seconds: 120,
          created_at: new Date().toISOString()
        })
      })
    } else {
      await route.continue()
    }
  })

  // 频道一覧取得
  await page.route('**/api/admin/channels', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      })
    } else {
      await route.continue()
    }
  })

  // 転写のチャンネル取得
  await page.route('**/api/transcriptions/*/channels', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    })
  })
}
