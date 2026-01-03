/**
 * Transcription Detail E2E Tests
 *
 * Tests for transcription detail page with Jotai state management.
 * Tests real Jotai atoms for detail page state, summary, edit mode.
 */

import { test, expect } from '@playwright/test'

test.describe('Transcription Detail', () => {
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

  test('転写詳細ページが正常にレンダリングされる', async ({ page }) => {
    // 転写詳細ページに遷移
    await page.goto('/transcriptions/trans-1')

    // ページタイトルが表示されることを確認
    await expect(page.locator('h1:has-text("test_audio.m4a")')).toBeVisible()

    // ファイル名が表示されることを確認
    await expect(page.locator('text=test_audio.m4a')).toBeVisible()
  })

  test('転写テキストが表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 転写テキストが表示されることを確認
    await expect(page.locator('[data-testid="transcription-text"]')).toBeVisible()
  })

  test('サマリーが表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // サマリーセクションが表示されることを確認
    await expect(page.locator('text=总结')).toBeVisible()

    // サマリーテキストが表示されることを確認
    await expect(page.locator('[data-testid="summary-text"]')).toBeVisible()
  })

  test('転写をダウンロードできる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // ダウンロードボタンをクリック
    const downloadPromise = page.waitForEvent('download')
    await page.click('button:has-text("下载")')
    const download = await downloadPromise

    // ダウンロードが開始されたことを確認
    expect(download.suggestedFilename()).toContain('test_audio')
  })

  test('チャンネルバッジが表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // チャンネルバッジが表示されることを確認
    await expect(page.locator('text=技术讨论')).toBeVisible()
  })

  test('チャンネル割り当てモーダルを開くことができる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // チャンネル割り当てボタンをクリック
    await page.click('button:has-text("分配频道")')

    // モーダルが表示されることを確認
    await expect(page.locator('text=分配频道')).toBeVisible()
  })

  test('編集モードを切り替えることができる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 編集ボタンをクリック
    await page.click('button:has-text("编辑")')

    // 編集モードが有効になることを確認
    await expect(page.locator('textarea[readonly]')).not.toBeVisible()

    // 保存ボタンが表示されることを確認
    await expect(page.locator('button:has-text("保存")')).toBeVisible()

    // キャンセルボタンが表示されることを確認
    await expect(page.locator('button:has-text("取消")')).toBeVisible()
  })

  test('編集内容を保存できる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 編集モードを開く
    await page.click('button:has-text("编辑")')

    // テキストを編集
    const textarea = page.locator('textarea:not([readonly])')
    await textarea.fill('Updated transcription text')

    // 保存ボタンをクリック
    await page.click('button:has-text("保存")')

    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=保存成功')).toBeVisible()

    // 編集モードが終了することを確認
    await expect(page.locator('textarea[readonly]')).toBeVisible()
  })

  test('編集をキャンセルできる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 編集モードを開く
    await page.click('button:has-text("编辑")')

    // テキストを編集
    const textarea = page.locator('textarea:not([readonly])')
    await textarea.fill('Changed text')

    // キャンセルボタンをクリック
    await page.click('button:has-text("取消")')

    // 編集モードが終了することを確認
    await expect(page.locator('textarea[readonly]')).toBeVisible()

    // 元のテキストが保持されていることを確認
    await expect(page.locator('text=这是测试转写文本')).toBeVisible()
  })

  test('転写を削除できる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 削除ボタンをクリック
    await page.click('button:has-text("删除")')

    // 確認ダイアログで「削除」をクリック
    await page.click('button:has-text("删除")')

    // 転写一覧ページにリダイレクトされることを確認
    await expect(page).toHaveURL(/\/transcriptions/)

    // 成功メッセージが表示されることを確認
    await expect(page.locator('text=転写が削除されました')).toBeVisible()
  })

  test('言語情報が表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 言語バッジが表示されることを確認
    await expect(page.locator('text=中文')).toBeVisible()
  })

  test('所要時間が表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 所要時間が表示されることを確認
    await expect(page.locator('text=2分0秒')).toBeVisible()
  })

  test('作成日時が表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // 作成日時が表示されることを確認
    await expect(page.locator('text=2024')).toBeVisible()
  })

  test('ローディング状態が表示される', async ({ page }) => {
    // 遅延レスポンスをモック
    await page.route('**/api/transcriptions/trans-1', async route => {
      if (route.request().method() === 'GET') {
        await new Promise(resolve => setTimeout(resolve, 1000))
        await route.continue()
      } else {
        await route.continue()
      }
    })

    await page.goto('/transcriptions/trans-1')

    // ローディングスピナーが表示されることを確認
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible()
  })

  test('エラー時にエラーメッセージが表示される', async ({ page }) => {
    // エラーレスポンスをモック
    await page.route('**/api/transcriptions/trans-1', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Transcription not found' })
        })
      } else {
        await route.continue()
      }
    })

    await page.goto('/transcriptions/trans-1')

    // エラーメッセージが表示されることを確認
    await expect(page.locator('text=転写が見つかりません')).toBeVisible()
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
          total: 1,
          page: 1,
          page_size: 10,
          total_pages: 1,
          data: [
            {
              id: 'trans-1',
              file_name: 'test_audio.m4a',
              stage: 'completed',
              language: 'zh',
              duration_seconds: 120,
              created_at: new Date().toISOString()
            }
          ]
        })
      })
    } else {
      await route.continue()
    }
  })

  // 転写詳細取得
  await page.route('**/api/transcriptions/trans-1', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'trans-1',
          file_name: 'test_audio.m4a',
          stage: 'completed',
          language: 'zh',
          duration_seconds: 120,
          text: '这是测试转写文本',
          summary: '这是测试总结',
          created_at: new Date().toISOString(),
          channels: [
            { id: 'channel-1', name: '技术讨论', description: '技术相关讨论' }
          ]
        })
      })
    } else if (route.request().method() === 'DELETE') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Transcription deleted' })
      })
    } else if (route.request().method() === 'PUT') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'trans-1',
          file_name: 'test_audio.m4a',
          text: 'Updated transcription text',
          summary: '这是测试总结'
        })
      })
    } else {
      await route.continue()
    }
  })

  // 転写のチャンネル取得
  await page.route('**/api/transcriptions/trans-1/channels', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'channel-1', name: '技术讨论', description: '技术相关讨论' }
        ])
      })
    } else if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Channels updated' })
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
