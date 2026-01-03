/**
 * Transcription List E2E Tests
 *
 * Tests for transcription list with Jotai channel filter state management.
 * Tests real Jotai atoms: channelFilterAtom, transcriptionsAtom, etc.
 */

import { test, expect } from '@playwright/test'

test.describe('Transcription List', () => {
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

  test('転写一覧が正常にレンダリングされる', async ({ page }) => {
    // 転写一覧ページが表示されることを確認
    await expect(page.locator('h1:has-text("转录列表")')).toBeVisible()

    // モック転写が表示されることを確認
    await expect(page.locator('text=test_audio.m4a')).toBeVisible()
    await expect(page.locator('text=meeting.mp3')).toBeVisible()
  })

  test('チャンネルフィルターが表示される', async ({ page }) => {
    // フィルターセレクトボックスが表示されることを確認
    const filterSelect = page.locator('select[aria-label="频道筛选:"]')
    await expect(filterSelect).toBeVisible()

    // オプションが表示されることを確認
    await expect(page.locator('option:has-text("全部内容")')).toBeVisible()
    await expect(page.locator('option:has-text("个人内容")')).toBeVisible()
    await expect(page.locator('option:has-text("技术讨论")')).toBeVisible()
  })

  test('チャンネルフィルター - 全部内容を表示', async ({ page }) => {
    // 「全部内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'all')

    // すべての転写が表示されることを確認
    await expect(page.locator('text=test_audio.m4a')).toBeVisible()
    await expect(page.locator('text=meeting.mp3')).toBeVisible()
  })

  test('チャンネルフィルター - 個人内容をフィルタリング', async ({ page }) => {
    // 「个人内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'personal')

    // 個人転写のみが表示されることを確認
    await expect(page.locator('text=test_audio.m4a')).toBeVisible()
    await expect(page.locator('text=meeting.mp3')).not.toBeVisible()
  })

  test('チャンネルフィルター - 特定チャンネルをフィルタリング', async ({ page }) => {
    // 「技术讨论」チャンネルを選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'channel-1')

    // チャンネルに割り当てられた転写のみが表示されることを確認
    await expect(page.locator('text=meeting.mp3')).toBeVisible()
    await expect(page.locator('text=test_audio.m4a')).not.toBeVisible()
  })

  test('フィルター状態がページ遷移間で保持される', async ({ page }) => {
    // 「个人内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'personal')

    // 転写詳細ページに遷移
    await page.click('text=test_audio.m4a')
    await expect(page).toHaveURL(/\/transcriptions\//)

    // 一覧ページに戻る
    await page.goBack()
    await expect(page).toHaveURL(/\/transcriptions/)

    // フィルター状態が保持されていることを確認
    const filterSelect = page.locator('select[aria-label="频道筛选:"]')
    await expect(filterSelect).toHaveValue('personal')
  })

  test('フィルター解除ボタンでフィルターがクリアされる', async ({ page }) => {
    // 「个人内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'personal')

    // クリアボタンをクリック
    await page.click('button[aria-label="清除筛选"]')

    // フィルターがクリアされ、「全部内容」に戻ることを確認
    const filterSelect = page.locator('select[aria-label="频道筛选:"]')
    await expect(filterSelect).toHaveValue('all')
  })

  test('転写をクリックして詳細ページに遷移できる', async ({ page }) => {
    // 転写をクリック
    await page.click('text=test_audio.m4a')

    // 詳細ページに遷移したことを確認
    await expect(page).toHaveURL(/\/transcriptions\/trans-1/)
  })

  test('チャンネルバッジが表示される', async ({ page }) => {
    // チャンネルバッジが表示されることを確認
    await expect(page.locator('text=个人')).toBeVisible()
    await expect(page.locator('text=技术讨论')).toBeVisible()
  })

  test('ローディング状態が表示される', async ({ page }) => {
    // ローディング状態をモック
    await page.route('**/api/transcriptions', async route => {
      // 遅延レスポンスをシミュレート
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.continue()
    })

    await page.reload()

    // ローディングスピナーが表示されることを確認
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible()
  })

  test('空状態が表示される', async ({ page }) => {
    // 空のレスポンスをモック
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

    await page.reload()

    // 空状態メッセージが表示されることを確認
    await expect(page.locator('text=転写がありません')).toBeVisible()
  })

  test('ページネーションが機能する', async ({ page }) => {
    // 複数ページのモックデータを設定
    await page.route('**/api/transcriptions', async route => {
      if (route.request().method() === 'GET') {
        const url = route.request().url()
        const pageParam = new URL(url).searchParams.get('page')

        if (pageParam === '1') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              total: 25,
              page: 1,
              page_size: 10,
              total_pages: 3,
              data: Array(10).fill(null).map((_, i) => ({
                id: `trans-${i}`,
                file_name: `audio_${i}.m4a`,
                stage: 'completed',
                created_at: new Date().toISOString()
              }))
            })
          })
        } else if (pageParam === '2') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              total: 25,
              page: 2,
              page_size: 10,
              total_pages: 3,
              data: Array(10).fill(null).map((_, i) => ({
                id: `trans-${i + 10}`,
                file_name: `audio_${i + 10}.m4a`,
                stage: 'completed',
                created_at: new Date().toISOString()
              }))
            })
          })
        }
      } else {
        await route.continue()
      }
    })

    await page.reload()

    // 次のページボタンをクリック
    await page.click('button:has-text("次へ")')

    // 2ページ目のデータが表示されることを確認
    await expect(page.locator('text=audio_10.m4a')).toBeVisible()
  })

  test('検索機能が動作する', async ({ page }) => {
    // 検索ボックスに入力
    await page.fill('input[placeholder="搜索转录..."]', 'meeting')

    // 検索結果がフィルタリングされることを確認
    await expect(page.locator('text=meeting.mp3')).toBeVisible()
    await expect(page.locator('text=test_audio.m4a')).not.toBeVisible()
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
              created_at: new Date().toISOString(),
              channels: [],
              is_personal: true
            },
            {
              id: 'trans-2',
              file_name: 'meeting.mp3',
              stage: 'completed',
              language: 'zh',
              duration_seconds: 300,
              created_at: new Date().toISOString(),
              channels: [
                { id: 'channel-1', name: '技术讨论', description: '技术相关讨论' }
              ],
              is_personal: false
            }
          ]
        })
      })
    } else {
      await route.continue()
    }
  })

  // 転写のチャンネル取得
  await page.route('**/api/transcriptions/*/channels', async route => {
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
}
