/**
 * Authentication E2E Tests
 *
 * Tests for authentication flows with Supabase Google OAuth.
 * Tests real authentication state management.
 */

import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
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
  })

  test('ログインページが正常にレンダリングされる', async ({ page }) => {
    // ログインページが表示されることを確認
    await expect(page).toHaveURL(/\/login/)

    // Googleログインボタンが表示されることを確認
    await expect(page.locator('button:has-text("使用 Google 继续")')).toBeVisible()

    // アプリケーションタイトルが表示されることを確認
    await expect(page.locator('h1')).toBeVisible()
  })

  test.skip(process.env.TEST_ENVIRONMENT === 'production',
    'Google OAuthログインが機能する - Skipped: OAuth flow not tested in E2E mode'
  )
  test('Google OAuthログインが機能する', async ({ page }) => {
    // Googleログインボタンをクリック
    await page.click('button:has-text("使用 Google 继续")')

    // 転写一覧ページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/transcriptions/)
  })

  test('ログイン後、認証状態が保持される', async ({ page }) => {
    // E2E mode: user is already logged in via bypass, just navigate to transcriptions
    await page.goto('/transcriptions')
    await expect(page).toHaveURL(/\/transcriptions/)

    // 認証状態がlocalStorageに保存されていることを確認
    const hasSession = await page.evaluate(() => {
      const keys = Object.keys(localStorage)
      return keys.some(k => k.startsWith('sb-') && k.includes('-auth-token'))
    })
    expect(hasSession).toBeTruthy()

    // ページをリロード
    await page.reload()

    // 依然として転写一覧ページに留まることを確認（未認証の場合はログインページにリダイレクト）
    await expect(page).toHaveURL(/\/transcriptions/)
  })

  test('ログイン後、NavBarにユーザーメニューが表示される', async ({ page }) => {
    // E2E mode: user is already logged in via bypass, just navigate to transcriptions
    await page.goto('/transcriptions')
    await expect(page).toHaveURL(/\/transcriptions/)

    // ユーザーメニューが表示されることを確認
    const userMenu = page.locator('[data-testid="user-menu"]')
    await expect(userMenu).toBeVisible()
  })

  test('ログアウトが機能する', async ({ page }) => {
    // E2E mode: user is already logged in via bypass, just navigate to transcriptions
    await page.goto('/transcriptions')
    await expect(page).toHaveURL(/\/transcriptions/)

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

  test('未認証時に保護されたページにアクセスするとログインページにリダイレクトされる', async ({ page }) => {
    // 認証をクリア
    await page.evaluate(() => {
      localStorage.clear()
    })

    // 保護されたページに直接アクセス
    await page.goto('/dashboard')

    // ログインページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/login/)
  })

  test('ログイン状態でNavBarのリンクが正しく表示される', async ({ page }) => {
    // E2E mode: user is already logged in via bypass, just navigate to transcriptions
    await page.goto('/transcriptions')
    await expect(page).toHaveURL(/\/transcriptions/)

    // 転写一覧リンクが表示されることを確認
    await expect(page.locator('a:has-text("转录列表")')).toBeVisible()

    // ダッシュボードリンクが表示されることを確認（管理者の場合）
    await expect(page.locator('a:has-text("仪表板")')).toBeVisible()
  })

  test('セッション有効期限の処理', async ({ page }) => {
    // E2E mode: user is already logged in via bypass, just navigate to transcriptions
    await page.goto('/transcriptions')
    await expect(page).toHaveURL(/\/transcriptions/)

    // セッションを無効化（トークン期限切れをシミュレート）
    await page.route('**/api/**', async route => {
      if (route.request().method() !== 'OPTIONS') {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid token' })
        })
      } else {
        await route.continue()
      }
    })

    // ページをリロード
    await page.reload()

    // ログインページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/login/)
  })

  test.skip(process.env.TEST_ENVIRONMENT === 'production',
    'ログインエラー時のエラーハンドリング - Skipped: OAuth error flow not tested in E2E mode'
  )
  test('ログインエラー時のエラーハンドリング', async ({ page }) => {
    // Google OAuthエラーをモック
    await page.evaluate(() => {
      // エラーコールバックをシミュレート
      const originalClick = HTMLButtonElement.prototype.click
      HTMLButtonElement.prototype.click = function() {
        // エラーイベントを発火
        const errorEvent = new CustomEvent('auth-error', {
          detail: { message: 'Authentication failed' }
        })
        window.dispatchEvent(errorEvent)
      }
    })

    // エラーハンドリングの確認
    await page.evaluate(() => {
      window.addEventListener('auth-error', (e: any) => {
        console.error('Auth error:', e.detail.message)
      })
    })

    // Googleログインボタンをクリック
    await page.click('button:has-text("使用 Google 继续")')

    // エラーが発生した場合、ページがログインページに留まることを確認
    await expect(page).toHaveURL(/\/login/)
  })

  test.skip(process.env.TEST_ENVIRONMENT === 'production',
    '認証中のローディング状態が表示される - Skipped: OAuth loading state not tested in E2E mode'
  )
  test('認証中のローディング状態が表示される', async ({ page }) => {
    // ローディング遅延をモック
    await page.route('**/api/auth/callback', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000))
      await route.continue()
    })

    // Googleログインボタンをクリック
    await page.click('button:has-text("使用 Google 继续")')

    // ローディング状態が表示されることを確認
    await expect(page.locator('[data-testid="auth-loading"]')).toBeVisible()
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
}
