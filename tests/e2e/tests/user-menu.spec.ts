/**
 * User Menu E2E Tests
 *
 * Tests for user menu state management with Jotai.
 * Tests real Jotai atoms for menu open/close state.
 */

import { test, expect } from '@playwright/test'

test.describe('User Menu', () => {
  test.beforeEach(async ({ page }) => {
    // E2Eテストモードフラグを設定
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.setItem('e2e-test-mode', 'true')
    })
    await page.reload()

    // APIルートのモック設定
    await setupMockRoutes(page)

    // E2EテストモードでGoogle OAuthログインをモック
    await page.click('button:has-text("使用 Google 继续")')
    await expect(page).toHaveURL(/\/transcriptions/)
  })

  test('ユーザーメニューが表示される', async ({ page }) => {
    // ユーザーメニューが表示されることを確認
    const userMenu = page.locator('[data-testid="user-menu"]')
    await expect(userMenu).toBeVisible()
  })

  test('ユーザーメニューを開くことができる', async ({ page }) => {
    // ユーザーメニューをクリック
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // メニュードロップダウンが表示されることを確認
    const dropdown = page.locator('[data-testid="user-menu-dropdown"]')
    await expect(dropdown).toBeVisible()
  })

  test('ユーザーメニューを閉じることができる', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()
    await expect(page.locator('[data-testid="user-menu-dropdown"]')).toBeVisible()

    // 外部をクリックして閉じる
    await page.click('body', { position: { x: 0, y: 0 } })

    // メニュードロップダウンが非表示になることを確認
    const dropdown = page.locator('[data-testid="user-menu-dropdown"]')
    await expect(dropdown).not.toBeVisible()
  })

  test('ユーザーメニューにユーザー情報が表示される', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // ユーザー情報が表示されることを確認
    await expect(page.locator('text=test@example.com')).toBeVisible()
  })

  test('ユーザーメニューからダッシュボードに遷移できる', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // ダッシュボードリンクをクリック
    await page.click('a:has-text("仪表板")')

    // ダッシュボードページに遷移したことを確認
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('ユーザーメニューから転写一覧に遷移できる', async ({ page }) => {
    // ダッシュボードから開始
    await page.goto('/dashboard')

    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // 転写一覧リンクをクリック
    await page.click('a:has-text("转录列表")')

    // 転写一覧ページに遷移したことを確認
    await expect(page).toHaveURL(/\/transcriptions/)
  })

  test('ログアウトが機能する', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // サインアウトボタンをクリック
    await page.click('button:has-text("退出")')

    // ログインページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/login/)

    // 認証状態がクリアされていることを確認
    const hasSession = await page.evaluate(() => {
      const keys = Object.keys(localStorage)
      return keys.some(k => k.startsWith('sb-') && k.includes('-auth-token'))
    })
    expect(hasSession).toBeFalsy()
  })

  test('ユーザーメニュー状態がページ遷移間でリセットされる', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()
    await expect(page.locator('[data-testid="user-menu-dropdown"]')).toBeVisible()

    // 転写詳細ページに遷移
    await page.goto('/transcriptions/test-transcription-1')

    // ユーザーメニューが閉じていることを確認
    const dropdown = page.locator('[data-testid="user-menu-dropdown"]')
    await expect(dropdown).not.toBeVisible()
  })

  test('管理者の場合、ダッシュボードリンクが表示される', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // ダッシュボードリンクが表示されることを確認
    await expect(page.locator('a:has-text("仪表板")')).toBeVisible()
  })

  test('非管理者の場合、ダッシュボードリンクが表示されない', async ({ page }) => {
    // 非管理者ユーザーをモック
    await page.route('**/api/auth/user', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-1',
          email: 'test@example.com',
          is_active: true,
          is_admin: false
        })
      })
    })

    await page.reload()

    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // ダッシュボードリンクが表示されないことを確認
    await expect(page.locator('a:has-text("仪表板")')).not.toBeVisible()
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

  // ユーザー情報取得
  await page.route('**/api/auth/user', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'user-1',
        email: 'test@example.com',
        is_active: true,
        is_admin: true
      })
    })
  })

  // 频道一覧取得
  await page.route('**/api/admin/channels', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    })
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

  // 転写のチャンネル取得
  await page.route('**/api/transcriptions/*/channels', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    })
  })
}
