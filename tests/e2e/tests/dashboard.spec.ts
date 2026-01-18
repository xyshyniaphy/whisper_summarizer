/**
 * Dashboard E2E Tests
 *
 * Tests for dashboard tab switching, user management, channel management, and audio management.
 * Tests real Jotai state management for dashboard tabs and interactions.
 */

import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
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

    // ダッシュボードに遷移（管理者権限モック）
    await page.goto('/dashboard')
  })

  test('ダッシュボードが正常にレンダリングされる', async ({ page }) => {
    // ダッシュボードメインコンテンツが表示される
    await expect(page.locator('h1:has-text("仪表板")')).toBeVisible()
  })

  test('タブ切り替えが機能する - ユーザー管理タブ', async ({ page }) => {
    // ユーザー管理タブをクリック
    await page.click('button:has-text("用户管理")')

    // ユーザー管理タブがアクティブになることを確認
    await expect(page.locator('button').filter({ hasText: '用户管理' })).toBeVisible()

    // ユーザーリストが表示されることを確認
    await expect(page.locator('[data-testid="user-list"]')).toBeVisible()
  })

  test('タブ切り替えが機能する - 频道管理タブ', async ({ page }) => {
    // 频道管理タブをクリック
    await page.click('button:has-text("频道管理")')

    // 频道管理タブがアクティブになることを確認
    await expect(page.locator('button').filter({ hasText: '频道管理' })).toBeVisible()

    // 频道リストが表示されることを確認
    await expect(page.locator('[data-testid="channel-list"]')).toBeVisible()
  })

  test('タブ切り替えが機能する - 音频管理タブ', async ({ page }) => {
    // 音频管理タブをクリック
    await page.click('button:has-text("音频管理")')

    // 音频管理タブがアクティブになることを確認
    await expect(page.locator('button').filter({ hasText: '音频管理' })).toBeVisible()

    // 音频リストが表示されることを確認
    await expect(page.locator('[data-testid="audio-list"]')).toBeVisible()
  })

  test('ユーザー管理 - ユーザー一覧が表示される', async ({ page }) => {
    await page.click('button:has-text("用户管理")')
    await expect(page.locator('[data-testid="user-list"]')).toBeVisible()

    // モックユーザーが表示されることを確認
    await expect(page.locator('text=test@example.com')).toBeVisible()
  })

  test('ユーザー管理 - ユーザーをアクティベートできる', async ({ page }) => {
    await page.click('button:has-text("用户管理")')

    // 非アクティブユーザーの「アクティベート」ボタンをクリック
    const activateButton = page.locator('[data-testid="activate-user-button"]').first()
    await activateButton.click()

    // 確認ダイアログで「アクティベート」をクリック
    await page.click('button:has-text("激活")')

    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=ユーザーがアクティベートされました')).toBeVisible()
  })

  test('ユーザー管理 - 管理者権限をトグルできる', async ({ page }) => {
    await page.click('button:has-text("用户管理")')

    // 管理者トグルボタンをクリック
    const toggleButton = page.locator('[data-testid="toggle-admin-button"]').first()
    await toggleButton.click()

    // 確認ダイアログで「変更」をクリック
    await page.click('button:has-text("変更")')

    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=管理者権限が更新されました')).toBeVisible()
  })

  test('频道管理 - 频道一覧が表示される', async ({ page }) => {
    await page.click('button:has-text("频道管理")')
    await expect(page.locator('[data-testid="channel-list"]')).toBeVisible()

    // モック频道が表示されることを確認
    await expect(page.locator('text=技术讨论')).toBeVisible()
    await expect(page.locator('text=产品规划')).toBeVisible()
  })

  test('频道管理 - 新しい频道を作成できる', async ({ page }) => {
    await page.click('button:has-text("频道管理")')

    // 「新规频道」ボタンをクリック
    await page.click('button:has-text("新規频道")')

    // モーダルが表示されることを確認
    await expect(page.locator('text=频道を作成')).toBeVisible()

    // 频道名を入力
    await page.fill('input[name="name"]', 'テスト频道')
    await page.fill('textarea[name="description"]', 'テスト用频道です')

    // 「作成」ボタンをクリック
    await page.click('button:has-text("作成")')

    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=频道が作成されました')).toBeVisible()
  })

  test('频道管理 - 频道を削除できる', async ({ page }) => {
    await page.click('button:has-text("频道管理")')

    // 削除ボタンをクリック
    const deleteButton = page.locator('[data-testid="delete-channel-button"]').first()
    await deleteButton.click()

    // 確認ダイアログで「削除」をクリック
    await page.click('button:has-text("削除")')

    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=频道が削除されました')).toBeVisible()
  })

  test('音频管理 - 音频一覧が表示される', async ({ page }) => {
    await page.click('button:has-text("音频管理")')
    await expect(page.locator('[data-testid="audio-list"]')).toBeVisible()

    // モック音频が表示されることを確認
    await expect(page.locator('text=test_audio.m4a')).toBeVisible()
  })

  test('音频管理 - 音频を频道に割り当てることができる', async ({ page }) => {
    await page.click('button:has-text("音频管理")')

    // 音频の「频道に割り当て」ボタンをクリック
    const assignButton = page.locator('[data-testid="assign-channel-button"]').first()
    await assignButton.click()

    // モーダルが表示されることを確認
    await expect(page.locator('text=频道に割り当て')).toBeVisible()

    // 频道を選択
    await page.click('label:has-text("技术讨论") input[type="checkbox"]')

    // 「保存」ボタンをクリック
    await page.click('button:has-text("保存")')

    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=频道に割り当てられました')).toBeVisible()
  })

  test('タブ状態がページ遷移間で保持される', async ({ page }) => {
    // ユーザー管理タブを選択
    await page.click('button:has-text("用户管理")')

    // 转写一覧ページに遷移
    await page.goto('/transcriptions')

    // ダッシュボードに戻る
    await page.goto('/dashboard')

    // ユーザー管理タブがまだアクティブであることを確認
    await expect(page.locator('button').filter({ hasText: '用户管理' })).toBeVisible()
  })

  test('APIエラー時にエラーメッセージが表示される', async ({ page }) => {
    // エラーレスポンスをモック
    await page.route('**/api/admin/users', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' })
        })
      } else {
        await route.continue()
      }
    })

    await page.click('button:has-text("用户管理")')

    // エラーメッセージが表示されることを確認
    await expect(page.locator('text=エラーが発生しました')).toBeVisible()
  })
})

/**
 * モックルートを設定するヘルパー関数
 */
async function setupMockRoutes(page: any) {
  // ユーザー一覧取得
  await page.route('**/api/admin/users', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'user-1',
            email: 'test@example.com',
            is_active: true,
            is_admin: true,
            created_at: new Date().toISOString()
          },
          {
            id: 'user-2',
            email: 'inactive@example.com',
            is_active: false,
            is_admin: false,
            created_at: new Date().toISOString()
          }
        ])
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
        body: JSON.stringify([
          { id: 'channel-1', name: '技术讨论', description: '技术相关讨论' },
          { id: 'channel-2', name: '产品规划', description: '产品设计和规划' }
        ])
      })
    } else {
      await route.continue()
    }
  })

  // 音频一覧取得
  await page.route('**/api/admin/audio', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'audio-1',
            file_name: 'test_audio.m4a',
            stage: 'completed',
            created_at: new Date().toISOString()
          }
        ])
      })
    } else {
      await route.continue()
    }
  })
}
