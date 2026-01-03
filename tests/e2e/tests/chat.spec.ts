/**
 * Chat Interface E2E Tests
 *
 * Tests for chat interface with Jotai state management.
 * Tests real Jotai atoms for messages, chat state, and real-time updates.
 */

import { test, expect } from '@playwright/test'

test.describe('Chat Interface', () => {
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

  test('チャットインターフェースが表示される', async ({ page }) => {
    // 転写詳細ページに遷移
    await page.goto('/transcriptions/trans-1')

    // チャットインターフェースが表示されることを確認
    await expect(page.locator('[data-testid="chat-interface"]')).toBeVisible()
  })

  test('メッセージ入力ボックスが表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージ入力ボックスが表示されることを確認
    const input = page.locator('textarea[placeholder*="输入消息"]')
    await expect(input).toBeVisible()
  })

  test('メッセージを送信できる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージを入力
    const input = page.locator('textarea[placeholder*="输入消息"]')
    await input.fill('この転写について説明してください')

    // 送信ボタンをクリック
    await page.click('button:has-text("发送")')

    // メッセージが送信されたことを確認（ローディング表示）
    await expect(page.locator('[data-testid="message-loading"]')).toBeVisible()
  })

  test('送信したメッセージが表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージを入力して送信
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('テストメッセージ')
    await page.click('button:has-text("发送")')

    // 送信したメッセージが表示されることを確認
    await expect(page.locator('text=テストメッセージ')).toBeVisible()
  })

  test('AIの返信が表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージを送信
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('この転写の要点は何ですか？')
    await page.click('button:has-text("发送")')

    // AIの返信が表示されることを確認
    await expect(page.locator('[data-testid="ai-message"]')).toBeVisible()
  })

  test('チャット履歴が保持される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージを送信
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('最初のメッセージ')
    await page.click('button:has-text("发送")')

    // ページをリロード
    await page.reload()

    // チャット履歴が保持されていることを確認
    await expect(page.locator('text=最初のメッセージ')).toBeVisible()
  })

  test('チャットをクリアできる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージを送信
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('クリアされるメッセージ')
    await page.click('button:has-text("发送")')
    await expect(page.locator('text=クリアされるメッセージ')).toBeVisible()

    // クリアボタンをクリック
    await page.click('button:has-text("清空")')

    // 確認ダイアログで「クリア」をクリック
    await page.click('button:has-text("清空")')

    // チャット履歴がクリアされていることを確認
    await expect(page.locator('text=クリアされるメッセージ')).not.toBeVisible()
  })

  test('メッセージストリーミングが機能する', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // ストリーミングレスポンスをモック
    await page.route('**/api/chat/**', async route => {
      if (route.request().method() === 'POST') {
        // ストリーミングレスポンスをシミュレート
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: `data: {"content": "これは", "done": false}\n\ndata: {"content": "ストリーミング", "done": false}\n\ndata: {"content": "レスポンス", "done": true}\n\n`
        })
      } else {
        await route.continue()
      }
    })

    // メッセージを送信
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('ストリーミングテスト')
    await page.click('button:has-text("发送")')

    // ストリーミングでテキストが順次表示されることを確認
    await expect(page.locator('text=これは')).toBeVisible()
  })

  test('チャット状態が転写間で独立している', async ({ page }) => {
    // 最初の転写でチャット
    await page.goto('/transcriptions/trans-1')
    const input1 = page.locator('textarea[placeholder*="入消息"]')
    await input1.fill('転写1のメッセージ')
    await page.click('button:has-text("发送")')

    // 別の転写に遷移
    await page.goto('/transcriptions/trans-2')

    // 転写1のメッセージが表示されないことを確認
    await expect(page.locator('text=転写1のメッセージ')).not.toBeVisible()

    // 転写2でメッセージを送信
    const input2 = page.locator('textarea[placeholder*="入消息"]')
    await input2.fill('転写2のメッセージ')
    await page.click('button:has-text("发送")')
    await expect(page.locator('text=転写2のメッセージ')).toBeVisible()

    // 転写1に戻る
    await page.goto('/transcriptions/trans-1')

    // 転写1のメッセージが表示されることを確認
    await expect(page.locator('text=転写1のメッセージ')).toBeVisible()

    // 転写2のメッセージが表示されないことを確認
    await expect(page.locator('text=転写2のメッセージ')).not.toBeVisible()
  })

  test('エラー時にエラーメッセージが表示される', async ({ page }) => {
    // エラーレスポンスをモック
    await page.route('**/api/chat/**', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' })
        })
      } else {
        await route.continue()
      }
    })

    await page.goto('/transcriptions/trans-1')

    // メッセージを送信
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('エラーテスト')
    await page.click('button:has-text("发送")')

    // エラーメッセージが表示されることを確認
    await expect(page.locator('text=エラーが発生しました')).toBeVisible()
  })

  test('送信中は送信ボタンが無効になる', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージを入力
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('テストメッセージ')

    // 送信ボタンをクリック
    const sendButton = page.locator('button:has-text("发送")')
    await sendButton.click()

    // 送信ボタンが無効になることを確認
    await expect(sendButton).toBeDisabled()
  })

  test('ローディング中はスピナーが表示される', async ({ page }) => {
    await page.goto('/transcriptions/trans-1')

    // メッセージを送信
    const input = page.locator('textarea[placeholder*="入消息"]')
    await input.fill('ローディングテスト')
    await page.click('button:has-text("发送")')

    // ローディングスピナーが表示されることを確認
    await expect(page.locator('[data-testid="chat-loading"]')).toBeVisible()
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
          total: 2,
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
            },
            {
              id: 'trans-2',
              file_name: 'meeting.mp3',
              stage: 'completed',
              language: 'zh',
              duration_seconds: 300,
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
  await page.route('**/api/transcriptions/trans-*', async route => {
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
          text: 'これはテスト転写テキストです',
          summary: 'テスト总结',
          created_at: new Date().toISOString()
        })
      })
    } else {
      await route.continue()
    }
  })

  // チャットAPI
  await page.route('**/api/chat/**', async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'これはAIの返信メッセージです',
          role: 'assistant'
        })
      })
    } else if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages: [
            { role: 'user', content: 'テストメッセージ' },
            { role: 'assistant', content: 'AIの返信' }
          ]
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
