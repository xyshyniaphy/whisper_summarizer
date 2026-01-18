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

    // E2E mode: user is already logged in via bypass, just navigate to transcriptions
    await page.goto('/transcriptions')
    await expect(page).toHaveURL(/\/transcriptions/)
  })

  test('ユーザーメニューが表示される', async ({ page }) => {
    // ユーザーメニューが表示されることを確認
    const userMenu = page.locator('[data-testid="user-menu"]')
    await expect(userMenu).toBeVisible({ timeout: 10000 })
  })

  test('ユーザーメニューを開くことができる', async ({ page }) => {
    // ユーザーメニューをクリック
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // メニュードロップダウンが表示されることを確認
    const dropdown = page.locator('[data-testid="user-menu-dropdown"]')
    await expect(dropdown).toBeVisible({ timeout: 10000 })
  })

  test('ユーザーメニューを閉じることができる', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()
    await expect(page.locator('[data-testid="user-menu-dropdown"]')).toBeVisible({ timeout: 10000 })

    // 外部をクリックして閉じる
    await page.click('body', { position: { x: 0, y: 0 } })

    // メニュードロップダウンが非表示になることを確認
    const dropdown = page.locator('[data-testid="user-menu-dropdown"]')
    await expect(dropdown).not.toBeVisible({ timeout: 10000 })
  })

  test('ユーザーメニューにユーザー情報が表示される', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // ユーザー情報が表示されることを確認
    await expect(page.locator('text=test@example.com')).toBeVisible({ timeout: 10000 })
  })

  test('ユーザーメニューからダッシュボードに遷移できる', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // ダッシュボードリンクをクリック
    await page.click('a:has-text("仪表板")')

    // ダッシュボードページに遷移したことを確認
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
  })

  test('ユーザーメニューから転写一覧に遷移できる', async ({ page }) => {
    // ダッシュボードから開始
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // 転写一覧リンクをクリック
    await page.click('a:has-text("转录列表")')

    // 転写一覧ページに遷移したことを確認
    await expect(page).toHaveURL(/\/transcriptions/, { timeout: 10000 })
  })

  test('ログアウトが機能する', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // サインアウトボタンをクリック
    await page.click('button:has-text("退出")')

    // ログインページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })

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
    await expect(page.locator('[data-testid="user-menu-dropdown"]')).toBeVisible({ timeout: 10000 })

    // 転写詳細ページに遷移
    await page.goto('/transcriptions/test-transcription-1')
    await page.waitForLoadState('networkidle') // Wait for API calls

    // ユーザーメニューが閉じていることを確認
    const dropdown = page.locator('[data-testid="user-menu-dropdown"]')
    await expect(dropdown).not.toBeVisible({ timeout: 10000 })
  })

  test('管理者の場合、ダッシュボードリンクが表示される', async ({ page }) => {
    // ユーザーメニューを開く
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.click()

    // ダッシュボードリンクが表示されることを確認
    await expect(page.locator('a:has-text("仪表板")')).toBeVisible({ timeout: 10000 })
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
    await expect(page.locator('a:has-text("仪表板")')).not.toBeVisible({ timeout: 10000 })
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
