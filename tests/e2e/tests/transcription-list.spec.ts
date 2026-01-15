/**
 * Transcription List E2E Tests
 *
 * Tests for transcription list with Jotai channel filter state management.
 * Tests real Jotai atoms: channelFilterAtom, transcriptionsAtom, etc.
 *
 * Uses production test data for realistic testing scenarios.
 */

import { test, expect } from '@playwright/test'
import { setupProductionTranscription, cleanupProductionTranscription } from '../helpers/production-data'

test.describe('Transcription List', () => {
  let transcriptionId: string | undefined

  test.beforeEach(async ({ page }) => {
    // Setup production test data (singleton pattern - only fetches once)
    transcriptionId = await setupProductionTranscription(page)

    // Validate transcriptionId is initialized
    if (!transcriptionId) {
      throw new Error('transcriptionId not initialized - run first test to setup production data')
    }

    // E2Eテストモードフラグを設定
    await page.goto('/login')
    await page.evaluate(() => {
      localStorage.setItem('e2e-test-mode', 'true')
    })
    await page.reload()

    // Note: Server-side auth bypass handles authentication automatically
    // Tests will navigate to /transcriptions as needed
  })

  test.afterAll(async () => {
    // Cleanup (no-op for existing transcriptions)
    await cleanupProductionTranscription()
  })

  test('転写一覧が正常にレンダリングされる', async ({ page }) => {
    // Navigate to transcriptions page (auth bypass is active)
    await page.goto('/transcriptions', { waitUntil: 'domcontentloaded' })

    // Wait a bit for auth and data to load
    await page.waitForTimeout(2000)

    // 転写一覧ページが表示されることを確認（check for any content)
    const content = await page.textContent('body')
    expect(content).toContain('转录')

    // Check that we have some page content loaded
    await expect(page.locator('body')).not.toHaveText(/登录/)
  })

  test('チャンネルフィルターが表示される', async ({ page }) => {
    await page.goto('/transcriptions')

    // フィルターセレクトボックスが表示されることを確認
    const filterSelect = page.locator('select[aria-label="频道筛选:"]')
    await expect(filterSelect).toBeVisible()

    // オプションが表示されることを確認
    await expect(page.locator('option:has-text("全部内容")')).toBeVisible()
    await expect(page.locator('option:has-text("个人内容")')).toBeVisible()
  })

  test('チャンネルフィルター - 全部内容を表示', async ({ page }) => {
    await page.goto('/transcriptions')

    // 「全部内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'all')

    // すべての転写が表示されることを確認（real data from API）
    await expect(page.locator(`text=audio1074124412.conved_20_min.m4a`)).toBeVisible()
  })

  test('チャンネルフィルター - 個人内容をフィルタリング', async ({ page }) => {
    await page.goto('/transcriptions')

    // 「个人内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'personal')

    // 個人転写のみが表示されることを確認（production data is personal）
    await expect(page.locator(`text=audio1074124412.conved_20_min.m4a`)).toBeVisible()
  })

  test('フィルター状態がページ遷移間で保持される', async ({ page }) => {
    await page.goto('/transcriptions')

    // 「个人内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'personal')

    // 転写詳細ページに遷移
    await page.click(`text=audio1074124412.conved_20_min.m4a`)
    await expect(page).toHaveURL(new RegExp(`/transcriptions/${transcriptionId}`))

    // 一覧ページに戻る
    await page.goBack()
    await expect(page).toHaveURL(/\/transcriptions/)

    // フィルター状態が保持されていることを確認
    const filterSelect = page.locator('select[aria-label="频道筛选:"]')
    await expect(filterSelect).toHaveValue('personal')
  })

  test('フィルター解除ボタンでフィルターがクリアされる', async ({ page }) => {
    await page.goto('/transcriptions')

    // 「个人内容」を選択
    await page.selectOption('select[aria-label="频道筛选:"]', 'personal')

    // クリアボタンをクリック
    await page.click('button[aria-label="清除筛选"]')

    // フィルターがクリアされ、「全部内容」に戻ることを確認
    const filterSelect = page.locator('select[aria-label="频道筛选:"]')
    await expect(filterSelect).toHaveValue('all')
  })

  test('転写をクリックして詳細ページに遷移できる', async ({ page }) => {
    await page.goto('/transcriptions')

    // 転写をクリック
    await page.click(`text=audio1074124412.conved_20_min.m4a`)

    // 詳細ページに遷移したことを確認（real transcriptionId）
    await expect(page).toHaveURL(new RegExp(`/transcriptions/${transcriptionId}`))
  })

  test('ローディング状態が表示される', async ({ page }) => {
    // NOTE: Mock kept to test loading UI state (hard to test with real API due to fast response)
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
    // NOTE: Mock kept to test empty state UI (edge case, hard to reproduce with real data)
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
    // NOTE: Mock kept to test pagination UI (edge case, requires 25+ items for real test)
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
    // 検索ボックスに入力（real production data search）
    await page.fill('input[placeholder="搜索转录..."]', '210min')

    // 検索結果がフィルタリングされることを確認（real data）
    await expect(page.locator('text=audio1074124412.conved_20_min.m4a')).toBeVisible()
  })
})
